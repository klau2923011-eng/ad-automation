from __future__ import annotations

import subprocess
from pathlib import Path


PRESETS = {"ultrafast", "superfast", "veryfast", "faster", "fast", "medium", "slow", "slower", "veryslow"}


def _encode_args(params: dict) -> list[str]:
    crf = int(params.get("crf", 23))
    preset = params.get("preset", "veryfast")
    width = params.get("width")
    height = params.get("height")
    if not 0 <= crf <= 51 or preset not in PRESETS:
        raise ValueError("编码参数无效")
    args = ["-c:v", "libx264", "-crf", str(crf), "-preset", preset, "-pix_fmt", "yuv420p", "-c:a", "aac", "-movflags", "+faststart"]
    if width or height:
        w = int(width or -2)
        h = int(height or -2)
        if w < -2 or h < -2 or (w > 0 and w % 2) or (h > 0 and h % 2):
            raise ValueError("输出宽高必须为正偶数")
        args.extend(["-vf", f"scale={w}:{h}"])
    return args


def _number(value: object, name: str) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} 必须为数字") from exc
    if result < 0:
        raise ValueError(f"{name} 不能为负数")
    return result


def _run(args: list[str], output: Path) -> Path:
    result = subprocess.run(args, capture_output=True, text=True, timeout=600, check=False)
    if result.returncode:
        raise ValueError((result.stderr or "FFmpeg 处理失败")[-1500:])
    if not output.is_file() or output.stat().st_size == 0:
        raise ValueError("FFmpeg 未生成有效输出文件")
    return output


def process_step(input_path: Path, output_path: Path, kind: str, params: dict, ffmpeg: str, ffprobe: str) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    encode_args = _encode_args(params)
    if kind == "trim":
        start = _number(params.get("start", 0), "start")
        end = _number(params.get("end"), "end")
        if end <= start:
            raise ValueError("end 必须大于 start")
        return _run([ffmpeg, "-y", "-ss", str(start), "-i", str(input_path), "-t", str(end - start), *encode_args, str(output_path)], output_path)
    if kind == "concat":
        segments = params.get("segments")
        if not isinstance(segments, list) or len(segments) < 2:
            raise ValueError("concat 至少需要两个片段")
        filters: list[str] = []
        labels: list[str] = []
        has_audio = subprocess.run(
            [ffprobe, "-v", "error", "-select_streams", "a", "-show_entries", "stream=index", "-of", "csv=p=0", str(input_path)],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        ).stdout.strip() != ""
        args = [ffmpeg, "-y"]
        for index, segment in enumerate(segments):
            start = _number(segment.get("start"), "segment.start")
            end = _number(segment.get("end"), "segment.end")
            if end <= start:
                raise ValueError("片段 end 必须大于 start")
            args.extend(["-i", str(input_path)])
            filters.append(f"[{index}:v]trim=start={start}:end={end},setpts=PTS-STARTPTS[v{index}]")
            labels.append(f"[v{index}]")
            if has_audio:
                filters.append(f"[{index}:a]atrim=start={start}:end={end},asetpts=PTS-STARTPTS[a{index}]")
                labels.append(f"[a{index}]")
        filters.append(f"{''.join(labels)}concat=n={len(segments)}:v=1:a={1 if has_audio else 0}[vout]" + ("[aout]" if has_audio else ""))
        args.extend(["-filter_complex", ";".join(filters), "-map", "[vout]"])
        if has_audio:
            args.extend(["-map", "[aout]"])
        return _run([*args, *encode_args, str(output_path)], output_path)
    if kind == "enhance":
        vf = "eq=contrast=1.05:saturation=1.04,unsharp=5:5:0.5:3:3:0.0"
        return _run([ffmpeg, "-y", "-i", str(input_path), "-vf", vf, *encode_args, str(output_path)], output_path)
    if kind == "overlay":
        text = str(params.get("text", "")).strip()
        if not text or len(text) > 120:
            raise ValueError("角标文字长度必须为 1 到 120 个字符")
        text_path = output_path.with_suffix(".txt")
        text_path.write_text(text, encoding="utf-8")
        escaped = str(text_path.resolve()).replace("\\", "/").replace(":", r"\:").replace("'", r"\'")
        font = params.get("fontFile", r"C:\Windows\Fonts\arial.ttf")
        font_escaped = str(font).replace("\\", "/").replace(":", r"\:").replace("'", r"\'")
        vf = f"drawtext=fontfile='{font_escaped}':textfile='{escaped}':x=w-tw-20:y=h-th-20:fontsize=24:fontcolor=white:box=1:boxcolor=black@0.45"
        return _run([ffmpeg, "-y", "-i", str(input_path), "-vf", vf, *encode_args, str(output_path)], output_path)
    if kind == "encode":
        return _run([ffmpeg, "-y", "-i", str(input_path), *encode_args, str(output_path)], output_path)
    raise ValueError(f"不支持的处理步骤: {kind}")
