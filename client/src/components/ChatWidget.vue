// src/components/ChatWidget.vue
<template>
  <div class="chat-container">
    <beautiful-chat :participants="participants" :titleImageUrl="titleImageUrl" :onMessageWasSent="onMessageWasSent"
      :messageList="messageList" :newMessagesCount="newMessagesCount" :isOpen="isOpen" :close="closeChat"
      :open="openChat" :showEmoji="true" :showFile="true" :acceptedFileTypes="['application/pdf']"
      :showTypingIndicator="showTypingIndicator" :colors="colors" :alwaysScrollToBottom="true" :messageStyling="true">
      <template v-slot:header>
        <div class="sc-header--title">
          <span class="sc-header--title-name">Chatbot Assistant</span>
        </div>
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
        </div>
      </template>
    </beautiful-chat>
  </div>
</template>

<script>
import Chat from 'vue3-beautiful-chat'
import { ref, onMounted, onUnmounted, watch, computed } from 'vue'
import { marked } from 'marked'
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
    const showTypingIndicator = ref(false);
    const wsService = ref(null);

    const botAvatarUrl = 'https://static.arttacsolutions.com/img/icon_atthene_interaction.svg';

    const participants = ref([
      {
        id: 'bot',
        name: 'Chatbot',
        imageUrl: botAvatarUrl
      }
    ]);

    const titleImageUrl = computed(() => botAvatarUrl);

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

    // Connect to WebSocket with error handling
    onMounted(() => {
      wsService.value = new WebSocketService(props.websocketUrl);

      wsService.value.onMessage((message) => {
        if (message.type === 'typing') {
          showTypingIndicator.value = message.isTyping;
        } else if (message.type === 'message') {
          // Convert markdown to HTML
          const html = marked(message.message);

          messageList.value.push({
            type: 'text',
            author: 'bot',
            data: {
              text: message.message,
              meta: new Date().toLocaleString(),
              html: html
            }
          });

          if (!isOpen.value) {
            newMessagesCount.value += 1;
          }
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
      if (message.type === 'file') {
        handleFileUpload(message.data.file);
        return;
      } else {
        // Handle text message (existing code)
        messageList.value.push({
          type: 'text',
          author: 'me',
          data: { text: message.data.text, meta: new Date().toLocaleString() }
        });

        if (wsService.value) {
          try {
            wsService.value.send({
              type: 'message',
              text: message.data.text
            });
          } catch (e) {
            console.warn('Failed to send message:', e);
          }
        }
      }
    };

    const handleFileUpload = (file) => {
      // Create message object with required meta field
      const message = {
        author: 'me',
        type: 'file',
        id: Date.now().toString(),
        isEdited: false,
        data: {
          file: {
            name: file.name,
            url: URL.createObjectURL(file),
          }
        }
      }
      messageList.value.push(message)

      // Send file to server via WebSocket
      if (wsService.value) {
        // Create FormData to send file
        const formData = new FormData();
        formData.append('file', file);

        // Make API call to upload file
        fetch('http://localhost:8000/api/upload/', {
          method: 'POST',
          body: formData
        })
          .then(response => response.json())
          .then(data => {
            // Send message to inform about successful upload
            wsService.value.send({
              type: 'file',
              fileName: file.name,
              documentId: data.document_id,
              sessionId: data.session_id
            });
          })
          .catch(error => {
            console.error('Error uploading file:', error);
            messageList.value.push({
              type: 'text',
              author: 'bot',
              data: {
                text: 'Error uploading file. Please try again.',
                meta: new Date().toLocaleString()
              }
            });
          });
      }
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

    return {
      isOpen,
      messageList,
      newMessagesCount,
      showTypingIndicator,
      participants,
      titleImageUrl,
      colors,
      onMessageWasSent,
      openChat,
      closeChat,
      messageStyles
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
</style>