import { defineStore } from "pinia";

const API_BASE = "http://localhost:8000";

export const usePlaybackCropStore = defineStore("playbackCrop", {
  state: () => ({
    videoSrc: "",
    videoPath: "",
    filename: "",
    isUploading: false,
    uploadProgress: 0,
  }),
  actions: {
    setVideoLocal(src) {
      this.videoSrc = src || "";
    },

    async uploadVideo(file, onProgress) {
      this.isUploading = true;
      this.uploadProgress = 0;

      return new Promise((resolve, reject) => {
        const xhr = new XMLHttpRequest();
        xhr.open("POST", `${API_BASE}/upload_video`);

        xhr.upload.onprogress = (evt) => {
          if (!evt.lengthComputable) return;
          const percent = Math.round((evt.loaded / evt.total) * 100);
          this.uploadProgress = percent;
          if (typeof onProgress === "function") onProgress(percent);
        };

        xhr.onload = () => {
          this.isUploading = false;
          try {
            const data = JSON.parse(xhr.responseText || "{}");
            if (!data.path || !data.filename) {
              reject(new Error("upload failed"));
              return;
            }
            this.videoPath = data.path;
            this.filename = data.filename;
            this.uploadProgress = 100;
            resolve(data);
          } catch (e) {
            reject(new Error("upload failed"));
          }
        };

        xhr.onerror = () => {
          this.isUploading = false;
          reject(new Error("upload failed"));
        };

        const fd = new FormData();
        fd.append("file", file);
        xhr.send(fd);
      });
    },

    reset() {
      this.videoSrc = "";
      this.videoPath = "";
      this.filename = "";
      this.isUploading = false;
      this.uploadProgress = 0;
    },
  },
});
