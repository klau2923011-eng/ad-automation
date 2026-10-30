from pathlib import Path

from fastapi.testclient import TestClient

from ad_automation.app import create_app
from ad_automation.config import Settings
from ad_automation.config import find_media_binary


def test_data_directory_can_be_overridden_by_environment(monkeypatch, tmp_path):
    configured_dir = tmp_path / "ad-data"
    monkeypatch.setenv("AD_AUTOMATION_DATA_DIR", str(configured_dir))

    settings = Settings.from_env()

    assert settings.data_dir == configured_dir
    assert configured_dir.is_dir()


def test_health_reports_database_and_ffmpeg_availability(tmp_path):
    settings = Settings(data_dir=tmp_path)
    expected_ffmpeg = bool(settings.ffmpeg_path and settings.ffprobe_path)
    app = create_app(settings)

    with TestClient(app) as client:
        response = client.get("/api/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["ready"] is True
    assert payload["database"] == "ok"
    assert payload["ffmpeg"] is expected_ffmpeg
    assert (tmp_path / "ad_automation.sqlite3").is_file()


def test_discovers_ffmpeg_from_winget_install_directory(monkeypatch, tmp_path):
    binary = tmp_path / "Microsoft" / "WinGet" / "Packages" / "Gyan.FFmpeg.Shared_pkg" / "ffmpeg-build" / "bin" / "ffprobe.exe"
    binary.parent.mkdir(parents=True)
    binary.write_bytes(b"test")
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    monkeypatch.setattr("ad_automation.config.shutil.which", lambda _: None)

    assert find_media_binary("ffprobe") == str(binary)


def test_settings_reads_spi_secret_from_environment(tmp_path, monkeypatch):
    monkeypatch.setenv("AD_AUTOMATION_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("AD_AUTOMATION_SPI_SECRET", "test-secret")

    settings = Settings.from_env()

    assert settings.spi_secret == "test-secret"
