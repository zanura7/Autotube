from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List
import os

router = APIRouter(prefix="/downloader", tags=["Downloader"])

class DownloadRequest(BaseModel):
    urls: List[str]
    format_type: str = "mp3_320"
    normalize: bool = True

@router.post("/batch")
async def download_batch(request: DownloadRequest, background_tasks: BackgroundTasks):
    from src.backend.downloader import Downloader
    
    # Run the download in background
    def run_download():
        from src.backend.downloader import Downloader
        from src.db.database import SessionLocal
        from src.db.models import Project
        import os

        dl = Downloader(output_folder="downloads")
        # Ensure folder exists
        os.makedirs("downloads", exist_ok=True)
        
        # We need a way to track the output file, but downloader currently handles it internally.
        # Let's just track the generic request in the DB for now.
        
        db = SessionLocal()
        project = Project(
            filename=f"Batch Download ({len(request.urls)} urls)",
            file_path="downloads/",
            project_type="Download",
            status="Processing"
        )
        db.add(project)
        db.commit()
        db.refresh(project)
        
        try:
            dl.download_batch(
                urls=request.urls, 
                format_type=request.format_type, 
                normalize=request.normalize
            )
            project.status = "Completed"
            db.commit()
        except Exception as e:
            project.status = "Failed"
            db.commit()
        finally:
            db.close()
            
    background_tasks.add_task(run_download)
    return {"message": "Download task submitted", "urls_count": len(request.urls)}
