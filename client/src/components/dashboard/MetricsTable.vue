<template>
  <div class="grid grid-cols-1 lg:grid-cols-2 gap-4 items-stretch h-[500px]">
    <div class="metrics1">
      <div class="flex items-center justify-between mb-3">
        <h3 class="text-base font-bold">Real-time Metrics (Precision/Recall/IDF1)</h3>
        <div class="text-xs text-slate-500">placeholder</div>
      </div>

      <div class="relative w-full h-[420px] bg-slate-100 p-4 rounded-xl border border-slate-200 flex flex-col">
          <div class="flex-1 w-full">
            <canvas id="realtimeChart"></canvas>
          </div>
      </div>
    </div>


    <div class="metrics2">
      <div class="flex items-center justify-between mb-3">
        <h3 class="text-base font-bold">Real-time Logs</h3>
        <div class="text-xs text-slate-500">placeholder</div>
      </div>

      <div class="overflow-auto">
        <table class="w-full text-sm">
          <thead class="text-slate-600">
            <tr class="border-b">
              <th class="text-left py-2 pr-3">Metric</th>
              <th class="text-left py-2 pr-3">Model A</th>
              <th class="text-left py-2 pr-3">Model B</th>
              <th class="text-left py-2 pr-3">Notes</th>
            </tr>
          </thead>
          <tbody>
            <tr class="border-b">
              <td class="py-2 pr-3 font-medium">FPS</td>
              <td class="py-2 pr-3">28.7</td>
              <td class="py-2 pr-3">26.9</td>
              <td class="py-2 pr-3 text-slate-600">backend inference loop</td>
            </tr>
            <tr class="border-b">
              <td class="py-2 pr-3 font-medium">Latency (ms)</td>
              <td class="py-2 pr-3">41.2</td>
              <td class="py-2 pr-3">52.8</td>
              <td class="py-2 pr-3 text-slate-600">ws update interval</td>
            </tr>
            <tr class="border-b">
              <td class="py-2 pr-3 font-medium">Detections/frame</td>
              <td class="py-2 pr-3">3.1</td>
              <td class="py-2 pr-3">3.4</td>
              <td class="py-2 pr-3 text-slate-600">threshold dependent</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, onUnmounted } from 'vue';
import Chart from 'chart.js/auto';







</script>