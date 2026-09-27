from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="OPENROOM_")

    room_name: str = "Meeting Room"

    # Milestone 3 has no calendar (Milestone 4) — a single fixed join URL
    # stands in for a real meeting so Join/Leave/Home can be exercised.
    demo_join_url: str = "https://teams.microsoft.com/l/meetup-join/demo"

    home_url: str = "http://127.0.0.1:8080/"
    external_base_url: str = "http://127.0.0.1:8080"
    join_by_id_url: str = "https://teams.microsoft.com/meet"

    cdp_host: str = "127.0.0.1"
    cdp_port: int = 9222

    # Where the control role packs the Leave & Home extension.
    extension_crx_path: str = "/opt/openroom/extension/src.crx"
    extension_id_path: str = "/opt/openroom/extension/id.txt"
    extension_version: str = "1.0.0"


settings = Settings()
