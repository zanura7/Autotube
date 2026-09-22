import subprocess
import os
import uuid
import time
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional

router = APIRouter(prefix="/livestream", tags=["Live Stream"])

# Store active streams to allow stopping them
active_streams = {}

class LiveStreamRequest(BaseModel):
    stream_key: str
    video_paths: List[str]
    audio_path: str
    thumbnail_path: Optional[str] = None
    loop: bool = True
    
class ScheduleRequest(BaseModel):
    stream_data: LiveStreamRequest
    start_time: str # Format "HH:MM" e.g., "08:00"
    stop_time: str  # Format "HH:MM" e.g., "17:00"

def run_ffmpeg_stream(request: LiveStreamRequest, stream_id: str):
    from api.logger import manager
    manager.sync_broadcast_log(f"Starting Live Stream for key ending in ...{request.stream_key[-4:]}", "INFO")
    
    # Create temp dir
    temp_dir = os.path.join(os.getcwd(), "temp_live")
    os.makedirs(temp_dir, exist_ok=True)
    
    # 1. Create Video Concat File
    video_concat_path = os.path.join(temp_dir, f"vid_{stream_id}.txt")
    with open(video_concat_path, "w") as f:
        for _ in range(1000): # Loop 1000 times
            for vp in request.video_paths:
                vp = os.path.abspath(vp).replace('\\', '/')
                f.write(f"file '{vp}'\n")
                
    # 2. Create Audio Concat File
    audio_concat_path = os.path.join(temp_dir, f"aud_{stream_id}.txt")
    with open(audio_concat_path, "w") as f:
        for _ in range(1000):
            ap = os.path.abspath(request.audio_path).replace('\\', '/')
            f.write(f"file '{ap}'\n")

    # Basic RTMP URL
    rtmp_url = f"rtmp://a.rtmp.youtube.com/live2/{request.stream_key}"
    
    # 3. Build robust FFmpeg command inspired by Streamflow
    cmd = [
        "ffmpeg", "-nostdin", "-loglevel", "warning", "-stats", "-re",
        "-fflags", "+genpts+igndts+discardcorrupt", "-avoid_negative_ts", "make_zero",
        "-f", "concat", "-safe", "0", "-i", video_concat_path,
        "-re", "-f", "concat", "-safe", "0", "-i", audio_concat_path,
        "-map", "0:v:0", "-map", "1:a:0",
        "-c:v", "libx264", "-preset", "veryfast", "-tune", "zerolatency",
        "-profile:v", "high", "-level", "4.1",
        "-b:v", "2500k", "-maxrate", "2750k", "-bufsize", "5000k",
        "-pix_fmt", "yuv420p", "-g", "60",
        "-c:a", "aac", "-b:a", "128k", "-ar", "44100",
        "-f", "flv", "-flvflags", "no_duration_filesize", rtmp_url
    ]

    try:
        process = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True
        )
        active_streams[stream_id] = process
        manager.sync_broadcast_log(f"Stream {stream_id} is running (PID: {process.pid})", "SUCCESS")
        
        for line in process.stdout:
            if "speed=" in line or "time=" in line:
                manager.sync_broadcast_progress(1, 100, text=line.strip())
            else:
                manager.sync_broadcast_log(f"[FFmpeg] {line.strip()}", "DEBUG")
                
        process.wait()
        manager.sync_broadcast_log(f"Stream {stream_id} ended (Code: {process.returncode})", "INFO")
    except Exception as e:
        manager.sync_broadcast_log(f"Stream Error: {str(e)}", "ERROR")
    finally:
        if stream_id in active_streams:
            del active_streams[stream_id]

def stop_ffmpeg_stream(stream_id: str):
    from api.logger import manager
    if stream_id in active_streams:
        process = active_streams[stream_id]
        process.terminate()
        del active_streams[stream_id]
        manager.sync_broadcast_log(f"Scheduled stop executed for stream {stream_id}", "INFO")

@router.post("/start")
async def start_stream(request: LiveStreamRequest, background_tasks: BackgroundTasks):
    stream_id = str(uuid.uuid4())
    if not request.stream_key:
        raise HTTPException(status_code=400, detail="Stream key is required")
    if not request.video_paths or len(request.video_paths) == 0:
        raise HTTPException(status_code=400, detail="At least one video path is required")
        
    background_tasks.add_task(run_ffmpeg_stream, request, stream_id)
    return {"message": "Live stream initialization started", "stream_id": stream_id}

@router.post("/stop/{stream_id}")
async def stop_stream(stream_id: str):
    if stream_id in active_streams:
        process = active_streams[stream_id]
        process.terminate()
        del active_streams[stream_id]
        return {"message": f"Stream {stream_id} stopped"}
    else:
        raise HTTPException(status_code=404, detail="Stream not found or already stopped")

@router.get("/active")
async def get_active_streams():
    return {"active_streams": list(active_streams.keys())}

@router.post("/schedule")
async def schedule_stream(request: ScheduleRequest):
    from src.api.scheduler import scheduler
    stream_id = str(uuid.uuid4())
    
    start_hour, start_minute = map(int, request.start_time.split(':'))
    stop_hour, stop_minute = map(int, request.stop_time.split(':'))
    
    # Add start job
    scheduler.add_job(
        func=run_ffmpeg_stream,
        trigger='cron',
        hour=start_hour,
        minute=start_minute,
        args=[request.stream_data, stream_id],
        id=f"start_{stream_id}",
        replace_existing=True
    )
    
    # Add stop job
    scheduler.add_job(
        func=stop_ffmpeg_stream,
        trigger='cron',
        hour=stop_hour,
        minute=stop_minute,
        args=[stream_id],
        id=f"stop_{stream_id}",
        replace_existing=True
    )
    
    return {
        "message": f"Stream scheduled. Starts at {request.start_time}, stops at {request.stop_time} daily.",
        "stream_id": stream_id
    }
