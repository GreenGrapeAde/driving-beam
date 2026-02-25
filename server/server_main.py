import os
from dataclasses import dataclass
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from server_routes import router, AppState, AppConfig


def create_app() -> FastAPI:
    app = FastAPI()

    # =========================
    # CORS 설정 (Vue 다른 PC 접속 허용)
    # =========================
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # 개발 단계 전체 허용
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # =========================
    # 업로드 저장 폴더
    # =========================
    video_dir = os.getenv("VIDEO_DIR", "videos")
    os.makedirs(video_dir, exist_ok=True)

    # =========================
    # 설정값(환경변수 기반)
    # =========================
    config = AppConfig(
        video_dir=video_dir,
        target_fps=int(os.getenv("TARGET_FPS", "30")),
        upload_infer_stride=int(os.getenv("UPLOAD_INFER_STRIDE", "10")),
        live_infer_stride=int(os.getenv("LIVE_INFER_STRIDE", "1")),
    )

    # =========================
    # 전역 상태(app.state)에 모든 공유변수 몰아넣기
    # =========================
    app.state.app_state = AppState(config=config)

    # 라우터 등록
    app.include_router(router)

    return app


app = create_app()