<template>
  <div class="chat-widget-container">
    <ChatWidget :websocketUrl="websocketUrl" :initialOpen="initialOpen" />
  </div>
</template>

<script>
import { ref, onMounted } from 'vue';
import ChatWidget from './components/ChatWidget.vue';

export default {
  name: 'App',
  components: {
    ChatWidget
  },
  setup() {
    const websocketUrl = ref('ws://localhost:8000/ws/chat/');
    const initialOpen = ref(false);

    onMounted(() => {
      document.addEventListener('chat-initialized', (event) => {
        const options = event.detail;
        if (options.websocketUrl) {
          websocketUrl.value = options.websocketUrl;
        }
        if (options.initialOpen !== undefined) {
          initialOpen.value = options.initialOpen;
        }
      });
    });

    return {
      websocketUrl,
      initialOpen
    };
  }
}
</script>