## ================================================================
## 모듈 로딩
## ================================================================
import sys
import os
import cv2

from PyQt5.QtWidgets import *
from PyQt5 import uic
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtCore import QTimer, QEvent, Qt

import logic_file      ## 함수 파일


## ================================================================
## UI Class 불러오기
## ================================================================
form_class = uic.loadUiType("PYTORCH_UI.ui")[0]
base_class = uic.loadUiType("PYTORCH_UI.ui")[1]


## ================================================================
## 클래스 정의
## ================================================================
class Program(base_class, form_class):
    def __init__(self):
        super().__init__()
        self.setupUi(self)

        self.image.setAlignment(Qt.AlignCenter)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.on_timer)

        self.crop_timer = QTimer(self)
        self.crop_timer.timeout.connect(self.auto_crop)

        self.cap = None
        self.current_frame = None  # 원본 프레임

        self.extract_mode = False
        self.drag_start = None
        self.drag_end = None

        self.crop_roi = None
        self.crop_remain_frames = 0
        self.total_save_count = 0
        self.roi_index = 0

        self.video_base_name = None
        self.save_dir = None

        self.image.setMouseTracking(True)
        self.image.installEventFilter(self)

        self.pushButton.clicked.connect(self.on_click_open_video)
        self.pushButton_2.clicked.connect(self.save_folder)
        self.pushButton_3.clicked.connect(self.on_click_extract)

    ## ============================================
    ## 영상 불러오기 버튼
    ## ============================================
    def on_click_open_video(self):
        f_path, _ = QFileDialog.getOpenFileName(
            self,
            '파일 선택',
            '',
            'Video Files (*.mp4 *.avi)'
        )

        if not f_path:        ## 취소 눌렀을 때 방어
            return

        self.cap = logic_file.load_video(f_path)
        if not self.cap.isOpened():   ## 영상 열기 실패 방어
            QMessageBox.warning(self, "오류", "영상을 열 수 없습니다.")
            return

        self.video_base_name = os.path.splitext(os.path.basename(f_path))[0]

        #---------------------------
        # 영상 기본정보 UI에 표시
        # --------------------------
        w = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = self.cap.get(cv2.CAP_PROP_FPS)

        frame_count = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))

        self.edit_w.setText(str(w))
        self.edit_h.setText(str(h))
        self.edit_fps.setText(f"{fps:.2f}")

        # 재생 시작
        logic_file.start_video(self.timer)


    ## ============================================
    ## 출력 폴더 지정 버튼
    ## ============================================
    def save_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "저장 폴더 선택")

        if folder:
            self.save_dir = folder


    ## ============================================
    ## 이미지 추출 버튼
    ## ============================================
    def on_click_extract(self):
        if self.current_frame is None:
            QMessageBox.warning(self, "오류", "먼저 영상을 재생하세요.")
            return
        
        self.extract_mode = True
        self.drag_start = None
        self.drag_end = None

        print("마우스로 ROI 영역을 드래그하세요")


    ## ============================================
    ## 이미지 추출 버튼
    ## ============================================
    def on_timer(self):
        if not self.cap:
            return

        ret, frame = self.cap.read()
        if not ret:
            self.timer.stop()
            return

        # RGB로 변환 + 원본 저장
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        self.current_frame = frame.copy()

        # 화면 표시용 프레임 (ROI 사각형은 여기에만 그림)
        display = frame.copy()

        if self.extract_mode and self.drag_start and self.drag_end:
            fx1, fy1, fx2, fy2 = logic_file.calc_roi(
                self.drag_start,
                self.drag_end,
                display.shape,
                (self.image.width(), self.image.height())
            )

            ## 초록색 테두리 그리기
            cv2.rectangle(display, (fx1, fy1), (fx2, fy2), (0, 255, 0), 2)

        ## QT창에 영상 출력
        h, w, c = display.shape
        qimg = QImage(display.data, w, h, w * c, QImage.Format_RGB888)
        pix = QPixmap.fromImage(qimg)

        # QLabel에 실제로 넣기
        self.image.setPixmap(
            pix.scaled(self.image.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        )


    ## ============================================
    ## 이미지 저장
    ## ============================================
    def save_roi(self):
        if self.current_frame is None or self.drag_start is None or self.drag_end is None:
            QMessageBox.warning(self, "오류", "프레임 또는 좌표가 없습니다.")
            return

        if not self.save_dir:
            QMessageBox.warning(self, "경로 없음", "저장 폴더를 먼저 선택하세요.")
            return

        # ROI 계산
        self.crop_roi = logic_file.calc_roi(
            self.drag_start,
            self.drag_end,
            self.current_frame.shape,
            (self.image.width(), self.image.height())
        )

        fx1, fy1, fx2, fy2 = self.crop_roi
        if fx2 - fx1 <= 0 or fy2 - fy1 <= 0:
            QMessageBox.warning(self, "ROI 오류", "선택한 영역이 너무 작습니다.")
            return

        # 입력값: t(s)
        try:
            crop_time = float(self.edit_t.text())
        except ValueError:
            QMessageBox.warning(self, "입력 오류", "t(s)를 숫자로 입력하세요.")
            return

        if crop_time <= 0:
            QMessageBox.warning(self, "입력 오류", "t(s)는 0보다 커야 합니다.")
            return

        # 입력값: rgb (비트수 @1px) — 과제 요구사항 맞추기용
        # 보통 24가 정답. 8/24/32만 허용(원하면 24만 허용해도 됨)
        try:
            rgb_bpp = int(self.edit_rgb.text())
        except ValueError:
            QMessageBox.warning(self, "입력 오류", "rgb(비트수)는 숫자로 입력하세요. 예: 24")
            return

        if rgb_bpp not in (8, 24, 32):
            QMessageBox.warning(self, "입력 오류", "rgb는 8/24/32 중 하나로 입력하세요. (일반적으로 24)")
            return

        fps_fixed = 30
        interval = int(1000 / fps_fixed)  # 33ms

        total_frames = int(round(crop_time * fps_fixed))
        if total_frames <= 0:
            QMessageBox.warning(self, "입력 오류", "t(s)가 너무 작아서 저장할 프레임이 없습니다.")
            return

        # 상태 초기화
        self.total_save_count = total_frames
        self.crop_remain_frames = total_frames
        self.roi_index = 0

        # 진행 표시
        self.label_7.setText(f"0 / {self.total_save_count}")

        # 타이머 시작
        self.crop_timer.start(interval)



    ## ============================================
    ## 이미지 추출 버튼
    ## ============================================
    def auto_crop(self):
        if self.crop_remain_frames <= 0:
            self.crop_timer.stop()
            print("자동 저장 종료")
            return

        if self.current_frame is None or self.crop_roi is None:
            return

        roi_img = logic_file.crop_frame(self.current_frame, self.crop_roi)

        self.roi_index += 1
        ok, filename = logic_file.save_roi_image(
            roi_img,
            self.save_dir,
            #self.video_base_name,
            self.roi_index
        )

        self.label_7.setText(
            f"{self.total_save_count - self.crop_remain_frames + 1} / {self.total_save_count}"
        )

        print("저장:", ok, filename)
        self.crop_remain_frames -= 1


    ## ============================================
    ## 이미지 추출 버튼
    ## ============================================
    def eventFilter(self, obj, event):
        if obj is self.image and self.extract_mode:
            if event.type() == QEvent.MouseButtonPress:
                self.drag_start = event.pos()
                self.drag_end = event.pos()
                return True

            elif event.type() == QEvent.MouseMove and self.drag_start:
                self.drag_end = event.pos()

                if self.current_frame is not None:
                    roi = logic_file.calc_roi(
                        self.drag_start,
                        self.drag_end,
                        self.current_frame.shape,
                        (self.image.width(), self.image.height())
                    )

                    fx1, fy1, fx2, fy2 = roi
                    w = fx2 - fx1
                    h = fy2 - fy1

                    roi_w = abs(fx2 - fx1)
                    roi_h = abs(fy2 - fy1)

                    # 실시간 UI 출력
                    self.edit_x.setText(str(fx1))
                    self.edit_y.setText(str(fy1))
                    self.edit_w_2.setText(str(roi_w))
                    self.edit_h_2.setText(str(roi_h))

                return True

            elif event.type() == QEvent.MouseButtonRelease:
                self.drag_end = event.pos()
                self.extract_mode = False
                self.save_roi()
                return True

        return super().eventFilter(obj, event)



if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = Program()
    win.show()
    sys.exit(app.exec_())
