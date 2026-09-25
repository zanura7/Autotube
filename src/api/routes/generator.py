from fastapi import APIRouter, BackgroundTasks, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from typing import Optional, List, Literal
from pathlib import Path
import logging
import shutil
import uuid

from src.db.database import SessionLocal
from src.db.models import Project

router = APIRouter(prefix="/generator", tags=["Generator"])
logger = logging.getLogger(__name__)
GENERATIONS = Path("generations")
UPLOADS = Path("uploads")
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".webp", ".tiff"}
AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg", ".wma"}
VIDEO_EXTENSIONS = {".mp4", ".mkv", ".mov", ".avi", ".webm", ".m4v"}


class VideoGenRequest(BaseModel):
    mode: Literal["simple", "loop", "visualizer", "mixer"] = "simple"
    output_name: str
    audio_path: Optional[str] = None
    bg_path: Optional[str] = None
    style: str = "Classic Bar"
    image_folder: Optional[str] = None
    audio_files: Optional[List[str]] = None
    background_type: Literal["images", "video"] = "images"
    image_files: Optional[List[str]] = None
    audio_mode: Literal["replace", "mix", "keep"] = "replace"
    video_shorter_mode: Literal["loop", "freeze"] = "loop"
    image_order: Literal["sequential", "random"] = "sequential"
    image_duration: float = 6.0
    transition_type: Literal["none", "fade", "crossfade"] = "crossfade"
    transition_duration: float = 0.8
    resolution: str = "1920x1080"
    visualizer_position: Literal["top", "center", "bottom"] = "bottom"
    spectrum_width: int = 1400
    spectrum_height: int = 210
    bar_count: int = 64
    sensitivity: float = 8.0
    opacity: float = 0.94
    panel_opacity: float = 0.38
    gradient_colors: List[str] = Field(default_factory=lambda: ["#c7ff2e", "#ff654a"])
    music_volume: float = 1.0
    original_audio_volume: float = 0.35


def require_media(value, extensions, label):
    if not value or not Path(value).is_file():
        raise HTTPException(422, f"{label}: file not found.")
    if Path(value).suffix.lower() not in extensions:
        raise HTTPException(422, f"{label}: unsupported file type.")


def validate_request(request):
    name = request.output_name.strip()
    if (not name or any(c in name for c in '<>:"/\\|?*')
            or any(ord(c) < 32 for c in name)
            or Path(name).suffix.lower() != ".mp4"
            or name.split(".")[0].upper() in
            {"CON", "PRN", "AUX", "NUL", *{f"COM{i}" for i in range(1, 10)},
             *{f"LPT{i}" for i in range(1, 10)}}):
        raise HTTPException(422, "Output name must be a valid MP4 filename without a folder path.")
    request.output_name = name
    if request.mode == "mixer":
        if not request.audio_files or len(request.audio_files) > 100:
            raise HTTPException(422, "Select between one and 100 audio files.")
        for path in request.audio_files:
            require_media(path, AUDIO_EXTENSIONS, "Audio")
        if request.background_type == "video":
            require_media(request.bg_path, VIDEO_EXTENSIONS, "Video")
        elif request.image_files:
            if len(request.image_files) > 100:
                raise HTTPException(422, "Select between one and 100 images.")
            for path in request.image_files:
                require_media(path, IMAGE_EXTENSIONS, "Image")
        else:
            if not request.image_folder or not Path(request.image_folder).is_dir():
                raise HTTPException(422, "Select images or provide an image folder.")
            if not any(p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS
                       for p in Path(request.image_folder).iterdir()):
                raise HTTPException(422, "Image folder contains no supported images.")
    elif request.mode == "visualizer":
        from src.backend.audio_visualizer import AudioVisualizer
        if request.style not in AudioVisualizer.STYLE_GROUPS:
            raise HTTPException(422, "Unsupported visualizer style.")
        if request.resolution not in {"1920x1080", "1280x720", "1080x1920", "1080x1080"}:
            raise HTTPException(422, "Unsupported output resolution.")
        numeric_ranges = {
            "image_duration": (0.5, 120.0),
            "transition_duration": (0.0, 30.0),
            "spectrum_width": (80, 3840),
            "spectrum_height": (40, 2160),
            "bar_count": (8, 256),
            "sensitivity": (0.1, 12.0),
            "opacity": (0.05, 1.0),
            "panel_opacity": (0.0, 0.9),
            "music_volume": (0.0, 3.0),
            "original_audio_volume": (0.0, 3.0),
        }
        for field, (minimum, maximum) in numeric_ranges.items():
            value = getattr(request, field)
            if value < minimum or value > maximum:
                raise HTTPException(422, f"{field} must be between {minimum} and {maximum}.")
        if request.transition_type != "none" and request.transition_duration >= request.image_duration:
            raise HTTPException(422, "Transition duration must be shorter than image duration.")
        if len(request.gradient_colors) < 1 or len(request.gradient_colors) > 4:
            raise HTTPException(422, "Choose between one and four visualizer colors.")
        if request.background_type == "images":
            if request.audio_mode != "replace":
                raise HTTPException(422, "Image backgrounds use the selected music as replacement audio.")
            require_media(request.audio_path, AUDIO_EXTENSIONS, "Audio")
            request.image_files = request.image_files or ([request.bg_path] if request.bg_path else [])
            if not request.image_files or len(request.image_files) > 100:
                raise HTTPException(422, "Select between one and 100 images.")
            for path in request.image_files:
                require_media(path, IMAGE_EXTENSIONS, "Image")
        else:
            require_media(request.bg_path, VIDEO_EXTENSIONS, "Video")
            if request.audio_mode != "keep":
                require_media(request.audio_path, AUDIO_EXTENSIONS, "Audio")
    else:
        if request.mode != "loop" or request.audio_path:
            require_media(request.audio_path, AUDIO_EXTENSIONS, "Audio")
        extensions = VIDEO_EXTENSIONS if request.mode == "loop" else IMAGE_EXTENSIONS | VIDEO_EXTENSIONS
        require_media(request.bg_path, extensions, "Visual")


@router.post("/upload")
def upload_file(file: UploadFile = File(...)):
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in IMAGE_EXTENSIONS | AUDIO_EXTENSIONS | VIDEO_EXTENSIONS:
        raise HTTPException(422, "Unsupported media file type.")
    UPLOADS.mkdir(parents=True, exist_ok=True)
    destination = UPLOADS / f"{uuid.uuid4().hex}{suffix}"
    try:
        with destination.open("xb") as output:
            shutil.copyfileobj(file.file, output)
        if destination.stat().st_size == 0:
            raise HTTPException(422, "Uploaded file is empty.")
    except Exception:
        destination.unlink(missing_ok=True)
        raise
    finally:
        file.file.close()
    return {"path": destination.resolve().as_posix()}


def run_generation(request, project_id, output):
    with SessionLocal() as db:
        project = db.get(Project, project_id)
        if project is None:
            return
        try:
            from src.backend.video_generator import VideoGenerator
            if request.mode == "loop":
                from src.backend.loop_creator import LoopCreator
                duration = 60
                if request.audio_path:
                    duration = VideoGenerator(output.parent).get_audio_duration(Path(request.audio_path))
                    if not duration or duration <= 0:
                        raise ValueError("Cannot read audio duration.")
                result = LoopCreator(output.parent).create_loop(
                    video_path=request.bg_path, target_duration=duration,
                    audio_path=request.audio_path, output_filename=output.name)
            elif request.mode == "visualizer":
                from src.backend.audio_visualizer import AudioVisualizer
                result = AudioVisualizer(output.parent).render_composition(
                    output_path=output,
                    background_type=request.background_type,
                    image_paths=request.image_files,
                    video_path=request.bg_path,
                    audio_path=request.audio_path,
                    audio_mode=request.audio_mode,
                    video_shorter_mode=request.video_shorter_mode,
                    image_order=request.image_order,
                    image_duration=request.image_duration,
                    transition_type=request.transition_type,
                    transition_duration=request.transition_duration,
                    resolution=request.resolution,
                    style=request.style,
                    position=request.visualizer_position,
                    spectrum_width=request.spectrum_width,
                    spectrum_height=request.spectrum_height,
                    bar_count=request.bar_count,
                    sensitivity=request.sensitivity,
                    opacity=request.opacity,
                    panel_opacity=request.panel_opacity,
                    gradient_colors=request.gradient_colors,
                    music_volume=request.music_volume,
                    original_audio_volume=request.original_audio_volume,
                )
            elif request.mode == "mixer":
                from src.backend.advanced_image_mixer import AdvancedImageMixer
                mixer = AdvancedImageMixer(output.parent)
                if request.background_type == "video":
                    from src.backend.loop_creator import LoopCreator
                    concatenated_audio = mixer.concatenate_audio(request.audio_files)
                    if not concatenated_audio:
                        raise RuntimeError("Could not concatenate the audio playlist.")
                    try:
                        duration = mixer.get_audio_duration(concatenated_audio)
                        if not duration or duration <= 0:
                            raise RuntimeError("Cannot read the audio playlist duration.")
                        result = LoopCreator(output.parent).create_loop(
                            video_path=request.bg_path,
                            target_duration=duration,
                            audio_path=str(concatenated_audio),
                            output_filename=output.name,
                        )
                    finally:
                        concatenated_audio.unlink(missing_ok=True)
                else:
                    result = mixer.generate_video(
                        image_folder=request.image_folder,
                        image_files=request.image_files,
                        audio_files=request.audio_files,
                        output_file=str(output),
                    )
            else:
                result = VideoGenerator(output.parent).generate_video(
                    audio_folder=request.audio_path, visual_path=request.bg_path,
                    output_filename=output.name)
            if not result or not output.is_file() or output.stat().st_size == 0:
                raise RuntimeError("Renderer did not produce a video.")
            project.status = "Completed"
        except Exception:
            logger.exception("Generation failed for project %s", project_id)
            project.status = "Failed"
        db.commit()


@router.post("/start")
def start_generation(request: VideoGenRequest, background_tasks: BackgroundTasks):
    validate_request(request)
    output = (GENERATIONS / uuid.uuid4().hex / request.output_name).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    with SessionLocal() as db:
        project = Project(filename=request.output_name, file_path=str(output),
                          project_type="Generator", status="Processing")
        db.add(project)
        db.commit()
        db.refresh(project)
        project_id = project.id
    background_tasks.add_task(run_generation, request, project_id, output)
    return {"message": "Generation started", "output": str(output), "project_id": project_id}


def get_project(project_id):
    with SessionLocal() as db:
        project = db.get(Project, project_id)
        if project is None or project.project_type != "Generator":
            raise HTTPException(404, "Generation not found.")
        return {"id": project.id, "status": project.status,
                "filename": project.filename, "file_path": project.file_path}


@router.get("/{project_id}")
def generation_status(project_id: int):
    return get_project(project_id)


@router.get("/{project_id}/download")
def download_generation(project_id: int):
    project = get_project(project_id)
    path = Path(project["file_path"]).resolve()
    if project["status"] != "Completed" or not path.is_file():
        raise HTTPException(404, "Generated video is not available.")
    if not path.is_relative_to(GENERATIONS.resolve()):
        raise HTTPException(404, "Generated video is outside the output folder.")
    return FileResponse(path, media_type="video/mp4", filename=project["filename"])
