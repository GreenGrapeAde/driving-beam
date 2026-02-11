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
        <span class="text-l text-slate-500">Mode</span>
        <span
          class="inline-flex items-center justify-center gap-1 rounded-full px-2 py-1 text-l font-semibold w-28"
          :class="mode === 'live' ? 'bg-red-100 text-red-800' : 'bg-emerald-100 text-emerald-800'"
        >
          <span>{{ mode.toUpperCase() }}</span>

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
