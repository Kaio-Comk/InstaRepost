"""Contrato da geração de legendas (permite trocar o backend de IA)."""
from __future__ import annotations

from abc import ABC, abstractmethod


class CaptionGenerator(ABC):
    @abstractmethod
    def generate(self, context: str, style: str, target_username: str = "", extra: str = "") -> str:
        """Gera uma legenda original a partir do contexto e do estilo escolhido."""
        raise NotImplementedError

    @abstractmethod
    def health_check(self) -> bool:
        """Indica se o backend de IA está acessível."""
        raise NotImplementedError
