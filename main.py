import os
import logging
import threading
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from config import settings
from scheduler import scheduler_instance
from upload_manager import upload_manager
from logger_service import logger_service
from sequence_manager import sequence_manager


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting OTA ReelFlow Agent...")
    scheduler_instance.start()
    logger.info(f"Scheduler started with {len(settings.upload_times_list)} jobs")

    def startup_upload():
        try:
            logger.info("Startup upload triggered")
            success, filename, video_id, error = scheduler_instance.trigger_manual_upload()
            if success:
                logger.info(f"Startup upload completed: {filename} -> {video_id}")
            else:
                logger.warning(f"Startup upload failed: {filename} - {error}")
        except Exception as e:
            logger.error(f"Startup upload exception: {e}")

    threading.Thread(target=startup_upload, daemon=True).start()

    yield
    logger.info("Shutting down OTA ReelFlow Agent...")
    scheduler_instance.stop()


app = FastAPI(
    title="OTA ReelFlow Agent",
    description="AI-powered YouTube Shorts sequential uploader from Google Drive",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class UploadResponse(BaseModel):
    success: bool
    filename: str | None
    video_id: str | None
    error: str | None
    message: str


class StatusResponse(BaseModel):
    sequence: dict
    pending_count: int
    next_pending: str | None
    scheduler_jobs: list[dict]
    upload_stats: dict


@app.get("/", tags=["Health"])
async def root():
    return {"status": "running", "service": "OTA ReelFlow Agent", "version": "1.0.0"}


@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "healthy"}


@app.post("/upload/trigger", response_model=UploadResponse, tags=["Upload"])
async def trigger_upload():
    try:
        success, filename, video_id, error = scheduler_instance.trigger_manual_upload()
        return UploadResponse(
            success=success,
            filename=filename,
            video_id=video_id,
            error=error,
            message="Upload completed successfully" if success else f"Upload failed: {error}",
        )
    except Exception as e:
        logger.error(f"Upload trigger error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/status", response_model=StatusResponse, tags=["Status"])
async def get_status():
    try:
        status = upload_manager.get_status()
        jobs = scheduler_instance.get_jobs()
        logs = logger_service.get_upload_logs()
        return StatusResponse(
            sequence=status["sequence"],
            pending_count=status["pending_count"],
            next_pending=status["next_pending"],
            scheduler_jobs=jobs,
            upload_stats=logs.get("stats", {}),
        )
    except Exception as e:
        logger.error(f"Status error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/logs", tags=["Logs"])
async def get_logs(limit: int = 20):
    history = logger_service.get_upload_history(limit)
    return {"logs": history, "count": len(history)}


@app.get("/sequence/status", tags=["Sequence"])
async def get_sequence_status():
    status = sequence_manager.get_status()
    return {"sequence": status}


@app.post("/scheduler/pause", tags=["Scheduler"])
async def pause_scheduler():
    scheduler_instance.stop()
    return {"status": "paused"}


@app.post("/scheduler/resume", tags=["Scheduler"])
async def resume_scheduler():
    scheduler_instance.start()
    return {"status": "resumed", "jobs": scheduler_instance.get_jobs()}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", 8000)), reload=False)