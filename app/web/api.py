"""Painel de aprovação (FastAPI).

Funcionalidades:
  - listar vídeos pendentes (processados, não publicados);
  - visualizar a legenda gerada e o vídeo;
  - editar a legenda;
  - aprovar / rejeitar;
  - reprocessar (regenerar) a legenda;
  - publicar os aprovados.
"""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.ai import get_caption_generator
from app.config.settings import get_settings
from app.db import init_db, session_scope
from app.models.video import Video
from app.repositories import CaptionRepository, VideoRepository
from app.services.caption_service import CaptionService
from app.services.pipeline_service import PipelineService
from app.utils.logging_config import get_logger

logger = get_logger(__name__)

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

app = FastAPI(title="InstaRepost — Painel de Aprovação")


@app.on_event("startup")
def _startup() -> None:
    get_settings().ensure_dirs()
    init_db()


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    with session_scope() as session:
        videos = VideoRepository(session).list_pending_publish()
        rows = []
        for v in videos:
            cap = v.latest_caption
            rows.append(
                {
                    "id": v.id,
                    "post": v.source_post_id,
                    "source_url": v.source_url,
                    "caption": cap.generated_caption if cap else "",
                    "style": cap.style if cap else "",
                    "approved": cap.approved if cap else False,
                    "has_file": bool(v.local_file and Path(v.local_file).exists()),
                }
            )
    settings = get_settings()
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"videos": rows, "settings": settings},
    )


@app.get("/video/{video_id}")
def serve_video(video_id: int):
    with session_scope() as session:
        video = session.get(Video, video_id)
        if video is None or not video.local_file or not Path(video.local_file).exists():
            raise HTTPException(404, "Vídeo não encontrado.")
        path = video.local_file
    return FileResponse(path, media_type="video/mp4")


@app.post("/caption/{video_id}/edit")
def edit_caption(video_id: int, caption_text: str = Form(...)):
    with session_scope() as session:
        cap = CaptionRepository(session).latest_for_video(video_id)
        if cap is None:
            raise HTTPException(404, "Legenda não encontrada.")
        cap.generated_caption = caption_text.strip()
    return RedirectResponse("/", status_code=303)


@app.post("/caption/{video_id}/approve")
def approve(video_id: int):
    with session_scope() as session:
        cap = CaptionRepository(session).latest_for_video(video_id)
        if cap is None:
            raise HTTPException(404, "Legenda não encontrada.")
        cap.approved = True
    logger.info("Vídeo %s aprovado no painel.", video_id)
    return RedirectResponse("/", status_code=303)


@app.post("/caption/{video_id}/reject")
def reject(video_id: int):
    with session_scope() as session:
        cap = CaptionRepository(session).latest_for_video(video_id)
        if cap is None:
            raise HTTPException(404, "Legenda não encontrada.")
        cap.approved = False
    return RedirectResponse("/", status_code=303)


@app.post("/caption/{video_id}/regenerate")
def regenerate(video_id: int, style: str = Form("")):
    with session_scope() as session:
        service = CaptionService(session, get_caption_generator())
        service.regenerate(video_id, style or None)
    return RedirectResponse("/", status_code=303)


@app.post("/publish")
def publish_all():
    report = PipelineService().publish_approved()
    logger.info("Publicação manual: %s", report.messages)
    return RedirectResponse("/", status_code=303)


def run_web() -> None:
    import uvicorn

    s = get_settings()
    uvicorn.run("app.web.api:app", host=s.web_host, port=s.web_port, reload=False)
