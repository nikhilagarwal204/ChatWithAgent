export default class WebSocketService {
    constructor(url) {
        // Get session ID from localStorage or generate new one
        this.sessionId = localStorage.getItem('chatSessionId') || this.generateSessionId();
        this.url = `${url}?session_id=${this.sessionId}`;
        this.socket = null;
        this.messageHandlers = [];
        this.connect();
    }

    generateSessionId() {
        const sessionId = crypto.randomUUID();
        localStorage.setItem('chatSessionId', sessionId);
        return sessionId;
    }

    connect() {
        return new Promise((resolve, reject) => {
            this.socket = new WebSocket(this.url);

            this.socket.onopen = () => {
                console.log("WebSocket connection established");
                resolve();
            };

            this.socket.onerror = (error) => {
                console.error("WebSocket error:", error);
                reject(error);
            };

            this.socket.onclose = () => {
                console.log("WebSocket connection closed");
                // Try to reconnect after 3 seconds
                setTimeout(() => this.connect(), 3000);
            };

            this.socket.onmessage = (event) => {
                const message = JSON.parse(event.data);
                this.messageHandlers.forEach(handler => handler(message));
            };
        });
    }

    disconnect() {
        if (this.socket) {
            this.socket.close();
        }
    }

    async send(message) {
        if (this.socket && this.socket.readyState === WebSocket.OPEN) {
            this.socket.send(JSON.stringify(message));
        } else {
            throw new Error("WebSocket is not connected");
        }
    }

    onMessage(handler) {
        this.messageHandlers.push(handler);
    }

    removeMessageHandler(handler) {
        const index = this.messageHandlers.indexOf(handler);
        if (index !== -1) {
            this.messageHandlers.splice(index, 1);
        }
    }
}