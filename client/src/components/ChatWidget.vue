// src/components/ChatWidget.vue
<template>
  <div class="chat-container">
    <div class="file-upload-area" v-if="isOpen">
      <input type="file" accept="application/pdf" @change="handleFileUpload" ref="fileInput">
      <button @click="triggerFileUpload">Upload PDF Document</button>
    </div>
    <beautiful-chat :participants="participants" :onMessageWasSent="onMessageWasSent" :messageList="messageList"
      :newMessagesCount="newMessagesCount" :isOpen="isOpen" :close="closeChat" :open="openChat" :showEmoji="true"
      :showFile="false" :acceptedFileTypes="['application/pdf']" :showTypingIndicator="showTypingIndicator"
      :colors="colors" :alwaysScrollToBottom="true" :messageStyling="true">
      <template v-slot:header>
        Agent is Connected!
      </template>
      <template v-slot:message="{ message }">
        <FileMessage v-if="message.type === 'file'" :message="message" />
      </template>
      <template v-slot:text-message-body="{ message }">
        <div class="message-content">
          <div class="message-text">{{ message.data?.text }}</div>
          <div class="message-meta" v-if="message.data?.meta">
            <small>{{ message.data.meta }}</small>
          </div>
          <!-- Add feedback buttons for bot messages only -->
          <div class="feedback-buttons" v-if="message.author === 'bot'">
            <button @click="submitFeedback(message.id, 'good')">
              👍
            </button>
            <button @click="submitFeedback(message.id, 'bad')">
              👎
            </button>
            <textarea v-model="feedbackComments[message.id]" placeholder="Optional Feedback" @click.stop></textarea>
          </div>
        </div>
      </template>
    </beautiful-chat>
  </div>
</template>

<script>
import Chat from 'vue3-beautiful-chat'
import { ref, onMounted, onUnmounted, watch, computed } from 'vue'
import WebSocketService from '../utils/websocket.js'
import FileMessage from './FileMessage.vue'

export default {
  name: 'ChatWidget',
  components: {
    'beautiful-chat': Chat.BeautifulChat,
    FileMessage
  },
  props: {
    websocketUrl: {
      type: String,
      required: true
    },
    initialOpen: {
      type: Boolean,
      default: false
    }
  },
  setup(props) {
    const isOpen = ref(props.initialOpen);
    const messageList = ref([]);
    const newMessagesCount = ref(0);
    const showTypingIndicator = ref('');
    const wsService = ref(null);
    const fileInput = ref(null);
    const sessionId = ref(null);
    const feedbackComments = ref({});

    const botAvatarUrl = 'https://static.arttacsolutions.com/img/icon_atthene_interaction.svg';

    const participants = ref([
      {
        id: 'bot',
        name: 'Chatbot',
        imageUrl: botAvatarUrl
      }
    ]);

    const colors = {
      header: {
        bg: '#4e8cff',
        text: '#ffffff'
      },
      launcher: {
        bg: '#4e8cff'
      },
      messageList: {
        bg: '#f7f9fa'
      },
      sentMessage: {
        bg: '#4e8cff',
        text: '#ffffff'
      },
      receivedMessage: {
        bg: '#f1f0f0',
        text: '#666666'
      },
      userInput: {
        bg: '#f4f7f9',
        text: '#565867'
      }
    };

    const wsUrl = computed(() => {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      return `${protocol}//${window.location.host}/ws/chat/`;
    });

    // Connect to WebSocket with error handling
    onMounted(() => {
      // Generate UUID for session if not exists
      sessionId.value = localStorage.getItem('chatSessionId') || crypto.randomUUID();
      localStorage.setItem('chatSessionId', sessionId.value);

      // Initialize WebSocket with session ID
      const wsUrlWithSession = `${props.websocketUrl}?session_id=${sessionId.value}`;
      wsService.value = new WebSocketService(wsUrlWithSession);

      wsService.value.onMessage((message) => {
        console.log('Received message:', message); // Debug log

        if (message.type === 'typing') {
          showTypingIndicator.value = message.isTyping ? 'Agent is typing...' : '';
        } else if (message.type === 'message') {
          showTypingIndicator.value = '';
          messageList.value.push({
            id: message.message_id,  // Store the message ID
            type: 'text',
            author: 'bot',
            data: {
              text: message.message,
              meta: new Date().toLocaleString()
            }
          });

          if (!isOpen.value) {
            newMessagesCount.value += 1;
          }
        } else if (message.type === 'error') {
          messageList.value.push({
            type: 'text',
            author: 'bot',
            data: {
              text: message.message,
              meta: new Date().toLocaleString()
            }
          });
        }
      });

      // Handle WebSocket connection with a mock fallback if it fails
      wsService.value.connect().catch(err => {
        console.warn('Failed to connect to WebSocket, using mock data instead:', err);

        // Add a welcome message since real WebSocket failed
        setTimeout(() => {
          messageList.value.push({
            type: 'text',
            author: 'bot',
            data: {
              text: "👋 Welcome! I'm your chatbot assistant. The WebSocket server is not available, but you can still see how the chat UI works.",
              html: "<p>👋 Welcome! I'm your chatbot assistant. The WebSocket server is not available, but you can still see how the chat UI works.</p>"
            }
          });
        }, 1000);
      });
    });

    onUnmounted(() => {
      if (wsService.value) {
        wsService.value.disconnect();
      }
    });

    watch(() => props.websocketUrl, (newUrl) => {
      if (wsService.value) {
        wsService.value.disconnect();
        wsService.value = new WebSocketService(newUrl);
        wsService.value.connect().catch(err => {
          console.warn('Failed to connect to WebSocket on URL change:', err);
        });
      }
    });

    const onMessageWasSent = async (message) => {
      if (message.type === 'text') {
        // Add message to chat immediately
        messageList.value.push({
          type: 'text',
          author: 'me',
          data: {
            text: message.data.text,
            meta: new Date().toLocaleString()
          }
        });

        // Send to WebSocket
        if (wsService.value) {
          try {
            await wsService.value.send({
              type: 'message',
              text: message.data.text
            });
          } catch (e) {
            console.error('Failed to send message:', e);
            messageList.value.push({
              type: 'text',
              author: 'bot',
              data: {
                text: 'Error: Failed to send message',
                meta: new Date().toLocaleString()
              }
            });
          }
        }
      }
    };

    const handleFileUpload = async (event) => {
      const file = event.target.files[0];
      if (!file) return;

      const formData = new FormData();
      formData.append('file', file);
      formData.append('session_id', sessionId.value); // Add session ID to form data

      try {
        const response = await fetch('http://localhost:8000/api/upload/', {
          method: 'POST',
          body: formData
        });
        const data = await response.json();

        // Show success message in chat
        messageList.value.push({
          type: 'text',
          author: 'bot',
          data: {
            text: `Document "${file.name}" uploaded successfully! You can now ask questions about it.`,
            meta: new Date().toLocaleString()
          }
        });
      } catch (error) {
        console.error('Error uploading file:', error);
      }
    };

    const triggerFileUpload = () => {
      fileInput.value.click();
    };

    // Add styles for file messages
    const messageStyles = {
      file: {
        container: {
          display: 'flex',
          alignItems: 'center',
          padding: '8px',
          backgroundColor: '#f0f0f0',
          borderRadius: '8px',
          margin: '4px 0'
        },
        icon: {
          marginRight: '8px'
        },
        text: {
          color: '#333'
        }
      }
    };

    const openChat = () => {
      isOpen.value = true;
      newMessagesCount.value = 0;
    };

    const closeChat = () => {
      isOpen.value = false;
    };

    const submitFeedback = async (messageId, rating) => {
      try {
        const response = await fetch('http://localhost:8000/api/feedback/', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            message_id: messageId,
            rating,
            comments: feedbackComments.value[messageId] || ''
          })
        });

        if (response.ok) {
          delete feedbackComments.value[messageId];
        }
      } catch (error) {
        console.error('Feedback submission failed:', error);
      }
    };

    return {
      isOpen,
      messageList,
      newMessagesCount,
      showTypingIndicator,
      participants,
      colors,
      onMessageWasSent,
      openChat,
      closeChat,
      messageStyles,
      fileInput,
      triggerFileUpload,
      handleFileUpload,
      feedbackComments,
      submitFeedback,
    };
  }
}
</script>

<style scoped>
.chat-container {
  width: 100%;
  height: 100%;
}

.file-message {
  display: flex;
  align-items: center;
  background-color: #f0f0f0;
  padding: 8px;
  border-radius: 8px;
  margin: 4px 0;
}

.file-message i {
  margin-right: 8px;
}

.file-message a {
  color: #4e8cff;
  text-decoration: none;
}

.file-message a:hover {
  text-decoration: underline;
}

.message-content {
  display: flex;
  flex-direction: column;
}

.message-meta {
  font-size: 0.8em;
  color: #666;
  margin-top: 2px;
}

.file-upload-area {
  padding: 10px;
  text-align: center;
  border-bottom: 1px solid #eee;
}

.file-upload-area input[type="file"] {
  display: none;
}

.file-upload-area button {
  padding: 8px 16px;
  background: #4e8cff;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.feedback-buttons {
  display: flex;
  gap: 8px;
  margin-top: 8px;
  align-items: center;
  flex-wrap: wrap;
}

.feedback-buttons button {
  padding: 4px 8px;
  border: 1px solid #ddd;
  border-radius: 4px;
  background: white;
  cursor: pointer;
  transition: background-color 0.2s;
}

.feedback-buttons button:hover {
  background-color: #f0f0f0;
}

.feedback-buttons textarea {
  width: 100%;
  margin-top: 4px;
  padding: 4px;
  border: 1px solid #ddd;
  border-radius: 4px;
  resize: vertical;
  min-height: 30px;
}
</style>