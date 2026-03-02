<template>
  <div class="dashboard-header">
    <!-- Left: Title block -->
    <div class="header-title-block">
      <div class="header-eyebrow">
        <span class="eyebrow-line" />
        <span class="eyebrow-text">Image Auto / Manual Crop Tool</span>
      </div>
      <h1 class="header-title">Dashboard</h1>
    </div>

    <!-- Right: Mode badge + time -->
    <div class="header-right">
      <div class="header-time" id="header-clock">{{ currentTime }}</div>

      <div class="mode-badge" :class="`mode-badge--${mode}`">
        <span class="mode-badge__dot" />
        <span class="mode-badge__label">{{ mode.toUpperCase() }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount } from "vue";

defineProps({
  mode: { type: String, required: true },
});

const currentTime = ref("");
let timer = null;

function updateClock() {
  const now = new Date();
  currentTime.value = now.toLocaleTimeString("ko-KR", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  });
}

onMounted(() => {
  updateClock();
  timer = setInterval(updateClock, 1000);
});

onBeforeUnmount(() => {
  clearInterval(timer);
});
</script>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=Rajdhani:wght@500;600;700&family=IBM+Plex+Mono:wght@400;500&display=swap');

.dashboard-header {
  display: flex;
  align-items: flex-start;      /* ← 상단 정렬 */
  justify-content: space-between;
  gap: 16px;
  padding: 0 0 16px 0;          /* ← 좌우 패딩 제거, 하단만 */
  margin-bottom: 20px;          /* ← 구분선과 아래 콘텐츠 사이 여백 */
  /* border-bottom: 1px solid rgba(15, 23, 42, 0.08); */
  background: transparent;      /* ← 배경 제거 */
  width: 100%;
}

/* ── Left ───────────────────────── */
.header-title-block {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.header-eyebrow {
  display: flex;
  align-items: center;
  gap: 8px;
}

.eyebrow-line {
  display: inline-block;
  width: 20px;
  height: 2px;
  background: #00d4ff;
  border-radius: 2px;
  flex-shrink: 0;
}

.eyebrow-text {
  font-family: 'IBM Plex Mono', monospace;
  font-size: 10px;
  font-weight: 500;
  letter-spacing: 0.15em;
  text-transform: uppercase;
  color: #64748b;
}

.header-title {
  font-family: 'Rajdhani', sans-serif;
  font-size: 28px;
  font-weight: 700;
  letter-spacing: 0.03em;
  color: #0f172a;
  line-height: 1;
  margin: 0;
  text-transform: uppercase;
}

/* ── Right ──────────────────────── */
.header-right {
  display: flex;
  align-items: center;
  gap: 16px;
  padding-top: 2px;             /* ← 시계/뱃지 살짝 위로 */
  flex-shrink: 0;               /* ← 오른쪽 영역 줄어들지 않게 */
}

.header-time {
  font-family: 'IBM Plex Mono', monospace;
  font-size: 13px;
  font-weight: 500;
  color: #94a3b8;
  letter-spacing: 0.08em;
  padding: 6px 12px;
  border-radius: 8px;
  background: rgba(15, 23, 42, 0.04);
  border: 1px solid rgba(15, 23, 42, 0.07);
}

/* ── Mode Badge ─────────────────── */
.mode-badge {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  padding: 6px 14px;
  border-radius: 999px;
  font-family: 'Rajdhani', sans-serif;
  font-size: 13px;
  font-weight: 700;
  letter-spacing: 0.12em;
  border: 1px solid transparent;
  transition: all 0.25s ease;
  min-width: 110px;
  justify-content: center;
}

.mode-badge__dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  flex-shrink: 0;
}

/* LIVE */
.mode-badge--live {
  background: rgba(239, 68, 68, 0.1);
  border-color: rgba(239, 68, 68, 0.25);
  color: #dc2626;
}
.mode-badge--live .mode-badge__dot {
  background: #ef4444;
  box-shadow: 0 0 6px #ef444488;
  animation: pulse-dot 1.2s ease-in-out infinite;
}

/* PLAYBACK */
.mode-badge--playback {
  background: rgba(16, 185, 129, 0.1);
  border-color: rgba(16, 185, 129, 0.25);
  color: #059669;
}
.mode-badge--playback .mode-badge__dot {
  background: #10b981;
  box-shadow: 0 0 6px #10b98188;
}

/* MANUAL */
.mode-badge--manual {
  background: rgba(59, 130, 246, 0.1);
  border-color: rgba(59, 130, 246, 0.25);
  color: #2563eb;
}
.mode-badge--manual .mode-badge__dot {
  background: #3b82f6;
  box-shadow: 0 0 6px #3b82f688;
}

@keyframes pulse-dot {
  0%, 100% { opacity: 1; transform: scale(1); }
  50%       { opacity: 0.4; transform: scale(0.8); }
}
</style>