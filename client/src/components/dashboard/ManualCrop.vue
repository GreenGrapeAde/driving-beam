<template>
  <section class="space-y-4 chat-safe">
    <UploadOnceBar
      :enabled="true"
      helper="Upload once for manual crop"
      @uploaded="onUploaded"
      @cleared="onCleared"
    />

    <div class="panel">
      <div class="flex items-center justify-between gap-3 mb-3">
        <div>
          <div class="text-sm text-slate-500">Manual Crop</div>
          <div class="text-lg font-bold">Single Video Playback</div>
        </div>
      </div>

      <ManualVideoWithOverlay
        :mode="'manual'"
        :slotName="'M'"
        :video-src="store.videoSrc"
        :play-token="store.playToken"
        :pause-token="store.pauseToken"
        :volume="store.volume"
        :seek-token="store.seekToken"
        :seek-fraction="store.seekFraction"
        :enable-roi="true"
        @play="onPlay"
        @pause="onPause"
        @volume-change="onVolume"
        @seek="onSeek"
        @roi-change="onRoi"
        @time-update="onTime"
        @display-change="onDisplay"
      />
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
      <!-- Preview -->
      <div class="panel">
        <div class="flex items-center justify-between mb-3">
          <div class="text-base font-semibold">Preview</div>
          <div class="text-xs text-slate-500" v-if="store.total">
            {{ store.currentIndex }} / {{ store.total }}
          </div>
        </div>

        <div v-if="store.status !== 'idle'" class="preview-wrap">
          <img v-if="currentPreview" :src="`data:image/png;base64,${currentPreview}`" class="preview-img" />
          <div v-else class="preview-empty">No preview loaded.</div>
        </div>
        <div v-else class="preview-empty">No preview yet.</div>

        <div v-if="store.status !== 'idle'" class="preview-nav">
          <button class="ui-btn-secondary" type="button" :disabled="store.currentIndex <= 1">&lt;</button>
          <div class="text-xs">
            <input class="page-input" type="number" :min="1" :max="store.total" v-model.number="pageInput" />
            / {{ store.total }}
          </div>
          <button class="ui-btn-secondary" type="button" :disabled="store.currentIndex >= store.total">&gt;</button>
          <button class="ui-btn-secondary" type="button">Go</button>
        </div>
      </div>

      <!-- Controls -->
      <div class="panel">
        <div class="text-base font-semibold mb-3">Controls</div>

        <div class="grid grid-cols-2 gap-3 text-sm">
          <div class="field"><div class="label">x</div><div class="value">{{ roiFrame.x ?? "-" }}</div></div>
          <div class="field"><div class="label">y</div><div class="value">{{ roiFrame.y ?? "-" }}</div></div>
          <div class="field"><div class="label">w</div><div class="value">{{ roiFrame.w ?? "-" }}</div></div>
          <div class="field"><div class="label">h</div><div class="value">{{ roiFrame.h ?? "-" }}</div></div>
        </div>

        <div class="mt-4 grid grid-cols-2 gap-3">
          <label class="input-row">
            <span>t(s)</span>
            <input class="input" type="number" min="0.1" step="0.1" v-model.number="store.tSec" />
          </label>
          <label class="input-row">
            <span>rgb</span>
            <input class="input" type="number" min="1" step="1" v-model.number="store.rgbCount" />
          </label>
        </div>

        <div class="mt-4 grid grid-cols-1 gap-2">
          <label class="input-row">
            <span>Save dir</span>
            <input class="input" type="text" v-model="store.saveDir" placeholder="C:\\path\\to\\output" />
          </label>
        </div>

        <div class="mt-4 flex items-center gap-2">
          <button class="ui-btn" type="button" v-if="store.status === 'idle'" @click="onExtract">Extract</button>
          <button class="ui-btn" type="button" v-if="store.status === 'extracted'">Save</button>
          <button class="ui-btn-secondary" type="button" @click="store.resetAll()">Reset</button>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup>
import { computed, ref } from "vue";
import { useManualCropStore } from "@/manualCrop";
import ManualVideoWithOverlay from "@/components/dashboard/ManualVideoWithOverlay.vue";
import UploadOnceBar from "@/components/dashboard/UploadOnceBar.vue";

const store = useManualCropStore();
const pageInput = ref(1);

const roiFrame = computed(() => store.roiFrame || {});
const currentPreview = computed(() => {
  if (!store.currentIndex) return "";
  return store.previews[store.currentIndex - 1] || "";
});

function onUploaded(payload) {
  store.videoSrc = payload.src;
  store.resetAll();
}

function onCleared() {
  store.videoSrc = "";
  store.resetAll();
}

function onPlay() { store.playToken += 1; }
function onPause() { store.pauseToken += 1; }
function onVolume(val) { store.volume = val; }
function onSeek(frac) { store.seekFraction = frac; store.seekToken += 1; }

function onRoi(payload) {
  store.roi = { x: payload.x, y: payload.y, w: payload.w, h: payload.h };
  store.displayW = payload.displayW || 0;
  store.displayH = payload.displayH || 0;
}

function onTime(payload) { store.currentTimeSec = payload.currentTime || 0; }
function onDisplay(payload) {
  store.displayW = payload.width || 0;
  store.displayH = payload.height || 0;
}

async function onExtract() {

  if (!store.roi || !store.saveDir || !store.tSec || !store.rgbCount) {
    alert("모든 값을 입력하세요");
    return;
  }

  const res = await fetch("http://localhost:8000/manual/extract", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      videoPath: store.videoSrc,
      roi: store.roi,
      t: store.tSec,
      rgb: store.rgbCount,
      saveDir: store.saveDir
    })
  });

  const data = await res.json();

  if (data.ok) {
    store.previews = data.items;
    store.total = data.total;
    store.status = "extracted";
    store.roiFrame = data.roiFrame;
  }
}


</script>

<style scoped>
.preview-wrap {
  width: 100%;
  height: 280px;
  border-radius: 12px;
  overflow: hidden;
  background: #0b1220;
  display: grid;
  place-items: center;
}

.preview-img {
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
}

.preview-empty {
  height: 280px;
  display: grid;
  place-items: center;
  color: #94a3b8;
  border: 1px dashed rgba(15, 23, 42, 0.1);
  border-radius: 12px;
}

.preview-nav {
  margin-top: 10px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.input-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  font-size: 13px;
}

.input {
  width: 140px;
  padding: 6px 8px;
  border-radius: 8px;
  border: 1px solid rgba(15, 23, 42, 0.12);
  background: #fff;
}

.field {
  border: 1px solid rgba(15, 23, 42, 0.08);
  border-radius: 8px;
  padding: 8px;
  background: #f8fafc;
}

.label {
  font-size: 11px;
  color: #64748b;
}

.value {
  font-size: 13px;
  font-weight: 600;
}

.page-input {
  width: 60px;
  padding: 4px 6px;
  border-radius: 6px;
  border: 1px solid rgba(15, 23, 42, 0.12);
}
</style>


