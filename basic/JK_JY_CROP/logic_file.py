## ================================================================
## 모듈 로딩
## ================================================================
import os
import cv2


## ================================================================
## 영상 업로드 :: 영상을 프레임 형태로 변환
## ================================================================
def load_video(path):
    return cv2.VideoCapture(path)


## ================================================================
## 영상 재생 :: 프레임을 33ms 간격으로 읽음
## ================================================================
def start_video(timer):
    timer.start(33)  # 약 1000ms/33ms= 30fps


## ================================================================
## x, y좌표 반환
## ================================================================
def xy_point(px, py, frame_w, frame_h, label_w, label_h):
    """
    QLabel에 영상을 띄웠을 때 생기는 여백을 고려해서
    label 좌표(px, py)를 frame 좌표(fx, fy)로 변환
    """

    ## 유효성 체크 
    if frame_w <= 0 or frame_h <= 0 or label_w <= 0 or label_h <= 0:
        return 0, 0

    ## 영상을 Qlabel 사이즈에 맞게 넣기
    scale = min(label_w / frame_w, label_h / frame_h)
    disp_w = frame_w * scale
    disp_h = frame_h * scale

    ## 여백 처리(가운데 정렬)
    off_x = (label_w - disp_w) / 2.0
    off_y = (label_h - disp_h) / 2.0

    ## 영상기준 마우스 좌표
    ## 여백에 마우스 크롭할 경우 좌표 0
    x = min(max(px - off_x, 0.0), disp_w)   
    y = min(max(py - off_y, 0.0), disp_h)

    ## 원본 영상 기준으로 변환
    ## 위에서 곱하기 scale로 사이즈를 바꿨으니 다시 나누기로 복구
    fx = int(x / scale)
    fy = int(y / scale)

    # # frame 경계 clamp
    # fx = max(0, min(frame_w - 1, fx))
    # fy = max(0, min(frame_h - 1, fy))

    return fx, fy


## ================================================================
## ROI 계산
## ================================================================
def calc_roi(drag_start, drag_end, frame_shape, label_size):
    """
    drag_start/drag_end: QPoint
    frame_shape         : (h, w, c)
    label_size          : (lw, lh)
    return              : (fx1, fy1, fx2, fy2)
    """
    h, w, _ = frame_shape
    lw, lh = label_size

    p1x, p1y = drag_start.x(), drag_start.y()
    p2x, p2y = drag_end.x(), drag_end.y()

    ## 원본 프레임 기준 좌표
    fx1, fy1 = xy_point(p1x, p1y, w, h, lw, lh)
    fx2, fy2 = xy_point(p2x, p2y, w, h, lw, lh)

    ## 드래그 방향에 따라 재정렬
    x1, x2 = sorted([fx1, fx2])
    y1, y2 = sorted([fy1, fy2])

    return x1, y1, x2, y2


## ================================================================
## 크롭된 이미지
## ================================================================
def crop_frame(frame, roi):
    fx1, fy1, fx2, fy2 = roi
    return frame[fy1:fy2, fx1:fx2]


## ================================================================
## 크롭 이미지 저장
## ================================================================
# def save_roi_image(roi_img, save_dir, base_name, index):
#     os.makedirs(save_dir, exist_ok=True)
#     filename = os.path.join(save_dir, f"{base_name}_{index:03d}.bmp")

#     ok = cv2.imwrite(filename, cv2.cvtColor(roi_img, cv2.COLOR_RGB2BGR))
#     return ok, filename

def save_roi_image(img, save_dir, idx):
    os.makedirs(save_dir, exist_ok=True)
    filename = f"roi_{idx:04d}.bmp"
    path = os.path.normpath(os.path.join(save_dir, filename))

    # RGB -> BGR 변환 후 저장 (current_frame이 RGB이므로)
    bgr = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
    ok = cv2.imwrite(path, bgr)
    return ok, path