import os
import cv2
import base64
import asyncio
import json
import time
import numpy as np
import pickle
from fastapi import FastAPI, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

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
VIDEO_DIR = "videos"
os.makedirs(VIDEO_DIR, exist_ok=True)

# =========================
# 설정값
# =========================
TARGET_FPS = 30
UPLOAD_INFER_STRIDE = 10
LIVE_INFER_STRIDE = 1

# =========================
# AI 모델 로딩 (pkl)
# =========================
# with open("examplemodel.pkl", "rb") as f:
#     model = pickle.load(f)
# print("AI model loaded from examplemodel.pkl")

def run_ai_inference(frame_bgr):
    """
    AI 모델 inference
    - frame_bgr: OpenCV BGR frame
    - return: detections 리스트
    예시: [{"x1":100,"y1":80,"x2":200,"y2":160,"cls":"car","conf":0.91}]
    실제 모델에 맞춰 model.predict() 사용
    """
    detections = []  # 실제 모델에서 predict 결과를 detections로 변환
    return detections

# =========================
# 시각화: 박스 + 클래스별 번호 라벨
# =========================
def draw_detections(frame_bgr, detections):
    out = frame_bgr.copy()
    cls_count = {}  # 클래스별 카운트

    for det in detections:
        x1 = int(det.get("x1", 0))
        y1 = int(det.get("y1", 0))
        x2 = int(det.get("x2", 0))
        y2 = int(det.get("y2", 0))
        cls = str(det.get("cls", "obj"))
        conf = float(det.get("conf", 0.0))

        # 클래스별 번호 붙이기
        cls_count[cls] = cls_count.get(cls, 0) + 1
        label = f"{cls}{cls_count[cls]} {conf:.2f}"

        # 박스 + 라벨
        cv2.rectangle(out, (x1,y1), (x2,y2), (0,255,0), 2)
        cv2.putText(out, label, (x1, max(20, y1-8)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,255,0), 2)
    return out

def frame_to_base64_jpg(frame_bgr, quality=80):
    ok, buffer = cv2.imencode(".jpg", frame_bgr, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
    if not ok:
        return None
    return base64.b64encode(buffer).decode("utf-8")

# =========================
# 1) 업로드 영상 API
# =========================
@app.post("/upload_video")
async def upload_video(file: UploadFile):
    save_path = os.path.join(VIDEO_DIR, file.filename)
    with open(save_path, "wb") as f:
        f.write(await file.read())
    return {"message": "upload success", "filename": file.filename, "path": save_path}

# =========================
# 2) 업로드 영상 스트리밍
# =========================
@app.websocket("/ws/stream/upload")
async def stream_uploaded_video(ws: WebSocket):
    await ws.accept()
    try:
        init_msg = await ws.receive_text()
        init = json.loads(init_msg)
        filename = init.get("filename", "").strip()
        video_path = os.path.join(VIDEO_DIR, filename)
        if not os.path.exists(video_path):
            await ws.send_text(json.dumps({"type":"error","message":"file not found"}))
            await ws.close()
            return

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            await ws.send_text(json.dumps({"type":"error","message":"cannot open video"}))
            await ws.close()
            return

        fps = cap.get(cv2.CAP_PROP_FPS) or TARGET_FPS
        skip = max(int(fps / TARGET_FPS), 1)
        frame_count = 0
        infer_stride = UPLOAD_INFER_STRIDE
        last_detections = []
        t0 = time.time()
        sent_frames = 0

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            frame_count += 1
            if fps > TARGET_FPS and (frame_count % skip != 0):
                continue

            # 10프레임마다 AI inference
            if frame_count % infer_stride == 0:
                last_detections = run_ai_inference(frame)

            vis_frame = draw_detections(frame, last_detections)
            jpg_base64 = frame_to_base64_jpg(vis_frame)
            if jpg_base64 is None:
                continue

            sent_frames += 1
            elapsed = max(1e-6, time.time()-t0)
            fps_out = sent_frames / elapsed

            payload = {
                "type": "frame",
                "mode": "upload",
                "frame_index": frame_count,
                "image_base64": jpg_base64,
                "detections": last_detections,
                "metrics": {"server_fps": fps_out, "infer_stride": infer_stride}
            }
            await ws.send_text(json.dumps(payload))
            await asyncio.sleep(1 / TARGET_FPS)

        cap.release()
        await ws.send_text(json.dumps({"type":"end","mode":"upload","message":"video stream ended"}))
        await ws.close()

    except WebSocketDisconnect:
        print("Upload WebSocket disconnected")
    except Exception as e:
        print("Upload WebSocket error:", e)
        try: await ws.send_text(json.dumps({"type":"error","message":str(e)}))
        except: pass
        await ws.close()

# =========================
# 3) Live 스트리밍
# =========================
@app.websocket("/ws/stream/live")
async def stream_live(ws: WebSocket):
    await ws.accept()
    try:
        init_msg = await ws.receive_text()
        init = json.loads(init_msg)
        mode = init.get("mode","live")
        if mode != "live":
            await ws.send_text(json.dumps({"type":"error","message":"invalid mode"}))
            await ws.close()
            return

        infer_stride = LIVE_INFER_STRIDE
        frame_count = 0
        last_detections = []
        t0 = time.time()
        recv_frames = 0
        sent_frames = 0

        while True:
            msg = await ws.receive_text()
            data = json.loads(msg)
            if data.get("type") == "control" and data.get("action") == "stop":
                await ws.send_text(json.dumps({"type":"end","mode":"live","message":"live stopped by client"}))
                break
            if data.get("type") != "frame":
                continue

            img_b64 = data.get("image_base64","")
            if not img_b64:
                continue

            jpg_bytes = base64.b64decode(img_b64)
            np_arr = np.frombuffer(jpg_bytes, dtype=np.uint8)
            frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
            if frame is None:
                continue

            frame_count += 1
            recv_frames += 1

            # 매 프레임 inference
            if frame_count % infer_stride == 0:
                last_detections = run_ai_inference(frame)

            vis_frame = draw_detections(frame, last_detections)
            out_b64 = frame_to_base64_jpg(vis_frame, quality=75)
            if out_b64 is None:
                continue

            sent_frames += 1
            elapsed = max(1e-6, time.time()-t0)
            fps_in = recv_frames / elapsed
            fps_out = sent_frames / elapsed

            payload = {
                "type": "frame",
                "mode": "live",
                "frame_index": frame_count,
                "image_base64": out_b64,
                "detections": last_detections,
                "metrics": {"recv_fps": fps_in, "send_fps": fps_out, "infer_stride": infer_stride}
            }
            await ws.send_text(json.dumps(payload))

    except WebSocketDisconnect:
        print("Live WebSocket disconnected")
    except Exception as e:
        print("Live WebSocket error:", e)
        try: await ws.send_text(json.dumps({"type":"error","message":str(e)}))
        except: pass
    finally:
        await ws.close()


# =========================
# Manual - ROI 추출 요청 API
# =========================
@app.post("/manual/extract")
async def manual_extract(payload: dict):
    video_path = payload.get("videoPath")
    roi = payload.get("roi")
    t_sec = payload.get("t")
    rgb = payload.get("rgb")
    save_dir = payload.get("saveDir")

    if not video_path or not roi:
        return {"ok": False, "error": "missing parameters"}

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return {"ok": False, "error": "cannot open video"}

    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    total_frames = int(t_sec * fps)

    previews = []
    count = 0

    x = roi["x"]
    y = roi["y"]
    w = roi["w"]
    h = roi["h"]

    while count < total_frames:
        ret, frame = cap.read()
        if not ret:
            break

        crop = frame[y:y+h, x:x+w]
        ok, buffer = cv2.imencode(".jpg", crop)

        if ok:
            b64 = base64.b64encode(buffer).decode()
            previews.append(b64)

        count += 1

    cap.release()

    return {
        "ok": True,
        "total": len(previews),
        "items": previews[:1],  # 첫 장만
        "roiFrame": roi
    }

# =========================
# Manual - preview 가져오기 (일단 첫장만)
# =========================
@app.get("/manual/preview")
async def manual_preview(index: int):
    # 실제 구현에서는 메모리 캐시에서 반환
    return {"ok": True, "previewBase64": "..."}