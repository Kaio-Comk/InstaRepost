"""Backends de IA local."""
from app.ai.base import CaptionGenerator
from app.ai.ollama_client import OllamaCaptionGenerator


def get_caption_generator() -> CaptionGenerator:
    """Resolve o gerador de legendas configurado (atualmente Ollama)."""
    return OllamaCaptionGenerator()


__all__ = ["CaptionGenerator", "OllamaCaptionGenerator", "get_caption_generator"]
