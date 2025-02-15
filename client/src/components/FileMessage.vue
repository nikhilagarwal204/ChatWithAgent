<template>
  <div class="file-message">
    <div class="file-info">
      <i class="file-icon">📎</i>
      <span class="file-name">{{ message.data.file.name }}</span>
    </div>
    <a :href="message.data.file.url" target="_blank" class="file-download">
      Download
    </a>
  </div>
</template>

<script>
export default {
  name: 'FileMessage',
  props: {
    message: {
      type: Object,
      required: true
    }
  }
}
</script>

<style scoped>
.file-message {
  padding: 10px;
  border: 1px solid #e0e0e0;
  border-radius: 4px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.file-info {
  display: flex;
  align-items: center;
  gap: 8px;
}

.file-download {
  color: #007bff;
  text-decoration: none;
}

.file-download:hover {
  text-decoration: underline;
}
</style>
