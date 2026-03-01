<template>
  <aside class="sidebar">
    <!-- Logo / Brand -->
    <div class="sidebar-brand">
      <div class="brand-icon">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
          <circle cx="12" cy="12" r="3" />
          <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2z" />
          <path d="M12 6v2M12 16v2M6 12H4M20 12h-2" />
        </svg>
      </div>
      <span class="brand-label">Hard-case Crop Tool</span>
    </div>

    <!-- Divider -->
    <div class="sidebar-divider" />

    <!-- Section Label -->
    <p class="sidebar-section-label">VIEW MODE</p>

    <!-- Nav Items -->
    <nav class="sidebar-nav">
      <button
        class="nav-item"
        :class="{ 'is-active': mode === 'live' }"
        @click="$emit('update:mode', 'live')"
      >
        <span class="nav-icon">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="3" fill="currentColor" />
            <path d="M5.64 5.64a9 9 0 1 0 12.72 12.72A9 9 0 0 0 5.64 5.64z" />
            <path d="M8.46 8.46a5 5 0 1 0 7.07 7.07A5 5 0 0 0 8.46 8.46z" />
          </svg>
        </span>
        <span class="nav-label">Live</span>
        <span v-if="mode === 'live'" class="live-badge">
          <span class="live-dot" />
          ON AIR
        </span>
        <span class="nav-arrow">›</span>
      </button>

      <button
        class="nav-item"
        :class="{ 'is-active': mode === 'playback' }"
        @click="$emit('update:mode', 'playback')"
      >
        <span class="nav-icon">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polygon points="5,3 19,12 5,21" fill="currentColor" stroke="none" />
          </svg>
        </span>
        <span class="nav-label">Playback</span>
        <span class="nav-arrow">›</span>
      </button>

      <button
        class="nav-item"
        :class="{ 'is-active': mode === 'manual' }"
        @click="$emit('update:mode', 'manual')"
      >
        <span class="nav-icon">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M12 20h9" />
            <path d="M16.5 3.5a2.12 2.12 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z" />
          </svg>
        </span>
        <span class="nav-label">Manual</span>
        <span class="nav-arrow">›</span>
      </button>
    </nav>

    <!-- Bottom status -->
    <div class="sidebar-footer">
      <div class="status-row">
        <span class="status-dot active" />
        <span class="status-text">System Online</span>
      </div>
      <div class="status-row">
        <span class="status-dot" />
        <span class="status-text">4 Cameras Active</span>
      </div>
    </div>
  </aside>
</template>

<script setup>
defineProps({
  mode: { type: String, required: true },
});
defineEmits(["update:mode"]);
</script>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=Rajdhani:wght@500;600;700&family=IBM+Plex+Mono:wght@400;500&display=swap');

.sidebar {
  width: 220px;
  height: 100vh;
  background: #0a0d14;
  border-right: 1px solid rgba(255, 255, 255, 0.06);
  display: flex;
  flex-direction: column;
  padding: 24px 0;
  font-family: 'Rajdhani', sans-serif;
  position: relative;
  overflow: hidden;
}

/* Subtle grid texture overlay */
.sidebar::before {
  content: '';
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(rgba(255,255,255,0.02) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255,255,255,0.02) 1px, transparent 1px);
  background-size: 24px 24px;
  pointer-events: none;
}

/* Accent glow line on left edge */
.sidebar::after {
  content: '';
  position: absolute;
  left: 0;
  top: 20%;
  bottom: 20%;
  width: 2px;
  background: linear-gradient(to bottom, transparent, #00d4ff, transparent);
  opacity: 0.5;
}

/* ── Brand ────────────────────────── */
.sidebar-brand {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 0 20px 20px;
}

.brand-icon {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  background: linear-gradient(135deg, #00d4ff22, #0066ff33);
  border: 1px solid #00d4ff44;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #00d4ff;
  flex-shrink: 0;
}

.brand-icon svg {
  width: 18px;
  height: 18px;
}

.brand-label {
  font-size: 15px;
  font-weight: 700;
  letter-spacing: 0.08em;
  color: #e8edf5;
  text-transform: uppercase;
}

/* ── Divider ──────────────────────── */
.sidebar-divider {
  height: 1px;
  margin: 0 16px 20px;
  background: linear-gradient(to right, transparent, rgba(255,255,255,0.08), transparent);
}

/* ── Section Label ────────────────── */
.sidebar-section-label {
  font-family: 'IBM Plex Mono', monospace;
  font-size: 9px;
  font-weight: 500;
  letter-spacing: 0.2em;
  color: rgba(255, 255, 255, 0.25);
  padding: 0 20px 10px;
  margin: 0;
  text-transform: uppercase;
}

/* ── Nav ──────────────────────────── */
.sidebar-nav {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 0 12px;
  flex: 1;
}

.nav-item {
  position: relative;
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
  padding: 12px 12px;
  border-radius: 8px;
  background: transparent;
  border: 1px solid transparent;
  cursor: pointer;
  transition: all 0.2s ease;
  color: rgba(255, 255, 255, 0.45);
  text-align: left;
}

.nav-item:hover {
  background: rgba(255, 255, 255, 0.05);
  color: rgba(255, 255, 255, 0.8);
  border-color: rgba(255, 255, 255, 0.07);
}

.nav-item.is-active {
  background: linear-gradient(135deg, rgba(0, 212, 255, 0.12), rgba(0, 102, 255, 0.08));
  border-color: rgba(0, 212, 255, 0.25);
  color: #ffffff;
}

/* Active left accent bar */
.nav-item.is-active::before {
  content: '';
  position: absolute;
  left: -12px;
  top: 50%;
  transform: translateY(-50%);
  width: 3px;
  height: 60%;
  border-radius: 0 2px 2px 0;
  background: #00d4ff;
  box-shadow: 0 0 8px #00d4ff88;
}

.nav-icon {
  width: 20px;
  height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  transition: color 0.2s;
}

.nav-icon svg {
  width: 16px;
  height: 16px;
}

.nav-item.is-active .nav-icon {
  color: #00d4ff;
}

.nav-label {
  font-size: 15px;
  font-weight: 600;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  flex: 1;
}

.nav-arrow {
  font-size: 18px;
  line-height: 1;
  opacity: 0;
  transform: translateX(-4px);
  transition: all 0.2s ease;
  color: #00d4ff;
}

.nav-item:hover .nav-arrow,
.nav-item.is-active .nav-arrow {
  opacity: 1;
  transform: translateX(0);
}

/* Live badge */
.live-badge {
  display: flex;
  align-items: center;
  gap: 4px;
  font-family: 'IBM Plex Mono', monospace;
  font-size: 8px;
  font-weight: 500;
  letter-spacing: 0.1em;
  color: #ff4757;
  background: rgba(255, 71, 87, 0.1);
  border: 1px solid rgba(255, 71, 87, 0.25);
  border-radius: 4px;
  padding: 2px 5px;
  white-space: nowrap;
}

.live-dot {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: #ff4757;
  flex-shrink: 0;
  animation: blink 1.2s ease-in-out infinite;
}

@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.2; }
}

/* ── Footer ───────────────────────── */
.sidebar-footer {
  padding: 20px 20px 0;
  border-top: 1px solid rgba(255, 255, 255, 0.06);
  margin: 0 0 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.status-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.2);
  flex-shrink: 0;
}

.status-dot.active {
  background: #00e676;
  box-shadow: 0 0 6px #00e67688;
}

.status-text {
  font-family: 'IBM Plex Mono', monospace;
  font-size: 10px;
  color: rgba(255, 255, 255, 0.3);
  letter-spacing: 0.05em;
}
</style>