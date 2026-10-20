<script setup>
defineProps(['kind'])
</script>
<template><svg viewBox="0 0 64 64" class="weather-icon" :class="kind" aria-hidden="true"><g v-if="kind==='clear'" class="sun"><circle cx="32" cy="32" r="12"/><path d="M32 6v6m0 40v6M6 32h6m40 0h6M14 14l4 4m28 28 4 4m0-36-4 4M18 46l-4 4"/></g><g v-else-if="kind==='unknown'"><circle cx="32" cy="32" r="20"/><path d="M26 25c0-9 15-9 15 0 0 6-9 5-9 12m0 7v1"/></g><g v-else><path d="M17 41C1 39 7 19 21 23c6-20 31-13 29 3 16 1 14 22-1 21H19"/><path v-if="kind==='rain'" class="precipitation" d="m23 49-3 8m15-8-3 8m15-8-3 8"/><path v-if="kind==='snow'" class="precipitation" d="M22 50v10m-5-5h10m15-5v10m-5-5h10"/><path v-if="kind==='storm'" d="m35 40-9 12h9l-6 10"/><path v-if="kind==='fog'" d="M13 53h40M19 60h28"/></g></svg></template>
