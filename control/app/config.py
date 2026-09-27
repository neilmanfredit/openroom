from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="OPENROOM_")

    room_name: str = "Meeting Room"

    home_url: str = "http://127.0.0.1:8080/"
    external_base_url: str = "http://127.0.0.1:8080"
    join_by_id_url: str = "https://teams.microsoft.com/meet"

    cdp_host: str = "127.0.0.1"
    cdp_port: int = 9222

    # Where the control role packs the Leave & Home extension.
    extension_crx_path: str = "/opt/openroom/extension/src.crx"
    extension_id_path: str = "/opt/openroom/extension/id.txt"
    extension_version: str = "1.0.0"

    # --- Calendar (Milestone 4) ---
    # Left blank by default: calendar polling stays disabled (rather than
    # crashing) until the room's app registration exists — see
    # docs/M365-SETUP.md. Certificate PEM contents are read from these
    # paths at runtime, never held directly in a setting/env var, and
    # deployed to the device via Ansible Vault (never committed).
    graph_tenant_id: str = ""
    graph_client_id: str = ""
    graph_cert_path: str = "/etc/openroom/graph/cert.pem"
    graph_key_path: str = "/etc/openroom/graph/key.pem"
    room_mailbox_upn: str = ""

    # Privacy: show the real subject only if the room's config allows;
    # otherwise show the organiser's name instead. Private-sensitivity
    # meetings always show as "Private" regardless of this setting.
    show_meeting_subject: bool = True

    calendar_poll_interval_seconds: int = 60
    calendar_timezone: str = "Europe/London"
    calendar_cache_path: str = "/opt/openroom/state/calendar-cache.json"


settings = Settings()
