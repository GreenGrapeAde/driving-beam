import os
import cv2
import base64
import asyncio
from fastapi import FastAPI, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# =========================
# CORS 설정 (Vue 다른 PC 접속 허용)
# =========================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # 개발단계라 전체 허용 (배포 시 특정 IP로 제한 추천)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================
# 업로드 저장 폴더
# =========================
VIDEO_DIR = "videos"
os.makedirs(VIDEO_DIR, exist_ok=True)


# =========================
# 1) 영상 업로드 API
# =========================
@app.post("/upload_video")
async def upload_video(file: UploadFile):
    save_path = os.path.join(VIDEO_DIR, file.filename)

    with open(save_path, "wb") as f:
        f.write(await file.read())

    return {
        "message": "upload success",
        "filename": file.filename,
        "path": save_path
    }


# =========================
# 2) WebSocket: 영상 프레임 전송
# =========================
@app.websocket("/ws/stream")
async def stream_video(ws: WebSocket):
    await ws.accept()

    try:
        # Vue가 보내는 첫 메시지: filename
        data = await ws.receive_text()
        filename = data.strip()

        video_path = os.path.join(VIDEO_DIR, filename)

        if not os.path.exists(video_path):
            await ws.send_text("ERROR: file not found")
            await ws.close()
            return

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            await ws.send_text("ERROR: cannot open video")
            await ws.close()
            return

        # 원본 FPS 확인
        fps = cap.get(cv2.CAP_PROP_FPS)
        if fps <= 0:
            fps = 30

        target_fps = 30
        frame_interval = 1 / target_fps

        # FPS > 30이면 프레임 스킵용
        skip = int(fps / target_fps) if fps > target_fps else 1
        if skip < 1:
            skip = 1

        frame_count = 0

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            frame_count += 1

            # FPS가 높으면 프레임 스킵
            if fps > target_fps and (frame_count % skip != 0):
                continue

            # JPEG 인코딩
            ok, buffer = cv2.imencode(".jpg", frame)
            if not ok:
                continue

            jpg_base64 = base64.b64encode(buffer).decode("utf-8")

            # 프레임 전송
            await ws.send_text(jpg_base64)

            # 30FPS 유지
            await asyncio.sleep(frame_interval)

        cap.release()
        await ws.close()

    except WebSocketDisconnect:
        print("WebSocket disconnected")

    except Exception as e:
        print("WebSocket error:", e)
        await ws.close()
