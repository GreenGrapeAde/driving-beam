<template>
  <section class="space-y-4">
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-4 items-stretch">
      <ModelPane :mode="mode" slotName="A" title="Model A (Baseline)" />
      <ModelPane :mode="mode" slotName="B" title="Model B (Custom)" />
    </div>

    <MetricsTable />
  </section>
</template>

<script setup>
import ModelPane from "./ModelPane.vue";
import MetricsTable from "./MetricsTable.vue";

defineProps({
  mode: { type: String, required: true },
});
</script>
