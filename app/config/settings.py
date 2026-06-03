"""Configuração central da aplicação.

Usa pydantic-settings para carregar variáveis do ambiente / .env com
validação forte de tipos. É a única fonte de verdade de configuração —
nenhum módulo deve ler ``os.environ`` diretamente (SOLID: dependa de
abstrações, não de detalhes do ambiente).
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Raiz do projeto (…/InstaRepost). Permite caminhos relativos no .env.
BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- Banco ---
    database_url: str = "sqlite:///database/instarepost.db"

    # --- Logging ---
    log_level: str = "INFO"
    log_dir: str = "logs"

    # --- Diretórios ---
    download_dir: str = "downloads"
    data_dir: str = "data"

    # --- Ingestão ---
    source_provider: str = "manual"
    target_username: str = "perfil_autorizado"
    watch_dir: str = "data/inbox"

    # --- Validação de download ---
    max_video_mb: float = 300.0
    min_video_mb: float = 0.05
    # Armazenado como CSV (pydantic-settings não faz JSON-parse de str). Use .allowed_extensions.
    allowed_extensions_raw: str = Field(default=".mp4,.mov", alias="ALLOWED_EXTENSIONS")

    # --- IA local ---
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen3"
    ollama_timeout: int = 120
    default_caption_style: str = "viral"

    # --- Aprovação ---
    require_manual_approval: bool = True

    # --- Publicação ---
    publisher: str = "dry_run"
    ig_user_id: str = ""
    ig_access_token: str = ""
    public_media_base_url: str = ""

    # --- Scheduler ---
    poll_interval_seconds: int = 900

    # --- Web ---
    web_host: str = "127.0.0.1"
    web_port: int = 8000

    @property
    def allowed_extensions(self) -> List[str]:
        """Lista normalizada de extensões permitidas (a partir do CSV do .env)."""
        return [e.strip().lower() for e in self.allowed_extensions_raw.split(",") if e.strip()]

    # ---- Helpers de caminho absoluto ----
    def _abs(self, value: str) -> Path:
        p = Path(value)
        return p if p.is_absolute() else (BASE_DIR / p)

    @property
    def download_path(self) -> Path:
        return self._abs(self.download_dir)

    @property
    def data_path(self) -> Path:
        return self._abs(self.data_dir)

    @property
    def watch_path(self) -> Path:
        return self._abs(self.watch_dir)

    @property
    def log_path(self) -> Path:
        return self._abs(self.log_dir)

    @property
    def caption_styles_path(self) -> Path:
        return BASE_DIR / "app" / "config" / "caption_styles.yaml"

    def ensure_dirs(self) -> None:
        """Cria os diretórios de trabalho se ainda não existirem."""
        for p in (self.download_path, self.data_path, self.watch_path, self.log_path):
            p.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    """Singleton de configuração (cacheado para o ciclo de vida do processo)."""
    return Settings()
