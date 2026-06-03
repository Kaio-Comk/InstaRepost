"""Contrato da camada de ingestão.

`SourceProvider` é a abstração que desacopla o NÚCLEO do sistema da forma
como o conteúdo autorizado chega. Isso permite trocar a origem sem tocar
em serviços, IA, publicação ou banco (Open/Closed + Dependency Inversion).

Implementações:
  - ManualSource       -> pasta observada (100% compatível com ToS).
  - InstaloaderSource  -> adaptador NÃO-oficial (opt-in, sob autorização).
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional


@dataclass
class RemoteMedia:
    """Descreve um item de mídia detectado numa origem.

    `local_path` pode já vir preenchido (fontes que entregam o arquivo, como a
    manual e o instaloader). Para fontes que só dão metadados, fica None e o
    DownloadService é responsável por obter o arquivo.
    """

    source_post_id: str
    source_url: Optional[str] = None
    caption: str = ""
    hashtags: List[str] = field(default_factory=list)
    local_path: Optional[Path] = None

    @property
    def context_for_ai(self) -> str:
        """Texto de contexto passado à IA (sem instruir a copiar)."""
        parts = []
        if self.caption:
            parts.append(self.caption)
        if self.hashtags:
            parts.append("Hashtags originais: " + " ".join(self.hashtags))
        return "\n".join(parts) or "(sem descrição original)"


class SourceProvider(ABC):
    """Interface de uma origem de conteúdo."""

    name: str = "base"

    @abstractmethod
    def fetch_new(self, target_username: str) -> List[RemoteMedia]:
        """Retorna os itens disponíveis na origem para o perfil alvo.

        A deduplicação contra o banco é responsabilidade do MonitorService;
        a origem apenas reporta o que enxerga.
        """
        raise NotImplementedError
