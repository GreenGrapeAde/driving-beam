import { defineStore } from "pinia";

const API_BASE = "http://localhost:8000";

export const useManualCropStore = defineStore("manualCrop", {
  state: () => ({
    status: "idle", // idle | extracted
    videoSrc: "",
    videoPath: "",

    roi: null, // live/display coords
    roiFrame: null, // server frame coords

    tSec: "",
    saveDir: "",

    previewIndex: 0,
    previewTotal: 0,
    previews: {}, // { [index]: base64 }

    // playback control
    playToken: 0,
    pauseToken: 0,
    volume: 0.5,
    seekToken: 0,
    seekFraction: 0,
    currentTimeSec: 0,
    displayW: 0,
    displayH: 0,
  }),
  actions: {
    setVideoLocal(src) {
      this.videoSrc = src;
    },

    async uploadVideo(file) {
      const fd = new FormData();
      fd.append("file", file);
      const res = await fetch(`${API_BASE}/upload_video`, { method: "POST", body: fd });
      const data = await res.json();
      if (!data.path) throw new Error("upload failed");
      this.videoPath = data.path;
    },

    setRoiLive(payload) {
      if (!payload || payload.cleared || payload.w <= 0 || payload.h <= 0) {
        this.roi = { x: 0, y: 0, w: 0, h: 0 };
        this.roiFrame = null;
        return;
      }
      this.roi = { x: payload.x, y: payload.y, w: payload.w, h: payload.h };
      this.displayW = payload.displayW || 0;
      this.displayH = payload.displayH || 0;
    },

    async extract() {
      if (!this.tSec || !this.saveDir || !this.videoPath) {
        throw new Error("missing required fields");
      }
      if (!this.roi || this.roi.w <= 0 || this.roi.h <= 0) {
        throw new Error("ROI required");
      }

      const res = await fetch(`${API_BASE}/manual/extract`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          videoPath: this.videoPath,
          roi: this.roi,
          t: Number(this.tSec),
          saveDir: this.saveDir,
          displayW: this.displayW,
          displayH: this.displayH,
          currentTimeSec: this.currentTimeSec,
        }),
      });

      const data = await res.json();
      if (!data.ok) throw new Error(data.error || "extract failed");

      this.previewTotal = data.total || 0;
      this.previewIndex = this.previewTotal ? 1 : 0;
      this.previews = {};
      if (data.items?.[0]) this.previews[1] = data.items[0];
      this.roiFrame = data.roiFrame || null;
      this.status = "extracted";
    },

    async saveAll() {
      const res = await fetch(`${API_BASE}/manual/save`, { method: "POST" });
      const data = await res.json();
      if (!data.ok) throw new Error(data.error || "save failed");
      return data;
    },

    async fetchPreview(index) {
      const res = await fetch(`${API_BASE}/manual/preview?index=${index}`);
      const data = await res.json();
      if (!data.ok) throw new Error(data.error || "preview failed");

      this.previewIndex = data.index;
      this.previewTotal = data.total;
      this.previews[index] = data.previewBase64;
    },

    resetInputs() {
      this.status = "idle";
      this.roi = null;
      this.roiFrame = null;
      this.tSec = "";
      this.saveDir = "";
      this.previewIndex = 0;
      this.previewTotal = 0;
      this.previews = {};
    },
    async save() {
      const res = await fetch(`${API_BASE}/manual/save`, { method: "POST" });
      const data = await res.json();
      if (!data.ok) throw new Error(data.error || "save failed");
      return data;
    }
  },
});

