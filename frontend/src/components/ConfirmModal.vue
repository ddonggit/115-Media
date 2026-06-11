<template>
  <div class="modal-overlay" :class="{ active: show }">
    <div class="modal" style="max-width:400px;text-align:center">
      <h2 style="justify-content:center">{{ message }}</h2>
      <div class="modal-actions" style="justify-content:center">
        <button class="btn-outline" @click="$emit('cancel')">取消</button>
        <button class="btn-glass" style="color:var(--red)" @click="$emit('confirm')">确认</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{ show: boolean; message: string }>()
defineEmits<{ confirm: []; cancel: [] }>()
</script>
