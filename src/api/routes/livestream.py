import json
import uuid
from datetime import datetime, timezone
from typing import List, Literal, Optional
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select

from src.api.scheduler import scheduler
from src.backend.live_stream_manager import LiveStreamManager
from src.db.database import SessionLocal
from src.db.models import LiveStream, LiveStreamLog

router = APIRouter(prefix="/livestream", tags=["Live Stream"])
live_stream_manager = LiveStreamManager()


class VisualizerSettings(BaseModel):
    visualizer_enabled: bool = True
    style: Literal["bars", "wave", "spectrum"] = "bars"
    visualizer_position: Literal["top", "center", "bottom"] = "bottom"
    spectrum_width: int = Field(default=960, ge=80, le=3840)
    spectrum_height: int = Field(default=180, ge=40, le=2160)
    sensitivity: float = Field(default=4.0, ge=0.1, le=12.0)
    opacity: float = Field(default=0.94, ge=0.05, le=1.0)
    panel_opacity: float = Field(default=0.35, ge=0.0, le=0.9)
    gradient_colors: List[str] = Field(
        default_factory=lambda: ["#c7ff2e", "#ff654a"], min_length=1, max_length=4
    )


class LiveStreamRequest(VisualizerSettings):
    title: str = Field(default="Autotube Live", min_length=1, max_length=200)
    stream_key: str = Field(min_length=1, max_length=500)
    rtmp_url: str = Field(
        default="rtmp://a.rtmp.youtube.com/live2", min_length=8, max_length=500
    )
    background_type: Literal["videos", "images"] = "videos"
    visual_paths: List[str] = Field(default_factory=list, max_length=100)
    audio_paths: List[str] = Field(default_factory=list, max_length=100)
    video_paths: List[str] = Field(default_factory=list, max_length=100)
    audio_path: Optional[str] = None
    audio_mode: Literal["replace", "mix", "keep"] = "replace"
    loop: bool = True
    shuffle: bool = False
    auto_restart: bool = True
    max_retries: int = Field(default=10, ge=0, le=50)
    image_duration: float = Field(default=8.0, ge=0.5, le=120.0)
    resolution: Literal["854x480", "1280x720", "1920x1080", "1080x1920", "1080x1080"] = (
        "1280x720"
    )
    fps: int = Field(default=30, ge=15, le=60)
    video_bitrate: int = Field(default=2500, ge=500, le=20000)
    audio_bitrate: int = Field(default=128, ge=64, le=320)
    preset: Literal["ultrafast", "superfast", "veryfast", "faster", "fast", "medium"] = (
        "veryfast"
    )
    music_volume: float = Field(default=1.0, ge=0.0, le=3.0)
    original_audio_volume: float = Field(default=0.35, ge=0.0, le=3.0)
    scheduled_start: Optional[datetime] = None
    scheduled_stop: Optional[datetime] = None


class DailyScheduleRequest(BaseModel):
    stream_data: LiveStreamRequest
    start_time: str = Field(pattern=r"^\d{2}:\d{2}$")
    stop_time: str = Field(pattern=r"^\d{2}:\d{2}$")
    timezone: str = "Asia/Jakarta"


def _start_scheduled_stream(stream_id: str) -> None:
    try:
        live_stream_manager.start(stream_id)
    except Exception as exc:
        live_stream_manager.add_log(stream_id, f"Scheduled start failed: {exc}", "ERROR")


def _stop_scheduled_stream(stream_id: str) -> None:
    try:
        live_stream_manager.stop(stream_id)
    except Exception as exc:
        live_stream_manager.add_log(stream_id, f"Scheduled stop failed: {exc}", "ERROR")


def _as_utc(value: Optional[datetime], field_name: str) -> Optional[datetime]:
    if value is None:
        return None
    if value.tzinfo is None:
        raise HTTPException(422, f"{field_name} must include a timezone.")
    return value.astimezone(timezone.utc)


def _normalized_paths(request: LiveStreamRequest):
    visuals = list(request.visual_paths or request.video_paths)
    audios = list(request.audio_paths)
    if request.audio_path and not audios:
        audios = [request.audio_path]
    if not visuals:
        raise HTTPException(422, "Select at least one image or video.")
    if request.audio_mode in {"replace", "mix"} and not audios:
        raise HTTPException(422, "Select at least one audio file.")
    if request.background_type == "images" and request.audio_mode != "replace":
        raise HTTPException(422, "Image backgrounds require replacement audio.")
    return visuals, audios


def _settings_dict(request: LiveStreamRequest):
    keys = (
        "audio_mode",
        "image_duration",
        "resolution",
        "fps",
        "video_bitrate",
        "audio_bitrate",
        "preset",
        "music_volume",
        "original_audio_volume",
        "visualizer_enabled",
        "style",
        "visualizer_position",
        "spectrum_width",
        "spectrum_height",
        "sensitivity",
        "opacity",
        "panel_opacity",
        "gradient_colors",
    )
    return {key: getattr(request, key) for key in keys}


def _create_record(request: LiveStreamRequest, status: str) -> LiveStream:
    visuals, audios = _normalized_paths(request)
    scheduled_start = _as_utc(request.scheduled_start, "scheduled_start")
    scheduled_stop = _as_utc(request.scheduled_stop, "scheduled_stop")
    if scheduled_start and scheduled_stop and scheduled_stop <= scheduled_start:
        raise HTTPException(422, "scheduled_stop must be later than scheduled_start.")

    try:
        return live_stream_manager.create_stream(
            {
                "id": str(uuid.uuid4()),
                "title": request.title,
                "status": status,
                "stream_key": request.stream_key,
                "rtmp_url": request.rtmp_url,
                "background_type": request.background_type,
                "visual_paths": visuals,
                "audio_paths": audios,
                "settings": _settings_dict(request),
                "loop": request.loop,
                "shuffle": request.shuffle,
                "auto_restart": request.auto_restart,
                "max_retries": request.max_retries,
                "scheduled_start": scheduled_start,
                "scheduled_stop": scheduled_stop,
            }
        )
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(422, str(exc)) from exc


def _serialize(stream: LiveStream):
    settings = json.loads(stream.settings_json or "{}")
    return {
        "id": stream.id,
        "title": stream.title,
        "status": stream.status,
        "rtmp_url": stream.rtmp_url,
        "stream_key_hint": "****" if stream.stream_key_encrypted else "",
        "background_type": stream.background_type,
        "visual_paths": json.loads(stream.visual_paths_json or "[]"),
        "audio_paths": json.loads(stream.audio_paths_json or "[]"),
        "settings": settings,
        "loop": stream.loop,
        "shuffle": stream.shuffle,
        "auto_restart": stream.auto_restart,
        "retry_count": stream.retry_count,
        "max_retries": stream.max_retries,
        "pid": stream.pid,
        "error_message": stream.error_message,
        "scheduled_start": stream.scheduled_start,
        "scheduled_stop": stream.scheduled_stop,
        "started_at": stream.started_at,
        "stopped_at": stream.stopped_at,
        "created_at": stream.created_at,
        "updated_at": stream.updated_at,
    }


def _get_stream(stream_id: str) -> LiveStream:
    with SessionLocal() as db:
        stream = db.get(LiveStream, stream_id)
        if stream is None:
            raise HTTPException(404, "Stream not found.")
        db.expunge(stream)
        return stream


def _schedule_once(stream: LiveStream) -> None:
    now = datetime.now(timezone.utc)
    if stream.scheduled_start and stream.scheduled_start > now:
        scheduler.add_job(
            _start_scheduled_stream,
            DateTrigger(run_date=stream.scheduled_start),
            args=[stream.id],
            id=f"live:{stream.id}:start",
            replace_existing=True,
            misfire_grace_time=300,
        )
    else:
        live_stream_manager.start(stream.id)

    if stream.scheduled_stop and stream.scheduled_stop > now:
        scheduler.add_job(
            _stop_scheduled_stream,
            DateTrigger(run_date=stream.scheduled_stop),
            args=[stream.id],
            id=f"live:{stream.id}:stop",
            replace_existing=True,
            misfire_grace_time=300,
        )


@router.post("/start")
def start_stream(request: LiveStreamRequest):
    start_at = _as_utc(request.scheduled_start, "scheduled_start")
    status = "scheduled" if start_at and start_at > datetime.now(timezone.utc) else "starting"
    stream = _create_record(request, status)
    try:
        _schedule_once(stream)
    except Exception as exc:
        live_stream_manager.add_log(stream.id, str(exc), "ERROR")
        raise HTTPException(422, str(exc)) from exc
    return {
        "message": "Stream scheduled." if status == "scheduled" else "Stream initialization started.",
        "stream_id": stream.id,
        "stream": _serialize(_get_stream(stream.id)),
    }


@router.post("/schedule")
def schedule_daily(request: DailyScheduleRequest):
    try:
        tz = ZoneInfo(request.timezone)
        start_hour, start_minute = (int(part) for part in request.start_time.split(":"))
        stop_hour, stop_minute = (int(part) for part in request.stop_time.split(":"))
    except (ValueError, ZoneInfoNotFoundError) as exc:
        raise HTTPException(422, "Invalid schedule time or timezone.") from exc
    if not all(
        (
            0 <= start_hour <= 23,
            0 <= stop_hour <= 23,
            0 <= start_minute <= 59,
            0 <= stop_minute <= 59,
        )
    ):
        raise HTTPException(422, "Schedule time is outside the valid range.")

    if (start_hour, start_minute) == (stop_hour, stop_minute):
        raise HTTPException(422, "Daily start and stop times must be different.")

    stream = _create_record(request.stream_data, "scheduled")
    scheduler.add_job(
        _start_scheduled_stream,
        CronTrigger(hour=start_hour, minute=start_minute, timezone=tz),
        args=[stream.id],
        id=f"live:{stream.id}:daily:start",
        replace_existing=True,
        misfire_grace_time=300,
    )
    scheduler.add_job(
        _stop_scheduled_stream,
        CronTrigger(hour=stop_hour, minute=stop_minute, timezone=tz),
        args=[stream.id],
        id=f"live:{stream.id}:daily:stop",
        replace_existing=True,
        misfire_grace_time=300,
    )
    live_stream_manager.add_log(
        stream.id,
        f"Daily schedule set for {request.start_time}-{request.stop_time} ({request.timezone}).",
    )
    return {
        "message": "Daily stream schedule created.",
        "stream_id": stream.id,
        "stream": _serialize(_get_stream(stream.id)),
    }


@router.post("/stop/{stream_id}")
def stop_stream(stream_id: str):
    try:
        changed = live_stream_manager.stop(stream_id)
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    return {"message": "Stream stop requested.", "changed": changed}


@router.post("/{stream_id}/restart")
def restart_stream(stream_id: str):
    try:
        live_stream_manager.restart(stream_id)
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(409, str(exc)) from exc
    return {"message": "Stream restart requested."}


@router.get("/active")
def active_streams():
    with SessionLocal() as db:
        streams = db.execute(
            select(LiveStream)
            .where(LiveStream.status.in_(["starting", "live", "retrying", "scheduled"]))
            .order_by(LiveStream.created_at.desc())
        ).scalars().all()
        return {"streams": [_serialize(stream) for stream in streams]}


@router.get("/")
def list_streams():
    with SessionLocal() as db:
        streams = db.execute(
            select(LiveStream).order_by(LiveStream.created_at.desc()).limit(100)
        ).scalars().all()
        return {"streams": [_serialize(stream) for stream in streams]}


@router.get("/{stream_id}/logs")
def stream_logs(stream_id: str, limit: int = 100):
    _get_stream(stream_id)
    limit = max(1, min(limit, 200))
    with SessionLocal() as db:
        logs = db.execute(
            select(LiveStreamLog)
            .where(LiveStreamLog.stream_id == stream_id)
            .order_by(LiveStreamLog.id.desc())
            .limit(limit)
        ).scalars().all()
        return {
            "logs": [
                {
                    "id": item.id,
                    "level": item.level,
                    "message": item.message,
                    "created_at": item.created_at,
                }
                for item in reversed(logs)
            ]
        }


@router.get("/{stream_id}")
def stream_status(stream_id: str):
    return _serialize(_get_stream(stream_id))


@router.delete("/{stream_id}")
def delete_stream(stream_id: str):
    with SessionLocal() as db:
        stream = db.get(LiveStream, stream_id)
        if stream is None:
            raise HTTPException(404, "Stream not found.")
        if stream.status not in TERMINAL_STATUSES | {"draft", "scheduled"}:
            raise HTTPException(409, "Stop the stream before deleting it.")
        db.delete(stream)
        db.commit()
    for suffix in ("start", "stop", "daily:start", "daily:stop"):
        job = scheduler.get_job(f"live:{stream_id}:{suffix}")
        if job:
            job.remove()
    return {"message": "Stream deleted."}


TERMINAL_STATUSES = {"stopped", "error", "completed"}
