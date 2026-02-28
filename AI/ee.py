import cv2
import os
from ultralytics import RTDETR

def collect_amodal_data(video_path, save_dir="./dataset/output_crops", left_ratio=0.4, conf_threshold=0.4):
    """
    RT-DETR와 ByteTrack을 사용하여 왼쪽 특정 영역의 차량을 Amodal 방식으로 크롭하여 저장하는 함수
    """
    # 1. 모델 로딩
    model = RTDETR("rtdetr-l.pt")
    
    # 2. 저장 폴더 생성
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)
        print(f"[알림] 폴더 생성 완료: {save_dir}")

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"[오류] 영상을 열 수 없습니다: {video_path}")
        return

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
    # 인식 구역 기준선 계산
    target_line = int(width * left_ratio) 
    
    frame_count = 0
    saved_count = 0

    print(f"[시작] '{os.path.basename(video_path)}'에서 데이터 수집 중... (영역: 왼쪽 {left_ratio*100}%)")

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
            
        frame_count += 1

        # 3. 모델 트래킹 (ByteTrack 사용)
        results = model.track(frame, persist=True, tracker="bytetrack.yaml", conf=conf_threshold, verbose=False)

        if results[0].boxes.id is not None:
            boxes = results[0].boxes.xyxy.cpu().numpy()
            ids = results[0].boxes.id.cpu().numpy()
            classes = results[0].boxes.cls.cpu().numpy()

            for box, track_id, cls_id in zip(boxes, ids, classes):
                cls_id = int(cls_id)
                track_id = int(track_id)
                
                # 자동차(2), 버스(5), 트럭(7) 필터링
                if cls_id not in [2, 5, 7]:
                    continue

                x1, y1, x2, y2 = map(int, box)
                cx = (x1 + x2) // 2
                
                # 4. 설정된 영역(왼쪽 40%) 안에 중심점이 있는 경우만 처리
                if cx <= target_line:
                    box_h = y2 - y1
                    
                    # 클래스별 Amodal 확장 비율 (승용차 x4, 대형차 x1.8)
                    if cls_id == 2:
                        extended_y2 = int(y1 + (box_h * 4))
                        cls_name = "car"
                    else:
                        extended_y2 = int(y1 + (box_h * 1.8))
                        cls_name = "heavy"
                    
                    # 화면 경계 보정
                    x1, y1 = max(0, x1), max(0, y1)
                    x2, extended_y2 = min(width, x2), min(height, extended_y2)
                    
                    # 이미지 크롭
                    crop_img = frame[y1:extended_y2, x1:x2]
                    
                    if crop_img.size > 0:
                        file_name = f"{cls_name}_id{track_id}_f{frame_count}.jpg"
                        save_path = os.path.join(save_dir, file_name)
                        cv2.imwrite(save_path, crop_img)
                        saved_count += 1

        if frame_count % 100 == 0:
            print(f" > 진행 중: {frame_count} 프레임 완료... (현재 {saved_count}장 저장)")

    cap.release()
    print("-" * 40)
    print(f"[완료] 총 저장된 이미지: {saved_count}장")
    print(f"[위치] {os.path.abspath(save_dir)}")
    print("-" * 40)

# --- 사용 예시 ---
if __name__ == "__main__":
    my_video = r"C:\Users\choju\Desktop\image_video\Video\segment_009.mp4"
    collect_amodal_data(video_path=my_video, left_ratio=0.4)