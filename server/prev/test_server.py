import os
import cv2
import base64
import asyncio

from fastapi import FastAPI, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# =========================
# CORS (Vue 연결 필수)
# =========================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vue(Vite) 기본 주소
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================
# 업로드 폴더 준비
# =========================
VIDEO_DIR = "videos"
os.makedirs(VIDEO_DIR, exist_ok=True)


# =========================
# 1) 영상 업로드 REST API
# =========================
@app.post("/upload_video")
async def upload_video(file: UploadFile):
    save_path = os.path.join(VIDEO_DIR, file.filename)

    with open(save_path, "wb") as f:
        f.write(await file.read())

    return {"filename": file.filename}


# =========================
# 2) WebSocket 스트리밍
# =========================
@app.websocket("/ws/stream")
async def stream_video(ws: WebSocket):
    await ws.accept()

    try:
        # Vue가 ws://localhost:8000/ws/stream?filename=xxx.mp4 로 연결해야 함
        filename = ws.query_params.get("filename")

        if not filename:
            await ws.send_json({"type": "error", "message": "filename query param missing"})
            await ws.close()
            return

        video_path = os.path.join(VIDEO_DIR, filename)

        if not os.path.exists(video_path):
            await ws.send_json({"type": "error", "message": f"file not found: {filename}"})
            await ws.close()
            return

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            await ws.send_json({"type": "error", "message": "video open failed"})
            await ws.close()
            return

        fps = cap.get(cv2.CAP_PROP_FPS)
        if fps <= 0:
            fps = 30.0  # fps 정보가 이상하면 기본값

        target_fps = 30.0
        frame_interval = 1.0 / target_fps

        # fps가 높으면 몇 프레임마다 하나씩 보낼지 결정
        # 예: 60fps면 2프레임마다 1개
        step = max(1, int(round(fps / target_fps)))

        frame_count = 0

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            frame_count += 1

            # FPS 다운샘플링 (프레임 스킵)
            if frame_count % step != 0:
                continue

            # JPEG 인코딩 (품질 낮추면 트래픽 감소)
            ok, buffer = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
            if not ok:
                continue

            jpg_base64 = base64.b64encode(buffer).decode("utf-8")

            # Vue에서 쉽게 쓰도록 JSON으로 보냄
            await ws.send_json({
                "type": "frame",
                "fps": target_fps,
                "image": jpg_base64
            })

            await asyncio.sleep(frame_interval)

        cap.release()

        await ws.send_json({"type": "end"})
        await ws.close()

    except WebSocketDisconnect:
        print("WebSocket disconnected")
    except Exception as e:
        print("WebSocket error:", e)
        try:
            await ws.send_json({"type": "error", "message": str(e)})
        except:
            pass
        try:
            await ws.close()
        except:
            pass
