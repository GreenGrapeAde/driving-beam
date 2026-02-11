import os
import cv2
import time
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk


# =========================================================
# Crop & Extract App (Tkinter + OpenCV)
# =========================================================
class VideoCropExtractorApp:
    ## ------------------------------------------------
    ## 함수 기능 : Tkinter 기반 동영상 Crop 및 이미지 추출기 초기화, UI 구성 및 상태 변수 설정
    ## 함수 이름 : __init__
    ## 매개 변수 : root (Tkinter 루트 윈도우)
    ## 결과 반환 : 없음
    ## ------------------------------------------------
    def __init__(self, root):
        self.root = root
        self.root.title("동영상 Crop & 이미지 추출기 (Tkinter)")
        self.root.geometry("1200x720")
        self.root.minsize(1100, 650)

        # -------------------------
        # 상태 변수 초기화
        # -------------------------
        self.cap = None              # cv2.VideoCapture 객체
        self.video_path = None       # 현재 로드된 동영상 경로
        self.output_dir = None       # 출력 이미지 저장 폴더 경로

        self.video_w = 0             # 동영상 너비
        self.video_h = 0             # 동영상 높이
        self.video_fps = 0.0         # 동영상 FPS
        self.total_frames = 0        # 전체 프레임 수

        self.current_frame_index = 0 # 현재 프레임 인덱스
        self.current_frame_bgr = None # 현재 프레임 (BGR)
        self.current_frame_rgb = None # 현재 프레임 (RGB)
        self.tkimg = None            # Tkinter에서 표시할 이미지 객체

        # Crop 상태
        self.crop_x = 0              # Crop 영역 시작 X
        self.crop_y = 0              # Crop 영역 시작 Y
        self.crop_w = 0              # Crop 영역 너비
        self.crop_h = 0              # Crop 영역 높이

        self.dragging = False        # 마우스 드래그 상태
        self.drag_start = (0, 0)     # 드래그 시작 좌표
        self.drag_rect_id = None     # Canvas 상 드래그 사각형 ID

        # 캔버스 표시용 스케일
        self.canvas_w = 720          # Canvas 너비
        self.canvas_h = 405          # Canvas 높이
        self.scale = 1.0             # Canvas <- Video 스케일 비율

        # 이미지 추출 상태
        self.is_extracting = False   # 추출 중 여부

        # -------------------------
        # UI 구성
        # -------------------------
        self._build_ui()             # UI 위젯 생성 함수 호출

        # 기본 입력 값 설정
        self.var_ts.set("300")       # 추출 간격 시간 (초)
        self.var_rgb.set("24")       # 비트 깊이


    # =====================================================
    # UI Build
    # =====================================================

    ## ------------------------------------------------
    ## 함수 기능 : Tkinter 기반 동영상 Crop & 이미지 추출기 UI 구성
    ## 함수 이름 : _build_ui
    ## 매개 변수 : 없음 (self 사용)
    ## 결과 반환 : 없음
    ## ------------------------------------------------
    def _build_ui(self):
        # -------------------------
        # Root 그리드 설정
        # -------------------------
        self.root.columnconfigure(0, weight=1)
        self.root.columnconfigure(1, weight=0)
        self.root.rowconfigure(0, weight=1)

        # -------------------------
        # 왼쪽: 영상 영역 프레임
        # -------------------------
        left = tk.Frame(self.root, bg="#F3F5F7")
        left.grid(row=0, column=0, sticky="nsew", padx=12, pady=12)
        left.rowconfigure(0, weight=1)
        left.columnconfigure(0, weight=1)

        # -------------------------
        # 오른쪽: 정보 패널
        # -------------------------
        right = tk.Frame(self.root, bg="#FFFFFF", relief="groove", bd=2)
        right.grid(row=0, column=1, sticky="ns", padx=(0, 12), pady=12)
        right.columnconfigure(0, weight=1)

        # -------------------------
        # Video canvas frame 생성
        # -------------------------
        canvas_frame = tk.Frame(left, bg="#FFFFFF", relief="groove", bd=2)
        canvas_frame.grid(row=0, column=0, sticky="nsew")
        canvas_frame.rowconfigure(0, weight=1)
        canvas_frame.columnconfigure(0, weight=1)

        title = tk.Label(
            canvas_frame,
            text="불러온 영상 화면",
            bg="#FFFFFF",
            fg="#333333",
            font=("Malgun Gothic", 12, "bold"),
            pady=8
        )
        title.grid(row=0, column=0, sticky="ew")

        self.canvas = tk.Canvas(
            canvas_frame,
            width=self.canvas_w,
            height=self.canvas_h,
            bg="#111111",
            highlightthickness=0
        )
        self.canvas.grid(row=1, column=0, padx=12, pady=12, sticky="nsew")

        # -------------------------
        # Canvas 마우스 이벤트 바인딩 (Crop 드래그용)
        # -------------------------
        self.canvas.bind("<Button-1>", self._on_mouse_down)
        self.canvas.bind("<B1-Motion>", self._on_mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_mouse_up)

        # -------------------------
        # Canvas 아래 버튼 컨트롤
        # -------------------------
        btn_frame = tk.Frame(left, bg="#F3F5F7")
        btn_frame.grid(row=1, column=0, sticky="ew", pady=(12, 0))
        btn_frame.columnconfigure((0, 1, 2), weight=1)

        # 영상 불러오기 버튼
        self.btn_load = tk.Button(
            btn_frame, text="영상\n불러오기",
            font=("Malgun Gothic", 11, "bold"),
            height=2, bg="#4B83D8", fg="white",
            relief="flat", command=self.load_video
        )
        self.btn_load.grid(row=0, column=0, sticky="ew", padx=(0, 10))

        # 출력 폴더 지정 버튼
        self.btn_out = tk.Button(
            btn_frame, text="출력 폴더\n지정",
            font=("Malgun Gothic", 11, "bold"),
            height=2, bg="#4B83D8", fg="white",
            relief="flat", command=self.choose_output_dir
        )
        self.btn_out.grid(row=0, column=1, sticky="ew", padx=10)

        # 이미지 추출 버튼
        self.btn_extract = tk.Button(
            btn_frame, text="이미지\n추출",
            font=("Malgun Gothic", 11, "bold"),
            height=2, bg="#4B83D8", fg="white",
            relief="flat", command=self.extract_images
        )
        self.btn_extract.grid(row=0, column=2, sticky="ew", padx=(10, 0))

        # 추출 진행도 라벨
        self.lbl_progress = tk.Label(
            left,
            text="0/0",
            bg="#F3F5F7",
            fg="#333333",
            font=("Consolas", 12, "bold")
        )
        self.lbl_progress.grid(row=2, column=0, sticky="e", pady=(10, 0))

        # -------------------------
        # 오른쪽 패널 헤더
        # -------------------------
        header = tk.Label(
            right,
            text="정보 패널",
            bg="#FFFFFF",
            fg="#222222",
            font=("Malgun Gothic", 13, "bold"),
            pady=10
        )
        header.grid(row=0, column=0, sticky="ew", padx=10)

        # -------------------------
        # 영상 정보
        # -------------------------
        vid_box = tk.LabelFrame(
            right, text="1. 영상 정보",
            bg="#FFFFFF", fg="#333333",
            font=("Malgun Gothic", 10, "bold"),
            padx=10, pady=10
        )
        vid_box.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 12))

        self.var_vid_w = tk.StringVar(value="-")
        self.var_vid_h = tk.StringVar(value="-")
        self.var_vid_fps = tk.StringVar(value="-")
        self.var_vid_frames = tk.StringVar(value="-")

        self._info_row(vid_box, 0, "w :", self.var_vid_w)
        self._info_row(vid_box, 1, "h :", self.var_vid_h)
        self._info_row(vid_box, 2, "fps :", self.var_vid_fps)
        self._info_row(vid_box, 3, "frames :", self.var_vid_frames)

        # -------------------------
        # Crop 정보
        # -------------------------
        crop_box = tk.LabelFrame(
            right, text="2. Crop 정보",
            bg="#FFFFFF", fg="#333333",
            font=("Malgun Gothic", 10, "bold"),
            padx=10, pady=10
        )
        crop_box.grid(row=2, column=0, sticky="ew", padx=10, pady=(0, 12))
        crop_box.columnconfigure(1, weight=1)

        self.var_crop_x = tk.StringVar(value="0")
        self.var_crop_y = tk.StringVar(value="0")
        self.var_crop_w = tk.StringVar(value="0")
        self.var_crop_h = tk.StringVar(value="0")

        self._entry_row(crop_box, 0, "x :", self.var_crop_x)
        self._entry_row(crop_box, 1, "y :", self.var_crop_y)
        self._entry_row(crop_box, 2, "w :", self.var_crop_w)
        self._entry_row(crop_box, 3, "h :", self.var_crop_h)

        # -------------------------
        # 사용자 입력 (t(s), rgb)
        # -------------------------
        input_box = tk.LabelFrame(
            right, text="사용자 입력",
            bg="#FFFFFF", fg="#333333",
            font=("Malgun Gothic", 10, "bold"),
            padx=10, pady=10
        )
        input_box.grid(row=3, column=0, sticky="ew", padx=10, pady=(0, 12))
        input_box.columnconfigure(1, weight=1)

        self.var_ts = tk.StringVar()
        self.var_rgb = tk.StringVar()

        self._entry_row(input_box, 0, "t(s) :", self.var_ts)
        self._entry_row(input_box, 1, "rgb :", self.var_rgb)

        hint = tk.Label(
            input_box,
            text="※ t(s): 추출 시간(초)\n※ rgb: 비트수(일반적으로 24)",
            bg="#FFFFFF",
            fg="#666666",
            font=("Malgun Gothic", 9),
            justify="left"
        )
        hint.grid(row=2, column=0, columnspan=2, sticky="w", pady=(6, 0))

        # -------------------------
        # 출력 정보
        # -------------------------
        out_box = tk.LabelFrame(
            right, text="출력",
            bg="#FFFFFF", fg="#333333",
            font=("Malgun Gothic", 10, "bold"),
            padx=10, pady=10
        )
        out_box.grid(row=4, column=0, sticky="ew", padx=10, pady=(0, 12))
        out_box.columnconfigure(0, weight=1)

        self.lbl_outdir = tk.Label(
            out_box,
            text="출력 폴더: (미지정)",
            bg="#FFFFFF",
            fg="#444444",
            font=("Malgun Gothic", 9),
            wraplength=330,
            justify="left"
        )
        self.lbl_outdir.grid(row=0, column=0, sticky="w")

        self.lbl_status = tk.Label(
            out_box,
            text="상태: 대기",
            bg="#FFFFFF",
            fg="#222222",
            font=("Malgun Gothic", 10, "bold"),
            pady=6
        )
        self.lbl_status.grid(row=1, column=0, sticky="w")

        # -------------------------
        # Footer
        # -------------------------
        footer = tk.Label(
            right,
            text="※ 추출 FPS: 원본 FPS 사용\n※ 저장 형식: BMP",
            bg="#FFFFFF",
            fg="#777777",
            font=("Malgun Gothic", 9),
            justify="left"
        )
        footer.grid(row=5, column=0, sticky="ew", padx=10)

        # 오른쪽 패널 세로로만 늘어나도록 설정
        right.rowconfigure(6, weight=1)


    ## ------------------------------------------------
    ## 함수 기능 : Label + 값(LabelVar) 한 행(row)으로 생성하여 부모 위젯에 배치
    ## 함수 이름 : _info_row
    ## 매개 변수 : 
    ##     parent (tk.Widget) - 라벨을 추가할 부모 위젯
    ##     r (int) - 행(row) 번호
    ##     label_text (str) - 라벨 텍스트
    ##     var (tk.StringVar) - 표시할 값
    ## 결과 반환 : 없음
    ## ------------------------------------------------
    def _info_row(self, parent, r, label_text, var):
        # 좌측 라벨 생성 (일반 텍스트)
        tk.Label(parent, text=label_text, bg="#FFFFFF", fg="#333333",
                font=("Consolas", 11)).grid(row=r, column=0, sticky="w", padx=(0, 6))
        
        # 우측 라벨 생성 (값, 볼드체)
        tk.Label(parent, textvariable=var, bg="#FFFFFF", fg="#111111",
                font=("Consolas", 11, "bold")).grid(row=r, column=1, sticky="w")



    ## ------------------------------------------------
    ## 함수 기능 : Label + Entry 한 행(row)으로 생성하여 부모 위젯에 배치
    ## 함수 이름 : _entry_row
    ## 매개 변수 : 
    ##     parent (tk.Widget) - Entry를 추가할 부모 위젯
    ##     r (int) - 행(row) 번호
    ##     label_text (str) - 라벨 텍스트
    ##     var (tk.StringVar) - Entry와 연결할 변수
    ## 결과 반환 : 생성된 Entry 위젯 (tk.Entry)
    ## ------------------------------------------------
    def _entry_row(self, parent, r, label_text, var):
        # 좌측 라벨 생성
        tk.Label(parent, text=label_text, bg="#FFFFFF", fg="#333333",
                font=("Consolas", 11)).grid(row=r, column=0, sticky="w", padx=(0, 6), pady=3)

        # 우측 Entry 생성 및 배치
        ent = tk.Entry(parent, textvariable=var, font=("Consolas", 11), width=14)
        ent.grid(row=r, column=1, sticky="ew", pady=3)
        
        # 생성된 Entry 반환
        return ent


    # =====================================================
    # Video load & preview
    # =====================================================
    ## ------------------------------------------------
    ## 함수 기능 : 파일 다이얼로그를 통해 동영상 선택 후 로드, 정보 패널 갱신, Canvas에 첫 프레임 표시
    ## 함수 이름 : load_video
    ## 매개 변수 : 없음 (self 사용)
    ## 결과 반환 : 없음
    ## ------------------------------------------------
    def load_video(self):
        # -------------------------
        # 동영상 파일 선택 다이얼로그
        # -------------------------
        path = filedialog.askopenfilename(
            title="동영상 파일 선택",
            filetypes=[
                ("Video Files", "*.mp4 *.avi *.mov *.mkv *.wmv"),  # 지원 동영상 확장자
                ("All Files", "*.*"),
            ]
        )
        if not path:  # 사용자가 취소했으면 함수 종료
            return

        # -------------------------
        # 기존 VideoCapture 객체 해제
        # -------------------------
        if self.cap:
            self.cap.release()

        # -------------------------
        # 새 VideoCapture 생성
        # -------------------------
        self.cap = cv2.VideoCapture(path)
        if not self.cap.isOpened():  # 영상 열기 실패 시 에러 메시지
            messagebox.showerror("오류", "영상을 열 수 없습니다.")
            return

        self.video_path = path  # 로드된 영상 경로 저장

        # -------------------------
        # 동영상 메타 정보 추출
        # -------------------------
        self.video_w = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))   # 영상 너비
        self.video_h = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))  # 영상 높이
        self.video_fps = float(self.cap.get(cv2.CAP_PROP_FPS))       # FPS
        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT)) # 총 프레임 수

        if self.video_fps <= 0:  # FPS 값이 이상하면 기본값 30으로 설정
            self.video_fps = 30.0

        # -------------------------
        # 정보 패널 업데이트
        # -------------------------
        self.var_vid_w.set(str(self.video_w))
        self.var_vid_h.set(str(self.video_h))
        self.var_vid_fps.set(f"{self.video_fps:.2f}")
        self.var_vid_frames.set(str(self.total_frames))

        # -------------------------
        # Crop 영역 초기화
        # -------------------------
        self.crop_x = 0
        self.crop_y = 0
        self.crop_w = self.video_w
        self.crop_h = self.video_h
        self._sync_crop_vars()  # UI Entry 값 동기화

        # -------------------------
        # 첫 프레임으로 이동 및 Canvas 표시
        # -------------------------
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        ok, frame = self.cap.read()
        if not ok:
            messagebox.showerror("오류", "첫 프레임을 읽을 수 없습니다.")
            return

        self.current_frame_index = 0
        self.current_frame_bgr = frame
        self._render_frame_to_canvas(frame)  # Canvas에 첫 프레임 렌더링

        # 상태 표시 업데이트
        self.lbl_status.config(text="상태: 영상 로드 완료")


    ## ------------------------------------------------
    ## 함수 기능 : BGR 형식의 프레임을 Canvas에 맞게 변환 후 렌더링, Crop 사각형 표시
    ## 함수 이름 : _render_frame_to_canvas
    ## 매개 변수 : 
    ##     frame_bgr (numpy.ndarray) - OpenCV BGR 포맷 프레임
    ## 결과 반환 : 없음
    ## ------------------------------------------------
    def _render_frame_to_canvas(self, frame_bgr):
        # -------------------------
        # BGR -> RGB 변환
        # -------------------------
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        self.current_frame_rgb = rgb  # 현재 RGB 프레임 저장

        # -------------------------
        # Canvas 크기에 맞게 비율 유지하며 축소/확대
        # -------------------------
        vh, vw = rgb.shape[:2]           # 영상 원본 높이, 너비
        cw, ch = self.canvas_w, self.canvas_h  # Canvas 크기

        scale_w = cw / vw
        scale_h = ch / vh
        self.scale = min(scale_w, scale_h)  # 비율 유지

        disp_w = int(vw * self.scale)
        disp_h = int(vh * self.scale)

        # -------------------------
        # PIL Image로 변환 후 Canvas에 표시
        # -------------------------
        img = Image.fromarray(rgb).resize((disp_w, disp_h))
        self.tkimg = ImageTk.PhotoImage(img)

        self.canvas.delete("all")  # 이전 프레임 제거

        # 중앙 정렬
        x0 = (cw - disp_w) // 2
        y0 = (ch - disp_h) // 2
        self.canvas.create_image(x0, y0, anchor="nw", image=self.tkimg, tags="frame")

        # Crop 사각형이 있으면 그리기
        self._draw_crop_rect()


    ## ------------------------------------------------
    ## 함수 기능 : 현재 Crop 영역을 Canvas 좌표에 맞춰 사각형으로 표시
    ## 함수 이름 : _draw_crop_rect
    ## 매개 변수 : 없음 (self 사용)
    ## 결과 반환 : 없음
    ## ------------------------------------------------
    def _draw_crop_rect(self):
        # -------------------------
        # 영상 크기 확인
        # -------------------------
        if self.video_w <= 0 or self.video_h <= 0:
            return  # 영상이 로드되지 않았으면 종료

        # -------------------------
        # 표시 영상 크기 및 오프셋 계산 (중앙 정렬)
        # -------------------------
        disp_w = int(self.video_w * self.scale)
        disp_h = int(self.video_h * self.scale)
        x0 = (self.canvas_w - disp_w) // 2
        y0 = (self.canvas_h - disp_h) // 2

        # Crop 좌표를 Canvas 좌표로 변환
        cx1 = x0 + int(self.crop_x * self.scale)
        cy1 = y0 + int(self.crop_y * self.scale)
        cx2 = x0 + int((self.crop_x + self.crop_w) * self.scale)
        cy2 = y0 + int((self.crop_y + self.crop_h) * self.scale)

        # Canvas 표시 영역 내로 좌표 제한
        cx1 = max(x0, min(x0 + disp_w, cx1))
        cx2 = max(x0, min(x0 + disp_w, cx2))
        cy1 = max(y0, min(y0 + disp_h, cy1))
        cy2 = max(y0, min(y0 + disp_h, cy2))

        # -------------------------
        # Crop 사각형 외곽선 그리기
        # -------------------------
        self.canvas.create_rectangle(
            cx1, cy1, cx2, cy2,
            outline="#ff2fb3",
            width=3,
            tags="crop"
        )

        # -------------------------
        # 반투명 채우기 (stipple 효과 사용)
        # -------------------------
        self.canvas.create_rectangle(
            cx1, cy1, cx2, cy2,
            outline="",
            fill="#00bfff",
            stipple="gray25",
            tags="crop"
        )


    # =====================================================
    # Mouse crop interaction
    # =====================================================
    ## ------------------------------------------------
    ## 함수 기능 : Canvas에서 마우스 클릭 시 드래그 시작, 이전 드래그 사각형 제거
    ## 함수 이름 : _on_mouse_down
    ## 매개 변수 : 
    ##     event (tk.Event) - 마우스 이벤트 객체 (x, y 좌표 포함)
    ## 결과 반환 : 없음
    ## ------------------------------------------------
    def _on_mouse_down(self, event):
        # -------------------------
        # 영상이 로드되지 않았으면 드래그 무시
        # -------------------------
        if not self.cap:
            return

        # -------------------------
        # 드래그 상태 시작
        # -------------------------
        self.dragging = True
        self.drag_start = (event.x, event.y)  # 드래그 시작 좌표 저장

        # -------------------------
        # 이전에 그린 드래그 사각형 제거
        # -------------------------
        if self.drag_rect_id:
            self.canvas.delete(self.drag_rect_id)
            self.drag_rect_id = None


    ## ------------------------------------------------
    ## 함수 기능 : 마우스를 드래그하는 동안 실시간으로 사각형 표시
    ## 함수 이름 : _on_mouse_drag
    ## 매개 변수 : 
    ##     event (tk.Event) - 마우스 이벤트 객체 (x, y 좌표 포함)
    ## 결과 반환 : 없음
    ## ------------------------------------------------
    def _on_mouse_drag(self, event):
        # -------------------------
        # 드래그 중이 아니거나 영상이 없으면 무시
        # -------------------------
        if not self.dragging or not self.cap:
            return

        # -------------------------
        # 드래그 시작점과 현재 마우스 좌표 가져오기
        # -------------------------
        x1, y1 = self.drag_start
        x2, y2 = event.x, event.y

        # -------------------------
        # 이전 드래그 사각형 제거
        # -------------------------
        if self.drag_rect_id:
            self.canvas.delete(self.drag_rect_id)

        # -------------------------
        # 실시간 드래그 사각형 생성 (점선)
        # -------------------------
        self.drag_rect_id = self.canvas.create_rectangle(
            x1, y1, x2, y2,
            outline="#ff2fb3",
            width=2,
            dash=(6, 3)
        )


    ## ------------------------------------------------
    ## 함수 기능 : 마우스 드래그 종료 시 선택 영역을 영상 좌표로 변환 후 Crop 영역 업데이트
    ## 함수 이름 : _on_mouse_up
    ## 매개 변수 : 
    ##     event (tk.Event) - 마우스 이벤트 객체 (x, y 좌표 포함)
    ## 결과 반환 : 없음
    ## ------------------------------------------------
    def _on_mouse_up(self, event):
        # -------------------------
        # 드래그 상태가 아니거나 영상이 없으면 무시
        # -------------------------
        if not self.dragging or not self.cap:
            return

        self.dragging = False  # 드래그 종료

        # -------------------------
        # 드래그 시작점과 종료점 좌표
        # -------------------------
        x1, y1 = self.drag_start
        x2, y2 = event.x, event.y

        # -------------------------
        # 좌표 정규화 (left, right, top, bottom)
        # -------------------------
        left = min(x1, x2)
        right = max(x1, x2)
        top = min(y1, y2)
        bottom = max(y1, y2)

        # -------------------------
        # Canvas 좌표 -> 영상 좌표 변환 준비
        # -------------------------
        disp_w = int(self.video_w * self.scale)
        disp_h = int(self.video_h * self.scale)
        img_x0 = (self.canvas_w - disp_w) // 2
        img_y0 = (self.canvas_h - disp_h) // 2

        # -------------------------
        # 선택 영역을 표시 영상 영역 안으로 제한
        # -------------------------
        left = max(img_x0, min(img_x0 + disp_w, left))
        right = max(img_x0, min(img_x0 + disp_w, right))
        top = max(img_y0, min(img_y0 + disp_h, top))
        bottom = max(img_y0, min(img_y0 + disp_h, bottom))

        sel_w = right - left
        sel_h = bottom - top

        # 너무 작은 영역은 무시
        if sel_w < 5 or sel_h < 5:
            if self.drag_rect_id:
                self.canvas.delete(self.drag_rect_id)
                self.drag_rect_id = None
            return

        # -------------------------
        # Canvas 좌표 -> 원본 영상 좌표 변환
        # -------------------------
        vx = int((left - img_x0) / self.scale)
        vy = int((top - img_y0) / self.scale)
        vw = int(sel_w / self.scale)
        vh = int(sel_h / self.scale)

        # 영상 크기 내로 Clamp
        vx = max(0, min(self.video_w - 1, vx))
        vy = max(0, min(self.video_h - 1, vy))
        vw = max(1, min(self.video_w - vx, vw))
        vh = max(1, min(self.video_h - vy, vh))

        # Crop 상태 업데이트 및 UI 동기화
        self.crop_x, self.crop_y, self.crop_w, self.crop_h = vx, vy, vw, vh
        self._sync_crop_vars()

        # -------------------------
        # Canvas에 프레임 + Crop 재렌더링
        # -------------------------
        self._render_frame_to_canvas(self.current_frame_bgr)

        # -------------------------
        # 드래그 사각형 제거
        # -------------------------
        if self.drag_rect_id:
            self.canvas.delete(self.drag_rect_id)
            self.drag_rect_id = None


    ## ------------------------------------------------
    ## 함수 기능 : Crop 좌표와 크기 상태를 UI 변수에 동기화
    ## 함수 이름 : _sync_crop_vars
    ## 매개 변수 : 없음 (self 사용)
    ## 결과 반환 : 없음
    ## ------------------------------------------------
    def _sync_crop_vars(self):
        # -------------------------
        # Crop 상태를 StringVar에 업데이트 (UI 표시)
        # -------------------------
        self.var_crop_x.set(str(self.crop_x))
        self.var_crop_y.set(str(self.crop_y))
        self.var_crop_w.set(str(self.crop_w))
        self.var_crop_h.set(str(self.crop_h))


    ## ------------------------------------------------
    ## 함수 기능 : UI에서 입력된 Crop 값 읽어와 유효성 검사 후 영상 좌표로 반환
    ## 함수 이름 : _read_crop_vars
    ## 매개 변수 : 없음 (self 사용)
    ## 결과 반환 : 
    ##     tuple (x, y, w, h) - 영상 좌표 기준 Crop 영역
    ## ------------------------------------------------
    def _read_crop_vars(self):
        # -------------------------
        # UI에서 입력값 읽기
        # -------------------------
        try:
            x = int(self.var_crop_x.get())
            y = int(self.var_crop_y.get())
            w = int(self.var_crop_w.get())
            h = int(self.var_crop_h.get())
        except:
            raise ValueError("Crop 값은 정수여야 합니다.")  # 숫자가 아니면 오류

        # -------------------------
        # 영상 로드 여부 확인
        # -------------------------
        if self.video_w <= 0 or self.video_h <= 0:
            raise ValueError("영상이 로드되지 않았습니다.")

        # -------------------------
        # Crop 크기 최소값 확인
        # -------------------------
        if w <= 0 or h <= 0:
            raise ValueError("w, h는 1 이상이어야 합니다.")

        # -------------------------
        # 영상 크기 내로 Clamp
        # -------------------------
        x = max(0, min(self.video_w - 1, x))
        y = max(0, min(self.video_h - 1, y))
        w = max(1, min(self.video_w - x, w))
        h = max(1, min(self.video_h - y, h))

        # -------------------------
        # 영상 좌표 Crop 반환
        # -------------------------
        return x, y, w, h


    # =====================================================
    # Output dir
    # =====================================================
    ## ------------------------------------------------
    ## 함수 기능 : 출력 이미지 저장용 폴더 선택 및 상태 업데이트
    ## 함수 이름 : choose_output_dir
    ## 매개 변수 : 없음 (self 사용)
    ## 결과 반환 : 없음
    ## ------------------------------------------------
    def choose_output_dir(self):
        # -------------------------
        # 사용자에게 폴더 선택 다이얼로그 표시
        # -------------------------
        folder = filedialog.askdirectory(title="출력 폴더 선택")
        if not folder:
            return  # 선택하지 않으면 종료

        # -------------------------
        # 선택한 폴더 저장 및 UI 업데이트
        # -------------------------
        self.output_dir = folder
        self.lbl_outdir.config(text=f"출력 폴더: {self.output_dir}")
        self.lbl_status.config(text="상태: 출력 폴더 지정 완료")


    # =====================================================
    # Extract
    # =====================================================
    ## ------------------------------------------------
    ## 함수 기능 : 지정된 Crop 영역 및 시간에 따라 영상에서 이미지를 추출하여 출력 폴더에 저장
    ## 함수 이름 : extract_images
    ## 매개 변수 : 없음 (self 사용)
    ## 결과 반환 : 없음
    ## ------------------------------------------------
    def extract_images(self):
        # -------------------------
        # 중복 추출 방지
        # -------------------------
        if self.is_extracting:
            messagebox.showinfo("알림", "이미 추출 중입니다.")
            return

        # -------------------------
        # 영상 로드 및 출력 폴더 확인
        # -------------------------
        if not self.cap or not self.video_path:
            messagebox.showwarning("경고", "먼저 영상을 불러오세요.")
            return

        if not self.output_dir:
            messagebox.showwarning("경고", "출력 폴더를 먼저 지정하세요.")
            return

        # -------------------------
        # UI에서 Crop 영역 읽기
        # -------------------------
        try:
            x, y, w, h = self._read_crop_vars()
        except Exception as e:
            messagebox.showerror("오류", str(e))
            return

        # -------------------------
        # 추출 시간(t_s) 확인
        # -------------------------
        try:
            t_s = float(self.var_ts.get())
        except:
            messagebox.showerror("오류", "t(s)는 숫자여야 합니다.")
            return

        if t_s <= 0:
            messagebox.showerror("오류", "t(s)는 0보다 커야 합니다.")
            return

        # -------------------------
        # RGB 비트수 확인 (BMP 저장용, 일반적으로 24bit)
        # -------------------------
        try:
            rgb_bit = int(self.var_rgb.get())
        except:
            messagebox.showerror("오류", "rgb는 정수여야 합니다.")
            return

        if rgb_bit not in (8, 16, 24, 32):
            if not messagebox.askyesno("확인", "rgb 값이 일반적이지 않습니다. 그래도 진행할까요?"):
                return

        # -------------------------
        # 추출할 프레임 계산
        # -------------------------
        frames_to_extract = int(t_s * self.video_fps)
        frames_to_extract = max(1, frames_to_extract)

        start_frame = 0  # 영상 처음부터 추출
        end_frame = min(self.total_frames, start_frame + frames_to_extract)

        if end_frame <= start_frame:
            messagebox.showerror("오류", "추출 가능한 프레임이 없습니다.")
            return

        base = os.path.splitext(os.path.basename(self.video_path))[0]

        # -------------------------
        # 추출 상태 초기화 및 UI 잠금
        # -------------------------
        self.is_extracting = True
        self.lbl_status.config(text="상태: 이미지 추출 중...")
        self.btn_extract.config(state="disabled")
        self.btn_load.config(state="disabled")
        self.btn_out.config(state="disabled")

        self.cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)

        # -------------------------
        # 프레임 루프: Crop 후 BMP 저장
        # -------------------------
        saved = 0
        total = end_frame - start_frame

        for i in range(start_frame, end_frame):
            ok, frame = self.cap.read()
            if not ok:
                break

            crop = frame[y:y + h, x:x + w]
            if crop.size == 0:
                continue

            # 파일명: base_###.bmp
            fname = f"{base}_{saved + 1:03d}.bmp"
            out_path = os.path.join(self.output_dir, fname)
            cv2.imwrite(out_path, crop)
            saved += 1

            # 진행률 업데이트
            self.lbl_progress.config(text=f"{saved}/{total}")
            if saved % 3 == 0:
                self.root.update_idletasks()

            # 미리보기 갱신
            if saved % 10 == 0:
                self.current_frame_bgr = frame
                self._render_frame_to_canvas(frame)

        # -------------------------
        # 추출 완료: 상태 업데이트 및 UI 해제
        # -------------------------
        self.is_extracting = False
        self.lbl_status.config(text=f"상태: 완료 (저장 {saved}장)")
        self.btn_extract.config(state="normal")
        self.btn_load.config(state="normal")
        self.btn_out.config(state="normal")

        messagebox.showinfo("완료", f"이미지 추출 완료!\n총 {saved}장 저장했습니다.")


    # =====================================================
    # Cleanup
    # =====================================================
    ## ------------------------------------------------
    ## 함수 기능 : 프로그램 종료 시 영상 캡처 해제 및 Tkinter 창 종료
    ## 함수 이름 : on_close
    ## 매개 변수 : 없음 (self 사용)
    ## 결과 반환 : 없음
    ## ------------------------------------------------
    def on_close(self):
        # -------------------------
        # 영상 캡처 객체 해제
        # -------------------------
        try:
            if self.cap:
                self.cap.release()
        except:
            pass  # 해제 중 오류 발생해도 무시

        # -------------------------
        # Tkinter 창 종료
        # -------------------------
        self.root.destroy()



# =========================================================
# Run
# =========================================================
if __name__ == "__main__":                              # 다른곳에서 import 하는 경우는 main임
    root = tk.Tk()                                      # tk 기본 창 생성
    app = VideoCropExtractorApp(root)                   # 커스텀 클래스 호출
    root.protocol("WM_DELETE_WINDOW", app.on_close)     # 창 닫기 기능에 커스텀 함수 연결
    root.mainloop()                                     # 프로그램 활성화
