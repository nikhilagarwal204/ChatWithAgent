export default class WebSocketService {
    constructor(url) {
        this.url = url;
        this.socket = null;
        this.messageHandlers = [];
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
            if (message.file) {
                // Handle file upload
                const reader = new FileReader();
                reader.onload = () => {
                    const base64File = reader.result.split(',')[1];
                    const fileMessage = {
                        type: 'file',
                        fileName: message.file.name,
                        fileType: message.file.type,
                        fileData: base64File
                    };
                    this.socket.send(JSON.stringify(fileMessage));
                };
                reader.readAsDataURL(message.file);
            } else {
                this.socket.send(JSON.stringify(message));
            }
        } else {
            console.error("WebSocket is not connected");
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