from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings, overridable via environment variables (prefix ``DNSMASQ_WEBMIN_``)."""

    model_config = SettingsConfigDict(env_prefix="DNSMASQ_WEBMIN_", env_file=".env", extra="ignore")

    conf_dir: Path = Field(
        default=Path("/etc/dnsmasq.d"),
        description="Directory dnsmasq reads sub config files from (conf-dir).",
    )
    db_path: Path = Field(
        default=Path("/tmp/dnsmasq-webmin/db.json"),
        description="Location of the TinyDB JSON document store.",
    )
    file_prefix: str = Field(
        default="webmin-",
        pattern=r"^[A-Za-z0-9_-]*$",
        description="Prefix for generated files. Only files with this prefix are ever touched.",
    )
    write_on_change: bool = Field(
        default=True,
        description="Write/delete the config file in conf_dir on every change.",
    )
    debug: bool = Field(
        default=False,
        validation_alias="APP_DEBUG",
        description="Enable uvicorn auto-reload when started via 'python -m app.main'.",
    )
    host: str = Field(
        default="0.0.0.0",
        validation_alias="APP_HOST",
        description="Bind address. 0.0.0.0 listens on all interfaces, 127.0.0.1 restricts to localhost.",
    )
    port: int = Field(default=5000, ge=1, le=65535, validation_alias="APP_PORT")
    systemd_unit: str = Field(
        default="dnsmasq.service",
        pattern=r"^([A-Za-z0-9@._:-]+\.service)?$",
        description="systemd unit to restart. Empty string disables the restart feature.",
    )
    frontend_dir: Path = Field(
        default=Path(__file__).resolve().parent.parent / "frontend" / "dist",
        description="Built SPA (npm run build). Served at '/' if it exists.",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
