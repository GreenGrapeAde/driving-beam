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
        ref="videoOverlay"
        :slotName="'M'"
        :video-src="store.videoSrc"
        :play-token="store.playToken"
        :pause-token="store.pauseToken"
        :volume="store.volume"
        :seek-token="store.seekToken"
        :seek-fraction="store.seekFraction"
        :enable-roi="!!store.videoSrc"
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
          <div class="text-xs text-slate-500" v-if="store.previewTotal">
            {{ store.previewIndex }} / {{ store.previewTotal }}
          </div>
        </div>

        <div v-if="store.previewIndex" class="preview-wrap">
          <img v-if="currentPreview" :src="`data:image/png;base64,${currentPreview}`" class="preview-img" />
          <div v-else class="preview-empty">No preview loaded.</div>
        </div>
        <div v-else class="preview-empty">No preview yet.</div>

        <div v-if="store.previewTotal" class="preview-nav flex items-center justify-between">
          
          <!-- 왼쪽 그룹 -->
          <div class="flex items-center gap-2 mx-auto">
            <button class="ui-btn-secondary" type="button" @click="prevPage" :disabled="store.previewIndex <= 1">&lt;</button>
            <div class="text-xs">
              <input class="page-input" type="number" :min="1" :max="store.previewTotal" v-model.number="pageInput" @keyup.enter="goPage" />
              / {{ store.previewTotal }}
            </div>
            <button class="ui-btn-secondary" type="button" @click="nextPage" :disabled="store.previewIndex >= store.previewTotal">&gt;</button>
          </div>

          <!-- 오른쪽 -->
          <button class="ui-btn" type="button" @click="onSave">
            Save All Frames
          </button>

        </div>

      </div>

      <!-- Controls -->
      <div class="panel">
        <div class="text-base font-semibold mb-3">Controls</div>

        <div class="grid grid-cols-2 gap-3 text-sm">
          <div class="field">
            <div class="label">x</div>
            <input class="input" type="text" :value="roiDisplay.x ?? '-'" readonly />
          </div>
          <div class="field">
            <div class="label">y</div>
            <input class="input" type="text" :value="roiDisplay.y ?? '-'" readonly />
          </div>
          <div class="field">
            <div class="label">w</div>
            <input class="input" type="text" :value="roiDisplay.w ?? '-'" readonly />
          </div>
          <div class="field">
            <div class="label">h</div>
            <input class="input" type="text" :value="roiDisplay.h ?? '-'" readonly />
          </div>
        </div>

        <div class="mt-4 grid grid-cols-2 gap-3">
          <label class="input-row">
            <span>t(s)</span>
            <input class="input" type="number" min="0.1" step="0.1" v-model="store.tSec" />
          </label>
          <label class="input-row">
            <span>rgb</span>
            <select class="input" v-model.number="store.rgbCount">
              <option :value="24">24 (default)</option>
            </select>
          </label>
        </div>

        <div class="mt-4 grid grid-cols-2 gap-3">
          <label class="input-row">
            <span>Save dir</span>
          </label>
          <label class="input-row">
            <span class="text-s text-blue-600" v-if="store.saveDir">
              ✓ Ok!
            </span>
            <span class="text-s" v-else>
              -
            </span>
            <button class="ui-btn-secondary" type="button" @click="pickSaveDir">Select</button>
          </label>
        </div>

        <div class="mt-4 flex items-center gap-2">
          <button class="ui-btn" type="button" @click="onExtract">Extract</button>
          <button class="ui-btn-secondary" type="button" @click="onReset">Reset</button>
          <span v-if="errorMsg" class="text-xs text-rose-600">{{ errorMsg }}</span>
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
const errorMsg = ref("");
const videoOverlay = ref(null);

const roiDisplay = computed(() => {
  const src = store.roiFrame || store.roi || { x: 0, y: 0, w: 0, h: 0 };
  return {
    x: Math.round(src.x || 0),
    y: Math.round(src.y || 0),
    w: Math.round(src.w || 0),
    h: Math.round(src.h || 0),
  };
});
const currentPreview = computed(() => {
  if (!store.previewIndex) return "";
  return store.previews[store.previewIndex] || "";
});

async function onUploaded(payload) {
  errorMsg.value = "";
  store.setVideoLocal(payload.src);
  store.resetInputs();
  try {
    await store.uploadVideo(payload.file);
  } catch (e) {
    errorMsg.value = e.message || "upload failed";
  }
}

function onCleared() {
  store.setVideoLocal("");
  store.videoPath = "";
  store.resetInputs();
}

function onPlay() { store.playToken += 1; }
function onPause() { store.pauseToken += 1; }
function onVolume(val) { store.volume = val; }
function onSeek(frac) { store.seekFraction = frac; store.seekToken += 1; }

function onRoi(payload) {
  store.setRoiLive(payload);
}

function onTime(payload) { store.currentTimeSec = payload.currentTime || 0; }
function onDisplay(payload) {
  store.displayW = payload.width || 0;
  store.displayH = payload.height || 0;
}

async function pickSaveDir() {
  errorMsg.value = "";
  if (window.showDirectoryPicker) {
    try {
      const dir = await window.showDirectoryPicker();
      store.saveDir = dir.name;
    } catch (e) {
      // user canceled
    }
  } else {
    const val = window.prompt("Save dir path");
    if (val) store.saveDir = val;
  }
}

async function onExtract() {
  errorMsg.value = "";
  try {
    await store.extract();
    pageInput.value = store.previewIndex || 1;
  } catch (e) {
    errorMsg.value = e.message || "extract failed";
  }
}

function onReset() {
  errorMsg.value = "";
  store.resetInputs();
  videoOverlay.value?.clearSelection(); // ROI 해제
}

async function prevPage() {
  const next = Math.max(1, store.previewIndex - 1);
  await store.fetchPreview(next);
  pageInput.value = next;
}

async function nextPage() {
  const next = Math.min(store.previewTotal, store.previewIndex + 1);
  await store.fetchPreview(next);
  pageInput.value = next;
}

async function goPage() {
  let target = Number(pageInput.value) || 1;
  if (target < 1) target = 1;
  if (target > store.previewTotal) target = store.previewTotal;
  await store.fetchPreview(target);
  pageInput.value = target;
}

async function onSave() {
  errorMsg.value = "";
  try {
    const result = await store.save(); // { ok, savedCount, dir }
    errorMsg.value = `Saved ${result.savedCount} BMP files to: ${result.dir}`;
  } catch (e) {
    errorMsg.value = e.message || "save failed";
  }
}


console.log("typeof save:", typeof store.save, "typeof saveAll:", typeof store.saveAll);
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
  width: 46px;
  padding: 4px 6px;
  border-radius: 6px;
  border: 1px solid rgba(15, 23, 42, 0.12);
}
</style>


