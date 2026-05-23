/**
 * AI Chat Widget — Shadow DOM ichidagi suzuvchi yordamchi.
 *
 * Bosh sahifaga `<div id="ai-chat-widget"></div>` qo'yiladi va shu skript
 * uning ichida ShadowRoot yaratib, barcha style/markup'ni izolyatsiya
 * qiladi. Backend: POST /api/v1/ai/chat/ (rag_mod.answer_question).
 */
(function () {
    'use strict';

    var HOST_ID = 'ai-chat-widget';
    var ENDPOINT = '/api/v1/ai/chat/';
    var STORAGE_KEY = 'ai_chat_widget_history_v1';

    function csrfToken() {
        var meta = document.querySelector('meta[name="csrf-token"]');
        if (meta && meta.content) { return meta.content; }
        var m = document.cookie.match(/csrftoken=([^;]+)/);
        return m ? m[1] : '';
    }

    function wrapTables(html) {
        // Markdown jadvallarini scroll qilish uchun div bilan o'rab beradi —
        // shunda bubble'ning o'zi gorizontal scroll qilmaydi, faqat jadval.
        return (html || '').replace(/<table([\s\S]*?)<\/table>/gi,
            '<div class="table-wrap"><table$1</table></div>');
    }

    function renderMarkdown(text) {
        if (window.marked && typeof window.marked.parse === 'function') {
            try { return wrapTables(window.marked.parse(text || '')); }
            catch (e) { /* ignore */ }
        }
        var div = document.createElement('div');
        div.textContent = text || '';
        return div.innerHTML.replace(/\n/g, '<br>');
    }

    function loadHistory() {
        try {
            var raw = sessionStorage.getItem(STORAGE_KEY);
            return raw ? JSON.parse(raw) : [];
        } catch (e) { return []; }
    }

    function saveHistory(messages) {
        try { sessionStorage.setItem(STORAGE_KEY, JSON.stringify(messages.slice(-50))); }
        catch (e) { /* quota — ignore */ }
    }

    var STYLES = [
        ':host { all: initial; }',
        '*, *::before, *::after { box-sizing: border-box; font-family: "Inter", system-ui, -apple-system, "Segoe UI", sans-serif; }',
        '.fab { position: fixed; right: 24px; bottom: 24px; width: 60px; height: 60px; border-radius: 50%; ',
        '  border: none; cursor: pointer; background: linear-gradient(135deg, #6366F1 0%, #8B5CF6 100%); ',
        '  color: #fff; box-shadow: 0 8px 24px rgba(99,102,241,.45); display: flex; align-items: center; ',
        '  justify-content: center; transition: transform .15s ease, box-shadow .15s ease; z-index: 9999; }',
        '.fab:hover { transform: translateY(-2px) scale(1.05); box-shadow: 0 12px 28px rgba(99,102,241,.55); }',
        '.fab svg { width: 28px; height: 28px; }',
        '.fab-badge { position: absolute; top: -2px; right: -2px; min-width: 18px; height: 18px; ',
        '  border-radius: 9px; background: #EF4444; color: #fff; font-size: 11px; font-weight: 700; ',
        '  display: flex; align-items: center; justify-content: center; padding: 0 5px; }',
        '.panel { position: fixed; right: 24px; bottom: 96px; width: 400px; height: 600px; max-height: 80vh; ',
        '  max-width: calc(100vw - 32px); background: #0F172A; color: #E2E8F0; border-radius: 18px; ',
        '  box-shadow: 0 24px 60px rgba(0,0,0,.45); display: flex; flex-direction: column; overflow: hidden; ',
        '  border: 1px solid rgba(99,102,241,.25); z-index: 9999; opacity: 0; transform: translateY(20px) scale(.96); ',
        '  pointer-events: none; transition: opacity .18s ease, transform .18s ease; }',
        '.panel.open { opacity: 1; transform: translateY(0) scale(1); pointer-events: auto; }',
        '.head { padding: 14px 16px; background: linear-gradient(135deg, #6366F1 0%, #8B5CF6 100%); ',
        '  color: #fff; display: flex; align-items: center; gap: 10px; }',
        '.head-avatar { width: 36px; height: 36px; border-radius: 50%; background: rgba(255,255,255,.18); ',
        '  display: flex; align-items: center; justify-content: center; font-size: 18px; }',
        '.head-meta { flex: 1; min-width: 0; }',
        '.head-title { font-size: 14px; font-weight: 700; margin: 0; }',
        '.head-sub { font-size: 12px; opacity: .8; margin: 2px 0 0; }',
        '.head-btn { background: rgba(255,255,255,.15); border: none; color: #fff; width: 30px; height: 30px; ',
        '  border-radius: 8px; cursor: pointer; display: flex; align-items: center; justify-content: center; ',
        '  transition: background .15s ease; }',
        '.head-btn:hover { background: rgba(255,255,255,.28); }',
        '.head-btn svg { width: 16px; height: 16px; }',
        '.body { flex: 1; overflow-y: auto; overflow-x: hidden; padding: 16px; display: flex; ',
        '  flex-direction: column; gap: 12px; background: #0F172A; scroll-behavior: smooth; min-width: 0; }',
        '.body::-webkit-scrollbar { width: 6px; }',
        '.body::-webkit-scrollbar-thumb { background: rgba(255,255,255,.15); border-radius: 3px; }',
        '.msg { display: flex; gap: 8px; max-width: 92%; min-width: 0; }',
        '.msg.user { align-self: flex-end; flex-direction: row-reverse; }',
        '.msg-avatar { width: 28px; height: 28px; border-radius: 50%; flex-shrink: 0; display: flex; ',
        '  align-items: center; justify-content: center; font-size: 12px; font-weight: 700; }',
        '.msg.ai .msg-avatar { background: linear-gradient(135deg, #6366F1, #8B5CF6); color: #fff; }',
        '.msg.user .msg-avatar { background: #334155; color: #E2E8F0; }',
        '.bubble { padding: 10px 14px; border-radius: 14px; font-size: 13.5px; line-height: 1.55; ',
        '  min-width: 0; max-width: 100%; overflow-wrap: anywhere; word-break: break-word; ',
        '  white-space: normal; }',
        '.msg.ai .bubble { background: #1E293B; color: #E2E8F0; border-bottom-left-radius: 4px; }',
        '.msg.user .bubble { background: linear-gradient(135deg, #6366F1, #8B5CF6); color: #fff; border-bottom-right-radius: 4px; }',
        '.bubble p { margin: 0 0 8px; }',
        '.bubble p:last-child { margin-bottom: 0; }',
        '.bubble ul, .bubble ol { margin: 4px 0 8px; padding-left: 20px; }',
        '.bubble li { margin: 2px 0; }',
        '.bubble code { background: rgba(255,255,255,.1); padding: 1px 5px; border-radius: 4px; font-size: 12px; ',
        '  font-family: "JetBrains Mono", "Courier New", monospace; white-space: pre-wrap; ',
        '  overflow-wrap: anywhere; word-break: break-word; }',
        '.bubble pre { background: rgba(0,0,0,.35); padding: 10px; border-radius: 8px; ',
        '  font-size: 12px; margin: 6px 0; white-space: pre-wrap; overflow-wrap: anywhere; ',
        '  word-break: break-word; max-width: 100%; }',
        '.bubble pre code { background: transparent; padding: 0; white-space: pre-wrap; ',
        '  overflow-wrap: anywhere; word-break: break-word; }',
        '.bubble strong { color: #C7D2FE; }',
        '.bubble a { color: #A5B4FC; overflow-wrap: anywhere; word-break: break-word; }',
        '.bubble img { max-width: 100%; height: auto; border-radius: 6px; }',
        '.bubble .table-wrap { max-width: 100%; overflow-x: auto; margin: 6px 0; }',
        '.bubble table { border-collapse: collapse; font-size: 12px; margin: 0; }',
        '.bubble th, .bubble td { border: 1px solid rgba(255,255,255,.15); padding: 4px 8px; text-align: left; ',
        '  white-space: normal; word-break: break-word; }',
        '.sources { margin-top: 8px; padding-top: 8px; border-top: 1px solid rgba(255,255,255,.1); ',
        '  font-size: 11px; opacity: .7; }',
        '.typing { display: inline-flex; gap: 4px; align-items: center; }',
        '.typing span { width: 6px; height: 6px; background: currentColor; border-radius: 50%; ',
        '  opacity: .4; animation: blink 1.2s infinite; }',
        '.typing span:nth-child(2) { animation-delay: .2s; }',
        '.typing span:nth-child(3) { animation-delay: .4s; }',
        '@keyframes blink { 0%, 60%, 100% { opacity: .3; } 30% { opacity: 1; } }',
        '.welcome { text-align: center; padding: 12px 8px; }',
        '.welcome-title { font-size: 15px; font-weight: 700; margin: 0 0 6px; color: #C7D2FE; }',
        '.welcome-sub { font-size: 12.5px; opacity: .7; margin: 0 0 14px; line-height: 1.5; }',
        '.suggestions { display: flex; flex-direction: column; gap: 6px; }',
        '.sug-btn { background: #1E293B; border: 1px solid rgba(99,102,241,.3); color: #E2E8F0; ',
        '  padding: 9px 12px; border-radius: 10px; cursor: pointer; font-size: 12.5px; text-align: left; ',
        '  transition: background .15s ease, border-color .15s ease; font-family: inherit; }',
        '.sug-btn:hover { background: #273549; border-color: rgba(99,102,241,.6); }',
        '.foot { padding: 12px; background: #0B1220; border-top: 1px solid rgba(255,255,255,.08); }',
        '.input-wrap { display: flex; gap: 8px; align-items: flex-end; background: #1E293B; ',
        '  border-radius: 12px; padding: 8px; border: 1px solid transparent; transition: border-color .15s ease; }',
        '.input-wrap:focus-within { border-color: rgba(99,102,241,.5); }',
        '.input { flex: 1; background: transparent; border: none; outline: none; color: #E2E8F0; ',
        '  font-size: 13.5px; resize: none; max-height: 120px; min-height: 22px; padding: 4px 6px; ',
        '  font-family: inherit; line-height: 1.4; }',
        '.input::placeholder { color: rgba(226,232,240,.4); }',
        '.send { background: linear-gradient(135deg, #6366F1, #8B5CF6); border: none; color: #fff; ',
        '  width: 36px; height: 36px; border-radius: 10px; cursor: pointer; display: flex; ',
        '  align-items: center; justify-content: center; flex-shrink: 0; transition: opacity .15s ease; }',
        '.send:disabled { opacity: .4; cursor: not-allowed; }',
        '.send svg { width: 16px; height: 16px; }',
        '.hint { font-size: 10.5px; opacity: .5; margin-top: 6px; text-align: center; }',
        '@media (max-width: 480px) {',
        '  .panel { right: 12px; left: 12px; bottom: 84px; width: auto; height: calc(100vh - 100px); }',
        '  .fab { right: 16px; bottom: 16px; width: 54px; height: 54px; }',
        '}',
    ].join('\n');

    var SUGGESTIONS = [
        'Bugungi sotuv natijalari qanday?',
        'Eng yaxshi menejer kim?',
        'Asosiy yutqazish sabablari nima?',
        'Konversiya foizini ko\'rsat',
    ];

    function buildWidget(host) {
        var root = host.attachShadow({ mode: 'open' });

        var style = document.createElement('style');
        style.textContent = STYLES;
        root.appendChild(style);

        // FAB
        var fab = document.createElement('button');
        fab.className = 'fab';
        fab.type = 'button';
        fab.setAttribute('aria-label', 'AI yordamchi');
        fab.title = 'AI yordamchi';
        fab.innerHTML =
            '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" ' +
            '     stroke-linecap="round" stroke-linejoin="round">' +
            '  <path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"/>' +
            '  <circle cx="9" cy="11" r="1" fill="currentColor"/>' +
            '  <circle cx="12" cy="11" r="1" fill="currentColor"/>' +
            '  <circle cx="15" cy="11" r="1" fill="currentColor"/>' +
            '</svg>';
        root.appendChild(fab);

        // Panel
        var panel = document.createElement('div');
        panel.className = 'panel';
        panel.innerHTML =
            '<div class="head">' +
            '  <div class="head-avatar">🤖</div>' +
            '  <div class="head-meta">' +
            '    <p class="head-title">AI Yordamchi</p>' +
            '    <p class="head-sub">Tizim haqida har qanday savol bering</p>' +
            '  </div>' +
            '  <button class="head-btn" data-action="clear" title="Suhbatni tozalash">' +
            '    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"' +
            '         stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"/>' +
            '      <path d="M19 6l-2 14a2 2 0 0 1-2 2H9a2 2 0 0 1-2-2L5 6"/></svg>' +
            '  </button>' +
            '  <button class="head-btn" data-action="close" title="Yopish">' +
            '    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"' +
            '         stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"/>' +
            '      <line x1="6" y1="6" x2="18" y2="18"/></svg>' +
            '  </button>' +
            '</div>' +
            '<div class="body" data-role="body"></div>' +
            '<div class="foot">' +
            '  <div class="input-wrap">' +
            '    <textarea class="input" data-role="input" placeholder="Savol yozing..." rows="1"></textarea>' +
            '    <button class="send" data-role="send" title="Yuborish">' +
            '      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"' +
            '           stroke-linecap="round" stroke-linejoin="round">' +
            '        <line x1="22" y1="2" x2="11" y2="13"/>' +
            '        <polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>' +
            '    </button>' +
            '  </div>' +
            '  <div class="hint">Enter — yuborish · Shift+Enter — yangi qator</div>' +
            '</div>';
        root.appendChild(panel);

        var body = panel.querySelector('[data-role="body"]');
        var input = panel.querySelector('[data-role="input"]');
        var send = panel.querySelector('[data-role="send"]');
        var btnClose = panel.querySelector('[data-action="close"]');
        var btnClear = panel.querySelector('[data-action="clear"]');

        var state = { busy: false, history: loadHistory() };

        function open() {
            panel.classList.add('open');
            setTimeout(function () { input.focus(); }, 150);
        }
        function close() { panel.classList.remove('open'); }
        function toggle() {
            if (panel.classList.contains('open')) { close(); } else { open(); }
        }

        function scrollDown() {
            requestAnimationFrame(function () { body.scrollTop = body.scrollHeight; });
        }

        function appendMessage(role, content, opts) {
            opts = opts || {};
            var wrap = document.createElement('div');
            wrap.className = 'msg ' + (role === 'user' ? 'user' : 'ai');

            var avatar = document.createElement('div');
            avatar.className = 'msg-avatar';
            avatar.textContent = role === 'user' ? 'Siz' : 'AI';
            wrap.appendChild(avatar);

            var bubble = document.createElement('div');
            bubble.className = 'bubble';
            if (opts.raw) {
                bubble.innerHTML = content;
            } else if (role === 'ai') {
                bubble.innerHTML = renderMarkdown(content);
            } else {
                bubble.textContent = content;
            }
            wrap.appendChild(bubble);

            body.appendChild(wrap);
            scrollDown();
            return bubble;
        }

        function renderWelcome() {
            body.innerHTML = '';
            var welcome = document.createElement('div');
            welcome.className = 'welcome';
            welcome.innerHTML =
                '<p class="welcome-title">Salom! 👋</p>' +
                '<p class="welcome-sub">Men ushbu tizim bo\'yicha AI yordamchiman.<br>' +
                'Sotuv, menejerlar, konversiyalar yoki istalgan savol bering.</p>';

            var sug = document.createElement('div');
            sug.className = 'suggestions';
            SUGGESTIONS.forEach(function (q) {
                var b = document.createElement('button');
                b.type = 'button';
                b.className = 'sug-btn';
                b.textContent = q;
                b.addEventListener('click', function () { sendQuery(q); });
                sug.appendChild(b);
            });
            welcome.appendChild(sug);
            body.appendChild(welcome);
        }

        function rehydrate() {
            if (!state.history.length) { renderWelcome(); return; }
            body.innerHTML = '';
            state.history.forEach(function (m) { appendMessage(m.role, m.content); });
        }

        function pushHistory(role, content) {
            state.history.push({ role: role, content: content });
            saveHistory(state.history);
        }

        function sendQuery(text) {
            text = (text || '').trim();
            if (!text || state.busy) { return; }
            state.busy = true;
            send.disabled = true;

            // Remove welcome if shown
            var welcome = body.querySelector('.welcome');
            if (welcome) { welcome.remove(); }

            appendMessage('user', text);
            pushHistory('user', text);
            input.value = '';
            input.style.height = 'auto';

            var thinking = appendMessage('ai',
                '<span class="typing"><span></span><span></span><span></span></span>',
                { raw: true });

            fetch(ENDPOINT, {
                method: 'POST',
                credentials: 'same-origin',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken(),
                },
                body: JSON.stringify({
                    message: text,
                    manager_id: 0,
                    source: window.__crmSource || '',
                }),
            })
                .then(function (r) {
                    return r.json().then(function (j) { return { ok: r.ok, data: j }; });
                })
                .then(function (res) {
                    if (!res.ok) { throw new Error((res.data && res.data.error) || 'Xatolik'); }
                    var html = renderMarkdown(res.data.answer || '');
                    if (res.data.sources && res.data.sources.length) {
                        html += '<div class="sources">📎 Manba: ' +
                                res.data.sources.map(function (s) {
                                    var d = document.createElement('span');
                                    d.textContent = s;
                                    return d.innerHTML;
                                }).join(', ') + '</div>';
                    }
                    thinking.innerHTML = html;
                    pushHistory('ai', res.data.answer || '');
                })
                .catch(function (e) {
                    thinking.innerHTML = '❌ Xatolik: ' +
                        (function () { var d = document.createElement('span'); d.textContent = e.message; return d.innerHTML; })();
                })
                .finally(function () {
                    state.busy = false;
                    send.disabled = false;
                    scrollDown();
                });
        }

        function clearChat() {
            state.history = [];
            saveHistory(state.history);
            renderWelcome();
        }

        // Auto-resize textarea
        function autosize() {
            input.style.height = 'auto';
            input.style.height = Math.min(input.scrollHeight, 120) + 'px';
        }

        // Events
        fab.addEventListener('click', toggle);
        btnClose.addEventListener('click', close);
        btnClear.addEventListener('click', clearChat);
        send.addEventListener('click', function () { sendQuery(input.value); });
        input.addEventListener('input', autosize);
        input.addEventListener('keydown', function (e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendQuery(input.value);
            }
        });

        // Close on Escape when panel focused
        root.addEventListener('keydown', function (e) {
            if (e.key === 'Escape' && panel.classList.contains('open')) { close(); }
        });

        // Initial render
        rehydrate();
    }

    function init() {
        var host = document.getElementById(HOST_ID);
        if (!host) {
            host = document.createElement('div');
            host.id = HOST_ID;
            document.body.appendChild(host);
        }
        if (host.shadowRoot) { return; }
        buildWidget(host);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
