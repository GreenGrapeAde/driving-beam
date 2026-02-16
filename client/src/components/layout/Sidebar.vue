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

    <button
      class="btn"
      :class="{ 'is-active': mode === 'manual' }"
      @click="$emit('update:mode', 'manual')"
    >
      Manual
    </button>
  </aside>
</template>

<script setup>
defineProps({
  mode: { type: String, required: true },
});
defineEmits(["update:mode"]);
</script>
