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
        return (html || '').replace(/<table([\s\S]*?)<\/table>/gi,
            '<div class="table-wrap"><table$1</table></div>');
    }

    function renderMarkdown(text) {
        if (window.marked && typeof window.marked.parse === 'function') {
            try { return wrapTables(window.marked.parse(text || '')); }
            catch (e) {  }
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
        catch (e) {  }
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
        '.chart-box { margin: 10px 0 4px; padding: 10px; background: rgba(15,23,41,.6); ',
        '  border: 1px solid rgba(99,102,241,.25); border-radius: 10px; }',
        '.chart-title { font-size: 12px; font-weight: 700; color: #C7D2FE; margin: 0 0 6px; }',
        '.chart-canvas-wrap { position: relative; width: 100%; height: 240px; }',
        '.cmd-pill { display: inline-flex; gap: 6px; align-items: center; margin: 6px 0 0; ',
        '  padding: 5px 10px; border-radius: 999px; background: rgba(34,197,94,.15); ',
        '  border: 1px solid rgba(34,197,94,.35); color: #86efac; font-size: 11.5px; }',
        '.cmd-pill.err { background: rgba(239,68,68,.15); border-color: rgba(239,68,68,.35); color: #fca5a5; }',
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
        '.mic { background: #334155; border: none; color: #E2E8F0; ',
        '  width: 36px; height: 36px; border-radius: 10px; cursor: pointer; display: flex; ',
        '  align-items: center; justify-content: center; flex-shrink: 0; transition: background .15s ease; }',
        '.mic:hover { background: #475569; }',
        '.mic.recording { background: linear-gradient(135deg, #EF4444, #DC2626); color: #fff; ',
        '  animation: micPulse 1.2s infinite; }',
        '@keyframes micPulse { 0%, 100% { box-shadow: 0 0 0 0 rgba(239,68,68,.6); } ',
        '  50% { box-shadow: 0 0 0 8px rgba(239,68,68,0); } }',
        '.mic svg { width: 18px; height: 18px; }',
        '.rec-bar { display: none; align-items: center; gap: 8px; padding: 8px; ',
        '  background: rgba(239,68,68,.12); border: 1px solid rgba(239,68,68,.35); ',
        '  border-radius: 12px; color: #fecaca; font-size: 13px; max-width: 100%; ',
        '  overflow: hidden; box-sizing: border-box; }',
        '.rec-bar.on { display: flex; }',
        '.rec-bar.on + .input-wrap { display: none; }',
        '.rec-dot { width: 10px; height: 10px; background: #EF4444; border-radius: 50%; ',
        '  animation: recBlink .9s infinite; flex-shrink: 0; }',
        '@keyframes recBlink { 0%, 100% { opacity: 1; } 50% { opacity: .25; } }',
        '.rec-time { font-variant-numeric: tabular-nums; font-weight: 600; min-width: 38px; ',
        '  flex-shrink: 0; font-size: 12px; }',
        '.rec-text { flex: 1 1 0; min-width: 0; font-size: 11.5px; opacity: .85; ',
        '  max-height: 36px; overflow-y: auto; line-height: 1.35; word-break: break-word; ',
        '  overflow-wrap: anywhere; white-space: normal; }',
        '.rec-text::-webkit-scrollbar { width: 4px; } ',
        '.rec-text::-webkit-scrollbar-thumb { background: rgba(255,255,255,.2); border-radius: 2px; }',
        '.rec-btn { background: transparent; border: none; cursor: pointer; width: 32px; height: 32px; ',
        '  border-radius: 8px; display: flex; align-items: center; justify-content: center; ',
        '  transition: background .12s ease; flex-shrink: 0; }',
        '.rec-btn svg { width: 18px; height: 18px; }',
        '.rec-cancel { color: #fca5a5; } .rec-cancel:hover { background: rgba(239,68,68,.18); }',
        '.rec-send { background: linear-gradient(135deg, #22C55E, #16A34A); color: #fff; }',
        '.rec-send:hover { filter: brightness(1.08); }',
        '.voice-bubble { display: flex; align-items: center; gap: 10px; padding: 4px 0; min-width: 180px; }',
        '.voice-play { width: 32px; height: 32px; border-radius: 50%; border: none; cursor: pointer; ',
        '  background: rgba(255,255,255,.22); color: #fff; display: flex; align-items: center; ',
        '  justify-content: center; flex-shrink: 0; transition: background .12s ease; }',
        '.voice-play:hover { background: rgba(255,255,255,.32); }',
        '.voice-play svg { width: 14px; height: 14px; }',
        '.voice-wave { display: flex; align-items: center; gap: 2px; flex: 1; height: 22px; min-width: 80px; }',
        '.voice-wave span { display: block; width: 2px; background: rgba(255,255,255,.55); border-radius: 1px; }',
        '.voice-wave span.on { background: #fff; }',
        '.voice-time { font-size: 11.5px; opacity: .85; font-variant-numeric: tabular-nums; flex-shrink: 0; }',
        '.voice-tx { font-size: 11.5px; opacity: .85; margin-top: 4px; line-height: 1.4; font-style: italic; }',
        '.ai-voice-bubble { margin-bottom: 8px; padding-bottom: 8px; border-bottom: 1px solid rgba(255,255,255,.12); }',
        '.msg.ai .bubble .ai-voice-bubble .voice-play { background: rgba(99,102,241,.25); color: #c7d2fe; }',
        '.msg.ai .bubble .ai-voice-bubble .voice-play:hover { background: rgba(99,102,241,.4); }',
        '.msg.ai .bubble .ai-voice-bubble .voice-wave span { background: rgba(199,210,254,.4); }',
        '.msg.ai .bubble .ai-voice-bubble .voice-wave span.on { background: #c7d2fe; }',
        '.hint { font-size: 10.5px; opacity: .5; margin-top: 6px; text-align: center; }',
        '@media (max-width: 480px) {',
        '  .panel { right: 12px; left: 12px; bottom: 84px; width: auto; height: calc(100vh - 100px); }',
        '  .fab { right: 16px; bottom: 16px; width: 54px; height: 54px; }',
        '}',
    ].join('\n');

    var SUGGESTIONS = [
        'Bugungi sotuv natijalari qanday?',
        'Eng yaxshi menejer kim?',
        'Menejerlarni pie chart bilan ko\'rsat',
        'Loss kartasini yashir',
    ];

    function appendChart(targetEl, spec) {
        var box = document.createElement('div');
        box.className = 'chart-box';

        var title = document.createElement('div');
        title.className = 'chart-title';
        title.textContent = '📊 ' + (spec.title || spec.card_label || 'Grafik') +
            '  ·  ' + (spec.viewType || 'bar');
        box.appendChild(title);
        targetEl.appendChild(box);

        if (window.AIChartRender && typeof window.AIChartRender.renderInto === 'function') {
            window.AIChartRender.renderInto(box, spec);
        } else {
            var err = document.createElement('div');
            err.style.cssText = 'color:#fca5a5;font-size:12px;';
            err.textContent = 'AIChartRender modul yuklanmagan (chart_render.js).';
            box.appendChild(err);
        }
    }

    function esc(s) {
        var d = document.createElement('div');
        d.textContent = (s == null ? '' : String(s));
        return d.innerHTML;
    }
    function fmtNum(n) {
        n = Number(n) || 0;
        return n.toLocaleString('ru-RU');
    }

    function appendCommandPill(targetEl, cmd, ok) {
        var p = document.createElement('div');
        p.className = 'cmd-pill' + (ok ? '' : ' err');
        var icon = ok ? '✅' : '⚠️';
        var labels = {
            show_card: 'kartasi ko\'rsatildi',
            hide_card: 'kartasi yashirildi',
            set_card_view: 'kartasi o\'zgartirildi',
            refresh_dashboard: 'dashboard yangilandi',
            open_ai_panel: 'AI panel ochildi',
            add_custom_card: 'yangi karta qo\'shildi',
            remove_custom_card: 'karta o\'chirildi',
            remove_all_custom: 'maxsus kartalar tozalandi',
            show_all_cards: 'barcha kartalar qaytarildi',
            hide_all_cards: 'barcha kartalar yashirildi',
            add_all_default_charts: 'default chartlar qo\'shildi',
            set_period: 'vaqt filtri o\'zgartirildi',
            set_source: 'CRM manbai o\'zgartirildi',
        };
        var what = labels[cmd.action] || cmd.action;
        var extra = '';
        if (cmd.action === 'set_period' && cmd.period) { extra = ' (' + cmd.period + ')'; }
        if (cmd.action === 'set_source') { extra = ' (' + (cmd.source || 'all') + ')'; }
        p.textContent = icon + ' ' + (cmd.card ? cmd.card + ' — ' : '') + what + extra;
        targetEl.appendChild(p);
    }

    function dispatchCommand(cmd) {
        try {
            var evt = new CustomEvent('dashboard:command', {
                detail: cmd, bubbles: true,
            });
            window.dispatchEvent(evt);
            return true;
        } catch (e) { return false; }
    }

    function buildWidget(host) {
        var root = host.attachShadow({ mode: 'open' });

        var style = document.createElement('style');
        style.textContent = STYLES;
        root.appendChild(style);

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
            '  <div class="rec-bar" data-role="rec-bar">' +
            '    <span class="rec-dot"></span>' +
            '    <span class="rec-time" data-role="rec-time">0:00</span>' +
            '    <span class="rec-text" data-role="rec-text">Tinglayapman...</span>' +
            '    <button class="rec-btn rec-cancel" data-role="rec-cancel" title="Bekor qilish">' +
            '      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4"' +
            '           stroke-linecap="round" stroke-linejoin="round">' +
            '        <polyline points="3 6 5 6 21 6"/>' +
            '        <path d="M19 6l-2 14a2 2 0 0 1-2 2H9a2 2 0 0 1-2-2L5 6"/></svg>' +
            '    </button>' +
            '    <button class="rec-btn rec-send" data-role="rec-send" title="Yuborish">' +
            '      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4"' +
            '           stroke-linecap="round" stroke-linejoin="round">' +
            '        <polyline points="20 6 9 17 4 12"/></svg>' +
            '    </button>' +
            '  </div>' +
            '  <div class="input-wrap" data-role="input-wrap">' +
            '    <textarea class="input" data-role="input" placeholder="Savol yozing yoki 🎤 bosing..." rows="1"></textarea>' +
            '    <button class="mic" data-role="mic" title="Ovozli xabar">' +
            '      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"' +
            '           stroke-linecap="round" stroke-linejoin="round">' +
            '        <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/>' +
            '        <path d="M19 10v2a7 7 0 0 1-14 0v-2"/>' +
            '        <line x1="12" y1="19" x2="12" y2="23"/>' +
            '        <line x1="8" y1="23" x2="16" y2="23"/></svg>' +
            '    </button>' +
            '    <button class="send" data-role="send" title="Yuborish">' +
            '      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"' +
            '           stroke-linecap="round" stroke-linejoin="round">' +
            '        <line x1="22" y1="2" x2="11" y2="13"/>' +
            '        <polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>' +
            '    </button>' +
            '  </div>' +
            '  <div class="hint">Enter — yuborish · Shift+Enter — yangi qator · 🎤 — ovozli</div>' +
            '</div>';
        root.appendChild(panel);

        var body = panel.querySelector('[data-role="body"]');
        var input = panel.querySelector('[data-role="input"]');
        var send = panel.querySelector('[data-role="send"]');
        var mic = panel.querySelector('[data-role="mic"]');
        var inputWrap = panel.querySelector('[data-role="input-wrap"]');
        var recBar = panel.querySelector('[data-role="rec-bar"]');
        var recTimeEl = panel.querySelector('[data-role="rec-time"]');
        var recTextEl = panel.querySelector('[data-role="rec-text"]');
        var recCancelBtn = panel.querySelector('[data-role="rec-cancel"]');
        var recSendBtn = panel.querySelector('[data-role="rec-send"]');
        var btnClose = panel.querySelector('[data-action="close"]');
        var btnClear = panel.querySelector('[data-action="clear"]');

        var MAX_REC_MS = 60000;

        var state = {
            busy: false,
            history: loadHistory(),
            aiVoiceMode: false,
            currentAudio: null,
            currentResetUI: null,
        };

        function playExclusive(audio, resetUI) {
            if (state.currentAudio && state.currentAudio !== audio) {
                try { state.currentAudio.pause(); } catch (e) {}
                if (typeof state.currentResetUI === 'function') {
                    try { state.currentResetUI(); } catch (e) {}
                }
            }
            state.currentAudio = audio;
            state.currentResetUI = resetUI;
            return audio.play();
        }

        function stopExclusive(audio) {
            if (state.currentAudio === audio) {
                state.currentAudio = null;
                state.currentResetUI = null;
            }
        }
        var voice = {
            recorder: null, stream: null, recognition: null, chunks: [],
            transcript: '', interim: '', start: 0, timer: 0,
            stopping: false, maxTimer: 0,
        };

        var TTS_ENDPOINT = '/api/v1/ai/tts/';

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
                    is_voice: !!state.aiVoiceMode,
                }),
            })
                .then(function (r) {
                    return r.json().then(function (j) { return { ok: r.ok, data: j }; });
                })
                .then(function (res) {
                    if (!res.ok) { throw new Error((res.data && res.data.error) || 'Xatolik'); }
                    var data = res.data || {};
                    var html = renderMarkdown(data.answer || '');
                    if (data.sources && data.sources.length) {
                        html += '<div class="sources">📎 Manba: ' +
                                data.sources.map(function (s) {
                                    var d = document.createElement('span');
                                    d.textContent = s;
                                    return d.innerHTML;
                                }).join(', ') + '</div>';
                    }
                    thinking.innerHTML = html;

                    var charts = Array.isArray(data.charts) ? data.charts : [];
                    charts.forEach(function (spec) { appendChart(thinking, spec); });

                    var cmds = Array.isArray(data.commands) ? data.commands : [];
                    cmds.forEach(function (cmd) {
                        var ok = dispatchCommand(cmd);
                        appendCommandPill(thinking, cmd, ok);
                    });

                    pushHistory('ai', data.answer || '');
                    scrollDown();
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

        function fmtDuration(ms) {
            var s = Math.max(0, Math.round(ms / 1000));
            var m = Math.floor(s / 60);
            var r = s % 60;
            return m + ':' + (r < 10 ? '0' : '') + r;
        }

        function makeWaveBars(blob, durationMs, onDone) {
            var Ctx = window.AudioContext || window.webkitAudioContext;
            if (!Ctx || !blob) { onDone(null); return; }
            var reader = new FileReader();
            reader.onload = function () {
                var ctx = new Ctx();
                ctx.decodeAudioData(reader.result, function (buf) {
                    var ch = buf.getChannelData(0);
                    var bars = 24, step = Math.max(1, Math.floor(ch.length / bars));
                    var arr = [];
                    for (var i = 0; i < bars; i++) {
                        var sum = 0, end = Math.min(ch.length, (i + 1) * step);
                        for (var j = i * step; j < end; j++) { sum += Math.abs(ch[j]); }
                        arr.push(sum / step);
                    }
                    var max = Math.max.apply(null, arr) || 1;
                    onDone(arr.map(function (v) { return v / max; }));
                    try { ctx.close(); } catch (e) {  }
                }, function () { onDone(null); });
            };
            reader.readAsArrayBuffer(blob);
        }

        function appendVoiceMessage(blob, transcript, durationMs) {
            var wrap = document.createElement('div');
            wrap.className = 'msg user';

            var avatar = document.createElement('div');
            avatar.className = 'msg-avatar';
            avatar.textContent = 'Siz';
            wrap.appendChild(avatar);

            var bubble = document.createElement('div');
            bubble.className = 'bubble';

            var vb = document.createElement('div');
            vb.className = 'voice-bubble';

            var url = blob ? URL.createObjectURL(blob) : null;
            var audio = url ? new Audio(url) : null;

            var playBtn = document.createElement('button');
            playBtn.type = 'button';
            playBtn.className = 'voice-play';
            playBtn.title = 'Tinglash';
            var playSVG = '<svg viewBox="0 0 24 24" fill="currentColor"><polygon points="6 4 20 12 6 20"/></svg>';
            var pauseSVG = '<svg viewBox="0 0 24 24" fill="currentColor"><rect x="6" y="5" width="4" height="14"/><rect x="14" y="5" width="4" height="14"/></svg>';
            playBtn.innerHTML = playSVG;

            var wave = document.createElement('div');
            wave.className = 'voice-wave';
            var barEls = [];
            for (var i = 0; i < 24; i++) {
                var s = document.createElement('span');
                s.style.height = '6px';
                wave.appendChild(s);
                barEls.push(s);
            }

            var timeEl = document.createElement('span');
            timeEl.className = 'voice-time';
            timeEl.textContent = fmtDuration(durationMs);

            vb.appendChild(playBtn);
            vb.appendChild(wave);
            vb.appendChild(timeEl);
            bubble.appendChild(vb);

            wrap.appendChild(bubble);
            body.appendChild(wrap);
            scrollDown();

            makeWaveBars(blob, durationMs, function (arr) {
                if (!arr) {
                    barEls.forEach(function (b, idx) {
                        var h = 4 + (Math.sin(idx * 0.7) + 1) * 6;
                        b.style.height = h + 'px';
                    });
                    return;
                }
                arr.forEach(function (v, idx) {
                    var h = Math.max(3, Math.round(v * 18));
                    barEls[idx].style.height = h + 'px';
                });
            });

            if (audio) {
                var resetUI = function () {
                    playBtn.innerHTML = playSVG;
                    barEls.forEach(function (b) { b.classList.remove('on'); });
                };
                audio.addEventListener('ended', function () {
                    resetUI();
                    stopExclusive(audio);
                });
                audio.addEventListener('timeupdate', function () {
                    var p = audio.duration ? audio.currentTime / audio.duration : 0;
                    var cutoff = Math.floor(p * barEls.length);
                    barEls.forEach(function (b, idx) {
                        if (idx < cutoff) { b.classList.add('on'); }
                        else { b.classList.remove('on'); }
                    });
                });
                playBtn.addEventListener('click', function () {
                    if (audio.paused) {
                        playExclusive(audio, resetUI).catch(function () {});
                        playBtn.innerHTML = pauseSVG;
                    } else {
                        audio.pause();
                        playBtn.innerHTML = playSVG;
                        stopExclusive(audio);
                    }
                });
            } else {
                playBtn.disabled = true;
                playBtn.style.opacity = '.5';
            }
        }

        function fetchAIVoice(text) {
            return fetch(TTS_ENDPOINT, {
                method: 'POST',
                credentials: 'same-origin',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken(),
                },
                body: JSON.stringify({ text: text }),
            }).then(function (r) {
                if (!r.ok) { throw new Error('TTS HTTP ' + r.status); }
                return r.blob();
            });
        }

        function prependAIVoiceBubble(targetEl, blob) {
            if (!blob || !targetEl) { return; }
            var vb = document.createElement('div');
            vb.className = 'voice-bubble ai-voice-bubble';

            var url = URL.createObjectURL(blob);
            var audio = new Audio(url);

            var playBtn = document.createElement('button');
            playBtn.type = 'button';
            playBtn.className = 'voice-play';
            playBtn.title = 'Tinglash';
            var playSVG = '<svg viewBox="0 0 24 24" fill="currentColor"><polygon points="6 4 20 12 6 20"/></svg>';
            var pauseSVG = '<svg viewBox="0 0 24 24" fill="currentColor"><rect x="6" y="5" width="4" height="14"/><rect x="14" y="5" width="4" height="14"/></svg>';
            playBtn.innerHTML = playSVG;

            var wave = document.createElement('div');
            wave.className = 'voice-wave';
            var barEls = [];
            for (var i = 0; i < 24; i++) {
                var s = document.createElement('span');
                var h = 4 + (Math.sin(i * 0.7) + 1) * 6;
                s.style.height = h + 'px';
                wave.appendChild(s);
                barEls.push(s);
            }

            var timeEl = document.createElement('span');
            timeEl.className = 'voice-time';
            timeEl.textContent = '0:00';

            vb.appendChild(playBtn);
            vb.appendChild(wave);
            vb.appendChild(timeEl);
            targetEl.insertBefore(vb, targetEl.firstChild);

            audio.addEventListener('loadedmetadata', function () {
                if (isFinite(audio.duration)) {
                    timeEl.textContent = fmtDuration(audio.duration * 1000);
                }
            });
            makeWaveBars(blob, 0, function (arr) {
                if (!arr) { return; }
                arr.forEach(function (v, idx) {
                    var bh = Math.max(3, Math.round(v * 18));
                    barEls[idx].style.height = bh + 'px';
                });
            });
            var resetUI = function () {
                playBtn.innerHTML = playSVG;
                barEls.forEach(function (b) { b.classList.remove('on'); });
            };
            audio.addEventListener('ended', function () {
                resetUI();
                stopExclusive(audio);
            });
            audio.addEventListener('timeupdate', function () {
                var p = audio.duration ? audio.currentTime / audio.duration : 0;
                var cutoff = Math.floor(p * barEls.length);
                barEls.forEach(function (b, idx) {
                    if (idx < cutoff) { b.classList.add('on'); }
                    else { b.classList.remove('on'); }
                });
                if (isFinite(audio.duration)) {
                    var remaining = (audio.duration - audio.currentTime) * 1000;
                    if (remaining > 0) { timeEl.textContent = fmtDuration(remaining); }
                }
            });
            playBtn.addEventListener('click', function () {
                if (audio.paused) {
                    playExclusive(audio, resetUI).catch(function () {});
                    playBtn.innerHTML = pauseSVG;
                } else {
                    audio.pause();
                    playBtn.innerHTML = playSVG;
                    stopExclusive(audio);
                }
            });

            playExclusive(audio, resetUI).then(function () {
                playBtn.innerHTML = pauseSVG;
            }).catch(function () {});
        }

        function showRecordingUI() {
            recTextEl.textContent = 'Tinglayapman...';
            recTimeEl.textContent = '0:00';
            recBar.classList.add('on');
            mic.classList.add('recording');
        }

        function hideRecordingUI() {
            recBar.classList.remove('on');
            mic.classList.remove('recording');
        }

        function tickTimer() {
            var elapsed = Date.now() - voice.start;
            recTimeEl.textContent = fmtDuration(elapsed);
            if (elapsed >= MAX_REC_MS) { stopRecording(); }
        }

        function startRecording() {
            if (voice.recorder || voice.stopping || state.busy) { return; }
            if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
                var isSecure = window.isSecureContext === true;
                var msg;
                if (!isSecure) {
                    msg = '⚠️ **Mikrofon faqat HTTPS yoki localhost da ishlaydi.**\n\n' +
                        'Hozir sayt `' + location.protocol + '//' + location.host + '` orqali ochilgan.\n\n' +
                        '**Yechimlar:**\n' +
                        '1. **Chrome flag** (test uchun): `chrome://flags/#unsafely-treat-insecure-origin-as-secure` ochib, ' +
                        'shu URL ni qo\'shing: `' + location.protocol + '//' + location.host + '` → "Enabled" → brauzerni qayta ishga tushiring.\n' +
                        '2. **SSH tunnel**: terminalda `ssh -L 7777:127.0.0.1:7777 user@server` → keyin `http://localhost:7777/` ochib ishlatasiz.\n' +
                        '3. **Nginx + HTTPS** (asosiy yechim): saytni `https://...` ostiga olib chiqish.';
                } else {
                    msg = '⚠️ Brauzer mikrofonni qo\'llab-quvvatlamaydi. Chrome/Edge\'ning so\'nggi versiyasini sinab ko\'ring.';
                }
                appendMessage('ai', msg);
                return;
            }
            navigator.mediaDevices.getUserMedia({ audio: true }).then(function (stream) {
                voice.stream = stream;
                voice.chunks = [];
                voice.transcript = '';
                voice.interim = '';
                voice.start = Date.now();

                var mime = 'audio/webm';
                try {
                    voice.recorder = new MediaRecorder(stream, { mimeType: mime });
                } catch (e) {
                    voice.recorder = new MediaRecorder(stream);
                }
                voice.recorder.addEventListener('dataavailable', function (e) {
                    if (e.data && e.data.size > 0) { voice.chunks.push(e.data); }
                });
                voice.recorder.start();

                var SR = window.SpeechRecognition || window.webkitSpeechRecognition;
                if (SR) {
                    var rec = new SR();
                    rec.lang = 'uz-UZ';
                    rec.continuous = true;
                    rec.interimResults = true;
                    rec.addEventListener('result', function (e) {
                        var fin = '', interim = '';
                        for (var i = e.resultIndex; i < e.results.length; i++) {
                            var t = e.results[i][0].transcript;
                            if (e.results[i].isFinal) { fin += t; } else { interim += t; }
                        }
                        if (fin) { voice.transcript += fin; }
                        voice.interim = interim;
                        var shown = (voice.transcript + ' ' + interim).trim();
                        recTextEl.textContent = shown || 'Tinglayapman...';
                        recTextEl.scrollTop = recTextEl.scrollHeight;
                    });
                    rec.addEventListener('error', function (e) {
                        if (e.error === 'not-allowed' || e.error === 'service-not-allowed') {
                            cancelRecording();
                        }
                    });
                    rec.addEventListener('end', function () {
                        if (voice.recorder && voice.recorder.state === 'recording') {
                            try { rec.start(); } catch (e) {  }
                        }
                    });
                    try { rec.start(); } catch (e) {  }
                    voice.recognition = rec;
                }

                showRecordingUI();
                voice.timer = setInterval(tickTimer, 250);
            }).catch(function (err) {
                appendMessage('ai', '⚠️ Mikrofonga ruxsat berilmadi: ' + (err && err.message ? err.message : err));
            });
        }

        function teardownRecording() {
            if (voice.timer) { clearInterval(voice.timer); voice.timer = 0; }
            if (voice.recognition) {
                try { voice.recognition.onend = null; voice.recognition.stop(); } catch (e) {  }
                voice.recognition = null;
            }
            if (voice.stream) {
                voice.stream.getTracks().forEach(function (t) { try { t.stop(); } catch (e) {} });
                voice.stream = null;
            }
            voice.recorder = null;
            voice.stopping = false;
            hideRecordingUI();
        }

        function cancelRecording() {
            if (voice.stopping) { return; }
            voice.stopping = true;
            if (voice.recorder) {
                try {
                    voice.recorder.onstop = null;
                    if (voice.recorder.state !== 'inactive') { voice.recorder.stop(); }
                } catch (e) {  }
            }
            voice.chunks = [];
            voice.transcript = '';
            voice.interim = '';
            teardownRecording();
        }

        function stopRecording() {
            if (voice.stopping) { return; }
            if (!voice.recorder) { hideRecordingUI(); return; }
            voice.stopping = true;

            var duration = Date.now() - voice.start;
            var rec = voice.recorder;
            var chunks = voice.chunks;
            var transcript = (voice.transcript + ' ' + voice.interim).trim();

            if (voice.recognition) {
                try { voice.recognition.onend = null; voice.recognition.stop(); } catch (e) {}
                voice.recognition = null;
            }
            if (voice.timer) { clearInterval(voice.timer); voice.timer = 0; }

            var finalize = function () {
                var blob = chunks.length ? new Blob(chunks, { type: (rec && rec.mimeType) || 'audio/webm' }) : null;
                var welcome = body.querySelector('.welcome');
                if (welcome) { welcome.remove(); }
                appendVoiceMessage(blob, transcript, duration);
                if (transcript) {
                    state.aiVoiceMode = true;
                    pushHistory('user', '🎤 ' + transcript);
                    askAI(transcript);
                } else {
                    appendMessage('ai', '⚠️ Ovozdan matn aniqlanmadi. Brauzer Uzbek tilini qo\'llab-quvvatlamayotgan bo\'lishi mumkin — ruscha yoki ingliz tilida sinab ko\'ring.');
                }
            };

            if (rec && rec.state !== 'inactive') {
                rec.onstop = function () {
                    teardownRecording();
                    finalize();
                };
                try { rec.stop(); } catch (e) {
                    teardownRecording();
                    finalize();
                }
            } else {
                teardownRecording();
                finalize();
            }
        }

        function askAI(text) {
            if (!text || state.busy) { return; }
            state.busy = true;
            send.disabled = true;

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
                    is_voice: !!state.aiVoiceMode,
                }),
            })
                .then(function (r) {
                    return r.json().then(function (j) { return { ok: r.ok, data: j }; });
                })
                .then(function (res) {
                    if (!res.ok) { throw new Error((res.data && res.data.error) || 'Xatolik'); }
                    var data = res.data || {};
                    var html = renderMarkdown(data.answer || '');
                    if (data.sources && data.sources.length) {
                        html += '<div class="sources">📎 Manba: ' +
                            data.sources.map(function (s) {
                                var d = document.createElement('span');
                                d.textContent = s;
                                return d.innerHTML;
                            }).join(', ') + '</div>';
                    }
                    thinking.innerHTML = html;

                    var charts = Array.isArray(data.charts) ? data.charts : [];
                    charts.forEach(function (spec) { appendChart(thinking, spec); });

                    var cmds = Array.isArray(data.commands) ? data.commands : [];
                    cmds.forEach(function (cmd) {
                        var ok = dispatchCommand(cmd);
                        appendCommandPill(thinking, cmd, ok);
                    });

                    pushHistory('ai', data.answer || '');
                    scrollDown();

                    if (state.aiVoiceMode && data.answer) {
                        var answerText = data.answer;
                        fetchAIVoice(answerText)
                            .then(function (blob) {
                                prependAIVoiceBubble(thinking, blob);
                                scrollDown();
                            })
                            .catch(function (err) {
                                console.warn('AI TTS failed:', err);
                            });
                    }
                })
                .catch(function (e) {
                    thinking.innerHTML = '❌ Xatolik: ' +
                        (function () { var d = document.createElement('span'); d.textContent = e.message; return d.innerHTML; })();
                })
                .finally(function () {
                    state.busy = false;
                    send.disabled = false;
                    state.aiVoiceMode = false;
                    scrollDown();
                });
        }

        function autosize() {
            input.style.height = 'auto';
            input.style.height = Math.min(input.scrollHeight, 120) + 'px';
        }

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
        mic.addEventListener('click', function () {
            if (voice.recorder) { stopRecording(); }
            else { startRecording(); }
        });
        recCancelBtn.addEventListener('click', cancelRecording);
        recSendBtn.addEventListener('click', stopRecording);

        root.addEventListener('keydown', function (e) {
            if (e.key === 'Escape' && panel.classList.contains('open')) { close(); }
        });

        window.AIChatWidget = {
            open: open,
            close: close,
            toggle: toggle,
            ask: function (text) {
                open();
                if (text) {
                    input.value = text;
                    autosize();
                }
            },
        };

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
