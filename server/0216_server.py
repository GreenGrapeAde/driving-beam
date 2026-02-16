# -*- coding: utf-8 -*-
import os
import cv2
import base64
import asyncio
import json
import time
import numpy as np
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

# Manual preview cache
MANUAL_PREVIEWS = []
MANUAL_TOTAL = 0

# Manual last params
LAST_VIDEO_PATH = ""
LAST_ROI_FRAME = None
LAST_T_SEC = 0
LAST_SAVE_DIR = ""
LAST_START_SEC = 0
# =========================
# 설정값
# =========================
TARGET_FPS = 30
UPLOAD_INFER_STRIDE = 10
LIVE_INFER_STRIDE = 1

# =========================
# AI inference placeholder
# =========================
def run_ai_inference(frame_bgr):
    detections = []
    return detections

def draw_detections(frame_bgr, detections):
    out = frame_bgr.copy()
    cls_count = {}

    for det in detections:
        x1 = int(det.get("x1", 0))
        y1 = int(det.get("y1", 0))
        x2 = int(det.get("x2", 0))
        y2 = int(det.get("y2", 0))
        cls = str(det.get("cls", "obj"))
        conf = float(det.get("conf", 0.0))

        cls_count[cls] = cls_count.get(cls, 0) + 1
        label = f"{cls}{cls_count[cls]} {conf:.2f}"

        cv2.rectangle(out, (x1, y1), (x2, y2), (0, 255, 0), 2)
        cv2.putText(out, label, (x1, max(20, y1 - 8)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
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
            await ws.send_text(json.dumps({"type": "error", "message": "file not found"}))
            await ws.close()
            return

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            await ws.send_text(json.dumps({"type": "error", "message": "cannot open video"}))
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

            if frame_count % infer_stride == 0:
                last_detections = run_ai_inference(frame)

            vis_frame = draw_detections(frame, last_detections)
            jpg_base64 = frame_to_base64_jpg(vis_frame)
            if jpg_base64 is None:
                continue

            sent_frames += 1
            elapsed = max(1e-6, time.time() - t0)
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
        await ws.send_text(json.dumps({"type": "end", "mode": "upload", "message": "video stream ended"}))
        await ws.close()

    except WebSocketDisconnect:
        print("Upload WebSocket disconnected")
    except Exception as e:
        print("Upload WebSocket error:", e)
        try:
            await ws.send_text(json.dumps({"type": "error", "message": str(e)}))
        except:
            pass
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
        mode = init.get("mode", "live")
        if mode != "live":
            await ws.send_text(json.dumps({"type": "error", "message": "invalid mode"}))
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
                await ws.send_text(json.dumps({"type": "end", "mode": "live", "message": "live stopped by client"}))
                break
            if data.get("type") != "frame":
                continue

            img_b64 = data.get("image_base64", "")
            if not img_b64:
                continue

            jpg_bytes = base64.b64decode(img_b64)
            np_arr = np.frombuffer(jpg_bytes, dtype=np.uint8)
            frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
            if frame is None:
                continue

            frame_count += 1
            recv_frames += 1

            if frame_count % infer_stride == 0:
                last_detections = run_ai_inference(frame)

            vis_frame = draw_detections(frame, last_detections)
            out_b64 = frame_to_base64_jpg(vis_frame, quality=75)
            if out_b64 is None:
                continue

            sent_frames += 1
            elapsed = max(1e-6, time.time() - t0)
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
        try:
            await ws.send_text(json.dumps({"type": "error", "message": str(e)}))
        except:
            pass
    finally:
        await ws.close()


## ROI 관련 ------------------------------------------------------------------------------------

# =========================
# Manual - ROI helpers
# =========================
def _map_display_to_frame(px, py, frame_w, frame_h, disp_w, disp_h):
    if frame_w <= 0 or frame_h <= 0 or disp_w <= 0 or disp_h <= 0:
        return 0, 0

    scale = min(disp_w / frame_w, disp_h / frame_h)
    disp_w2 = frame_w * scale
    disp_h2 = frame_h * scale

    off_x = (disp_w - disp_w2) / 2.0
    off_y = (disp_h - disp_h2) / 2.0

    x = min(max(px - off_x, 0.0), disp_w2)
    y = min(max(py - off_y, 0.0), disp_h2)

    fx = int(x / scale)
    fy = int(y / scale)
    return fx, fy

def _convert_roi(roi, frame_w, frame_h, disp_w, disp_h):
    x, y, w, h = roi["x"], roi["y"], roi["w"], roi["h"]
    fx1, fy1 = _map_display_to_frame(x, y, frame_w, frame_h, disp_w, disp_h)
    fx2, fy2 = _map_display_to_frame(x + w, y + h, frame_w, frame_h, disp_w, disp_h)

    x1, x2 = sorted([fx1, fx2])
    y1, y2 = sorted([fy1, fy2])

    x1 = max(0, min(frame_w - 1, x1))
    x2 = max(0, min(frame_w, x2))
    y1 = max(0, min(frame_h - 1, y1))
    y2 = max(0, min(frame_h, y2))

    return {"x": x1, "y": y1, "w": max(1, x2 - x1), "h": max(1, y2 - y1)}

# =========================
# Manual - ROI 추출 요청 API
# =========================
@app.post("/manual/extract")
async def manual_extract(payload: dict):
    video_path = payload.get("videoPath")
    roi = payload.get("roi")
    t_sec = payload.get("t")
    disp_w = payload.get("displayW")
    disp_h = payload.get("displayH")
    start_sec = payload.get("currentTimeSec", 0)

    save_dir = (payload.get("saveDir") or "").strip()

    if not save_dir:
        return {"ok": False, "error": "saveDir required"}

    
    # rgb/saveDir 더 이상 안 받음
    if (not video_path) or (roi is None) or (t_sec is None):
        return {"ok": False, "error": "missing parameters"}

    # ROI 유효성 체크
    try:
        if float(roi.get("w", 0)) <= 0 or float(roi.get("h", 0)) <= 0:
            return {"ok": False, "error": "ROI required"}
    except:
        return {"ok": False, "error": "invalid ROI"}

    # t(s)
    try:
        t_sec_f = float(t_sec)
        if t_sec_f <= 0:
            return {"ok": False, "error": "t(s) must be > 0"}
    except:
        return {"ok": False, "error": "invalid t(s)"}

    # start sec
    try:
        start_sec = max(float(start_sec or 0), 0.0)
    except:
        start_sec = 0.0

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return {"ok": False, "error": "cannot open video"}

    #  fps는 무조건 30으로 고정
    fps = float(TARGET_FPS)

    frame_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    # display -> frame ROI 변환
    if disp_w and disp_h:
        try:
            roi_frame = _convert_roi(roi, frame_w, frame_h, float(disp_w), float(disp_h))
        except Exception as e:
            cap.release()
            return {"ok": False, "error": f"roi convert failed: {e}"}
    else:
        roi_frame = roi

    # 시작 시점 이동
    cap.set(cv2.CAP_PROP_POS_MSEC, start_sec * 1000.0)

    #  t초 동안 "연속" 프레임 수 = t * 30
    total_frames = max(int(round(t_sec_f * fps)), 1)

    x = int(roi_frame["x"]); y = int(roi_frame["y"])
    w = int(roi_frame["w"]); h = int(roi_frame["h"])

    # bounds clamp
    x = max(0, min(frame_w - 1, x))
    y = max(0, min(frame_h - 1, y))
    w = max(1, min(frame_w - x, w))
    h = max(1, min(frame_h - y, h))

    previews = []

    #  저장은 안 하고 preview만 만든다
    for i in range(total_frames):
        ret, frame = cap.read()
        if not ret:
            break

        crop = frame[y:y + h, x:x + w]
        ok, buffer = cv2.imencode(".jpg", crop, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
        if ok:
            previews.append(base64.b64encode(buffer).decode())
        else:
            previews.append("")

    cap.release()

    global MANUAL_PREVIEWS, MANUAL_TOTAL
    MANUAL_PREVIEWS = previews
    MANUAL_TOTAL = len(previews)

    global LAST_VIDEO_PATH, LAST_ROI_FRAME, LAST_T_SEC, LAST_SAVE_DIR, LAST_START_SEC
    LAST_VIDEO_PATH = video_path
    LAST_ROI_FRAME = {"x": x, "y": y, "w": w, "h": h}
    LAST_T_SEC = float(t_sec_f)
    LAST_SAVE_DIR = save_dir
    LAST_START_SEC = float(start_sec)

    return {
        "ok": True,
        "total": MANUAL_TOTAL,          # 정상이면 t=1 -> 30
        "items": previews,              # 그리드로 바로 보여주기 편하게 전체 반환
        "roiFrame": {"x": x, "y": y, "w": w, "h": h},
        "startSec": start_sec,
        "requestedFrames": total_frames,
        "fpsUsed": fps,
    }


# =========================
# Manual - preview 가져오기
# =========================
@app.get("/manual/preview")
async def manual_preview(index: int):
    if not MANUAL_PREVIEWS:
        return {"ok": False, "error": "no previews"}

    if index < 1 or index > len(MANUAL_PREVIEWS):
        return {"ok": False, "error": "index out of range"}

    return {
        "ok": True,
        "index": index,
        "total": len(MANUAL_PREVIEWS),
        "previewBase64": MANUAL_PREVIEWS[index - 1],
    }




# =========================
# Manual - 저장 (BMP)
# =========================
@app.post("/manual/save")
async def manual_save():
    global LAST_VIDEO_PATH, LAST_ROI_FRAME, LAST_T_SEC, LAST_SAVE_DIR, LAST_START_SEC

    if not LAST_VIDEO_PATH or not LAST_ROI_FRAME or not LAST_T_SEC or not LAST_SAVE_DIR:
        return {"ok": False, "error": "missing cached params"}

    cap = cv2.VideoCapture(LAST_VIDEO_PATH)
    if not cap.isOpened():
        return {"ok": False, "error": "cannot open video"}

    os.makedirs(LAST_SAVE_DIR, exist_ok=True)

    if LAST_START_SEC:
        cap.set(cv2.CAP_PROP_POS_MSEC, float(LAST_START_SEC) * 1000.0)

    fps = float(TARGET_FPS)
    total_frames = max(int(LAST_T_SEC * fps), 1)

    saved = 0

    for i in range(total_frames):
        ret, frame = cap.read()
        if not ret:
            break

        x = LAST_ROI_FRAME["x"]
        y = LAST_ROI_FRAME["y"]
        w = LAST_ROI_FRAME["w"]
        h = LAST_ROI_FRAME["h"]

        crop = frame[y:y+h, x:x+w]
        bmp_path = os.path.join(LAST_SAVE_DIR, f"roi_{saved+1:04d}.bmp")
        cv2.imwrite(bmp_path, crop)
        saved += 1

    cap.release()

    return {"ok": True, "savedCount": saved, "dir": LAST_SAVE_DIR}
