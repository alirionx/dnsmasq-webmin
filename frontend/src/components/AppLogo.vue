<script setup>
// Logo: a globe (DNS) on a tile in the accent color
defineProps({ size: { type: Number, default: 36 } })
</script>

<template>
  <svg :width="size" :height="size" viewBox="0 0 32 32" aria-hidden="true">
    <rect width="32" height="32" rx="9" fill="rgb(var(--v-theme-primary))" />
    <g fill="none" stroke="rgb(var(--v-theme-on-primary))" stroke-width="2.4" stroke-linecap="round">
      <circle cx="16" cy="16" r="9" />
      <ellipse cx="16" cy="16" rx="3.8" ry="9" />
      <path d="M7.5 13h17M7.5 19h17" opacity="0.55" />
    </g>
  </svg>
</template>
