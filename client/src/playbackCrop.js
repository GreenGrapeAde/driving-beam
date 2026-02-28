import { defineStore } from "pinia";

const API_BASE = "http://localhost:8000";
const WS_BASE  = "ws://localhost:8000";

export const usePlaybackCropStore = defineStore("playbackCrop", {
  state: () => ({
    videoSrc:  "",
    videoPath: "",
    filename:  "",

    // 업로드
    isUploading:    false,
    uploadProgress: 0,
    _xhr:           null,

    // 추론 + 크롭 (단일 단계)
    isAnalyzing:     false,
    analyzeProgress: 0,     // 0~100
    analyzeEta:      0,     // 남은 초
    analyzeWritten:  0,     // 저장된 크롭 이미지 수
    analyzePhase:    "",    // "analyzing" | "zipping" | "done"
    analyzeError:    "",
    _analyzeWs:      null,

    // playback 오버레이용 det 캐시
    detList:  [],    // [{frame_index, t_ms, detections}]
    metaInfo: null,  // {fps_src, frame_w, frame_h, infer_stride}
  }),

  actions: {
    setVideoLocal(src) {
      this.videoSrc = src || "";
    },

    // ── 업로드 ──────────────────────────────────────────────
    async uploadVideo(file, onProgress) {
      if (this._xhr) { try { this._xhr.abort(); } catch {} this._xhr = null; }
      this.isUploading    = true;
      this.uploadProgress = 0;

      return new Promise((resolve, reject) => {
        const xhr = new XMLHttpRequest();
        this._xhr = xhr;
        xhr.open("POST", `${API_BASE}/upload_video`);

        xhr.upload.onprogress = (evt) => {
          if (!evt.lengthComputable) return;
          const pct = Math.round((evt.loaded / evt.total) * 100);
          this.uploadProgress = pct;
          if (typeof onProgress === "function") onProgress(pct);
        };

        xhr.onload = () => {
          this.isUploading = false;
          this._xhr = null;
          try {
            const data = JSON.parse(xhr.responseText || "{}");
            if (!data.path || !data.filename) {
              reject(new Error("upload failed: invalid response"));
              return;
            }
            this.videoPath      = data.path;
            this.filename       = data.filename;
            this.uploadProgress = 100;
            resolve(data);
          } catch {
            reject(new Error("upload failed: parse error"));
          }
        };
        xhr.onerror = () => {
          this.isUploading = false;
          this._xhr = null;
          reject(new Error("upload failed: network error"));
        };
        xhr.onabort = () => {
          this.isUploading    = false;
          this.uploadProgress = 0;
          this._xhr           = null;
        };

        const fd = new FormData();
        fd.append("file", file);
        xhr.send(fd);
      });
    },

    // ── 추론 + 크롭 + 다운로드 (단일 WS) ───────────────────
    // done 시 자동 다운로드 후 resolve
    analyzeVideo(filename, inferStride = 10, leftRatio = 0.4) {
      return new Promise((resolve, reject) => {
        this.isAnalyzing     = true;
        this.analyzeProgress = 0;
        this.analyzeEta      = 0;
        this.analyzeWritten  = 0;
        this.analyzePhase    = "analyzing";
        this.analyzeError    = "";
        this.detList         = [];
        this.metaInfo        = null;

        const ws = new WebSocket(`${WS_BASE}/ws/analyze`);
        this._analyzeWs = ws;

        ws.onopen = () => {
          ws.send(JSON.stringify({
            filename,
            infer_stride: inferStride,
            left_ratio:   leftRatio,
          }));
        };

        ws.onmessage = async (evt) => {
          let msg;
          try { msg = JSON.parse(evt.data); } catch { return; }

          // ── meta ──────────────────────────────────────
          if (msg.type === "meta") {
            this.metaInfo = {
              fps_src:      msg.fps_src,
              frame_w:      msg.frame_w,
              frame_h:      msg.frame_h,
              infer_stride: msg.infer_stride,
              total_frames: msg.total_frames,
              infer_frames: msg.infer_frames,
            };
            return;
          }

          // ── progress ──────────────────────────────────
          if (msg.type === "progress") {
            this.analyzeProgress = msg.progress;
            this.analyzeEta      = msg.remaining_sec ?? 0;
            this.analyzeWritten  = msg.written       ?? this.analyzeWritten;
            this.analyzePhase    = "analyzing";
            return;
          }

          // ── zipping (ZIP 생성 시작) ────────────────────
          if (msg.type === "zipping") {
            this.analyzeProgress = 99;
            this.analyzePhase    = "zipping";
            this.analyzeWritten  = msg.written ?? this.analyzeWritten;
            return;
          }

          // ── done ──────────────────────────────────────
          if (msg.type === "done") {
            this.analyzeProgress = 100;
            this.analyzePhase    = "done";
            this.analyzeWritten  = msg.written ?? this.analyzeWritten;
            this._analyzeWs      = null;

            // det/all 로드 (playback 오버레이용)
            try {
              await this._fetchDetAll(filename);
            } catch (e) {
              console.warn("[playbackCrop] det/all fetch failed:", e);
            }

            // 자동 다운로드
            try {
              const res  = await fetch(`${API_BASE}${msg.download_url}`);
              const blob = await res.blob();
              const url  = window.URL.createObjectURL(blob);
              const a    = document.createElement("a");
              a.href = url;
              a.download = msg.zip_name || "occ_dataset.zip";
              document.body.appendChild(a);
              a.click();
              a.remove();
              window.URL.revokeObjectURL(url);
            } catch (e) {
              this.isAnalyzing = false;
              reject(new Error("download failed: " + e.message));
              return;
            }

            this.isAnalyzing = false;
            resolve();
            return;
          }

          // ── error ─────────────────────────────────────
          if (msg.type === "error") {
            this.isAnalyzing  = false;
            this.analyzeError = msg.message || "analyze error";
            this._analyzeWs   = null;
            reject(new Error(this.analyzeError));
            return;
          }

          // ── cancelled ─────────────────────────────────
          if (msg.type === "cancelled") {
            this.isAnalyzing = false;
            this._analyzeWs  = null;
            resolve("cancelled");
            return;
          }
        };

        ws.onerror = () => {
          this.isAnalyzing  = false;
          this.analyzeError = "WebSocket error";
          this._analyzeWs   = null;
          reject(new Error("analyze WebSocket error"));
        };

        ws.onclose = () => { this._analyzeWs = null; };
      });
    },

    cancelAnalyze() {
      const ws = this._analyzeWs;
      if (ws && ws.readyState === WebSocket.OPEN) {
        try { ws.send(JSON.stringify({ type: "control", action: "cancel" })); } catch {}
      }
      this.isAnalyzing = false;
    },

    // playback 오버레이용 det 전체 로드
    async _fetchDetAll(filename) {
      const res = await fetch(`${API_BASE}/det/all?filename=${encodeURIComponent(filename)}`);
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || "det/all fetch failed");
      }
      const data = await res.json();
      this.metaInfo = {
        ...this.metaInfo,
        fps_src:      data.fps_src,
        frame_w:      data.frame_w,
        frame_h:      data.frame_h,
        infer_stride: data.infer_stride,
      };
      this.detList = data.detections || [];
    },

    // ── Reset ───────────────────────────────────────────────
    reset() {
      if (this._xhr)       { try { this._xhr.abort(); }       catch {} this._xhr = null; }
      if (this._analyzeWs) { try { this._analyzeWs.close(); } catch {} this._analyzeWs = null; }

      this.videoSrc        = "";
      this.videoPath       = "";
      this.filename        = "";
      this.isUploading     = false;
      this.uploadProgress  = 0;
      this.isAnalyzing     = false;
      this.analyzeProgress = 0;
      this.analyzeEta      = 0;
      this.analyzeWritten  = 0;
      this.analyzePhase    = "";
      this.analyzeError    = "";
      this.detList         = [];
      this.metaInfo        = null;
    },
  },
});