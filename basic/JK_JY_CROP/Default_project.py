## ========================================================
## 모듈 로딩
## ========================================================
from re import X
import sys
import os
import cv2
import time

from PyQt5.QtWidgets import *
from PyQt5 import uic                       # Qt Designer로 만든 ui파일 -> python 코드
from PyQt5.QtGui import QImage, QPixmap     # QImage: 이미지 데이터
from PyQt5.QtCore import QEvent
                                            # QPixmap: QLabel 등에 표시용 이미지
from PyQt5.QtCore import QTimer             # 일정 시간마다 특정 함수를 반복 실행할 타이머

import logic_file


## ========================================================
## UI 불러오기
## ========================================================
form_class = uic.loadUiType("PYTORCH_UI.ui")[0]

class MyWork(QWidget, form_class):  ## QMainWindow(메인창) / form_class(.ui에 있는 위젯들)
    def __init__(self):
        super().__init__()
        self.setupUi(self)  ## 부모클래스 초기화

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.on_timer)

        self.crop_timer = QTimer(self)
        self.crop_timer.timeout.connect(self.auto_crop)

        self.video_path = None
        self.cap = None

        ## 영상추출함수에 필요
        self.extract_mode = False   # 이미지 추출 모드인지
        self.drag_start = None
        self.drag_end = None
        self.current_frame = None  # 현재 프레임 저장용

        self.video_base_name = None   # 영상 파일명 (확장자 제거)
        self.roi_index = 0            # ROI 카운터

        self.crop_remain_frames = 0
        self.crop_roi = None

        self.save_dir = None

        self.image.setMouseTracking(True)
        self.image.installEventFilter(self)   # QLabel 이벤트 받기

        ## 영상 불러오기 버튼
        self.pushButton.clicked.connect(self.on_click_open_video)
        ## 출력 폴더 지정 버튼
        self.pushButton_2.clicked.connect(self.save_folder)
        ## 이미지 추출 버튼
        self.pushButton_3.clicked.connect(self.on_click_extract)

    ## ========================================================
    ## 영상 불러오기 버튼
    ## ========================================================
    def on_click_open_video(self):
        f_path, _ = QFileDialog.getOpenFileName(
            self,
            '파일 선택',                   # 다이얼로그 제목
            '',                            # 시작 폴더(빈 문자열이면 기본 위치)
            'Video Files (*.mp4 *.avi)'  # 선택 가능한 파일 확장자
        )

        if f_path:
            self.video_path = f_path
            self.cap = logic_file.load_video(f_path)

            ## 파일명(확장자 제거)
            self.video_base_name = os.path.splitext(
                os.path.basename(f_path))[0]
            
            self.roi_index = 0  ## 새 영상 열면 카운터 리셋
            
            w = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            h = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = self.cap.get(cv2.CAP_PROP_FPS)

            ## UI에 반영
            self.edit_w.setText(str(w))
            self.edit_h.setText(str(h))
            self.edit_fps.setText(f"{fps:.2f}")

            logic_file.start_video(self.timer)


    ## ========================================================
    ## 출력 폴더 지정 버튼
    ## ========================================================
    def save_folder(self):
        folder_path = QFileDialog.getExistingDirectory(
            self,
            '저장 폴더 선택',   ## 다이얼로그 제목
            ''                ## 시작 폴더
        )

        if folder_path:
            self.save_dir = folder_path
            print("저장 폴더:", self.save_dir)

    
    ## ========================================================
    ## 이미지 추출 버튼
    ## ========================================================
    def on_click_extract(self):
        print("마우스로 영상에서 영역을 드래그하세요")

        self.extract_mode = True
        self.drag_start = None
        self.drag_end = None


    ## ========================================================
    ## 타이머 연결
    ## ========================================================
    def on_timer(self):
        if self.cap is None:
            return

        ret, frame = self.cap.read()
        if not ret:
            self.timer.stop()
            self.cap.release()
            return

        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        self.current_frame = frame.copy()

        # ROI 네모 표시
        if self.extract_mode and self.drag_start and self.drag_end:
            x1 = min(self.drag_start.x(), self.drag_end.x())
            y1 = min(self.drag_start.y(), self.drag_end.y())
            x2 = max(self.drag_start.x(), self.drag_end.x())
            y2 = max(self.drag_start.y(), self.drag_end.y())

            h, w, _ = frame.shape
            lw = self.image.width()
            lh = self.image.height()

            fx1 = int(x1 * w / lw)
            fy1 = int(y1 * h / lh)
            fx2 = int(x2 * w / lw)
            fy2 = int(y2 * h / lh)

            cv2.rectangle(frame, (fx1, fy1), (fx2, fy2), (0, 255, 0), 2)

        h, w, c = frame.shape
        q_img = QImage(frame.data, w, h, w * c, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(q_img)

        self.image.setPixmap(
            pixmap.scaled(self.image.width(), self.image.height())
        )


    ## ========================================================
    ## 마우스 쿨릭
    ## ========================================================
    def mousePressEvent(self, event):
        if not self.extract_mode:
            return

        self.drag_start = event.pos()
        self.drag_end = event.pos()

        # QLabel → 프레임 좌표 변환
        h, w, _ = self.current_frame.shape
        lw = self.image.width()
        lh = self.image.height()

        fx = int(self.drag_start.x() * w / lw)
        fy = int(self.drag_start.y() * h / lh)

        # x, y 즉시 표시
        self.edit_x.setText(str(fx))
        self.edit_y.setText(str(fy))


    ## ========================================================
    ## 마우스 이동
    ## ========================================================
    def mouseMoveEvent(self, event):
        if not self.extract_mode or self.drag_start is None:
            return

        self.drag_end = event.pos()

        h, w, _ = self.current_frame.shape
        lw = self.image.width()
        lh = self.image.height()

        fx1 = int(self.drag_start.x() * w / lw)
        fy1 = int(self.drag_start.y() * h / lh)
        fx2 = int(self.drag_end.x()   * w / lw)
        fy2 = int(self.drag_end.y()   * h / lh)

        roi_w = abs(fx2 - fx1)
        roi_h = abs(fy2 - fy1)

        # w, h 실시간 업데이트
        self.edit_w_2.setText(str(roi_w))
        self.edit_h_2.setText(str(roi_h))


    ## ========================================================
    ## 마우스 버튼 off -> 저장
    ## ========================================================
    def mouseReleaseEvent(self, event):
        if not self.extract_mode or self.current_frame is None:
            return

        self.drag_end = event.pos()
        self.extract_mode = False

        self.save_roi()


    ## ========================================================
    ## ROI 영역 저장
    ## ========================================================
    def save_roi(self):
        if self.current_frame is None or self.drag_start is None or self.drag_end is None:
            QMessageBox.warning(self, "오류", "프레임 또는 좌표가 없습니다.")
            return

        if not self.save_dir:
            QMessageBox.warning(self, "경로 없음", "저장 폴더를 먼저 선택하세요.")
            return
    
        x1 = min(self.drag_start.x(), self.drag_end.x())
        y1 = min(self.drag_start.y(), self.drag_end.y())
        x2 = max(self.drag_start.x(), self.drag_end.x())
        y2 = max(self.drag_start.y(), self.drag_end.y())

        h, w, _ = self.current_frame.shape
        lw = self.image.width()
        lh = self.image.height()

        fx1 = max(0, min(w-1, int(x1 * w / lw)))
        fy1 = max(0, min(h-1, int(y1 * h / lh)))
        fx2 = max(0, min(w,   int(x2 * w / lw)))
        fy2 = max(0, min(h,   int(y2 * h / lh)))

        self.crop_roi = (fx1, fy1, fx2, fy2)

        # -------------------------------
        # 시간 (초)
        # -------------------------------
        try:
            total_time_sec = float(self.edit_t.text())
        except ValueError:
            QMessageBox.warning(self, "입력 오류", "시간(초)은 숫자로 입력하세요.")
            return

        if total_time_sec <= 0:
            QMessageBox.warning(self, "입력 오류", "시간은 0보다 커야 합니다.")
            return


        # -------------------------------
        # 저장할 이미지 개수
        # -------------------------------
        try:
            self.crop_remain_frames = int(self.edit_rgb.text())
        except ValueError:
            QMessageBox.warning(self, "입력 오류", "저장 개수는 숫자로 입력하세요.")
            return

        if self.crop_remain_frames <= 0:
            QMessageBox.warning(self, "입력 오류", "저장 개수는 1 이상이어야 합니다.")
            return
        

        # -------------------------------
        # 타이머 간격 계산 (ms)
        # -------------------------------
        interval_ms = int(total_time_sec * 1000 / self.crop_remain_frames)

        
        # -------------------------------
        # 상태 초기화
        # -------------------------------
        self.total_save_count = self.crop_remain_frames
        self.roi_index = 0
        self.label_7.setText(f"0 / {self.total_save_count}")

        print(
            f"자동 저장 시작: {total_time_sec}s 동안 "
            f"{self.total_save_count}장 저장 "
            f"(간격 {interval_ms}ms)"
        )

        # -------------------------------
        # 타이머 시작
        # -------------------------------
        self.crop_timer.start(interval_ms)


    ## ========================================================
    ## ROI 영역 자동 저장
    ## ========================================================
    def auto_crop(self):
        if self.crop_remain_frames <= 0:
            self.crop_timer.stop()
            print("자동 저장 종료")
            return

        if self.current_frame is None or self.crop_roi is None:
            return

        fx1, fy1, fx2, fy2 = self.crop_roi
        roi = self.current_frame[fy1:fy2, fx1:fx2]

        self.roi_index += 1

        save_dir = self.save_dir or os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "output"
        )
        os.makedirs(save_dir, exist_ok=True)

        filename = os.path.join(
            save_dir,
            f"{self.video_base_name}_{self.roi_index:03d}.bmp"
        )

        ok = cv2.imwrite(filename, cv2.cvtColor(roi, cv2.COLOR_RGB2BGR))
        self.label_7.setText(
        f"{self.total_save_count - self.crop_remain_frames + 1} / {self.total_save_count}"
        )

        print("저장:", ok, filename)

        self.crop_remain_frames -= 1


    ## ========================================================
    ## 
    ## ========================================================
    def update_xy(self):
        h, w, _ = self.current_frame.shape
        lw = self.image.width()
        lh = self.image.height()

        fx = int(self.drag_start.x() * w / lw)
        fy = int(self.drag_start.y() * h / lh)

        self.edit_x.setText(str(fx))
        self.edit_y.setText(str(fy))


    def update_wh(self):
        h, w, _ = self.current_frame.shape
        lw = self.image.width()
        lh = self.image.height()

        fx1 = int(self.drag_start.x() * w / lw)
        fy1 = int(self.drag_start.y() * h / lh)
        fx2 = int(self.drag_end.x()   * w / lw)
        fy2 = int(self.drag_end.y()   * h / lh)

        self.edit_w_2.setText(str(abs(fx2 - fx1)))
        self.edit_h_2.setText(str(abs(fy2 - fy1)))



    def eventFilter(self, obj, event):
        if obj is self.image and self.extract_mode:
            if event.type() == QEvent.MouseButtonPress:
                self.drag_start = event.pos()
                self.drag_end = event.pos()
                self.update_xy()
                return True

            elif event.type() == QEvent.MouseMove and self.drag_start:
                self.drag_end = event.pos()
                self.update_wh()
                return True

            elif event.type() == QEvent.MouseButtonRelease:
                self.drag_end = event.pos()
                self.extract_mode = False
                self.save_roi()
                return True

        return super().eventFilter(obj, event)



## ========================================================
# 실행
## ========================================================
if __name__ == "__main__":
    app = QApplication(sys.argv) 
    window = MyWork() 
    window.show() 
    sys.exit(app.exec_())