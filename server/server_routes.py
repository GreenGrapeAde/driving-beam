import os
import cv2
import base64
import asyncio
import json
import time
import numpy as np

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, UploadFile, WebSocket, WebSocketDisconnect, Request

# AI
import torch
from ultralytics import YOLO, RTDETR

router = APIRouter()


# =========================
# Config / State
# =========================
@dataclass
class AppConfig:
    video_dir: str = "videos"
    target_fps: int = 30
    upload_infer_stride: int = 10
    live_infer_stride: int = 1


@dataclass
class ManualCache:
    previews: List[str] = field(default_factory=list)
    total: int = 0

    last_video_path: str = ""
    last_roi_frame: Optional[Dict[str, int]] = None
    last_t_sec: float = 0.0
    last_save_dir: str = ""
    last_start_sec: float = 0.0


class ModelManager:
    def __init__(self):
        self.model_kind = os.getenv("MODEL_KIND", "RTDETR")  # "YOLO" or "RTDETR"
        self.model_path = os.getenv("MODEL_PATH", "rtdetr-l.pt")
        self.model_imgsz = int(os.getenv("MODEL_IMGSZ", "1280"))
        self.model_conf = float(os.getenv("MODEL_CONF", "0.25"))

        # COCO Í∏∞Ï? ?êÎèôÏ∞??§ÌÜ†Î∞îÏù¥/Î≤ÑÏä§/?∏Îü≠Îß?
        self.target_classes = [2, 3, 5, 7]

        self.tracker_cfg = os.getenv("TRACKER_CFG", "botsort.yaml")  # or "bytetrack.yaml"

        self.device = "cuda:0" if torch.cuda.is_available() else "cpu"
        self._model = None

    def get_model(self):
        if self._model is None:
            if self.model_kind.upper() == "RTDETR" or ("rtdetr" in self.model_path.lower()):
                self._model = RTDETR(self.model_path)
            else:
                self._model = YOLO(self.model_path)

            # Î™ÖÏãú?ÅÏúºÎ°?device ?¨Î¶¨Í∏?Í∞Ä?•ÌïòÎ©?
            try:
                self._model.to(self.device)
            except Exception:
                pass
        return self._model

    def run_ai_inference(self, frame_bgr) -> List[Dict[str, Any]]:
        model = self.get_model()
        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)

        results = model.track(
            source=frame_rgb,
            imgsz=self.model_imgsz,
            conf=self.model_conf,
            classes=self.target_classes,
            tracker=self.tracker_cfg,
            persist=True,
            device=self.device,
            verbose=False,
        )

        r0 = results[0]
        dets: List[Dict[str, Any]] = []
        if r0.boxes is None or len(r0.boxes) == 0:
            return dets

        names = r0.names
        h, w = frame_bgr.shape[:2]

        ids = None
        try:
            ids = r0.boxes.id
        except Exception:
            ids = None

        for i, b in enumerate(r0.boxes):
            x1, y1, x2, y2 = b.xyxy[0].tolist()
            conf = float(b.conf[0].item()) if hasattr(b.conf[0], "item") else float(b.conf[0])
            cls_id = int(b.cls[0].item()) if hasattr(b.cls[0], "item") else int(b.cls[0])

            x1 = max(0, min(w - 1, int(round(x1))))
            y1 = max(0, min(h - 1, int(round(y1))))
            x2 = max(0, min(w - 1, int(round(x2))))
            y2 = max(0, min(h - 1, int(round(y2))))

            try:
                cls_name = names[cls_id]
            except Exception:
                cls_name = str(cls_id)

            det = {"x1": x1, "y1": y1, "x2": x2, "y2": y2, "cls": str(cls_name), "conf": float(conf)}

            if ids is not None:
                try:
                    det["id"] = int(ids[i].item())
                except Exception:
                    pass

            dets.append(det)

        return dets


@dataclass
class AppState:
    config: AppConfig
    manual: ManualCache = field(default_factory=ManualCache)
    model_mgr: ModelManager = field(default_factory=ModelManager)


def get_state(request_or_ws) -> AppState:
    # Request / WebSocket Î™®Îëê .app.state ?ëÍ∑º Í∞Ä??
    return request_or_ws.app.state.app_state


# =========================
# Utils
# =========================
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
# 1) ?ÖÎ°ú???ÅÏÉÅ API
# =========================
@router.post("/upload_video")
async def upload_video(request: Request, file: UploadFile):
    st = get_state(request)
    save_path = os.path.join(st.config.video_dir, file.filename)
    with open(save_path, "wb") as f:
        f.write(await file.read())
    return {"message": "upload success", "filename": file.filename, "path": save_path}


# =========================
# 2) ?ÖÎ°ú???ÅÏÉÅ ?§Ìä∏Î¶¨Î∞ç
# =========================
@router.websocket("/ws/stream/upload")
async def stream_uploaded_video(ws: WebSocket):
    await ws.accept()
    st = get_state(ws)

    try:
        init_msg = await ws.receive_text()
        init = json.loads(init_msg)
        filename = (init.get("filename") or "").strip()
        video_path = os.path.join(st.config.video_dir, filename)

        if not os.path.exists(video_path):
            await ws.send_text(json.dumps({"type": "error", "message": "file not found"}))
            await ws.close()
            return

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            await ws.send_text(json.dumps({"type": "error", "message": "cannot open video"}))
            await ws.close()
            return

        fps_src = cap.get(cv2.CAP_PROP_FPS) or float(st.config.target_fps)
        frame_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
        frame_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)

        infer_stride = st.config.upload_infer_stride
        frame_count = 0
        last_detections = []

        # Î©îÌ? Î®ºÏ? Î≥¥ÎÇ¥Í∏?(?¥Îùº overlay ?§Ï???Í≥ÑÏÇ∞???ÑÏöî)
        await ws.send_text(json.dumps({
            "type": "meta",
            "mode": "upload",
            "fps_src": fps_src,
            "frame_w": frame_w,
            "frame_h": frame_h,
            "infer_stride": infer_stride,
        }))

        paused = False
        stop_flag = False
        end_sent = False

        t0 = time.time()
        sent = 0

        while cap.isOpened():
            # ---- control Ï≤òÎ¶¨ ----
            while True:
                try:
                    msg = await asyncio.wait_for(ws.receive_text(), timeout=0.003)
                    ctrl = json.loads(msg)
                    if ctrl.get("type") == "control":
                        action = ctrl.get("action")
                        if action == "pause":
                            paused = True
                            await ws.send_text(json.dumps({"type": "state", "state": "PAUSED"}))
                        elif action == "resume":
                            paused = False
                            await ws.send_text(json.dumps({"type": "state", "state": "PLAYING"}))
                        elif action == "seek":
                            try:
                                t_ms = float(ctrl.get("t_ms") or 0.0)
                                cap.set(cv2.CAP_PROP_POS_MSEC, t_ms)
                                frame_count = int(round((t_ms / 1000.0) * fps_src))
                                last_detections = []
                                t0 = time.time()
                                sent = 0
                                await ws.send_text(json.dumps({"type": "state", "state": "SEEKED", "t_ms": t_ms}))
                            except Exception:
                                await ws.send_text(json.dumps({"type": "state", "state": "SEEK_FAILED"}))
                        elif action == "stop":
                            stop_flag = True
                            await ws.send_text(json.dumps({"type": "end", "mode": "upload", "message": "stopped"}))
                            end_sent = True
                            break
                except asyncio.TimeoutError:
                    break
                except WebSocketDisconnect:
                    stop_flag = True
                    break
                except Exception:
                    break

            if stop_flag:
                break

            if paused:
                await asyncio.sleep(0.05)
                continue

            ret, frame = cap.read()
            if not ret:
                break

            frame_count += 1

            # ?ÑÏû¨ ?ÑÎ†à??timestamp(ms)
            t_ms = float(cap.get(cv2.CAP_PROP_POS_MSEC) or 0.0)

            # inference??strideÎßàÎã§
            if frame_count % infer_stride == 0:
                last_detections = st.model_mgr.run_ai_inference(frame)

                sent += 1
                elapsed = max(1e-6, time.time() - t0)
                server_fps = sent / elapsed

                # det-only payload
                await ws.send_text(json.dumps({
                    "type": "det",
                    "mode": "upload",
                    "frame_index": frame_count,
                    "t_ms": t_ms,
                    "detections": last_detections,
                    "metrics": {"server_fps": server_fps, "infer_stride": infer_stride}
                }))

            # ?àÎ¨¥ Îπ®Î¶¨ Î£®ÌîÑÍ∞Ä ?ÑÎäî Í≤ÉÎßå Î∞©Ï? (?êÌïòÎ©??úÍ±∞ Í∞Ä??
            await asyncio.sleep(0)

        cap.release()

        if not end_sent:
            try:
                await ws.send_text(json.dumps({"type": "end", "mode": "upload", "message": "ended"}))
            except Exception:
                pass

        try:
            await ws.close()
        except Exception:
            pass

    except WebSocketDisconnect:
        print("Upload WebSocket disconnected")
    except Exception as e:
        print("Upload WebSocket error:", e)
        try:
            await ws.send_text(json.dumps({"type": "error", "message": str(e)}))
        except Exception:
            pass
        try:
            await ws.close()
        except Exception:
            pass


# =========================
# Manual helpers
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
# Manual - ROI Ï∂îÏ∂ú ?îÏ≤≠ API (preview ?ùÏÑ±)
# =========================
@router.post("/manual/extract")
async def manual_extract(request: Request, payload: dict):
    st = get_state(request)

    video_path = payload.get("videoPath")
    roi = payload.get("roi")
    t_sec = payload.get("t")
    disp_w = payload.get("displayW")
    disp_h = payload.get("displayH")
    start_sec = payload.get("currentTimeSec", 0)

    save_dir = (payload.get("saveDir") or "").strip()
    if not save_dir:
        return {"ok": False, "error": "saveDir required"}

    if (not video_path) or (roi is None) or (t_sec is None):
        return {"ok": False, "error": "missing parameters"}

    # ROI ?†Ìö®??Ï≤¥ÌÅ¨
    try:
        if float(roi.get("w", 0)) <= 0 or float(roi.get("h", 0)) <= 0:
            return {"ok": False, "error": "ROI required"}
    except Exception:
        return {"ok": False, "error": "invalid ROI"}

    # t(s)
    try:
        t_sec_f = float(t_sec)
        if t_sec_f <= 0:
            return {"ok": False, "error": "t(s) must be > 0"}
    except Exception:
        return {"ok": False, "error": "invalid t(s)"}

    # start sec
    try:
        start_sec = max(float(start_sec or 0), 0.0)
    except Exception:
        start_sec = 0.0

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return {"ok": False, "error": "cannot open video"}

    fps = float(st.config.target_fps)

    frame_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    # display -> frame ROI Î≥Ä??
    if disp_w and disp_h:
        try:
            roi_frame = _convert_roi(roi, frame_w, frame_h, float(disp_w), float(disp_h))
        except Exception as e:
            cap.release()
            return {"ok": False, "error": f"roi convert failed: {e}"}
    else:
        roi_frame = roi

    # ?úÏûë ?úÏ†ê ?¥Îèô
    cap.set(cv2.CAP_PROP_POS_MSEC, start_sec * 1000.0)

    # tÏ¥??ôÏïà "?∞ÏÜç" ?ÑÎ†à????= t * 30
    total_frames = max(int(round(t_sec_f * fps)), 1)

    x = int(roi_frame["x"]); y = int(roi_frame["y"])
    w = int(roi_frame["w"]); h = int(roi_frame["h"])

    # bounds clamp
    x = max(0, min(frame_w - 1, x))
    y = max(0, min(frame_h - 1, y))
    w = max(1, min(frame_w - x, w))
    h = max(1, min(frame_h - y, h))

    previews: List[str] = []

    # ?Ä?•Ï? ???òÍ≥† previewÎß?ÎßåÎì†??
    for _ in range(total_frames):
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

    # cache ?Ä??app.state)
    st.manual.previews = previews
    st.manual.total = len(previews)

    st.manual.last_video_path = video_path
    st.manual.last_roi_frame = {"x": x, "y": y, "w": w, "h": h}
    st.manual.last_t_sec = float(t_sec_f)
    st.manual.last_save_dir = save_dir
    st.manual.last_start_sec = float(start_sec)

    return {
        "ok": True,
        "total": st.manual.total,       # ?ïÏÉÅ?¥Î©¥ t=1 -> 30
        "items": previews,              # Í∑∏Î¶¨?úÎ°ú Î∞îÎ°ú Î≥¥Ïó¨Ï£ºÍ∏∞ ?∏ÌïòÍ≤??ÑÏ≤¥ Î∞òÌôò
        "roiFrame": {"x": x, "y": y, "w": w, "h": h},
        "startSec": start_sec,
        "requestedFrames": total_frames,
        "fpsUsed": fps,
    }


# =========================
# Manual - preview Í∞Ä?∏Ïò§Í∏?
# =========================
@router.get("/manual/preview")
async def manual_preview(request: Request, index: int):
    st = get_state(request)

    if not st.manual.previews:
        return {"ok": False, "error": "no previews"}

    if index < 1 or index > len(st.manual.previews):
        return {"ok": False, "error": "index out of range"}

    return {
        "ok": True,
        "index": index,
        "total": len(st.manual.previews),
        "previewBase64": st.manual.previews[index - 1],
    }


# =========================
# Manual - ?Ä??(BMP)
# =========================
@router.post("/manual/save")
async def manual_save(request: Request):
    st = get_state(request)

    if (not st.manual.last_video_path) or (not st.manual.last_roi_frame) or (not st.manual.last_t_sec) or (not st.manual.last_save_dir):
        return {"ok": False, "error": "missing cached params"}

    cap = cv2.VideoCapture(st.manual.last_video_path)
    if not cap.isOpened():
        return {"ok": False, "error": "cannot open video"}

    os.makedirs(st.manual.last_save_dir, exist_ok=True)

    if st.manual.last_start_sec:
        cap.set(cv2.CAP_PROP_POS_MSEC, float(st.manual.last_start_sec) * 1000.0)

    fps = float(st.config.target_fps)
    total_frames = max(int(st.manual.last_t_sec * fps), 1)

    saved = 0

    x = st.manual.last_roi_frame["x"]
    y = st.manual.last_roi_frame["y"]
    w = st.manual.last_roi_frame["w"]
    h = st.manual.last_roi_frame["h"]

    for _ in range(total_frames):
        ret, frame = cap.read()
        if not ret:
            break

        crop = frame[y:y + h, x:x + w]
        bmp_path = os.path.join(st.manual.last_save_dir, f"roi_{saved+1:04d}.bmp")
        cv2.imwrite(bmp_path, crop)
        saved += 1

    cap.release()
    return {"ok": True, "savedCount": saved, "dir": st.manual.last_save_dir}
