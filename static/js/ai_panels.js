/* AI panellari: avto-hisobotlar, metrik alertlar va Excel eksport.
   base.html da barcha sahifalarga ulanadi. API global obyektidan foydalanadi. */
(function () {
    'use strict';

    var modal = document.getElementById('ai-modal');
    var titleEl = document.getElementById('ai-modal-title');
    var bodyEl = document.getElementById('ai-modal-body');
    var headActions = document.getElementById('ai-modal-head-actions');
    var badge = document.getElementById('ai-bell-badge');

    function esc(s) {
        return String(s == null ? '' : s)
            .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    }

    function fmtDate(iso) {
        if (!iso) { return ''; }
        var d = new Date(iso);
        if (isNaN(d)) { return iso; }
        var p = function (n) { return (n < 10 ? '0' : '') + n; };
        return p(d.getDate()) + '.' + p(d.getMonth() + 1) + '.' + d.getFullYear() +
               ' ' + p(d.getHours()) + ':' + p(d.getMinutes());
    }

    function open() { modal.removeAttribute('hidden'); }

    function close() {
        modal.setAttribute('hidden', '');
        headActions.innerHTML = '';
    }

    function loading() {
        bodyEl.innerHTML = '<div class="ai-modal-loading">Yuklanmoqda…</div>';
    }

    // ── Hisobotlar ──────────────────────────────────────────────
    function openReports() {
        titleEl.textContent = '📊 AI hisobotlar';
        headActions.innerHTML =
            '<select class="ai-modal-select" id="ai-rep-kind">' +
            '<option value="">Barchasi</option>' +
            '<option value="daily">Kunlik</option>' +
            '<option value="weekly">Haftalik</option></select>';
        open();
        loading();
        document.getElementById('ai-rep-kind').addEventListener('change', loadReports);
        loadReports();
    }

    function loadReports() {
        var kind = (document.getElementById('ai-rep-kind') || {}).value || '';
        loading();
        API.get('/ai/reports/' + (kind ? '?kind=' + kind : ''))
            .then(function (data) {
                var reports = data.reports || [];
                if (!reports.length) {
                    bodyEl.innerHTML = '<div class="ai-modal-empty">Hali hisobot yo\'q. ' +
                        'Kunlik (08:00) va haftalik (dushanba) avtomatik tuziladi.</div>';
                    return;
                }
                bodyEl.innerHTML = reports.map(function (r) {
                    var kindLabel = r.kind === 'weekly' ? 'Haftalik' : 'Kunlik';
                    var html = (typeof marked !== 'undefined')
                        ? marked.parse(r.content || '') : esc(r.content);
                    return '<details class="ai-report"' + (r === reports[0] ? ' open' : '') + '>' +
                        '<summary><span class="ai-report-kind ai-rep-' + esc(r.kind) + '">' +
                        kindLabel + '</span> ' + esc(r.title) +
                        '<span class="ai-report-date">' + fmtDate(r.created_at) + '</span></summary>' +
                        '<div class="ai-report-content">' + html + '</div></details>';
                }).join('');
            })
            .catch(function (e) {
                bodyEl.innerHTML = '<div class="ai-modal-empty">Xato: ' + esc(e.message) + '</div>';
            });
    }

    // ── Alertlar ────────────────────────────────────────────────
    function openAlerts() {
        titleEl.textContent = '🔔 Metrik alertlar';
        headActions.innerHTML =
            '<button class="ai-modal-btn" onclick="AIPanels.markAllRead()">Hammasini o\'qildi</button>';
        open();
        loading();
        loadAlerts();
    }

    function loadAlerts() {
        API.get('/ai/alerts/')
            .then(function (data) {
                var alerts = data.alerts || [];
                updateBadge(data.unread || 0);
                if (!alerts.length) {
                    bodyEl.innerHTML = '<div class="ai-modal-empty">Alert yo\'q — hammasi joyida ✅</div>';
                    return;
                }
                bodyEl.innerHTML = alerts.map(function (a) {
                    return '<div class="ai-alert ai-sev-' + esc(a.severity) +
                        (a.is_read ? ' ai-alert-read' : '') + '">' +
                        '<div class="ai-alert-msg">' + esc(a.message) + '</div>' +
                        '<div class="ai-alert-meta">' + esc(a.source || 'all') +
                        ' · ' + fmtDate(a.created_at) + '</div></div>';
                }).join('');
            })
            .catch(function (e) {
                bodyEl.innerHTML = '<div class="ai-modal-empty">Xato: ' + esc(e.message) + '</div>';
            });
    }

    function markAllRead() {
        API.patch('/ai/alerts/', {}).then(function () {
            updateBadge(0);
            loadAlerts();
        });
    }

    function updateBadge(n) {
        if (!badge) { return; }
        if (n > 0) {
            badge.textContent = n > 99 ? '99+' : n;
            badge.removeAttribute('hidden');
        } else {
            badge.setAttribute('hidden', '');
        }
    }

    function refreshBadge() {
        API.get('/ai/alerts/?unread=1')
            .then(function (data) { updateBadge(data.unread || 0); })
            .catch(function () {});
    }

    // ── Excel eksport ───────────────────────────────────────────
    function exportExcel() {
        var src = window.__crmSource || '';
        var url = '/api/v1/ai/export/' + (src ? '?source=' + encodeURIComponent(src) : '');
        window.location.href = url;
    }

    // ── Chat feedback (👍/👎) — chat va widget uchun umumiy ──────
    window.buildChatFeedback = function (messageId) {
        var wrap = document.createElement('div');
        wrap.className = 'chat-feedback';
        var up = document.createElement('button');
        up.className = 'chat-fb-btn'; up.type = 'button';
        up.textContent = '👍'; up.title = 'Foydali';
        var down = document.createElement('button');
        down.className = 'chat-fb-btn'; down.type = 'button';
        down.textContent = '👎'; down.title = 'Foydasiz';

        function send(value, btn) {
            API.post('/ai/feedback/', { message_id: messageId, feedback: value })
                .then(function () {
                    up.classList.remove('fb-on-up');
                    down.classList.remove('fb-on-down');
                    btn.classList.add(value === 'up' ? 'fb-on-up' : 'fb-on-down');
                })
                .catch(function () {});
        }
        up.addEventListener('click', function () { send('up', up); });
        down.addEventListener('click', function () { send('down', down); });
        wrap.appendChild(up);
        wrap.appendChild(down);
        return wrap;
    };

    window.AIPanels = {
        openReports: openReports, openAlerts: openAlerts,
        exportExcel: exportExcel, markAllRead: markAllRead, close: close,
    };

    document.addEventListener('keydown', function (e) {
        if (e.key === 'Escape' && !modal.hasAttribute('hidden')) { close(); }
    });

    // Qo'ng'iroq belgisini boshda va har 5 daqiqada yangilaymiz
    if (badge) {
        refreshBadge();
        setInterval(refreshBadge, 300000);
    }
})();
