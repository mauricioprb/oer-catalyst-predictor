<template>
  <span
    class="inline-block h-2 w-2 rounded-full"
    :class="online ? 'bg-emerald-500 shadow-[0_0_6px_rgba(34,197,94,0.4)]' : 'bg-red-500'"
    :aria-label="online ? 'Online' : 'Offline'"
    role="status"
  ></span>
</template>

<script setup lang="ts">
defineProps<{
  online: boolean
}>()
</script>
