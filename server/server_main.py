import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from server_routes import router, AppState, AppConfig


def create_app() -> FastAPI:
    app = FastAPI()

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    video_dir = os.getenv("VIDEO_DIR", "videos")
    os.makedirs(video_dir, exist_ok=True)

    export_dir = os.getenv("EXPORT_DIR", "exports")
    os.makedirs(export_dir, exist_ok=True)

    config = AppConfig(
        video_dir=video_dir,
        target_fps=int(os.getenv("TARGET_FPS", "30")),
        upload_infer_stride=int(os.getenv("UPLOAD_INFER_STRIDE", "10")),
        live_infer_stride=int(os.getenv("LIVE_INFER_STRIDE", "1")),
    )

    app.state.app_state = AppState(config=config)

    app.include_router(router)

    return app


app = create_app()