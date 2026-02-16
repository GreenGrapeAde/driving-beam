import { defineStore } from "pinia";

export const useManualCropStore = defineStore("manualCrop", {
  state: () => ({
    status: "idle", // idle | extracted | saved
    videoSrc: "",
    roi: null, // {x,y,w,h}
    roiFrame: null, // {x,y,w,h} from server
    tSec: 2,
    rgbCount: 10,
    saveDir: "",
    previews: [],
    total: 0,
    currentIndex: 0,

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
    resetAll() {
      this.status = "idle";
      this.roi = null;
      this.roiFrame = null;
      this.previews = [];
      this.total = 0;
      this.currentIndex = 0;
    },
  },
});
