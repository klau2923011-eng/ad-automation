from ad_automation.config import Settings
from ad_automation.demo import create_demo_video
from ad_automation.media.probe import probe_video


def test_demo_video_is_generated_as_a_playable_local_asset(tmp_path):
    settings = Settings(data_dir=tmp_path)

    video_path = create_demo_video(settings)

    assert video_path.is_file()
    assert video_path.parent == tmp_path / "demo"
    metadata = probe_video(video_path, settings.ffprobe_path)
    assert metadata["duration_seconds"] > 0
    assert metadata["width"] == 720
    assert metadata["height"] == 1280
