## ========================================================
## 모듈 로딩
## ========================================================
import os
import cv2

from PyQt5.QtWidgets import *
from PyQt5 import uic                       # Qt Designer로 만든 ui파일 -> python 코드
from PyQt5.QtGui import QImage, QPixmap     # QImage: 이미지 데이터
                                            # QPixmap: QLabel 등에 표시용 이미지
from PyQt5.QtCore import QTimer             # 일정 시간마다 특정 함수를 반복 실행할 타이머


## ========================================================
## 영상 파일 열기
## ========================================================
def load_video(path):
    cap = cv2.VideoCapture(path)
    return cap


## ========================================================
## 영상 재생 시작
## ========================================================
def start_video(timer):
    timer.start(30)    # 30ms마다 timeout 발생 -> 약 33fps (1초/0.03초 ≈ 33)


## ========================================================
## 영상 프레임을 읽어서 QLabel에 띄우는 함수
## ========================================================
def display_frame(self):
    self.current_frame = frame.copy()


    if not self.cap:        ## 영상 로드 안 됐으면 아무것도 하지 않음
        return

    ret, frame = self.cap.read()        ## 영상에서 프레임(한 장의 이미지)을 읽음

    if not ret:                 ## 프레임 못 읽을 경우
        self.timer.stop()
        self.cap.release()      ## 영상 닫기
        return

    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)  ## 색상 변환해야 색이 정상으로 보임
    h, w, c = frame.shape

    ## w*c: 한 줄(가로 한 줄)
    ## QImage.Format_RGB888: RGB 3채널(24bit) 형식
    q_img = QImage(frame.data, w, h, w * c, QImage.Format_RGB888)
    pixmap = QPixmap.fromImage(q_img)  # QImage QPixmap으로 변환

    ## QLabel 크기에 맞게 이미지 리사이즈
    self.image.setPixmap(
        pixmap.scaled(self.image.width(), self.image.height())
    )