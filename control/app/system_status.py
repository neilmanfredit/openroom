from pathlib import Path

# The udev rule in roles/av only creates this symlink when the configured
# camera's vendor/product ID is actually present (see
# ansible/roles/av/templates/70-openroom-camera.rules.j2).
CAMERA_DEVICE_PATH = Path("/dev/openroom-camera")

# Kernel-level ALSA card registration — readable regardless of which user
# owns the PipeWire session, unlike querying wpctl/PipeWire directly
# (the control service runs as its own user, not the kiosk user whose
# session owns the audio server).
ALSA_CARDS_PATH = Path("/proc/asound/cards")


def camera_present() -> bool:
    return CAMERA_DEVICE_PATH.exists()


def audio_present() -> bool:
    try:
        return bool(ALSA_CARDS_PATH.read_text().strip())
    except OSError:
        return False
