(function () {
    'use strict';

    var API = {
        managers:  '/api/v1/ai/managers/',
        documents: '/api/v1/ai/rag/documents/',
        upload:    '/api/v1/ai/rag/upload/',
        chat:      '/api/v1/ai/chat/',
        history:   '/api/v1/ai/chat/history/',
        agent:     '/api/v1/ai/agent/analyze/',
    };

    var elMessages   = document.getElementById('chat-messages');
    var elInput      = document.getElementById('chat-input');
    var elSend       = document.getElementById('chat-send-btn');
    var elManager    = document.getElementById('ailab-manager-select');
    var elAgentBtn   = document.getElementById('ailab-agent-btn');
    var elFile       = document.getElementById('ailab-file');
    var elUpload     = document.getElementById('ailab-upload');
    var elDocList    = document.getElementById('ailab-doc-list');

    var CSRF = (document.querySelector('meta[name="csrf-token"]') || {}).content || '';

    var busy = false;

    function render(text) {
        if (typeof marked !== 'undefined') {
            return marked.parse(text || '');
        }
        return (text || '').replace(/\n/g, '<br>');
    }

    function addMessage(role, html, opts) {
        opts = opts || {};
        var wrap = document.createElement('div');
        wrap.className = 'chat-message ' + (role === 'human' ? 'user' : 'ai');

        var avatar = document.createElement('div');
        avatar.className = 'chat-avatar';
        avatar.textContent = role === 'human' ? 'S' : 'AI';

        var bubble = document.createElement('div');
        bubble.className = 'chat-bubble';
        if (opts.raw) {
            bubble.innerHTML = html;
        } else {
            bubble.textContent = html;
        }

        if (role === 'human') {
            wrap.appendChild(bubble);
            wrap.appendChild(avatar);
        } else {
            wrap.appendChild(avatar);
            wrap.appendChild(bubble);
        }
        elMessages.appendChild(wrap);
        elMessages.scrollTop = elMessages.scrollHeight;
        return bubble;
    }

    function loadManagers() {
        fetch(API.managers)
            .then(function (r) { return r.json(); })
            .then(function (data) {
                (data.managers || []).forEach(function (m) {
                    var opt = document.createElement('option');
                    opt.value = m.id;
                    opt.textContent = m.name;
                    elManager.appendChild(opt);
                });
            })
            .catch(function () {  });
    }

    function loadHistory() {
        var managerId = elManager.value || '0';
        var welcome = elMessages.querySelector('.chat-message');
        elMessages.innerHTML = '';
        if (welcome) { elMessages.appendChild(welcome); }

        fetch(API.history + '?manager_id=' + encodeURIComponent(managerId))
            .then(function (r) { return r.json(); })
            .then(function (data) {
                (data.messages || []).forEach(function (m) {
                    addMessage(m.role, m.role === 'ai' ? render(m.content) : m.content,
                               { raw: m.role === 'ai' });
                });
            })
            .catch(function () {});
    }

    function loadDocuments() {
        fetch(API.documents)
            .then(function (r) { return r.json(); })
            .then(function (data) {
                var docs = data.documents || [];
                if (!docs.length) {
                    elDocList.innerHTML = '<div class="ailab-doc-empty">Hozircha hujjat yo\'q</div>';
                    return;
                }
                elDocList.innerHTML = '';
                docs.forEach(function (d) {
                    var item = document.createElement('div');
                    item.className = 'ailab-doc ailab-doc-' + d.status;
                    var icon = d.file_type === 'pdf' ? '📄' : '📊';
                    item.innerHTML =
                        '<span class="ailab-doc-icon">' + icon + '</span>' +
                        '<span class="ailab-doc-info">' +
                            '<span class="ailab-doc-title">' + d.title + '</span>' +
                            '<span class="ailab-doc-meta">' + d.chunk_count + ' bo\'lak · ' +
                            statusLabel(d.status) + '</span>' +
                        '</span>' +
                        '<button class="ailab-doc-del" data-id="' + d.id + '" title="O\'chirish">×</button>';
                    elDocList.appendChild(item);
                });
                elDocList.querySelectorAll('.ailab-doc-del').forEach(function (btn) {
                    btn.addEventListener('click', function () { deleteDocument(btn.dataset.id); });
                });
            })
            .catch(function () {});
    }

    function statusLabel(s) {
        if (s === 'ready') return 'tayyor';
        if (s === 'error') return 'xatolik';
        return 'qayta ishlanmoqda';
    }

    function uploadFile(file) {
        if (!file || busy) { return; }
        busy = true;
        elUpload.classList.add('ailab-upload-busy');
        elUpload.querySelector('.ailab-upload-text').textContent = 'Yuklanmoqda: ' + file.name;

        var fd = new FormData();
        fd.append('file', file);

        fetch(API.upload, {
            method: 'POST',
            headers: { 'X-CSRFToken': CSRF },
            body: fd,
        })
            .then(function (r) { return r.json().then(function (j) { return { ok: r.ok, j: j }; }); })
            .then(function (res) {
                if (!res.ok) { throw new Error(res.j.error || 'Yuklashda xatolik'); }
                addMessage('ai', '✅ "<b>' + res.j.title + '</b>" hujjati qo\'shildi (' +
                           res.j.chunk_count + ' bo\'lak). Endi shu hujjat bo\'yicha savol bering.',
                           { raw: true });
            })
            .catch(function (e) {
                addMessage('ai', '❌ Xatolik: ' + e.message, { raw: true });
            })
            .finally(function () {
                busy = false;
                elUpload.classList.remove('ailab-upload-busy');
                elUpload.querySelector('.ailab-upload-text').textContent = 'PDF yoki Excel yuklang';
                elFile.value = '';
                loadDocuments();
            });
    }

    function deleteDocument(id) {
        if (!confirm('Hujjat o\'chirilsinmi? Vektor indeksi qayta quriladi.')) { return; }
        fetch(API.documents + id + '/', {
            method: 'DELETE',
            headers: { 'X-CSRFToken': CSRF },
        })
            .then(function () { loadDocuments(); })
            .catch(function () {});
    }

    function sendMessage() {
        var text = (elInput.value || '').trim();
        if (!text || busy) { return; }
        busy = true;
        elInput.value = '';
        elInput.style.height = 'auto';

        addMessage('human', text);
        var thinking = addMessage('ai', '<span class="ailab-typing">●●●</span>', { raw: true });

        fetch(API.chat, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': CSRF },
            body: JSON.stringify({ message: text, manager_id: elManager.value || 0 }),
        })
            .then(function (r) { return r.json().then(function (j) { return { ok: r.ok, j: j }; }); })
            .then(function (res) {
                if (!res.ok) { throw new Error(res.j.error || 'Xatolik'); }
                var html = render(res.j.answer);
                if (res.j.sources && res.j.sources.length) {
                    html += '<div class="ailab-sources">📎 Manba: ' +
                            res.j.sources.join(', ') + '</div>';
                }
                thinking.innerHTML = html;
            })
            .catch(function (e) {
                thinking.innerHTML = '❌ Xatolik: ' + e.message;
            })
            .finally(function () {
                busy = false;
                elMessages.scrollTop = elMessages.scrollHeight;
            });
    }

    function runAgent() {
        if (busy) { return; }
        busy = true;
        elAgentBtn.disabled = true;
        elAgentBtn.textContent = '⏳ Agent tahlil qilmoqda…';

        addMessage('human', '🤖 Agent: dashboard\'ni tahlil qil');
        var thinking = addMessage('ai',
            '<span class="ailab-typing">●●●</span> Agent tool\'lar orqali ma\'lumot yig\'moqda…',
            { raw: true });

        var source = window.__crmSource || '';
        fetch(API.agent, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': CSRF },
            body: JSON.stringify({ source: source }),
        })
            .then(function (r) { return r.json().then(function (j) { return { ok: r.ok, j: j }; }); })
            .then(function (res) {
                if (!res.ok) { throw new Error(res.j.error || 'Xatolik'); }
                var html = render(res.j.analysis);
                if (res.j.steps && res.j.steps.length) {
                    html += '<div class="ailab-sources">🔧 Ishlatilgan tool\'lar: ' +
                            res.j.steps.join(', ') + '</div>';
                }
                thinking.innerHTML = html;
            })
            .catch(function (e) {
                thinking.innerHTML = '❌ Xatolik: ' + e.message;
            })
            .finally(function () {
                busy = false;
                elAgentBtn.disabled = false;
                elAgentBtn.textContent = '🤖 Agent tahlil qilsin';
                elMessages.scrollTop = elMessages.scrollHeight;
            });
    }

    elSend.addEventListener('click', sendMessage);
    elInput.addEventListener('keydown', function (e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });
    elInput.addEventListener('input', function () {
        elInput.style.height = 'auto';
        elInput.style.height = Math.min(elInput.scrollHeight, 140) + 'px';
    });

    elManager.addEventListener('change', loadHistory);
    elAgentBtn.addEventListener('click', runAgent);

    elFile.addEventListener('change', function () {
        if (elFile.files.length) { uploadFile(elFile.files[0]); }
    });

    ['dragenter', 'dragover'].forEach(function (ev) {
        elUpload.addEventListener(ev, function (e) {
            e.preventDefault();
            elUpload.classList.add('ailab-upload-over');
        });
    });
    ['dragleave', 'drop'].forEach(function (ev) {
        elUpload.addEventListener(ev, function (e) {
            e.preventDefault();
            elUpload.classList.remove('ailab-upload-over');
        });
    });
    elUpload.addEventListener('drop', function (e) {
        if (e.dataTransfer.files.length) { uploadFile(e.dataTransfer.files[0]); }
    });

    loadManagers();
    loadDocuments();
})();
