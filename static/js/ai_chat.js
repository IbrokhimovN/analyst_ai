class AIChatWidget {
    constructor(containerId, inputId, sendBtnId) {
        this.container = document.getElementById(containerId);
        this.input = document.getElementById(inputId);
        this.sendBtn = document.getElementById(sendBtnId);
        this.ws = null;
        this.isStreaming = false;

        this.init();
    }

    init() {
        this.sendBtn.addEventListener('click', () => {
            const text = this.input.value.trim();
            if (text) this.sendMessage(text);
        });

        this.input.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                const text = this.input.value.trim();
                if (text) this.sendMessage(text);
            }
        });

        this.connectWebSocket();
    }

    connectWebSocket() {
        try {
            const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
            this.ws = new WebSocket(`${protocol}//${location.host}/ws/ai/`);

            this.ws.onopen = () => console.log('AI WebSocket ulandi');

            this.ws.onmessage = (e) => {
                const data = JSON.parse(e.data);
                if (data.type === 'stream') {
                    this.appendStreamChunk(data.chunk);
                } else if (data.type === 'message') {
                    this.finalizeStream(data.message);
                } else if (data.type === 'typing') {
                    this.showTyping();
                } else if (data.type === 'error') {
                    this.appendMessage('ai', `⚠️ ${data.message}`);
                }
            };

            this.ws.onerror = () => {
                console.log('WebSocket xatolik, REST ga o\'tilmoqda');
                this.ws = null;
            };

            this.ws.onclose = () => {
                this.ws = null;
            };
        } catch {
            this.ws = null;
        }
    }

    async sendMessage(text) {
        if (this.isStreaming) return;

        const source = window.__crmSource || '';
        this.appendMessage('user', text);
        this.input.value = '';
        this.input.style.height = 'auto';
        this.isStreaming = true;

        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify({ message: text, source: source }));
        } else {
            this.showTyping();
            try {
                const data = await API.post('/ai/chat/', { message: text, source: source });
                this.removeTyping();
                this.appendMessage('ai', data.answer, data.message_id);
            } catch (err) {
                this.removeTyping();
                this.appendMessage('ai', `⚠️ Xatolik: ${err.message}`);
            }
            this.isStreaming = false;
        }
    }

    appendMessage(role, text, messageId) {
        const div = document.createElement('div');
        div.className = `chat-message ${role}`;

        const avatar = document.createElement('div');
        avatar.className = 'chat-avatar';
        avatar.textContent = role === 'ai' ? 'AI' : 'S';

        const bubble = document.createElement('div');
        bubble.className = 'chat-bubble';

        if (role === 'ai' && typeof marked !== 'undefined') {
            bubble.innerHTML = marked.parse(text);
        } else {
            bubble.textContent = text;
        }

        div.appendChild(avatar);
        div.appendChild(bubble);
        if (role === 'ai' && messageId) {
            bubble.appendChild(window.buildChatFeedback(messageId));
        }
        this.container.appendChild(div);
        this.scrollToBottom();
    }

    showTyping() {
        this.removeTyping();
        const div = document.createElement('div');
        div.className = 'chat-message ai';
        div.id = 'typing-indicator';

        const avatar = document.createElement('div');
        avatar.className = 'chat-avatar';
        avatar.textContent = 'AI';

        const bubble = document.createElement('div');
        bubble.className = 'chat-bubble';
        bubble.innerHTML = '<span class="typing-dots">AI o\'ylayapti<span>.</span><span>.</span><span>.</span></span>';
        bubble.style.cssText = 'color: var(--text-muted); font-style: italic;';

        div.appendChild(avatar);
        div.appendChild(bubble);
        this.container.appendChild(div);
        this.scrollToBottom();
    }

    removeTyping() {
        const el = document.getElementById('typing-indicator');
        if (el) el.remove();
    }

    appendStreamChunk(chunk) {
        let streamBubble = document.getElementById('stream-bubble');
        if (!streamBubble) {
            this.removeTyping();
            const div = document.createElement('div');
            div.className = 'chat-message ai';
            div.id = 'stream-message';

            const avatar = document.createElement('div');
            avatar.className = 'chat-avatar';
            avatar.textContent = 'AI';

            streamBubble = document.createElement('div');
            streamBubble.className = 'chat-bubble';
            streamBubble.id = 'stream-bubble';

            div.appendChild(avatar);
            div.appendChild(streamBubble);
            this.container.appendChild(div);
        }
        streamBubble.textContent += chunk;
        this.scrollToBottom();
    }

    finalizeStream(fullText) {
        const streamMsg = document.getElementById('stream-message');
        if (streamMsg) streamMsg.remove();

        this.appendMessage('ai', fullText);
        this.isStreaming = false;
    }

    scrollToBottom() {
        this.container.scrollTop = this.container.scrollHeight;
    }
}
