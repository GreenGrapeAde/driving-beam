<template>
  <div v-if="enabled" class="flex flex-wrap items-center gap-2">
    <button class="ui-btn" type="button" @click="openPicker">Upload once</button>
    <button class="ui-btn-secondary" type="button" :disabled="!fileName" @click="clearInternal">
      Delete
    </button>
    <span class="text-s text-slate-600" v-if="fileName">Loaded: {{ fileName }}</span>
    <span class="text-s text-slate-500" v-else-if="helper">{{ helper }}</span>
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
  (val) => {
    if (!val) {
      clearInternal();
    }
  }
);

onBeforeUnmount(() => {
  if (objectUrl) URL.revokeObjectURL(objectUrl);
});
</script>
