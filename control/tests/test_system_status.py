from app import system_status


def test_camera_present_true_when_symlink_exists(tmp_path, monkeypatch):
    fake = tmp_path / "openroom-camera"
    fake.write_text("")
    monkeypatch.setattr(system_status, "CAMERA_DEVICE_PATH", fake)
    assert system_status.camera_present() is True


def test_camera_present_false_when_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(system_status, "CAMERA_DEVICE_PATH", tmp_path / "missing")
    assert system_status.camera_present() is False


def test_audio_present_true_when_cards_listed(tmp_path, monkeypatch):
    fake = tmp_path / "cards"
    fake.write_text(" 0 [PCH]: HDA-Intel - HDA Intel PCH\n")
    monkeypatch.setattr(system_status, "ALSA_CARDS_PATH", fake)
    assert system_status.audio_present() is True


def test_audio_present_false_when_empty(tmp_path, monkeypatch):
    fake = tmp_path / "cards"
    fake.write_text("")
    monkeypatch.setattr(system_status, "ALSA_CARDS_PATH", fake)
    assert system_status.audio_present() is False


def test_audio_present_false_when_file_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(system_status, "ALSA_CARDS_PATH", tmp_path / "missing")
    assert system_status.audio_present() is False
