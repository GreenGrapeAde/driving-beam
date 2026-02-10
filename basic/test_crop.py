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
    def __init__(self, root):
        self.root = root
        self.root.title("동영상 Crop & 이미지 추출기 (Tkinter)")
        self.root.geometry("1200x720")
        self.root.minsize(1100, 650)

        # -------------------------
        # State
        # -------------------------
        self.cap = None
        self.video_path = None
        self.output_dir = None

        self.video_w = 0
        self.video_h = 0
        self.video_fps = 0.0
        self.total_frames = 0

        self.current_frame_index = 0
        self.current_frame_bgr = None
        self.current_frame_rgb = None
        self.tkimg = None

        # Crop state
        self.crop_x = 0
        self.crop_y = 0
        self.crop_w = 0
        self.crop_h = 0

        self.dragging = False
        self.drag_start = (0, 0)
        self.drag_rect_id = None

        # Display scale for canvas
        self.canvas_w = 720
        self.canvas_h = 405
        self.scale = 1.0  # canvas <- video scale

        # Extract state
        self.is_extracting = False

        # -------------------------
        # UI
        # -------------------------
        self._build_ui()

        # Default inputs
        self.var_ts.set("300")  # seconds
        self.var_rgb.set("24")  # bit

    # =====================================================
    # UI Build
    # =====================================================
    def _build_ui(self):
        # Root grid
        self.root.columnconfigure(0, weight=1)
        self.root.columnconfigure(1, weight=0)
        self.root.rowconfigure(0, weight=1)

        # Left: Video area
        left = tk.Frame(self.root, bg="#F3F5F7")
        left.grid(row=0, column=0, sticky="nsew", padx=12, pady=12)
        left.rowconfigure(0, weight=1)
        left.columnconfigure(0, weight=1)

        # Right: Info panel
        right = tk.Frame(self.root, bg="#FFFFFF", relief="groove", bd=2)
        right.grid(row=0, column=1, sticky="ns", padx=(0, 12), pady=12)
        right.columnconfigure(0, weight=1)

        # -------------------------
        # Video canvas frame
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

        # Canvas mouse events (crop drag)
        self.canvas.bind("<Button-1>", self._on_mouse_down)
        self.canvas.bind("<B1-Motion>", self._on_mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_mouse_up)

        # -------------------------
        # Controls under canvas
        # -------------------------
        btn_frame = tk.Frame(left, bg="#F3F5F7")
        btn_frame.grid(row=1, column=0, sticky="ew", pady=(12, 0))
        btn_frame.columnconfigure((0, 1, 2), weight=1)

        self.btn_load = tk.Button(
            btn_frame, text="영상\n불러오기",
            font=("Malgun Gothic", 11, "bold"),
            height=2, bg="#4B83D8", fg="white",
            relief="flat", command=self.load_video
        )
        self.btn_load.grid(row=0, column=0, sticky="ew", padx=(0, 10))

        self.btn_out = tk.Button(
            btn_frame, text="출력 폴더\n지정",
            font=("Malgun Gothic", 11, "bold"),
            height=2, bg="#4B83D8", fg="white",
            relief="flat", command=self.choose_output_dir
        )
        self.btn_out.grid(row=0, column=1, sticky="ew", padx=10)

        self.btn_extract = tk.Button(
            btn_frame, text="이미지\n추출",
            font=("Malgun Gothic", 11, "bold"),
            height=2, bg="#4B83D8", fg="white",
            relief="flat", command=self.extract_images
        )
        self.btn_extract.grid(row=0, column=2, sticky="ew", padx=(10, 0))

        # Progress label (bottom)
        self.lbl_progress = tk.Label(
            left,
            text="0/0",
            bg="#F3F5F7",
            fg="#333333",
            font=("Consolas", 12, "bold")
        )
        self.lbl_progress.grid(row=2, column=0, sticky="e", pady=(10, 0))

        # =====================================================
        # Right panel contents
        # =====================================================
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
        # Video info
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
        # Crop info
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
        # User inputs (t(s), rgb)
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
        # Output info
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

        # Footer
        footer = tk.Label(
            right,
            text="※ 추출 FPS: 원본 FPS 사용\n※ 저장 형식: BMP",
            bg="#FFFFFF",
            fg="#777777",
            font=("Malgun Gothic", 9),
            justify="left"
        )
        footer.grid(row=5, column=0, sticky="ew", padx=10, pady=(0, 10))

        # Make right panel stretch only vertically
        right.rowconfigure(6, weight=1)

    def _info_row(self, parent, r, label_text, var):
        tk.Label(parent, text=label_text, bg="#FFFFFF", fg="#333333",
                 font=("Consolas", 11)).grid(row=r, column=0, sticky="w", padx=(0, 6))
        tk.Label(parent, textvariable=var, bg="#FFFFFF", fg="#111111",
                 font=("Consolas", 11, "bold")).grid(row=r, column=1, sticky="w")

    def _entry_row(self, parent, r, label_text, var):
        tk.Label(parent, text=label_text, bg="#FFFFFF", fg="#333333",
                 font=("Consolas", 11)).grid(row=r, column=0, sticky="w", padx=(0, 6), pady=3)

        ent = tk.Entry(parent, textvariable=var, font=("Consolas", 11), width=14)
        ent.grid(row=r, column=1, sticky="ew", pady=3)
        return ent

    # =====================================================
    # Video load & preview
    # =====================================================
    def load_video(self):
        path = filedialog.askopenfilename(
            title="동영상 파일 선택",
            filetypes=[
                ("Video Files", "*.mp4 *.avi *.mov *.mkv *.wmv"),
                ("All Files", "*.*"),
            ]
        )
        if not path:
            return

        # Release old
        if self.cap:
            self.cap.release()

        self.cap = cv2.VideoCapture(path)
        if not self.cap.isOpened():
            messagebox.showerror("오류", "영상을 열 수 없습니다.")
            return

        self.video_path = path

        self.video_w = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.video_h = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.video_fps = float(self.cap.get(cv2.CAP_PROP_FPS))
        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))

        if self.video_fps <= 0:
            self.video_fps = 30.0

        # Update info panel
        self.var_vid_w.set(str(self.video_w))
        self.var_vid_h.set(str(self.video_h))
        self.var_vid_fps.set(f"{self.video_fps:.2f}")
        self.var_vid_frames.set(str(self.total_frames))

        # Reset crop
        self.crop_x = 0
        self.crop_y = 0
        self.crop_w = self.video_w
        self.crop_h = self.video_h
        self._sync_crop_vars()

        # Seek to first frame
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        ok, frame = self.cap.read()
        if not ok:
            messagebox.showerror("오류", "첫 프레임을 읽을 수 없습니다.")
            return

        self.current_frame_index = 0
        self.current_frame_bgr = frame
        self._render_frame_to_canvas(frame)

        self.lbl_status.config(text="상태: 영상 로드 완료")

    def _render_frame_to_canvas(self, frame_bgr):
        # Convert to RGB
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        self.current_frame_rgb = rgb

        # Fit to canvas while preserving aspect
        vh, vw = rgb.shape[:2]
        cw, ch = self.canvas_w, self.canvas_h

        scale_w = cw / vw
        scale_h = ch / vh
        self.scale = min(scale_w, scale_h)

        disp_w = int(vw * self.scale)
        disp_h = int(vh * self.scale)

        img = Image.fromarray(rgb).resize((disp_w, disp_h))
        self.tkimg = ImageTk.PhotoImage(img)

        self.canvas.delete("all")
        # center
        x0 = (cw - disp_w) // 2
        y0 = (ch - disp_h) // 2
        self.canvas.create_image(x0, y0, anchor="nw", image=self.tkimg, tags="frame")

        # draw crop rect if exists
        self._draw_crop_rect()

    def _draw_crop_rect(self):
        # crop -> canvas coords
        if self.video_w <= 0 or self.video_h <= 0:
            return

        # Displayed image offset (centered)
        disp_w = int(self.video_w * self.scale)
        disp_h = int(self.video_h * self.scale)
        x0 = (self.canvas_w - disp_w) // 2
        y0 = (self.canvas_h - disp_h) // 2

        cx1 = x0 + int(self.crop_x * self.scale)
        cy1 = y0 + int(self.crop_y * self.scale)
        cx2 = x0 + int((self.crop_x + self.crop_w) * self.scale)
        cy2 = y0 + int((self.crop_y + self.crop_h) * self.scale)

        # Clamp to displayed image
        cx1 = max(x0, min(x0 + disp_w, cx1))
        cx2 = max(x0, min(x0 + disp_w, cx2))
        cy1 = max(y0, min(y0 + disp_h, cy1))
        cy2 = max(y0, min(y0 + disp_h, cy2))

        # draw
        self.canvas.create_rectangle(
            cx1, cy1, cx2, cy2,
            outline="#ff2fb3",
            width=3,
            tags="crop"
        )

        # translucent fill (fake: draw stipple)
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
    def _on_mouse_down(self, event):
        if not self.cap:
            return

        self.dragging = True
        self.drag_start = (event.x, event.y)

        # Remove old drag rect
        if self.drag_rect_id:
            self.canvas.delete(self.drag_rect_id)
            self.drag_rect_id = None

    def _on_mouse_drag(self, event):
        if not self.dragging or not self.cap:
            return

        x1, y1 = self.drag_start
        x2, y2 = event.x, event.y

        # Draw live rect
        if self.drag_rect_id:
            self.canvas.delete(self.drag_rect_id)

        self.drag_rect_id = self.canvas.create_rectangle(
            x1, y1, x2, y2,
            outline="#ff2fb3",
            width=2,
            dash=(6, 3)
        )

    def _on_mouse_up(self, event):
        if not self.dragging or not self.cap:
            return

        self.dragging = False

        x1, y1 = self.drag_start
        x2, y2 = event.x, event.y

        # Normalize
        left = min(x1, x2)
        right = max(x1, x2)
        top = min(y1, y2)
        bottom = max(y1, y2)

        # Convert canvas coords -> video coords
        disp_w = int(self.video_w * self.scale)
        disp_h = int(self.video_h * self.scale)
        img_x0 = (self.canvas_w - disp_w) // 2
        img_y0 = (self.canvas_h - disp_h) // 2

        # Clamp selection inside displayed image
        left = max(img_x0, min(img_x0 + disp_w, left))
        right = max(img_x0, min(img_x0 + disp_w, right))
        top = max(img_y0, min(img_y0 + disp_h, top))
        bottom = max(img_y0, min(img_y0 + disp_h, bottom))

        sel_w = right - left
        sel_h = bottom - top

        # If too small, ignore
        if sel_w < 5 or sel_h < 5:
            if self.drag_rect_id:
                self.canvas.delete(self.drag_rect_id)
                self.drag_rect_id = None
            return

        # Convert to video coords
        vx = int((left - img_x0) / self.scale)
        vy = int((top - img_y0) / self.scale)
        vw = int(sel_w / self.scale)
        vh = int(sel_h / self.scale)

        # Clamp
        vx = max(0, min(self.video_w - 1, vx))
        vy = max(0, min(self.video_h - 1, vy))
        vw = max(1, min(self.video_w - vx, vw))
        vh = max(1, min(self.video_h - vy, vh))

        self.crop_x, self.crop_y, self.crop_w, self.crop_h = vx, vy, vw, vh
        self._sync_crop_vars()

        # redraw
        self._render_frame_to_canvas(self.current_frame_bgr)

        # cleanup
        if self.drag_rect_id:
            self.canvas.delete(self.drag_rect_id)
            self.drag_rect_id = None

    def _sync_crop_vars(self):
        self.var_crop_x.set(str(self.crop_x))
        self.var_crop_y.set(str(self.crop_y))
        self.var_crop_w.set(str(self.crop_w))
        self.var_crop_h.set(str(self.crop_h))

    def _read_crop_vars(self):
        try:
            x = int(self.var_crop_x.get())
            y = int(self.var_crop_y.get())
            w = int(self.var_crop_w.get())
            h = int(self.var_crop_h.get())
        except:
            raise ValueError("Crop 값은 정수여야 합니다.")

        if self.video_w <= 0 or self.video_h <= 0:
            raise ValueError("영상이 로드되지 않았습니다.")

        if w <= 0 or h <= 0:
            raise ValueError("w, h는 1 이상이어야 합니다.")

        # Clamp
        x = max(0, min(self.video_w - 1, x))
        y = max(0, min(self.video_h - 1, y))
        w = max(1, min(self.video_w - x, w))
        h = max(1, min(self.video_h - y, h))

        return x, y, w, h

    # =====================================================
    # Output dir
    # =====================================================
    def choose_output_dir(self):
        folder = filedialog.askdirectory(title="출력 폴더 선택")
        if not folder:
            return
        self.output_dir = folder
        self.lbl_outdir.config(text=f"출력 폴더: {self.output_dir}")
        self.lbl_status.config(text="상태: 출력 폴더 지정 완료")

    # =====================================================
    # Extract
    # =====================================================
    def extract_images(self):
        if self.is_extracting:
            messagebox.showinfo("알림", "이미 추출 중입니다.")
            return

        if not self.cap or not self.video_path:
            messagebox.showwarning("경고", "먼저 영상을 불러오세요.")
            return

        if not self.output_dir:
            messagebox.showwarning("경고", "출력 폴더를 먼저 지정하세요.")
            return

        # read crop from UI (user may edit)
        try:
            x, y, w, h = self._read_crop_vars()
        except Exception as e:
            messagebox.showerror("오류", str(e))
            return

        # seconds
        try:
            t_s = float(self.var_ts.get())
        except:
            messagebox.showerror("오류", "t(s)는 숫자여야 합니다.")
            return

        if t_s <= 0:
            messagebox.showerror("오류", "t(s)는 0보다 커야 합니다.")
            return

        # rgb bit (not critical for bmp, but keep as input)
        try:
            rgb_bit = int(self.var_rgb.get())
        except:
            messagebox.showerror("오류", "rgb는 정수여야 합니다.")
            return

        if rgb_bit not in (8, 16, 24, 32):
            # bmp는 보통 24bit
            if not messagebox.askyesno("확인", "rgb 값이 일반적이지 않습니다. 그래도 진행할까요?"):
                return

        # Calculate frames to extract
        frames_to_extract = int(t_s * self.video_fps)
        frames_to_extract = max(1, frames_to_extract)

        start_frame = int(self.cap.get(cv2.CAP_PROP_POS_FRAMES))
        # 보통은 처음부터 뽑는게 자연스러움
        start_frame = 0

        end_frame = min(self.total_frames, start_frame + frames_to_extract)

        if end_frame <= start_frame:
            messagebox.showerror("오류", "추출 가능한 프레임이 없습니다.")
            return

        base = os.path.splitext(os.path.basename(self.video_path))[0]

        # Setup extraction
        self.is_extracting = True
        self.lbl_status.config(text="상태: 이미지 추출 중...")
        self.btn_extract.config(state="disabled")
        self.btn_load.config(state="disabled")
        self.btn_out.config(state="disabled")

        # Seek start
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)

        # Extract loop
        saved = 0
        total = end_frame - start_frame

        for i in range(start_frame, end_frame):
            ok, frame = self.cap.read()
            if not ok:
                break

            crop = frame[y:y + h, x:x + w]
            if crop.size == 0:
                continue

            # Save BMP
            # filename: base_###.bmp (### is 001..)
            fname = f"{base}_{saved + 1:03d}.bmp"
            out_path = os.path.join(self.output_dir, fname)

            cv2.imwrite(out_path, crop)
            saved += 1

            # Update progress UI
            self.lbl_progress.config(text=f"{saved}/{total}")
            if saved % 3 == 0:
                self.root.update_idletasks()

            # Also update preview sometimes
            if saved % 10 == 0:
                self.current_frame_bgr = frame
                self._render_frame_to_canvas(frame)

        # Done
        self.is_extracting = False
        self.lbl_status.config(text=f"상태: 완료 (저장 {saved}장)")
        self.btn_extract.config(state="normal")
        self.btn_load.config(state="normal")
        self.btn_out.config(state="normal")

        messagebox.showinfo("완료", f"이미지 추출 완료!\n총 {saved}장 저장했습니다.")

    # =====================================================
    # Cleanup
    # =====================================================
    def on_close(self):
        try:
            if self.cap:
                self.cap.release()
        except:
            pass
        self.root.destroy()


# =========================================================
# Run
# =========================================================
if __name__ == "__main__":
    root = tk.Tk()
    app = VideoCropExtractorApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()
