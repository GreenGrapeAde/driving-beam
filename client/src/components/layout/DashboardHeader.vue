<template>
  <header class="mb-4">
    <div class="flex items-start justify-between gap-4">
      <div>
        <h1 class="text-2xl font-extrabold tracking-tight">
          ADB Performance Validation Dashboard
        </h1>
        <p class="mt-1 text-sm text-slate-600">
          Compare baseline vs custom detection behavior in real-time / playback.
        </p>
      </div>

      <div class="flex items-center gap-2">
        <span class="text-xs text-slate-500">Mode</span>
        <span
          class="inline-flex items-center rounded-full px-2 py-1 text-xs font-semibold"
          :class="mode === 'live' ? 'bg-emerald-100 text-emerald-800' : 'bg-indigo-100 text-indigo-800'"
        >
          {{ mode.toUpperCase() }}
        </span>
      </div>
    </div>
  </header>
</template>

<script setup>
defineProps({
  mode: { type: String, required: true },
});
</script>
