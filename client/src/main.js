// src/main.js
import { createApp } from 'vue';
import App from './App.vue';
import { createVuetify } from 'vuetify';
import Chat from 'vue3-beautiful-chat';
import 'vuetify/styles';
import './assets/styles.css';

// Import vue3-beautiful-chat styles
import 'vue3-beautiful-chat/dist/vue3-beautiful-chat.css';

const vuetify = createVuetify();

// Create and mount the app
const app = createApp(App);
app.use(vuetify);
app.use(Chat); // Register the Chat plugin
app.mount('#chat-widget');

// Expose the app instance to window for external control
window.ChatWidget = {
    initialize(options = {}) {
        app.config.globalProperties.$chatOptions = options;
        const event = new CustomEvent('chat-initialized', { detail: options });
        document.dispatchEvent(event);
    }
};