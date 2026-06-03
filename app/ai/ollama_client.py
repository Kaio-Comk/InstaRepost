"""Gerador de legendas usando Ollama (IA 100% local).

Compatível com qualquer modelo servido pelo Ollama (qwen3, llama3, mistral…).
Os prompts vêm de app/config/caption_styles.yaml — editáveis sem mexer no código.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Dict

import requests
import yaml

from app.ai.base import CaptionGenerator
from app.config.settings import get_settings
from app.utils.logging_config import get_logger
from app.utils.validators import clean_caption

logger = get_logger(__name__)


@lru_cache
def _load_styles() -> dict:
    settings = get_settings()
    path = settings.caption_styles_path
    with open(path, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


class OllamaCaptionGenerator(CaptionGenerator):
    def __init__(self, base_url: str | None = None, model: str | None = None,
                 timeout: int | None = None) -> None:
        s = get_settings()
        self.base_url = (base_url or s.ollama_base_url).rstrip("/")
        self.model = model or s.ollama_model
        self.timeout = timeout or s.ollama_timeout

    # ---- API pública ----
    def generate(self, context: str, style: str, target_username: str = "", extra: str = "") -> str:
        prompt = self._build_prompt(context, style, target_username, extra)
        raw = self._call_ollama(prompt)
        caption = clean_caption(raw)
        if not caption:
            raise RuntimeError("Ollama retornou legenda vazia.")
        return caption

    def health_check(self) -> bool:
        try:
            resp = requests.get(f"{self.base_url}/api/tags", timeout=5)
            return resp.status_code == 200
        except requests.RequestException as exc:
            logger.warning("Ollama indisponível: %s", exc)
            return False

    # ---- Internos ----
    def _build_prompt(self, context: str, style: str, target_username: str, extra: str) -> str:
        styles = _load_styles()
        style_cfg: Dict = styles.get("styles", {}).get(style)
        if not style_cfg:
            available = ", ".join(styles.get("styles", {}).keys())
            raise ValueError(f"Estilo {style!r} inexistente. Disponíveis: {available}")

        template = style_cfg["prompt"].format(
            context=context or "(sem descrição)",
            target_username=target_username,
            extra=extra,
        )
        global_rules = styles.get("global_rules", "")
        return f"{template}\n\n{global_rules}"

    def _call_ollama(self, prompt: str) -> str:
        url = f"{self.base_url}/api/generate"
        payload = {"model": self.model, "prompt": prompt, "stream": False}
        try:
            resp = requests.post(url, json=payload, timeout=self.timeout)
            resp.raise_for_status()
        except requests.RequestException as exc:
            logger.error("Erro ao chamar Ollama (%s): %s", self.model, exc)
            raise RuntimeError(f"Falha na IA local: {exc}") from exc

        data = resp.json()
        return data.get("response", "")
