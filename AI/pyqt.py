# pip install pyqt6 opencv-python ultralytics torch
import os, cv2, time, zipfile, shutil
from dataclasses import dataclass
from datetime import datetime
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt5.QtGui import QImage, QPixmap, QPainter, QPen, QColor
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QProgressBar, QFileDialog, QMessageBox
)

import torch
from ultralytics import RTDETR

@dataclass
class Det:
    x1:int; y1:int; x2:int; y2:int; cls:str; conf:float

def coco_to_occ(cls_name: str):
    name = (cls_name or "").lower()
    if name == "car": return 0
    if name == "bus": return 1
    if name == "truck": return 2
    return None

class InferWorker(QThread):
    detReady = pyqtSignal(int, list)   # frame_idx, dets(List[dict])

    def __init__(self, model_path="rtdetr-l.pt", imgsz=1280, conf=0.25, device=None):
        super().__init__()
        self.model_path = model_path
        self.imgsz = imgsz
        self.conf = conf
        self.device = device or ("cuda:0" if torch.cuda.is_available() else "cpu")
        self._stop = False
        self._frame = None
        self._frame_idx = 0
        self._has_job = False
        self.target_classes = [2,3,5,7]  # COCO

        self.model = RTDETR(self.model_path)

    def submit(self, frame_bgr, frame_idx):
        # 최신 프레임만 유지(큐 폭주 방지)
        self._frame = frame_bgr
        self._frame_idx = frame_idx
        self._has_job = True

    def stop(self):
        self._stop = True

    def run(self):
        while not self._stop:
            if not self._has_job:
                time.sleep(0.005)
                continue
            frame = self._frame
            idx = self._frame_idx
            self._has_job = False
            if frame is None:
                continue

            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            try:
                results = self.model.predict(
                    source=rgb, imgsz=self.imgsz, conf=self.conf,
                    classes=self.target_classes, device=self.device, verbose=False
                )
                r0 = results[0]
                dets = []
                if r0.boxes is not None and len(r0.boxes) > 0:
                    names = r0.names
                    h, w = frame.shape[:2]
                    for b in r0.boxes:
                        x1,y1,x2,y2 = b.xyxy[0].tolist()
                        c = float(b.conf[0])
                        cls_id = int(b.cls[0])
                        cls_name = names.get(cls_id, str(cls_id)) if isinstance(names, dict) else str(cls_id)

                        x1 = max(0, min(w-1, int(round(x1))))
                        y1 = max(0, min(h-1, int(round(y1))))
                        x2 = max(0, min(w-1, int(round(x2))))
                        y2 = max(0, min(h-1, int(round(y2))))
                        dets.append({"x1":x1,"y1":y1,"x2":x2,"y2":y2,"cls":cls_name,"conf":c})
                self.detReady.emit(idx, dets)
            except Exception:
                self.detReady.emit(idx, [])

class App(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Playback + RT-DETR + Export ZIP (MVP)")
        self.video_path = None
        self.cap = None
        self.fps = 30
        self.frame_idx = 0
        self.last_dets = []

        self.view = QLabel("Open a video")
        self.view.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.view.setMinimumHeight(520)

        self.btn_open = QPushButton("Open Video")
        self.btn_play = QPushButton("Play")
        self.btn_pause = QPushButton("Pause")
        self.btn_export = QPushButton("Export ZIP")
        self.btn_export.setEnabled(False)

        self.pbar = QProgressBar()
        self.pbar.setValue(0)

        top = QHBoxLayout()
        top.addWidget(self.btn_open)
        top.addWidget(self.btn_play)
        top.addWidget(self.btn_pause)
        top.addWidget(self.btn_export)

        layout = QVBoxLayout()
        layout.addLayout(top)
        layout.addWidget(self.pbar)
        layout.addWidget(self.view)
        self.setLayout(layout)

        self.timer = QTimer()
        self.timer.timeout.connect(self.tick)

        self.worker = InferWorker()
        self.worker.detReady.connect(self.onDetReady)
        self.worker.start()

        self.btn_open.clicked.connect(self.openVideo)
        self.btn_play.clicked.connect(self.play)
        self.btn_pause.clicked.connect(self.pause)
        self.btn_export.clicked.connect(self.exportZip)

    def closeEvent(self, e):
        self.worker.stop()
        self.worker.wait(500)
        e.accept()

    def openVideo(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select video", "", "Video Files (*.mp4 *.avi *.mov)")
        if not path: return
        self.video_path = path
        if self.cap: self.cap.release()
        self.cap = cv2.VideoCapture(self.video_path)
        if not self.cap.isOpened():
            QMessageBox.critical(self, "Error", "Cannot open video")
            return
        self.fps = self.cap.get(cv2.CAP_PROP_FPS) or 30
        self.frame_idx = 0
        self.pbar.setValue(0)
        self.btn_export.setEnabled(True)
        self.showFrameOnce()

    def showFrameOnce(self):
        if not self.cap: return
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        ret, frame = self.cap.read()
        if ret:
            self.displayFrame(frame, [])

    def play(self):
        if not self.cap: return
        self.timer.start(int(1000 / 30))  # 30fps 고정 UI/동작

    def pause(self):
        self.timer.stop()

    def tick(self):
        if not self.cap: return
        ret, frame = self.cap.read()
        if not ret:
            self.timer.stop()
            return
        self.frame_idx += 1

        # 추론은 stride로 (예: 10프레임마다)
        if self.frame_idx % 10 == 0:
            self.worker.submit(frame.copy(), self.frame_idx)

        self.displayFrame(frame, self.last_dets)

        # 진행률
        total = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        if total > 0:
            self.pbar.setValue(int(100 * self.frame_idx / total))

    def onDetReady(self, idx, dets):
        # 최신 det만 적용(단순)
        self.last_dets = dets

    def displayFrame(self, frame_bgr, dets):
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        h, w = rgb.shape[:2]
        qimg = QImage(rgb.data, w, h, 3*w, QImage.Format.Format_RGB888)
        pix = QPixmap.fromImage(qimg)

        painter = QPainter(pix)
        pen = QPen(QColor("lime"))
        pen.setWidth(2)
        painter.setPen(pen)
        painter.setFont(self.font())

        for d in dets:
            x1,y1,x2,y2 = d["x1"],d["y1"],d["x2"],d["y2"]
            painter.drawRect(x1,y1,x2-x1,y2-y1)
            painter.drawText(x1, max(14, y1-6), f'{d["cls"]} {d["conf"]:.2f}')
        painter.end()

        self.view.setPixmap(pix.scaled(self.view.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))

    def exportZip(self):
        if not self.video_path:
            return
        out_path, _ = QFileDialog.getSaveFileName(self, "Save ZIP", f"occ_dataset_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip", "Zip (*.zip)")
        if not out_path:
            return
        # 여기서: 0.5초=15f 샘플링으로 프레임 읽고 det 수행 -> crop 저장 -> dataset.yaml/README 생성 -> zip
        QMessageBox.information(self, "Todo", "Export ZIP 로직은 서버 export_zip에서 쓰던 코드를 그대로 이쪽으로 옮기면 됨.")

if __name__ == "__main__":
    app = QApplication([])
    w = App()
    w.resize(1000, 720)
    w.show()
    app.exec()