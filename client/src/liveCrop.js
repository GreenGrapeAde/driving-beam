import { defineStore } from "pinia";

const API_BASE = `http://${location.hostname}:8000`;
const WS_BASE  = `ws://${location.hostname}:8000`;

export const useLiveCropStore = defineStore("liveCrop", {
  state: () => ({
    isStreaming:  false,
    streamUrl:    "",
    errorMsg:     "",
    writtenCount: 0,
    exportMsg:    "",
    dets:         [],
    frameW:       0,
    frameH:       0,
    _detWs:       null,
    _pollId:      null,
  }),

  actions: {
    startLive() {
      this.errorMsg   = "";
      this.exportMsg  = "";
      this.streamUrl  = `${API_BASE}/live/mjpeg`;
      this.isStreaming = true;
      this._startDetWs();
      this._startPoll();
    },

    stopLive() {
      this.isStreaming = false;
      this.streamUrl   = "";
      this.errorMsg    = "";
      this._stopDetWs();
      this._stopPoll();
    },

    onStreamError() {
      this.errorMsg   = "스트림 연결 실패. 서버를 확인해주세요.";
      this.isStreaming = false;
      this.streamUrl   = "";
      this._stopDetWs();
      this._stopPoll();
    },

    async exportZip() {
      this.exportMsg = "ZIP 생성 중...";
      try {
        const res  = await fetch(`${API_BASE}/live/export`, { method: "POST" });
        if (!res.ok) {
          const err = await res.json().catch(() => ({}));
          throw new Error(err.detail || "export failed");
        }
        const data = await res.json();
        const dl   = await fetch(`${API_BASE}${data.download_url}`);
        const blob = await dl.blob();
        const url  = URL.createObjectURL(blob);
        const a    = document.createElement("a");
        a.href = url; a.download = "live_dataset.zip";
        document.body.appendChild(a); a.click(); a.remove();
        URL.revokeObjectURL(url);
        this.exportMsg = `완료 · ${data.written}장 다운로드됨`;
      } catch (e) {
        this.exportMsg = "실패: " + (e.message || "unknown");
      }
    },

    _startDetWs() {
      if (this._detWs) return;
      const ws = new WebSocket(`${WS_BASE}/live/ws/det`);
      this._detWs = ws;
      ws.onmessage = (evt) => {
        try {
          const msg    = JSON.parse(evt.data);
          this.dets    = msg.dets    || [];
          this.frameW  = msg.frame_w || this.frameW;
          this.frameH  = msg.frame_h || this.frameH;
        } catch {}
      };
      ws.onerror = () => { this.dets = []; };
      ws.onclose = () => { this._detWs = null; };
    },

    _stopDetWs() {
      if (this._detWs) {
        try { this._detWs.close(); } catch {}
        this._detWs = null;
      }
      this.dets = [];
    },

    _startPoll() {
      this._stopPoll();
      this._pollId = setInterval(async () => {
        try {
          const res  = await fetch(`${API_BASE}/live/written`);
          const data = await res.json();
          this.writtenCount = data.written ?? 0;
        } catch {}
      }, 3000);
    },

    _stopPoll() {
      if (this._pollId) {
        clearInterval(this._pollId);
        this._pollId = null;
      }
    },

    reset() {
      this.stopLive();
      this.writtenCount = 0;
      this.exportMsg    = "";
      this.dets         = [];
      this.frameW       = 0;
      this.frameH       = 0;
    },
  },
});