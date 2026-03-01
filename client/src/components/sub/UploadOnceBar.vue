<template>
  <div v-if="enabled" class="upload-bar">
    <!-- 업로드 전 -->
    <template v-if="!fileName">
      <button class="upload-btn" type="button" @click="openPicker">
        <span class="upload-btn__icon">
          <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.8">
            <path d="M8 11V3M5 6l3-3 3 3" stroke-linecap="round" stroke-linejoin="round"/>
            <path d="M2 12v1a1 1 0 0 0 1 1h10a1 1 0 0 0 1-1v-1" stroke-linecap="round"/>
          </svg>
        </span>
        <span>Upload video</span>
      </button>
      <span class="upload-helper" v-if="helper">{{ helper }}</span>
    </template>

    <!-- 업로드 후 -->
    <template v-else>
      <div class="file-chip">
        <span class="file-chip__icon">
          <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.8">
            <rect x="3" y="1" width="10" height="14" rx="2"/>
            <path d="M6 5h4M6 8h4M6 11h2" stroke-linecap="round"/>
          </svg>
        </span>
        <span class="file-chip__name">{{ fileName }}</span>
        <button class="file-chip__delete" type="button" @click="clearInternal" title="Delete">
          <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M4 4l8 8M12 4l-8 8" stroke-linecap="round"/>
          </svg>
        </button>
      </div>
    </template>

    <input ref="fileInput" type="file" accept="video/*" class="hidden" @change="onFileChange" />
  </div>
</template>

<script setup>
import { onBeforeUnmount, ref, watch } from "vue";

const props = defineProps({
  enabled: { type: Boolean, default: true },
  helper: { type: String, default: "" },
});

const emit = defineEmits(["uploaded", "cleared"]);

const fileInput = ref(null);
const fileName = ref("");
let objectUrl = null;

function openPicker() {
  fileInput.value?.click();
}

function onFileChange(e) {
  const file = e.target.files?.[0];
  if (!file) return;
  if (objectUrl) URL.revokeObjectURL(objectUrl);
  objectUrl = URL.createObjectURL(file);
  fileName.value = file.name;
  emit("uploaded", { src: objectUrl, name: file.name, file });
  e.target.value = "";
}

function clearInternal() {
  if (objectUrl) URL.revokeObjectURL(objectUrl);
  objectUrl = null;
  fileName.value = "";
  emit("cleared");
}

watch(
  () => props.enabled,
  (val) => { if (!val) clearInternal(); }
);

onBeforeUnmount(() => {
  if (objectUrl) URL.revokeObjectURL(objectUrl);
});
</script>

<style scoped>
.upload-bar {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

/* ── Upload 버튼 ─────────────────────────── */
.upload-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px 6px 10px;
  border-radius: 8px;
  border: 1px solid rgba(15, 23, 42, 0.14);
  background: #ffffff;
  color: #0f172a;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.15s, border-color 0.15s, box-shadow 0.15s;
  box-shadow: 0 1px 3px rgba(0,0,0,0.06);
  white-space: nowrap;
}

.upload-btn:hover {
  background: #f8fafc;
  border-color: rgba(15, 23, 42, 0.22);
  box-shadow: 0 2px 6px rgba(0,0,0,0.08);
}

.upload-btn:active {
  background: #f1f5f9;
  box-shadow: none;
}

.upload-btn__icon {
  width: 15px;
  height: 15px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #64748b;
  flex-shrink: 0;
}

.upload-btn__icon svg {
  width: 15px;
  height: 15px;
}

/* ── Helper 텍스트 ─────────────────────── */
.upload-helper {
  font-size: 12px;
  color: #94a3b8;
}

/* ── 파일 칩 ──────────────────────────── */
.file-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 5px 6px 5px 10px;
  border-radius: 8px;
  border: 1px solid rgba(15, 23, 42, 0.1);
  background: #f8fafc;
  max-width: 420px;
  transition: border-color 0.15s;
}

.file-chip:hover {
  border-color: rgba(15, 23, 42, 0.18);
}

.file-chip__icon {
  width: 14px;
  height: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #94a3b8;
  flex-shrink: 0;
}

.file-chip__icon svg {
  width: 14px;
  height: 14px;
}

.file-chip__name {
  font-size: 12px;
  font-weight: 500;
  color: #334155;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 280px;
}

.file-chip__delete {
  width: 22px;
  height: 22px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 5px;
  border: none;
  background: transparent;
  color: #94a3b8;
  cursor: pointer;
  flex-shrink: 0;
  transition: background 0.12s, color 0.12s;
  padding: 0;
}

.file-chip__delete:hover {
  background: rgba(239, 68, 68, 0.08);
  color: #ef4444;
}

.file-chip__delete svg {
  width: 11px;
  height: 11px;
}
</style>