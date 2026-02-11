<template>
  <aside class="toolbar">     <button
      class="btn"
      :class="{ 'is-active': mode === 'live' }"
      @click="$emit('update:mode', 'live')"
    >
      Live
    </button>

    <button
      class="btn"
      :class="{ 'is-active': mode === 'playback' }"
      @click="$emit('update:mode', 'playback')"
    >
      Playback
    </button>

    <!-- <div class="mt-4 text-xs text-slate-200/80 leading-relaxed">
      <div class="font-semibold text-slate-100 mb-1">ADB Test Dashboard</div>
      <div>• A/B 모델 비교</div>
      <div>• Beam Visualization</div>
      <div>• Metrics 로그</div>
    </div> -->
  </aside>
</template>

<script setup>
defineProps({
  mode: { type: String, required: true },
});
defineEmits(["update:mode"]);
</script>
