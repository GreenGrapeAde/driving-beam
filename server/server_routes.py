import os
import cv2
import base64
import asyncio
import json
import time
import shutil
import tempfile
import zipfile
import numpy as np

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime

from fastapi import APIRouter, UploadFile, WebSocket, WebSocketDisconnect, Request, Body, HTTPException
from fastapi.responses import FileResponse

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


@dataclass
class DetCache:
    data:   Dict[str, Dict[int, Any]] = field(default_factory=dict)
    fps:    Dict[str, float]           = field(default_factory=dict)
    size:   Dict[str, tuple]           = field(default_factory=dict)
    stride: Dict[str, int]             = field(default_factory=dict)


# =========================
# Post-NMS / 필터
# =========================
def _post_nms(dets: List[Dict], iou_thr: float = 0.4) -> List[Dict]:
    if len(dets) <= 1:
        return dets
    dets = sorted(dets, key=lambda d: d["conf"], reverse=True)

    def iou(a, b):
        ix1 = max(a["x1"], b["x1"]); iy1 = max(a["y1"], b["y1"])
        ix2 = min(a["x2"], b["x2"]); iy2 = min(a["y2"], b["y2"])
        inter = max(0, ix2-ix1) * max(0, iy2-iy1)
        if inter == 0: return 0.0
        aa = (a["x2"]-a["x1"]) * (a["y2"]-a["y1"])
        ab = (b["x2"]-b["x1"]) * (b["y2"]-b["y1"])
        return inter / (aa + ab - inter)

    keep = []; suppressed = [False] * len(dets)
    for i in range(len(dets)):
        if suppressed[i]: continue
        keep.append(dets[i])
        for j in range(i+1, len(dets)):
            if not suppressed[j] and iou(dets[i], dets[j]) >= iou_thr:
                suppressed[j] = True
    return keep


def _filter_large_boxes(dets, frame_w, frame_h, max_area_ratio=0.5):
    fa = frame_w * frame_h
    return [d for d in dets if (d["x2"]-d["x1"])*(d["y2"]-d["y1"])/fa <= max_area_ratio]


# =========================
# ModelManager
# =========================
class ModelManager:
    def __init__(self):
        self.model_kind         = os.getenv("MODEL_KIND", "RTDETR")
        self.model_path         = os.getenv("MODEL_PATH", "rtdetr-l.pt")
        self.model_imgsz        = int(os.getenv("MODEL_IMGSZ", "640"))
        self.model_conf         = float(os.getenv("MODEL_CONF", "0.35"))
        self.model_iou          = float(os.getenv("MODEL_IOU", "0.3"))
        self.post_nms_iou       = float(os.getenv("POST_NMS_IOU", "0.4"))
        self.max_box_area_ratio = float(os.getenv("MAX_BOX_AREA_RATIO", "0.5"))
        _cls = os.getenv("TARGET_CLASSES", "2,5,7")
        self.target_classes = [int(c.strip()) for c in _cls.split(",")]
        self.device = "cuda:0" if torch.cuda.is_available() else "cpu"
        self._model = None

    def get_model(self):
        if self._model is None:
            if self.model_kind.upper() == "RTDETR" or "rtdetr" in self.model_path.lower():
                self._model = RTDETR(self.model_path)
            else:
                self._model = YOLO(self.model_path)
            try: self._model.to(self.device)
            except: pass
        return self._model

    def run_ai_inference(self, frame_bgr) -> List[Dict[str, Any]]:
        model     = self.get_model()
        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        is_rtdetr = self.model_kind.upper() == "RTDETR" or "rtdetr" in self.model_path.lower()

        results = model.predict(
            source=frame_rgb, imgsz=self.model_imgsz,
            conf=self.model_conf, iou=self.model_iou,
            classes=self.target_classes, device=self.device,
            half=True, verbose=False,
        ) if is_rtdetr else model.track(
            source=frame_rgb, imgsz=self.model_imgsz,
            conf=self.model_conf, iou=self.model_iou,
            classes=self.target_classes, device=self.device,
            half=True, verbose=False,
        )

        r0  = results[0]
        ids = None
        if not is_rtdetr:
            try: ids = r0.boxes.id
            except: pass

        dets = []
        if r0.boxes is None or len(r0.boxes) == 0:
            return dets

        names = r0.names
        h, w  = frame_bgr.shape[:2]

        for i, b in enumerate(r0.boxes):
            x1, y1, x2, y2 = b.xyxy[0].tolist()
            conf   = float(b.conf[0].item()) if hasattr(b.conf[0], "item") else float(b.conf[0])
            cls_id = int(b.cls[0].item())    if hasattr(b.cls[0],  "item") else int(b.cls[0])
            x1 = max(0, min(w-1, int(round(x1)))); y1 = max(0, min(h-1, int(round(y1))))
            x2 = max(0, min(w-1, int(round(x2)))); y2 = max(0, min(h-1, int(round(y2))))
            cls_name = names.get(cls_id, str(cls_id)) if isinstance(names, dict) else (
                names[cls_id] if cls_id < len(names) else str(cls_id))
            det = {"x1": x1, "y1": y1, "x2": x2, "y2": y2,
                   "cls": str(cls_name), "conf": float(conf)}
            if ids is not None:
                try: det["id"] = int(ids[i].item())
                except: pass
            dets.append(det)

        dets = _post_nms(dets, self.post_nms_iou)
        dets = _filter_large_boxes(dets, w, h, self.max_box_area_ratio)
        return dets


@dataclass
class AppState:
    config:    AppConfig
    manual:    ManualCache  = field(default_factory=ManualCache)
    model_mgr: ModelManager = field(default_factory=ModelManager)
    det_cache: DetCache      = field(default_factory=DetCache)


def get_state(request_or_ws) -> AppState:
    return request_or_ws.app.state.app_state


# =========================
# Playback crop 헬퍼
# =========================
def _ensure_dirs(root):
    for s in ["train", "valid", "test"]:
        os.makedirs(os.path.join(root, s, "images"), exist_ok=True)
        os.makedirs(os.path.join(root, s, "images_full"), exist_ok=True)
        os.makedirs(os.path.join(root, s, "labels"), exist_ok=True)

def _write_dataset_yaml(root):
    with open(os.path.join(root, "dataset.yaml"), "w") as f:
        f.write("path: .\ntrain: train/images\nval: valid/images\ntest: test/images\n\n"
                "names:\n  0: car\n  1: bus\n  2: truck\n")

def _write_readme(root, stats):
    with open(os.path.join(root, "README.txt"), "w") as f:
        for k, v in stats.items(): f.write(f"- {k}: {v}\n")

def _coco_to_occ(cls_name):
    n = (cls_name or "").lower()
    if n == "car":   return 0
    if n == "bus":   return 1
    if n == "truck": return 2
    return None

def _pick_split(idx):
    r = idx % 10
    return "train" if r < 8 else ("valid" if r < 9 else "test")

def _bbox_to_yolo(ox1, oy1, ox2, oy2, cx1, cy1, cw, ch):
    rx1 = max(0, min(cw, ox1-cx1)); ry1 = max(0, min(ch, oy1-cy1))
    rx2 = max(0, min(cw, ox2-cx1)); ry2 = max(0, min(ch, oy2-cy1))
    if rx2 <= rx1 or ry2 <= ry1: return None
    return (f"{(rx1+rx2)/2/cw:.6f} {(ry1+ry2)/2/ch:.6f} "
            f"{(rx2-rx1)/cw:.6f} {(ry2-ry1)/ch:.6f}")

def _crop_and_save(frame, det, frame_w, frame_h, target_line,
                   ds_root, img_idx) -> bool:
    """
    det 하나를 amodal(가려진 부분까지 포함한 전체 객체) 크롭하여 저장.
    성공하면 True, 건너뛰면 False 반환.
    """
    occ_cls = _coco_to_occ(det.get("cls"))
    if occ_cls is None:
        return False

    ox1, oy1 = int(det["x1"]), int(det["y1"])
    ox2, oy2 = int(det["x2"]), int(det["y2"])

    # 중심이 target_line 오른쪽이면 스킵
    if (ox1 + ox2) // 2 > target_line:
        return False

    cls_name = det.get("cls", "").lower()
    box_h    = oy2 - oy1
    ext_y2   = int(oy1 + box_h * (4.0 if cls_name == "car" else 1.8))

    cx1 = max(0, ox1);       cy1 = max(0, oy1)
    cx2 = min(frame_w, ox2); cy2 = min(frame_h, ext_y2)
    if cx2 <= cx1 or cy2 <= cy1:
        return False

    crop = frame[cy1:cy2, cx1:cx2]
    if crop.size == 0:
        return False

    split = _pick_split(img_idx)
    stem  = f"sample_{img_idx:06d}"
    img_p = os.path.join(ds_root, split, "images", f"{stem}.jpg")
    img_full_p = os.path.join(ds_root, split, "images_full", f"{stem}.jpg")
    lbl_p = os.path.join(ds_root, split, "labels", f"{stem}.txt")

    if not cv2.imwrite(img_p, crop):
        return False

    cv2.imwrite(img_full_p, frame)  # 원본 이미지 저장

    yolo = _bbox_to_yolo(ox1, oy1, ox2, oy2, cx1, cy1, cx2-cx1, cy2-cy1)
    if yolo is None:
        os.remove(img_p)
        return False

    with open(lbl_p, "w") as f:
        f.write(f"{occ_cls} {yolo}\n")

    return True


# =========================
# 1) 영상 업로드
# =========================
@router.post("/upload_video")
async def upload_video(request: Request, file: UploadFile):
    st = get_state(request)
    ts_prefix     = int(time.time() * 1000)
    safe_filename = f"{ts_prefix}_{file.filename}"
    save_path     = os.path.join(st.config.video_dir, safe_filename)
    content       = await file.read()
    with open(save_path, "wb") as f:
        f.write(content)
    return {
        "message": "upload success",
        "filename": safe_filename,
        "original_filename": file.filename,
        "path": save_path,
    }


# =========================
# 2) 추론 + 크롭 동시 처리 WebSocket
#
#   클라이언트 → 서버: {filename, infer_stride, left_ratio}
#   서버 → 클라이언트:
#     {type:"meta", fps_src, frame_w, frame_h, ...}
#     {type:"progress", progress, written, remaining_sec}
#     {type:"zipping"}                     ← ZIP 생성 시작 알림
#     {type:"done", download_url, zip_name, written}
#     {type:"error", message}
#     {type:"cancelled"}
# =========================
@router.websocket("/ws/analyze")
async def analyze_video(ws: WebSocket):
    await ws.accept()
    st      = get_state(ws)
    cap     = None
    tmp_dir = None

    try:
        init_msg     = await ws.receive_text()
        init         = json.loads(init_msg)
        filename     = (init.get("filename") or "").strip()
        infer_stride = int(init.get("infer_stride") or st.config.upload_infer_stride)
        left_ratio   = float(init.get("left_ratio") or 0.4)
        video_path   = os.path.join(st.config.video_dir, filename)

        if not os.path.exists(video_path):
            await ws.send_text(json.dumps({"type": "error", "message": "file not found"}))
            return

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            await ws.send_text(json.dumps({"type": "error", "message": "cannot open video"}))
            return

        fps_src      = cap.get(cv2.CAP_PROP_FPS) or float(st.config.target_fps)
        frame_w      = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)  or 0)
        frame_h      = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)  or 0)
        infer_frames = max(1, total_frames // infer_stride)
        target_line  = int(frame_w * left_ratio)

        await ws.send_text(json.dumps({
            "type": "meta",
            "fps_src": fps_src, "frame_w": frame_w, "frame_h": frame_h,
            "total_frames": total_frames, "infer_frames": infer_frames,
            "infer_stride": infer_stride, "left_ratio": left_ratio,
        }))

        # 데이터셋 임시 디렉토리 준비
        export_dir = os.getenv("EXPORT_DIR", "exports")
        os.makedirs(export_dir, exist_ok=True)
        tmp_dir     = tempfile.mkdtemp(prefix="occ_export_")
        created_at  = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        ds_name     = f"occ_dataset_{created_at}"
        ds_root     = os.path.join(tmp_dir, ds_name)
        os.makedirs(ds_root, exist_ok=True)
        _ensure_dirs(ds_root)
        _write_dataset_yaml(ds_root)

        det_map     = {}   # playback 오버레이용 캐시
        meta_samples = []   # metadata 저장용 list
        frame_count = 0
        infer_count = 0
        img_idx     = 0    # 저장된 이미지 인덱스
        written     = 0    # 저장 성공 수
        t0          = time.time()
        last_pct    = -1

        while cap.isOpened():
            # 취소 메시지 확인
            try:
                msg  = await asyncio.wait_for(ws.receive_text(), timeout=0.001)
                ctrl = json.loads(msg)
                if ctrl.get("type") == "control" and ctrl.get("action") == "cancel":
                    await ws.send_text(json.dumps({"type": "cancelled"}))
                    return
            except asyncio.TimeoutError:
                pass
            except WebSocketDisconnect:
                return

            ret, frame = cap.read()
            if not ret:
                break

            frame_count += 1
            if frame_count % infer_stride != 0:
                continue

            # ── 추론 ──────────────────────────────────────
            dets = st.model_mgr.run_ai_inference(frame)
            t_ms = (frame_count / fps_src) * 1000.0

            # playback 오버레이용 캐시 저장
            det_map[frame_count] = {"t_ms": t_ms, "detections": dets}

            
            # ── 추론 결과로 즉시 크롭 저장 ────────────────
            for det in dets:
                ok = _crop_and_save(
                    frame, det, frame_w, frame_h, target_line,
                    ds_root, img_idx,
                )
                if ok:
                    split = _pick_split(img_idx)
                    meta_samples.append({
                        "id":            f"sample_{img_idx:06d}",
                        "split":         split,
                        "timestamp_sec": round(t_ms / 1000, 2),
                        "frame_index":   frame_count,
                        "class_name":    det.get("cls", ""),
                    })
                    img_idx += 1
                    written += 1

            infer_count += 1

            # 진행률 (1% 단위)
            pct = min(99, int(infer_count / infer_frames * 100))
            if pct != last_pct:
                last_pct = pct
                elapsed  = time.time() - t0
                fps_est  = infer_count / max(elapsed, 1e-6)
                eta      = max(0, (infer_frames - infer_count) / max(fps_est, 1e-6))
                await ws.send_text(json.dumps({
                    "type":          "progress",
                    "progress":      pct,
                    "written":       written,
                    "remaining_sec": round(eta),
                }))
                await asyncio.sleep(0)  # event loop yield

        # ── 메모리 캐시 저장 (playback 오버레이용) ────────
        st.det_cache.data[filename]   = det_map
        st.det_cache.fps[filename]    = fps_src
        st.det_cache.size[filename]   = (frame_w, frame_h)
        st.det_cache.stride[filename] = infer_stride

        # ── ZIP 생성 알림 ─────────────────────────────────
        await ws.send_text(json.dumps({"type": "zipping", "progress": 99, "written": written}))
        await asyncio.sleep(0)

        # ── README 작성 ───────────────────────────────────
        _write_readme(ds_root, {
            "created_at":   created_at,
            "total_images": written,
            "left_ratio":   left_ratio,
            "splits":       "train:valid:test=8:1:1",
        })

        # ── metadat.json 생성 ───────────────────────────────────
        with open(os.path.join(ds_root, "metadata.json"), "w", encoding="utf-8") as f:
            json.dump({"samples": meta_samples}, f, indent=2, ensure_ascii=False)
        # ── ZIP 압축 ──────────────────────────────────────
        zip_name = f"{ds_name}.zip"
        zip_path = os.path.join(export_dir, zip_name)
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for rd, _, files in os.walk(ds_root):
                for fn in files:
                    abs_p = os.path.join(rd, fn)
                    zf.write(abs_p, os.path.relpath(abs_p, tmp_dir))

        written_counts = {}
        for s in meta_samples:
            cls = s["class_name"]
            written_counts[cls] = written_counts.get(cls, 0) + 1

        await ws.send_text(json.dumps({
            "type":         "done",
            "progress":     100,
            "written":      written,
            "zip_name":     zip_name,
            "download_url": f"/export_download/{zip_name}",
            "total_inferred": infer_count,
            "written_counts": written_counts,
        }))

    except WebSocketDisconnect:
        pass
    except Exception as e:
        print("Analyze WS error:", e)
        try: await ws.send_text(json.dumps({"type": "error", "message": str(e)}))
        except: pass
    finally:
        if cap is not None:
            cap.release()
        if tmp_dir:
            shutil.rmtree(tmp_dir, ignore_errors=True)
        try: await ws.close()
        except: pass


# =========================
# 3) 전체 det 조회 (playback 오버레이용)
# =========================
@router.get("/det/all")
async def get_det_all(request: Request, filename: str):
    st = get_state(request)
    det_map = st.det_cache.data.get(filename)
    if det_map is None:
        raise HTTPException(status_code=404, detail="no cache. analyze first.")

    result = [
        {"frame_index": fi, "t_ms": entry["t_ms"], "detections": entry["detections"]}
        for fi, entry in sorted(det_map.items())
    ]
    return {
        "filename":     filename,
        "fps_src":      st.det_cache.fps[filename],
        "frame_w":      st.det_cache.size[filename][0],
        "frame_h":      st.det_cache.size[filename][1],
        "infer_stride": st.det_cache.stride[filename],
        "count":        len(result),
        "detections":   result,
    }


# =========================
# 4) ZIP 다운로드
# =========================
@router.get("/export_download/{zip_name}")
async def export_download(zip_name: str):
    export_dir = os.getenv("EXPORT_DIR", "exports")
    zip_path   = os.path.join(export_dir, zip_name)
    if not os.path.exists(zip_path):
        raise HTTPException(status_code=404, detail="zip not found")
    return FileResponse(
        path=zip_path, media_type="application/zip", filename=zip_name,
        headers={"Content-Disposition": f'attachment; filename="{zip_name}"'},
    )


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
# Manual - ROI 추출하기
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

    # ROI ? íš¨??ì²´í¬
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

    # display -> frame ROI ë³€??
    if disp_w and disp_h:
        try:
            roi_frame = _convert_roi(roi, frame_w, frame_h, float(disp_w), float(disp_h))
        except Exception as e:
            cap.release()
            return {"ok": False, "error": f"roi convert failed: {e}"}
    else:
        roi_frame = roi

    # ?œìž‘ ?œì  ?´ë™
    cap.set(cv2.CAP_PROP_POS_MSEC, start_sec * 1000.0)

    # tì´??™ì•ˆ "?°ì†" ?„ë ˆ????= t * 30
    total_frames = max(int(round(t_sec_f * fps)), 1)

    x = int(roi_frame["x"]); y = int(roi_frame["y"])
    w = int(roi_frame["w"]); h = int(roi_frame["h"])

    # bounds clamp
    x = max(0, min(frame_w - 1, x))
    y = max(0, min(frame_h - 1, y))
    w = max(1, min(frame_w - x, w))
    h = max(1, min(frame_h - y, h))

    previews: List[str] = []

    # ?€?¥ì? ???˜ê³  previewë§?ë§Œë“ ??
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

    # cache ?€??app.state)
    st.manual.previews = previews
    st.manual.total = len(previews)

    st.manual.last_video_path = video_path
    st.manual.last_roi_frame = {"x": x, "y": y, "w": w, "h": h}
    st.manual.last_t_sec = float(t_sec_f)
    st.manual.last_save_dir = save_dir
    st.manual.last_start_sec = float(start_sec)

    return {
        "ok": True,
        "total": st.manual.total,       # ?•ìƒ?´ë©´ t=1 -> 30
        "items": previews,              # ê·¸ë¦¬?œë¡œ ë°”ë¡œ ë³´ì—¬ì£¼ê¸° ?¸í•˜ê²??„ì²´ ë°˜í™˜
        "roiFrame": {"x": x, "y": y, "w": w, "h": h},
        "startSec": start_sec,
        "requestedFrames": total_frames,
        "fpsUsed": fps,
    }


# =========================
# Manual - 미리보기
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
# Manual - 저장하기
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

# ============================================================================
# 서버 상태 ping으로 받기
# ============================================================================
@router.get("/health")
async def health():
    return {"ok": True}


# ════════════════════════════════════════════════════════════════
# 15. Live MJPEG (GoPro)
# ════════════════════════════════════════════════════════════════
from fastapi.responses import StreamingResponse

async def _mjpeg_generator(model_mgr, cap_index: int = 1):
    cap = cv2.VideoCapture(cap_index, cv2.CAP_DSHOW)
    try:
        while True:
            ret, frame = cap.read()
            if not ret or frame is None:
                await asyncio.sleep(0.01)
                continue

            # AI 추론 + 오버레이
            dets = model_mgr.run_ai_inference(frame)
            for d in dets:
                cv2.rectangle(frame, (d["x1"], d["y1"]), (d["x2"], d["y2"]), (0, 0, 255), 2)
                cv2.putText(frame, d["cls"], (d["x1"], d["y1"] - 5),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)

            ok, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
            if not ok:
                continue

            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n\r\n" +
                buf.tobytes() +
                b"\r\n"
            )

            await asyncio.sleep(1 / 30)  # 30fps
    finally:
        cap.release()


@router.get("/live/mjpeg")
async def live_mjpeg(request: Request):
    st = get_state(request)
    return StreamingResponse(
        _mjpeg_generator(st.model_mgr, cap_index=1),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )