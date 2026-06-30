"""Application settings.

Loads strongly-typed configuration from environment variables / ``.env`` using
``pydantic-settings``. A single cached :class:`Settings` instance is exposed via
:func:`get_settings` (dependency-injection friendly, importable anywhere).

Design notes
------------
* All values have sane defaults so the app boots even without a ``.env`` file
  (development-first experience).
* ``DB_MODE`` switches between a zero-config SQLite database (development) and
  SQL Server (production) without code changes -> see :pyattr:`Settings.database_url`.
* Paths are resolved relative to the *project root* (the parent of ``backend/``)
  so the same config works whether you launch from the repo root or ``backend/``.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import List, Literal
from urllib.parse import quote_plus

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

# ----------------------------------------------------------------------------
# Path anchors
# ----------------------------------------------------------------------------
# settings.py -> config/ -> app/ -> backend/ -> <PROJECT_ROOT>
BACKEND_DIR: Path = Path(__file__).resolve().parents[2]
PROJECT_ROOT: Path = BACKEND_DIR.parent
ENV_FILE: Path = BACKEND_DIR / ".env"


class Settings(BaseSettings):
    """Typed application configuration sourced from the environment."""

    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ---------- Application ----------
    app_name: str = Field(default="Smart Factory Vision Inspection")
    app_env: Literal["development", "production"] = Field(default="development")
    app_debug: bool = Field(default=True)
    app_host: str = Field(default="0.0.0.0")
    app_port: int = Field(default=8000)

    # ---------- Database ----------
    db_mode: Literal["sqlite", "mssql"] = Field(default="sqlite")
    db_sqlite_path: str = Field(default="database/factory.db")

    mssql_host: str = Field(default="localhost")
    mssql_port: int = Field(default=1433)
    mssql_database: str = Field(default="SmartFactory")
    mssql_user: str = Field(default="sa")
    mssql_password: str = Field(default="YourStrong!Passw0rd")
    mssql_driver: str = Field(default="ODBC Driver 17 for SQL Server")

    # ---------- Security ----------
    jwt_secret_key: str = Field(default="change-this-to-a-long-random-secret-string")
    jwt_algorithm: str = Field(default="HS256")
    jwt_access_token_expire_minutes: int = Field(default=60)
    api_key: str = Field(default="dev-api-key-change-me")
    cors_origins: str = Field(default="http://localhost:5173,app://.")

    # ---------- MQTT ----------
    mqtt_broker_host: str = Field(default="localhost")
    mqtt_broker_port: int = Field(default=1883)
    mqtt_username: str = Field(default="")
    mqtt_password: str = Field(default="")
    mqtt_client_id: str = Field(default="smart-factory-backend")
    mqtt_keepalive: int = Field(default=60)

    # ---------- TCP / PLC ----------
    tcp_host: str = Field(default="0.0.0.0")
    tcp_port: int = Field(default=9000)

    # ---------- Vision Inspection ----------
    inspection_confidence_threshold: float = Field(default=0.75)
    images_captured_dir: str = Field(default="images/captured")
    images_processed_dir: str = Field(default="images/processed")
    images_defects_dir: str = Field(default="images/defects")

    # ---------- Logging ----------
    log_level: str = Field(default="INFO")
    log_dir: str = Field(default="logs")
    log_max_bytes: int = Field(default=10 * 1024 * 1024)
    log_backup_count: int = Field(default=5)

    # ------------------------------------------------------------------
    # Derived / computed properties
    # ------------------------------------------------------------------
    @property
    def is_production(self) -> bool:
        """Return ``True`` when running with ``APP_ENV=production``."""
        return self.app_env == "production"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def cors_origin_list(self) -> List[str]:
        """Parse the comma-separated ``CORS_ORIGINS`` string into a list."""
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @computed_field  # type: ignore[prop-decorator]
    @property
    def database_url(self) -> str:
        """Build the SQLAlchemy connection URL for the active ``DB_MODE``.

        * ``sqlite`` -> ``sqlite:///<absolute path>`` (file auto-created).
        * ``mssql``  -> ``mssql+pyodbc://...`` with URL-encoded credentials.
        """
        if self.db_mode == "sqlite":
            db_path = self._resolve_path(self.db_sqlite_path)
            db_path.parent.mkdir(parents=True, exist_ok=True)
            return f"sqlite:///{db_path.as_posix()}"

        # SQL Server via pyodbc
        params = quote_plus(
            f"DRIVER={{{self.mssql_driver}}};"
            f"SERVER={self.mssql_host},{self.mssql_port};"
            f"DATABASE={self.mssql_database};"
            f"UID={self.mssql_user};"
            f"PWD={self.mssql_password};"
            "TrustServerCertificate=yes;"
        )
        return f"mssql+pyodbc:///?odbc_connect={params}"

    # ------------------------------------------------------------------
    # Path helpers (all relative paths anchored at PROJECT_ROOT)
    # ------------------------------------------------------------------
    @staticmethod
    def _resolve_path(relative_or_absolute: str) -> Path:
        """Resolve a path against the project root unless it is already absolute."""
        p = Path(relative_or_absolute)
        return p if p.is_absolute() else (PROJECT_ROOT / p)

    @property
    def log_dir_path(self) -> Path:
        return self._resolve_path(self.log_dir)

    @property
    def captured_dir_path(self) -> Path:
        return self._resolve_path(self.images_captured_dir)

    @property
    def processed_dir_path(self) -> Path:
        return self._resolve_path(self.images_processed_dir)

    @property
    def defects_dir_path(self) -> Path:
        return self._resolve_path(self.images_defects_dir)

    def ensure_runtime_dirs(self) -> None:
        """Create all directories the application writes to at runtime."""
        for path in (
            self.log_dir_path,
            self.captured_dir_path,
            self.processed_dir_path,
            self.defects_dir_path,
        ):
            path.mkdir(parents=True, exist_ok=True)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a process-wide cached :class:`Settings` instance.

    Using ``lru_cache`` guarantees the ``.env`` file is parsed only once and the
    same object is shared across the whole application (FastAPI ``Depends``,
    background workers, CLI scripts, tests, ...).
    """
    return Settings()
