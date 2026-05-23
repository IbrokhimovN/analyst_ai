/**
 * dashboard_dynamic.js — Dinamik Savdo Dashboard.
 *
 * Imkoniyatlar:
 *   1. AJAX yangilash — period/source o'zgarganda sahifa qayta yuklanmaydi,
 *      faqat #dash-root ichidagi kartalar almashtiriladi.
 *   2. Avto-yangilanish — har 60 soniyada ma'lumot jimgina yangilanadi.
 *   3. Manual refresh tugmasi + "oxirgi yangilanish" vaqti.
 *   4. Kartalar: jadval <-> grafik toggle (funnel, managers).
 *   5. Har-karta AI paneli:
 *        - "AI tahlil"  -> LangChain agent kartani tahlil qiladi.
 *        - "Ko'rinishni o'zgartir" -> AI xavfsiz view-spec (JSON config)
 *          qaytaradi, frontend kartani shu konfiguratsiya bo'yicha chizadi.
 */
(function () {
    'use strict';

    // ===== API endpointlari =====
    var API = {
        data:        '/api/v1/dashboard/data/',
        weekly:      '/api/v1/ai/report/weekly/',
        cardAnalyze: '/api/v1/ai/card/analyze/',
        cardRender:  '/api/v1/ai/card/render/',
    };

    var AUTO_REFRESH_MS = 60000;   // avto-yangilanish oralig'i
    var CSRF = (document.querySelector('meta[name="csrf-token"]') || {}).content || '';

    // Joriy holat — period/source dashboard bo'ylab shu yerda saqlanadi.
    var state = {
        period: 'all',
        source: window.__crmSource || '',
        busy: false,
    };

    // Chart.js instansiyalari — qayta chizishdan oldin destroy qilish uchun.
    var charts = {};

    // Kartalarning ma'lumot manbai (json_script id) va kategoriya maydoni.
    var CARD_META = {
        funnel:      { json: 'funnel-data',      cat: 'name' },
        managers:    { json: 'managers-data',    cat: 'manager_name' },
        loss:        { json: 'loss-data',        cat: 'reason' },
        finance:     { json: 'finance-data',     cat: null },
        conversions: { json: 'conversions-data', cat: 'label' },
        daily:       { json: 'daily-data',       cat: 'date' },
        followup:    { json: 'followup-data',    cat: 'manager_name' },
        best_days:   { json: 'best-days-data',   cat: 'day' },
    };

    // Metrik kalitlari uchun o'zbekcha sarlavhalar (jadval/grafik uchun).
    var METRIC_LABELS = {
        count: 'Soni', pct: 'Foiz, %', revenue: 'Tushum', won: 'Sotuv',
        calls: 'Call', conversations: 'Conversation', total_leads: 'Lidlar',
        conversion_rate: 'Konversiya, %', convo_rate: 'Convo, %',
        sale_rate: 'Sale, %', lead_to_sale: 'Lid->Sale, %', value: 'Qiymat',
        num: 'Soni', den: 'Umumiy', leads: 'Lid', sales: 'Sotuv',
        conversion: 'Konversiya, %', lost: 'Yutqazgan',
        total_revenue: 'Tushum', avg_deal: "O'rtacha chek",
        lead_value: '1 lid qiymati', sale_value: '1 sale qiymati',
    };

    // =========================================================================
    // Umumiy yordamchilar
    // =========================================================================

    function esc(s) {
        var d = document.createElement('div');
        d.textContent = (s == null ? '' : String(s));
        return d.innerHTML;
    }

    function fmt(n) {
        n = Number(n) || 0;
        return n.toLocaleString('ru-RU');
    }

    function metricLabel(m) {
        return METRIC_LABELS[m] || m;
    }

    function render(md) {
        if (typeof marked !== 'undefined') { return marked.parse(md || ''); }
        return (md || '').replace(/\n/g, '<br>');
    }

    function readJSON(id) {
        var node = document.getElementById(id);
        if (!node) { return null; }
        try { return JSON.parse(node.textContent); }
        catch (e) { return null; }
    }

    function themeColors() {
        var dark = document.documentElement.getAttribute('data-theme') === 'dark';
        return {
            isDark: dark,
            grid: dark ? 'rgba(255,255,255,0.07)' : 'rgba(15,23,41,0.08)',
            tick: dark ? '#94a3b8' : '#64748b',
        };
    }

    var PALETTE = ['#3b82f6', '#22c55e', '#f59e0b', '#ef4444', '#8b5cf6',
                   '#06b6d4', '#ec4899', '#14b8a6', '#f97316', '#a855f7'];

    // Barcha grafiklarni o'chirish (innerHTML almashtirishdan oldin shart).
    function destroyCharts() {
        Object.keys(charts).forEach(function (k) {
            try { charts[k].destroy(); } catch (e) { /* e'tiborsiz */ }
        });
        charts = {};
    }

    // =========================================================================
    // Kartalardagi standart grafiklar (kunlik dinamika, loss bar)
    // =========================================================================

    function initDailyChart() {
        var ctx = document.getElementById('dailyDynamicsChart');
        var daily = readJSON('daily-data') || [];
        if (!ctx || typeof Chart === 'undefined') { return; }
        var c = themeColors();
        var labels = daily.map(function (d) {
            var dt = new Date(d.date);
            return dt.toLocaleDateString('uz-UZ', { day: 'numeric', month: 'short' });
        });
        charts.daily = new Chart(ctx, {
            data: {
                labels: labels,
                datasets: [
                    { type: 'bar', label: 'Lid', yAxisID: 'y',
                      data: daily.map(function (d) { return d.leads; }),
                      backgroundColor: '#3b82f6', borderRadius: 4, barPercentage: 0.6 },
                    { type: 'bar', label: 'Sotuv', yAxisID: 'y',
                      data: daily.map(function (d) { return d.sales; }),
                      backgroundColor: '#22c55e', borderRadius: 4, barPercentage: 0.6 },
                    { type: 'line', label: 'Conversion %', yAxisID: 'y1',
                      data: daily.map(function (d) { return d.conversion; }),
                      borderColor: '#f59e0b', backgroundColor: '#f59e0b',
                      borderWidth: 2.5, tension: 0.4, pointRadius: 3 },
                ],
            },
            options: {
                responsive: true, maintainAspectRatio: false,
                plugins: {
                    legend: { position: 'top',
                        labels: { color: c.tick, usePointStyle: true,
                                  font: { family: 'Inter', size: 11 } } },
                },
                scales: {
                    x: { ticks: { color: c.tick }, grid: { color: c.grid } },
                    y: { position: 'left', beginAtZero: true,
                         ticks: { color: c.tick }, grid: { color: c.grid },
                         title: { display: true, text: 'Lid / Sotuv soni', color: c.tick } },
                    y1: { position: 'right', beginAtZero: true,
                          ticks: { color: c.tick, callback: function (v) { return v + '%'; } },
                          grid: { drawOnChartArea: false },
                          title: { display: true, text: 'Conversion %', color: c.tick } },
                },
            },
        });
    }

    function initLossBars() {
        var fills = document.querySelectorAll('.dr-fill');
        var maxCount = 0;
        fills.forEach(function (f) {
            var v = parseInt(f.dataset.count, 10) || 0;
            if (v > maxCount) { maxCount = v; }
        });
        fills.forEach(function (f, i) {
            var v = parseInt(f.dataset.count, 10) || 0;
            var pct = maxCount > 0 ? (v / maxCount) * 100 : 0;
            setTimeout(function () { f.style.width = Math.max(pct, 4) + '%'; }, 70 * i);
        });
    }

    // =========================================================================
    // Funnel / Managers — jadval <-> grafik toggle (inline onclick chaqiradi)
    // =========================================================================

    window.toggleCardView = function (card, btn) {
        var tableView = document.getElementById(card + '-table-view');
        var chartView = document.getElementById(card + '-chart-view');
        if (!tableView || !chartView) { return; }

        var showChart = chartView.hasAttribute('hidden');
        if (showChart) {
            tableView.setAttribute('hidden', '');
            chartView.removeAttribute('hidden');
            btn.textContent = '📋 Jadval';
            btn.classList.add('dash-toggle-on');
            renderToggleChart(card);
        } else {
            chartView.setAttribute('hidden', '');
            tableView.removeAttribute('hidden');
            btn.textContent = (card === 'funnel' ? '📊 Grafik' : '🥧 Grafik');
            btn.classList.remove('dash-toggle-on');
        }
    };

    function renderToggleChart(card) {
        if (charts[card] || typeof Chart === 'undefined') { return; }
        var c = themeColors();

        if (card === 'funnel') {
            var funnel = readJSON('funnel-data') || [];
            var fctx = document.getElementById('funnelBarChart');
            if (!fctx) { return; }
            charts.funnel = new Chart(fctx, {
                type: 'bar',
                data: {
                    labels: funnel.map(function (s) { return s.name; }),
                    datasets: [{
                        label: 'Soni',
                        data: funnel.map(function (s) { return s.count; }),
                        backgroundColor: funnel.map(function (s) { return s.color; }),
                        borderRadius: 6,
                    }],
                },
                options: {
                    responsive: true, maintainAspectRatio: false,
                    plugins: {
                        legend: { display: false },
                        tooltip: { callbacks: { label: function (ct) {
                            var s = funnel[ct.dataIndex] || {};
                            return ct.parsed.y + ' ta  (' + (s.pct || 0) + '%)';
                        } } },
                    },
                    scales: {
                        x: { ticks: { color: c.tick }, grid: { display: false } },
                        y: { beginAtZero: true, ticks: { color: c.tick },
                             grid: { color: c.grid } },
                    },
                },
            });
        } else if (card === 'managers') {
            var managers = readJSON('managers-data') || [];
            var mctx = document.getElementById('managersPieChart');
            if (!mctx) { return; }
            var values = managers.map(function (m) { return m.revenue; });
            var metric = 'Tushum';
            if (values.every(function (v) { return !v; })) {
                values = managers.map(function (m) { return m.won; });
                metric = 'Sotuvlar';
            }
            charts.managers = new Chart(mctx, {
                type: 'pie',
                data: {
                    labels: managers.map(function (m) { return m.manager_name; }),
                    datasets: [{
                        data: values,
                        backgroundColor: managers.map(function (_, i) {
                            return PALETTE[i % PALETTE.length]; }),
                        borderColor: c.isDark ? '#0a0a1c' : '#ffffff',
                        borderWidth: 2,
                    }],
                },
                options: {
                    responsive: true, maintainAspectRatio: false,
                    plugins: {
                        legend: { position: 'right',
                            labels: { color: c.tick, usePointStyle: true,
                                      font: { family: 'Inter', size: 11 } } },
                        title: { display: true,
                            text: 'Menejerlar reytingi — ' + metric,
                            color: c.tick, font: { family: 'Inter', size: 12 } },
                    },
                },
            });
        }
    }

    // =========================================================================
    // Har-karta AI paneli
    // =========================================================================

    function initCardAI() {
        document.querySelectorAll('.dcard-ai-btn').forEach(function (btn) {
            btn.addEventListener('click', function () {
                toggleAiPanel(btn.dataset.card);
            });
        });
    }

    function toggleAiPanel(card) {
        var cardEl = document.querySelector('.dash-card[data-card="' + card + '"]');
        if (!cardEl) { return; }
        var panel = cardEl.querySelector('.dcard-ai');
        if (panel) {
            // mavjud panelni ko'rsatish/yashirish
            if (panel.hasAttribute('hidden')) { panel.removeAttribute('hidden'); }
            else { panel.setAttribute('hidden', ''); }
            return;
        }
        panel = buildAiPanel(card);
        var head = cardEl.querySelector('.dash-card-head');
        head.insertAdjacentElement('afterend', panel);
    }

    // AI panelining DOM tuzilishini quradi.
    function buildAiPanel(card) {
        var panel = document.createElement('div');
        panel.className = 'dcard-ai';
        panel.dataset.card = card;
        panel.innerHTML =
            '<div class="dca-tabs">' +
                '<button type="button" class="dca-tab dca-tab-on" data-mode="analyze">🔍 AI tahlil</button>' +
                '<button type="button" class="dca-tab" data-mode="render">🎨 Ko\'rinishni o\'zgartir</button>' +
            '</div>' +
            '<div class="dca-pane" data-pane="analyze">' +
                '<button type="button" class="dca-go" data-act="analyze">AI bu kartani tahlil qilsin</button>' +
                '<div class="dca-out" hidden></div>' +
            '</div>' +
            '<div class="dca-pane" data-pane="render" hidden>' +
                '<div class="dca-row">' +
                    '<input type="text" class="dca-input" ' +
                        'placeholder="Masalan: pie chart qil, top 3 ko\'rsat, tushum bo\'yicha sarala">' +
                    '<button type="button" class="dca-go" data-act="render">Qo\'lla</button>' +
                '</div>' +
                '<div class="dca-hint">AI siz xohlagan ko\'rinishni tanlab kartani qayta chizadi.</div>' +
                '<div class="dca-out" hidden></div>' +
            '</div>';

        // Tab almashtirish
        panel.querySelectorAll('.dca-tab').forEach(function (tab) {
            tab.addEventListener('click', function () {
                var mode = tab.dataset.mode;
                panel.querySelectorAll('.dca-tab').forEach(function (t) {
                    t.classList.toggle('dca-tab-on', t === tab);
                });
                panel.querySelectorAll('.dca-pane').forEach(function (p) {
                    if (p.dataset.pane === mode) { p.removeAttribute('hidden'); }
                    else { p.setAttribute('hidden', ''); }
                });
            });
        });

        // "Tahlil" va "Qo'lla" tugmalari
        panel.querySelectorAll('.dca-go').forEach(function (go) {
            go.addEventListener('click', function () {
                if (go.dataset.act === 'analyze') { runCardAnalyze(card, panel, go); }
                else { runCardRender(card, panel, go); }
            });
        });
        // Enter bilan ham yuborish
        var input = panel.querySelector('.dca-input');
        input.addEventListener('keydown', function (e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                runCardRender(card, panel, panel.querySelector('.dca-go[data-act="render"]'));
            }
        });
        return panel;
    }

    // --- AI: kartani tahlil qilish (LangChain agent) ---
    function runCardAnalyze(card, panel, btn) {
        var out = panel.querySelector('.dca-pane[data-pane="analyze"] .dca-out');
        btn.disabled = true;
        var oldText = btn.textContent;
        btn.textContent = '⏳ Tahlil qilinmoqda…';
        out.removeAttribute('hidden');
        out.className = 'dca-out dca-loading';
        out.textContent = 'AI ma\'lumotni ko\'rib chiqmoqda…';

        fetch(API.cardAnalyze, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': CSRF },
            body: JSON.stringify({ card: card, source: state.source,
                                   period: apiPeriod() }),
        })
            .then(function (r) { return r.json().then(function (j) {
                return { ok: r.ok, j: j }; }); })
            .then(function (res) {
                if (!res.ok) { throw new Error(res.j.error || 'Xatolik'); }
                out.className = 'dca-out';
                out.innerHTML = render(res.j.analysis);
            })
            .catch(function (e) {
                out.className = 'dca-out dca-error';
                out.textContent = '❌ ' + e.message;
            })
            .finally(function () {
                btn.disabled = false;
                btn.textContent = oldText;
            });
    }

    // --- AI: kartaning ko'rinishini o'zgartirish (view-spec) ---
    function runCardRender(card, panel, btn) {
        var input = panel.querySelector('.dca-input');
        var out = panel.querySelector('.dca-pane[data-pane="render"] .dca-out');
        var instruction = (input.value || '').trim();
        if (!instruction) { input.focus(); return; }

        btn.disabled = true;
        var oldText = btn.textContent;
        btn.textContent = '⏳…';
        out.removeAttribute('hidden');
        out.className = 'dca-out dca-loading';
        out.textContent = 'AI ko\'rinishni tayyorlamoqda…';

        fetch(API.cardRender, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': CSRF },
            body: JSON.stringify({ card: card, instruction: instruction,
                                   source: state.source, period: apiPeriod() }),
        })
            .then(function (r) { return r.json().then(function (j) {
                return { ok: r.ok, j: j }; }); })
            .then(function (res) {
                if (!res.ok) { throw new Error(res.j.error || 'Xatolik'); }
                applyViewSpec(card, res.j.spec);
                out.className = 'dca-out dca-spec-ok';
                out.innerHTML = '✅ ' + esc(res.j.spec.note || 'Ko\'rinish yangilandi.') +
                    ' <button type="button" class="dca-revert-link">↩ asl ko\'rinish</button>';
                out.querySelector('.dca-revert-link').addEventListener('click', function () {
                    revertCard(card);
                    out.setAttribute('hidden', '');
                });
            })
            .catch(function (e) {
                out.className = 'dca-out dca-error';
                out.textContent = '❌ ' + e.message;
            })
            .finally(function () {
                btn.disabled = false;
                btn.textContent = oldText;
            });
    }

    // =========================================================================
    // View-spec — AI konfiguratsiyasi bo'yicha kartani qayta chizish
    // =========================================================================

    // Karta uchun ma'lumot qatorlarini tayyorlaydi (massiv ko'rinishida).
    function cardRows(card) {
        var meta = CARD_META[card];
        var raw = readJSON(meta.json);
        if (card === 'finance') {
            var f = raw || {};
            return [
                { _label: 'Umumiy tushum',  value: Number(f.total_revenue) || 0,
                  total_revenue: Number(f.total_revenue) || 0,
                  avg_deal: Number(f.avg_deal) || 0,
                  lead_value: Number(f.lead_value) || 0,
                  sale_value: Number(f.sale_value) || 0 },
                { _label: "O'rtacha chek",  value: Number(f.avg_deal) || 0,
                  total_revenue: Number(f.total_revenue) || 0,
                  avg_deal: Number(f.avg_deal) || 0,
                  lead_value: Number(f.lead_value) || 0,
                  sale_value: Number(f.sale_value) || 0 },
                { _label: '1 lid qiymati',  value: Number(f.lead_value) || 0,
                  total_revenue: Number(f.total_revenue) || 0,
                  avg_deal: Number(f.avg_deal) || 0,
                  lead_value: Number(f.lead_value) || 0,
                  sale_value: Number(f.sale_value) || 0 },
                { _label: '1 sale qiymati', value: Number(f.sale_value) || 0,
                  total_revenue: Number(f.total_revenue) || 0,
                  avg_deal: Number(f.avg_deal) || 0,
                  lead_value: Number(f.lead_value) || 0,
                  sale_value: Number(f.sale_value) || 0 },
            ];
        }
        return Array.isArray(raw) ? raw.slice() : [];
    }

    function defaultMetric(card) {
        return {
            funnel: 'count', managers: 'revenue', loss: 'count',
            finance: 'value', conversions: 'pct', daily: 'leads',
            followup: 'lost', best_days: 'leads',
        }[card];
    }

    // 'YYYY-MM-DD' -> 'DD.MM' (daily chartda sanani qisqartirish uchun).
    function shortLabel(card, val) {
        if (card === 'daily' && /^\d{4}-\d{2}-\d{2}$/.test(val)) {
            var p = val.split('-');
            return p[2] + '.' + p[1];
        }
        return val;
    }

    // AI view-spec ni kartaga qo'llaydi.
    function applyViewSpec(card, spec) {
        var cardEl = document.querySelector('.dash-card[data-card="' + card + '"]');
        if (!cardEl) { return; }
        revertCard(card);  // avvalgi maxsus ko'rinish bo'lsa tozalaymiz

        // Standart bolalarni (head va AI paneldan tashqari) yashiramiz.
        Array.prototype.forEach.call(cardEl.children, function (ch) {
            if (ch.classList.contains('dash-card-head') ||
                ch.classList.contains('dcard-ai')) { return; }
            ch.classList.add('dcard-orig-hidden');
        });
        // Toggle tugmasi maxsus ko'rinishda chalkashmasligi uchun yashiramiz.
        var toggle = cardEl.querySelector('.dash-toggle');
        if (toggle) { toggle.style.display = 'none'; }

        var box = document.createElement('div');
        box.className = 'dcard-custom';
        box.innerHTML =
            '<div class="dcard-custom-head">' +
                '<span class="dcard-custom-title">🎨 ' + esc(spec.title || 'AI ko\'rinish') + '</span>' +
                '<button type="button" class="dcard-custom-revert">↩ Asl ko\'rinish</button>' +
            '</div>' +
            '<div class="dcard-custom-body"></div>';
        cardEl.appendChild(box);
        box.querySelector('.dcard-custom-revert').addEventListener('click', function () {
            revertCard(card);
        });

        renderSpecContent(card, spec, box.querySelector('.dcard-custom-body'));
    }

    // Maxsus ko'rinishni olib tashlab, kartani asl holiga qaytaradi.
    function revertCard(card) {
        var cardEl = document.querySelector('.dash-card[data-card="' + card + '"]');
        if (!cardEl) { return; }
        var ch = charts['custom-' + card];
        if (ch) { try { ch.destroy(); } catch (e) {} delete charts['custom-' + card]; }
        var custom = cardEl.querySelector('.dcard-custom');
        if (custom) { custom.remove(); }
        cardEl.querySelectorAll('.dcard-orig-hidden').forEach(function (el) {
            el.classList.remove('dcard-orig-hidden');
        });
        var toggle = cardEl.querySelector('.dash-toggle');
        if (toggle) { toggle.style.display = ''; }
    }

    // View-spec asosida tarkibni (grafik/jadval/kpi) chizadi.
    function renderSpecContent(card, spec, body) {
        var meta = CARD_META[card];
        var rows = cardRows(card);

        // Asosiy metrikni tekshiramiz — yaroqsiz bo'lsa standartga qaytamiz.
        var metric = (card === 'finance' && (!spec.metric || !(spec.metric in (rows[0] || {}))))
                     ? 'value' : spec.metric;
        if (!rows.length || !(metric in rows[0])) { metric = defaultMetric(card); }

        // Multi-metric: bo'sh yoki yaroqsizlarni tozalaymiz.
        var metrics = Array.isArray(spec.metrics) ? spec.metrics.slice() : [];
        metrics = metrics.filter(function (m) {
            return rows.length && (m in rows[0]);
        });
        if (!metrics.length) { metrics = [metric]; }

        // Saralash
        if (spec.sortBy && rows.length && (spec.sortBy in rows[0])) {
            var dir = spec.sortDir === 'asc' ? 1 : -1;
            rows.sort(function (a, b) {
                return (Number(a[spec.sortBy]) - Number(b[spec.sortBy])) * dir;
            });
        }
        // Limit
        if (spec.limit && spec.limit > 0) { rows = rows.slice(0, spec.limit); }

        var labels = rows.map(function (r) {
            if (card === 'finance') { return r._label; }
            return shortLabel(card, r[meta.cat]);
        });

        var vt = spec.viewType;
        // Asosiy 10 tur — dashboard'ning lokal render funksiyalari (eski path).
        var BASIC_VTS = {
            bar: 1, line: 1, area: 1, pie: 1, doughnut: 1,
            stacked: 1, horizontalBar: 1, table: 1, kpi: 1,
        };

        if (BASIC_VTS[vt]) {
            if (vt === 'table') {
                body.appendChild(buildSpecTable(rows, labels, metrics));
            } else if (vt === 'kpi') {
                var kpiValues = rows.map(function (r) { return Number(r[metric]) || 0; });
                body.appendChild(buildSpecKpi(labels, kpiValues));
            } else {
                var area = document.createElement('div');
                area.className = 'dash-chart-area';
                var canvas = document.createElement('canvas');
                area.appendChild(canvas);
                body.appendChild(area);
                drawSpecChart(card, canvas, vt, labels, rows, metrics);
            }
            return;
        }

        // Kengaytirilgan 43 turidan biri — AIChartRender shared modulga
        // delegate qilamiz. Rows va metrics ni unga mos labels+datasets ga
        // aylantiramiz.
        var sharedSpec = {
            card: card,
            card_label: (meta && meta.label) || (CARD_META[card] && CARD_META[card].cat) || card,
            viewType: vt,
            title: spec.title || '',
            labels: labels,
            datasets: metrics.map(function (m) {
                return {
                    label: metricLabel(m),
                    metric: m,
                    data: rows.map(function (r) { return Number(r[m]) || 0; }),
                };
            }),
            metric: metric,
            metrics: metrics,
            sortBy: spec.sortBy || '',
            sortDir: spec.sortDir || 'desc',
            limit: spec.limit || 0,
        };
        var area2 = document.createElement('div');
        area2.className = 'dash-chart-area';
        area2.style.cssText = 'position:relative;min-height:240px;';
        body.appendChild(area2);
        if (window.AIChartRender && typeof window.AIChartRender.renderInto === 'function') {
            window.AIChartRender.renderInto(area2, sharedSpec);
        } else {
            // Fallback — VIEW_NORMALIZE va eski path
            var normalized = VIEW_NORMALIZE[vt] || 'bar';
            var canvas2 = document.createElement('canvas');
            area2.appendChild(canvas2);
            drawSpecChart(card, canvas2, normalized, labels, rows, metrics);
        }
    }

    function buildSpecTable(rows, labels, metrics) {
        var wrap = document.createElement('div');
        wrap.className = 'dash-table-wrap';
        var head = '<th>Nomi</th>' + metrics.map(function (m) {
            return '<th>' + esc(metricLabel(m)) + '</th>';
        }).join('');
        var bodyRows = rows.map(function (r, i) {
            var cells = metrics.map(function (m) {
                return '<td>' + fmt(r[m]) + '</td>';
            }).join('');
            return '<tr><td class="dt-name">' + esc(labels[i]) + '</td>' + cells + '</tr>';
        }).join('');
        var empty = '<tr><td colspan="' + (metrics.length + 1) +
                    '" class="dash-empty">Ma\'lumot yo\'q</td></tr>';
        wrap.innerHTML = '<table class="dash-table"><thead><tr>' + head +
                         '</tr></thead><tbody>' + (bodyRows || empty) +
                         '</tbody></table>';
        return wrap;
    }

    function buildSpecKpi(labels, values) {
        var box = document.createElement('div');
        box.className = 'dash-finance';
        box.innerHTML = labels.map(function (l, i) {
            return '<div class="dash-fin-box"><div class="dfb-value">' +
                   fmt(values[i]) + '</div><div class="dfb-label">' +
                   esc(l) + '</div></div>';
        }).join('');
        return box;
    }

    // Bitta metrik uchun rang (palitra orqali).
    function metricColor(i) { return PALETTE[i % PALETTE.length]; }

    function drawSpecChart(card, canvas, viewType, labels, rows, metrics) {
        if (typeof Chart === 'undefined') { return; }
        var c = themeColors();
        var multi = metrics.length > 1;
        var cfg;

        // ---- Pie / doughnut — faqat birinchi metric ishlatiladi ----
        if (viewType === 'pie' || viewType === 'doughnut') {
            var m0 = metrics[0];
            var values = rows.map(function (r) { return Number(r[m0]) || 0; });
            var sliceColors = labels.map(function (_, i) {
                return PALETTE[i % PALETTE.length];
            });
            cfg = {
                type: viewType === 'doughnut' ? 'doughnut' : 'pie',
                data: { labels: labels, datasets: [{
                    label: metricLabel(m0), data: values,
                    backgroundColor: sliceColors,
                    borderColor: c.isDark ? '#0a0a1c' : '#ffffff', borderWidth: 2,
                }] },
                options: {
                    responsive: true, maintainAspectRatio: false,
                    plugins: {
                        legend: { position: 'right',
                            labels: { color: c.tick, usePointStyle: true,
                                      font: { family: 'Inter', size: 11 } } },
                        title: { display: !!metricLabel(m0),
                            text: metricLabel(m0), color: c.tick,
                            font: { family: 'Inter', size: 12 } },
                    },
                },
            };
            charts['custom-' + card] = new Chart(canvas, cfg);
            return;
        }

        // ---- Bar / line / area / stacked / horizontalBar ----
        var datasets = metrics.map(function (m, idx) {
            var data = rows.map(function (r) { return Number(r[m]) || 0; });
            var color = metricColor(idx);
            if (viewType === 'line' || viewType === 'area') {
                return {
                    type: 'line', label: metricLabel(m), data: data,
                    borderColor: color,
                    backgroundColor: viewType === 'area'
                        ? hexToRgba(color, 0.18) : color,
                    borderWidth: 2.5, tension: 0.4, pointRadius: 3,
                    fill: viewType === 'area',
                };
            }
            // bar / stacked / horizontalBar — multi bo'lsa har metric o'z rangi
            return {
                type: 'bar', label: metricLabel(m), data: data,
                backgroundColor: multi ? color
                    : labels.map(function (_, i) { return PALETTE[i % PALETTE.length]; }),
                borderRadius: 6,
            };
        });

        var isHoriz = viewType === 'horizontalBar';
        var stacked = viewType === 'stacked';
        var chartType = (viewType === 'line' || viewType === 'area')
                        ? 'line' : 'bar';

        var opts = barLineOptions(c, multi);
        if (isHoriz) { opts.indexAxis = 'y'; }
        if (stacked) {
            opts.scales.x.stacked = true;
            opts.scales.y.stacked = true;
        }

        cfg = { type: chartType, data: { labels: labels, datasets: datasets },
                options: opts };
        charts['custom-' + card] = new Chart(canvas, cfg);
    }

    // #rrggbb -> rgba(...)
    function hexToRgba(hex, alpha) {
        var m = /^#?([0-9a-f]{6})$/i.exec(hex || '');
        if (!m) { return hex; }
        var n = parseInt(m[1], 16);
        var r = (n >> 16) & 255, g = (n >> 8) & 255, b = n & 255;
        return 'rgba(' + r + ',' + g + ',' + b + ',' + alpha + ')';
    }

    function barLineOptions(c, showLegend) {
        return {
            responsive: true, maintainAspectRatio: false,
            plugins: { legend: { display: !!showLegend, position: 'top',
                labels: { color: c.tick, usePointStyle: true,
                          font: { family: 'Inter', size: 11 } } } },
            scales: {
                x: { ticks: { color: c.tick }, grid: { display: false } },
                y: { beginAtZero: true, ticks: { color: c.tick },
                     grid: { color: c.grid } },
            },
        };
    }

    // =========================================================================
    // Dinamik yangilash — AJAX
    // =========================================================================

    // 'all' -> '' (endpoint bo'sh period ni "barchasi" deb tushunadi).
    function apiPeriod() {
        return state.period === 'all' ? '' : state.period;
    }

    // #dash-root ichini API dan kelgan HTML bilan almashtiradi.
    function loadDashboard(opts) {
        opts = opts || {};
        var root = document.getElementById('dash-root');
        if (!root || state.busy) { return; }
        state.busy = true;
        if (!opts.silent) { root.classList.add('dash-loading'); }

        var url = API.data + '?period=' + encodeURIComponent(apiPeriod()) +
                  '&source=' + encodeURIComponent(state.source || '');

        fetch(url, { headers: { 'Accept': 'application/json' } })
            .then(function (r) { return r.json(); })
            .then(function (data) {
                if (data && data.html) {
                    destroyCharts();
                    root.innerHTML = data.html;
                    initDashBody();
                    stampUpdated(data.updated_at);
                }
            })
            .catch(function () { /* tarmoq xatosi — jimgina o'tkazamiz */ })
            .finally(function () {
                state.busy = false;
                root.classList.remove('dash-loading');
            });
    }

    // #dash-root yangilangach ishga tushadigan barcha initlar.
    function initDashBody() {
        initDailyChart();
        initLossBars();
        initCardAI();
        applyHiddenFromStorage();
        rehydrateCustomCards();
    }

    function stampUpdated(time) {
        var el = document.getElementById('dash-updated');
        if (el && time) { el.textContent = '⟳ ' + time; }
    }

    // Maxsus AI ko'rinish yoki ochiq AI panel bo'lsa — avto-yangilashni o'tkazamiz
    // (foydalanuvchining ishini buzmaslik uchun).
    function hasActiveAI() {
        return !!document.querySelector('.dcard-custom') ||
               !!document.querySelector('.dcard-ai:not([hidden])');
    }

    // =========================================================================
    // Global funksiyalar (inline onclick chaqiradi)
    // =========================================================================

    // 'YYYY-MM-DD' -> 'DD.MM' (Oraliq pill yorlig'i uchun).
    function shortDate(iso) {
        var p = (iso || '').split('-');
        return p.length === 3 ? p[2] + '.' + p[1] : iso;
    }

    // Joriy period holatiga ko'ra pillalarni va "Oraliq" pill yorlig'ini yangilaydi.
    function highlightPeriod() {
        var isRange = state.period.indexOf('range:') === 0;
        document.querySelectorAll('#dash-period .dperiod').forEach(function (b) {
            var on = isRange ? (b.dataset.period === 'range')
                             : (b.dataset.period === state.period);
            b.classList.toggle('dperiod-on', on);
        });
        var rb = document.getElementById('dperiod-range-btn');
        if (rb) {
            if (isRange) {
                var pp = state.period.split(':');
                rb.textContent = '📅 ' + shortDate(pp[1]) + '–' + shortDate(pp[2]);
            } else {
                rb.textContent = '📅 Oraliq';
            }
        }
    }

    // URL dagi ?period= ni joriy holat bilan moslaydi (refresh/ulashish uchun).
    function syncPeriodUrl() {
        var url = new URL(window.location.href);
        if (state.period === 'all') { url.searchParams.delete('period'); }
        else { url.searchParams.set('period', state.period); }
        history.replaceState(null, '', url.toString());
    }

    function closeRangePicker() {
        var el = document.getElementById('dash-range');
        if (el) { el.setAttribute('hidden', ''); }
    }

    // Davr (period) tanlovi — AJAX bilan, sahifa qayta yuklanmaydi.
    window.setPeriod = function (p) {
        state.period = p || 'all';
        closeRangePicker();
        highlightPeriod();
        syncPeriodUrl();
        loadDashboard();
    };

    // "Oraliq" pill — sana tanlash panelini ochish/yopish.
    window.toggleRangePicker = function () {
        var el = document.getElementById('dash-range');
        if (!el) { return; }
        if (el.hasAttribute('hidden')) { el.removeAttribute('hidden'); }
        else { el.setAttribute('hidden', ''); }
    };

    // Tanlangan sana oralig'ini qo'llash.
    window.applyRange = function () {
        var fromEl = document.getElementById('range-from');
        var toEl = document.getElementById('range-to');
        var errEl = document.getElementById('range-err');
        var f = fromEl ? fromEl.value : '';
        var t = toEl ? toEl.value : '';

        if (errEl) { errEl.setAttribute('hidden', ''); }
        function showErr(msg) {
            if (errEl) { errEl.textContent = msg; errEl.removeAttribute('hidden'); }
        }
        if (!f || !t) { showErr('Ikkala sanani ham tanlang.'); return; }
        if (f > t) {                       // tartibni to'g'rilaymiz
            var tmp = f; f = t; t = tmp;
            if (fromEl) { fromEl.value = f; }
            if (toEl) { toEl.value = t; }
        }
        state.period = 'range:' + f + ':' + t;
        closeRangePicker();
        highlightPeriod();
        syncPeriodUrl();
        loadDashboard();
    };

    // CRM source — base.html dagi versiyani AJAX variantiga almashtiramiz.
    window.setCrmSource = function (source) {
        source = source || '';
        state.source = source;
        if (source) { localStorage.setItem('crmSource', source); }
        else { localStorage.removeItem('crmSource'); }
        window.__crmSource = source;
        // Topbar CRM tugmalari holatini yangilash
        document.querySelectorAll('.crm-filter-btn').forEach(function (b) {
            b.classList.remove('crm-active');
        });
        if (source === 'amocrm') {
            var a = document.querySelector('.crm-btn-amo');
            if (a) { a.classList.add('crm-active'); }
        } else if (source === 'bitrix') {
            var x = document.querySelector('.crm-btn-btx');
            if (x) { x.classList.add('crm-active'); }
        } else {
            var first = document.querySelector('.crm-filter-btn');
            if (first) { first.classList.add('crm-active'); }
        }
        // URL ni yangilash
        var url = new URL(window.location.href);
        if (source) { url.searchParams.set('source', source); }
        else { url.searchParams.delete('source'); }
        history.replaceState(null, '', url.toString());
        loadDashboard();
    };

    // Manual yangilash tugmasi
    window.refreshDashboard = function () {
        var btn = document.getElementById('dash-refresh');
        if (btn) { btn.classList.add('dash-refresh-spin'); }
        loadDashboard();
        setTimeout(function () {
            if (btn) { btn.classList.remove('dash-refresh-spin'); }
        }, 700);
    };

    // Pastdagi umumiy AI tahlil tugmasi (haftalik hisobot)
    window.runAiAnalysis = function () {
        var btn = document.getElementById('ai-analyze-btn');
        var box = document.getElementById('ai-result');
        if (!btn || !box) { return; }
        btn.disabled = true;
        btn.textContent = 'Tahlil qilinmoqda…';
        box.removeAttribute('hidden');
        box.className = 'dash-ai-result dash-ai-loading';
        box.innerHTML = '<span class="dash-ai-spinner"></span> ' +
                        'AI ma\'lumotlarni tahlil qilmoqda, kuting…';

        var url = API.weekly + (state.source ?
                  '?source=' + encodeURIComponent(state.source) : '');
        fetch(url, { headers: { 'Accept': 'application/json' } })
            .then(function (r) { return r.json(); })
            .then(function (data) {
                var text = data.report || data.error || 'Tahlil natijasi bo\'sh.';
                box.className = 'dash-ai-result';
                box.innerHTML = render(text);
            })
            .catch(function (e) {
                box.className = 'dash-ai-result dash-ai-error';
                box.textContent = 'Xatolik: ' + e;
            })
            .finally(function () {
                btn.disabled = false;
                btn.textContent = 'Qayta tahlil qilish';
            });
    };

    // =========================================================================
    // AI chat widget'dan keladigan buyruqlar (dashboard:command event)
    // =========================================================================

    // Yashirilgan kartalarni qayta yuklashda esda saqlash uchun localStorage.
    var HIDDEN_KEY = 'ai_dash_hidden_cards_v1';

    function getHiddenCards() {
        try { return JSON.parse(localStorage.getItem(HIDDEN_KEY)) || []; }
        catch (e) { return []; }
    }
    function setHiddenCards(arr) {
        try { localStorage.setItem(HIDDEN_KEY, JSON.stringify(arr)); }
        catch (e) {}
    }

    function applyHiddenFromStorage() {
        getHiddenCards().forEach(function (card) {
            var el = document.querySelector('.dash-card[data-card="' + card + '"]');
            if (el) { el.classList.add('dash-card-hidden'); el.style.display = 'none'; }
        });
    }

    // Dashboard renderer faqat asosiy 8 turni biladi. Chat'dan kengaytirilgan
    // 43+ tur kelsa, eng yaqin asosiy turga normallashtiramiz.
    var VIEW_NORMALIZE = {
        // Bar oilasi
        barChart: 'bar', bar: 'bar', columnChart: 'bar', columnBar: 'bar',
        groupedBar: 'bar', stackedBar: 'stacked', stacked: 'stacked',
        horizontalBar: 'horizontalBar', horizontalStackedBar: 'horizontalBar',
        percentBar: 'stacked', rangeBar: 'bar', bulletChart: 'horizontalBar',
        stepBar: 'bar', waterfallBar: 'bar', waterfallChart: 'bar',
        // Line oilasi
        lineChart: 'line', line: 'line', smoothLine: 'line', splineLine: 'line',
        straightLine: 'line', steppedLine: 'line', stepChart: 'line',
        dashedLine: 'line', multiLine: 'line', pointLine: 'line',
        bumpChart: 'line', sparkline: 'line',
        // Area oilasi
        areaChart: 'area', area: 'area', smoothArea: 'area',
        stackedArea: 'area', streamGraph: 'area', streamArea: 'area',
        percentArea: 'area', gradientArea: 'area',
        // Pie / Radial
        pieChart: 'pie', pie: 'pie', doughnutChart: 'doughnut',
        doughnut: 'doughnut', halfPie: 'pie', halfDoughnut: 'doughnut',
        semicircleDoughnut: 'doughnut', gaugeChart: 'doughnut',
        gauge: 'doughnut', polarArea: 'pie', nightingaleRose: 'pie',
        waffleChart: 'pie', sunburst: 'doughnut', marimekko: 'stacked',
        // Distribution
        histogram: 'bar', boxPlot: 'bar', violinPlot: 'bar',
        dotPlot: 'bar', densityChart: 'line',
        // Scatter / Correlation
        scatterPlot: 'bar', scatter: 'bar', bubbleChart: 'bar', bubble: 'bar',
        connectedScatter: 'line', jitterScatter: 'bar', bubbleHeatmap: 'bar',
        heatmap: 'horizontalBar', correlationMatrix: 'horizontalBar',
        // Radar / Spider
        radarChart: 'bar', radar: 'bar', spiderChart: 'bar', spiderWeb: 'bar',
        filledRadar: 'bar', multiRadar: 'bar',
        // Geo (fallback bar)
        choroplethMap: 'horizontalBar', bubbleMap: 'bar',
        flowMap: 'horizontalBar', geoHeatmap: 'horizontalBar',
        // Flow / Hierarchy
        sankeyDiagram: 'horizontalBar', sankey: 'horizontalBar',
        funnelChart: 'horizontalBar', ganttChart: 'horizontalBar',
        gantt: 'horizontalBar', treemap: 'horizontalBar',
        // Network
        networkGraph: 'bar', chordDiagram: 'pie', arcDiagram: 'line',
        // Combo
        barLine: 'bar', areaBar: 'area', dualAxisBar: 'bar',
        comboMultiAxis: 'bar',
        // Display
        kpiCard: 'kpi', kpi: 'kpi', metricTile: 'kpi', numberCards: 'kpi',
        progressBar: 'horizontalBar', table: 'table',
    };

    // Chat'dan kelgan spec'ni applyViewSpec uchun moslaymiz. Endi
    // renderSpecContent AIChartRender'ga delegate qilgani uchun, 43 turning
    // hammasi to'g'ridan-to'g'ri ishlaydi — normalize qilish shart emas.
    function applySpecFromChat(card, spec) {
        if (!spec) { return false; }
        applyViewSpec(card, {
            viewType: spec.viewType || 'bar',
            metric: spec.metric || (spec.metrics && spec.metrics[0]),
            metrics: spec.metrics || [],
            sortBy: spec.sortBy || '',
            sortDir: spec.sortDir || 'desc',
            limit: Number(spec.limit) || 0,
            title: spec.title || '',
            note: '',
        });
        return true;
    }

    // ----- Custom kartalar (chat orqali qo'shilgan) -----
    var CUSTOM_KEY = 'ai_dash_custom_cards_v1';

    function getCustomCards() {
        try { return JSON.parse(localStorage.getItem(CUSTOM_KEY)) || []; }
        catch (e) { return []; }
    }
    function setCustomCards(arr) {
        try { localStorage.setItem(CUSTOM_KEY, JSON.stringify(arr.slice(-30))); }
        catch (e) {}
    }

    function customCardId(card) {
        return 'ai-custom-' + card + '-' + Math.random().toString(36).slice(2, 7);
    }

    function renderCustomCard(item) {
        var host = document.getElementById('ai-custom-cards');
        if (!host) { return; }
        host.removeAttribute('hidden');

        var el = document.createElement('div');
        el.className = 'dash-card dash-card-custom';
        el.dataset.customId = item.id;
        el.innerHTML =
            '<div class="dash-card-head">' +
                '<span class="dch-icon">✨</span>' +
                '<h2 class="dch-title">' + escapeHtml(item.spec.title ||
                    item.spec.card_label || 'Maxsus karta') + '</h2>' +
                '<div class="dch-actions">' +
                    '<button type="button" class="dash-toggle" ' +
                        'data-custom-id="' + item.id + '">✕ O\'chirish</button>' +
                '</div>' +
            '</div>' +
            '<div class="dash-chart-area" style="position:relative;min-height:280px;"></div>';
        host.appendChild(el);

        var area = el.querySelector('.dash-chart-area');
        var btn = el.querySelector('[data-custom-id]');
        btn.addEventListener('click', function () { removeCustomCard(item.id); });

        // Server pre-built labels+datasets bilan spec berib qo'ygan, shuni
        // AIChartRender'ga to'g'ridan-to'g'ri uzatamiz — 43 turning hammasi
        // ishlaydi.
        if (window.AIChartRender && typeof window.AIChartRender.renderInto === 'function') {
            try { window.AIChartRender.renderInto(area, item.spec); }
            catch (e) { area.textContent = 'Grafik xato: ' + e.message; }
        } else {
            var canvas = document.createElement('canvas');
            area.appendChild(canvas);
            renderCustomChart(canvas, item.spec,
                              VIEW_NORMALIZE[item.spec.viewType] || 'bar');
        }
    }

    // Dashboard'da custom karta uchun soddalashtirilgan renderer.
    function renderCustomChart(canvas, spec, normalizedVt) {
        if (typeof Chart === 'undefined') { return; }
        var c = themeColors();
        var labels = spec.labels || [];
        var dss = spec.datasets || [];
        var multi = dss.length > 1;

        if (normalizedVt === 'pie' || normalizedVt === 'doughnut') {
            var first = dss[0] || { data: [] };
            charts['cust-' + spec.card + Math.random()] = new Chart(canvas, {
                type: normalizedVt,
                data: { labels: labels, datasets: [{
                    label: first.label, data: first.data,
                    backgroundColor: labels.map(function (_, i) {
                        return PALETTE[i % PALETTE.length]; }),
                    borderColor: c.isDark ? '#0a0a1c' : '#ffffff', borderWidth: 2,
                }] },
                options: { responsive: true, maintainAspectRatio: false,
                    plugins: { legend: { position: 'right',
                        labels: { color: c.tick, font: { size: 11 } } } } },
            });
            return;
        }

        var datasets = dss.map(function (d, i) {
            var color = PALETTE[i % PALETTE.length];
            if (normalizedVt === 'line' || normalizedVt === 'area') {
                return {
                    type: 'line', label: d.label, data: d.data,
                    borderColor: color,
                    backgroundColor: normalizedVt === 'area'
                        ? hexToRgba(color, 0.18) : color,
                    fill: normalizedVt === 'area', tension: 0.4,
                    borderWidth: 2.5, pointRadius: 3,
                };
            }
            return {
                type: 'bar', label: d.label, data: d.data,
                backgroundColor: multi ? color
                    : labels.map(function (_, k) { return PALETTE[k % PALETTE.length]; }),
                borderRadius: 6,
            };
        });
        var chartType = (normalizedVt === 'line' || normalizedVt === 'area')
                        ? 'line' : 'bar';
        var opts = barLineOptions(c, multi);
        if (normalizedVt === 'horizontalBar') { opts.indexAxis = 'y'; }
        if (normalizedVt === 'stacked') {
            opts.scales.x.stacked = true; opts.scales.y.stacked = true;
        }
        charts['cust-' + spec.card + Math.random()] = new Chart(canvas, {
            type: chartType,
            data: { labels: labels, datasets: datasets },
            options: opts,
        });
    }

    function removeCustomCard(id) {
        setCustomCards(getCustomCards().filter(function (it) { return it.id !== id; }));
        var el = document.querySelector('.dash-card-custom[data-custom-id="' + id + '"]');
        if (el) { el.remove(); }
        var host = document.getElementById('ai-custom-cards');
        if (host && !host.querySelector('.dash-card-custom')) {
            host.setAttribute('hidden', '');
        }
    }

    function removeAllCustomCards() {
        setCustomCards([]);
        var host = document.getElementById('ai-custom-cards');
        if (host) { host.innerHTML = ''; host.setAttribute('hidden', ''); }
    }

    function rehydrateCustomCards() {
        var host = document.getElementById('ai-custom-cards');
        if (!host) { return; }
        host.innerHTML = '';
        var items = getCustomCards();
        if (!items.length) { host.setAttribute('hidden', ''); return; }
        items.forEach(renderCustomCard);
    }

    function escapeHtml(s) {
        var d = document.createElement('div');
        d.textContent = (s == null ? '' : String(s));
        return d.innerHTML;
    }

    function hideAllMainCards() {
        var hidden = [];
        document.querySelectorAll('.dash-card[data-card]').forEach(function (el) {
            var key = el.getAttribute('data-card');
            el.style.display = 'none';
            el.classList.add('dash-card-hidden');
            if (hidden.indexOf(key) === -1) { hidden.push(key); }
        });
        setHiddenCards(hidden);
    }

    function showAllMainCards() {
        document.querySelectorAll('.dash-card[data-card]').forEach(function (el) {
            el.style.display = '';
            el.classList.remove('dash-card-hidden');
        });
        setHiddenCards([]);
    }

    window.addEventListener('dashboard:command', function (evt) {
        var cmd = (evt && evt.detail) || {};
        var action = cmd.action;
        var card = cmd.card;

        if (action === 'hide_card' && card) {
            var el = document.querySelector('.dash-card[data-card="' + card + '"]');
            if (el) { el.style.display = 'none'; el.classList.add('dash-card-hidden'); }
            var hidden = getHiddenCards();
            if (hidden.indexOf(card) === -1) { hidden.push(card); setHiddenCards(hidden); }
            return;
        }
        if (action === 'show_card' && card) {
            var el2 = document.querySelector('.dash-card[data-card="' + card + '"]');
            if (el2) { el2.style.display = ''; el2.classList.remove('dash-card-hidden'); }
            setHiddenCards(getHiddenCards().filter(function (c) { return c !== card; }));
            return;
        }
        if (action === 'set_card_view' && card) {
            applySpecFromChat(card, cmd.spec);
            return;
        }
        if (action === 'add_custom_card' && cmd.spec) {
            var item = { id: customCardId(cmd.card || 'x'), spec: cmd.spec };
            var arr = getCustomCards();
            arr.push(item);
            setCustomCards(arr);
            renderCustomCard(item);
            return;
        }
        if (action === 'remove_custom_card' && card) {
            // card kalit emas, custom_id sifatida ham qabul qilamiz
            var arr2 = getCustomCards().filter(function (it) {
                return it.id !== card && it.spec.card !== card;
            });
            setCustomCards(arr2);
            document.querySelectorAll('.dash-card-custom').forEach(function (el) {
                if (el.dataset.customId === card ||
                    (el.querySelector('.dch-title') &&
                     el.querySelector('.dch-title').textContent.indexOf(card) > -1)) {
                    el.remove();
                }
            });
            return;
        }
        if (action === 'remove_all_custom') { removeAllCustomCards(); return; }
        if (action === 'show_all_cards') { showAllMainCards(); return; }
        if (action === 'hide_all_cards') { hideAllMainCards(); return; }
        if (action === 'refresh_dashboard') { loadDashboard(); return; }
        if (action === 'open_ai_panel' && card) { toggleAiPanel(card); return; }
    });

    // =========================================================================
    // Boshlash
    // =========================================================================

    document.addEventListener('DOMContentLoaded', function () {
        // Boshlang'ich period ni URL dan o'qiymiz.
        var params = new URLSearchParams(window.location.search);
        var p = params.get('period');
        var rangeRe = /^range:\d{4}-\d{2}-\d{2}:\d{4}-\d{2}-\d{2}$/;
        if (p === 'day' || p === 'week' || p === 'month') {
            state.period = p;
        } else if (p && rangeRe.test(p)) {
            // Maxsus sana oralig'i — date inputlarni ham to'ldiramiz.
            state.period = p;
            var pp = p.split(':');
            var rf = document.getElementById('range-from');
            var rt = document.getElementById('range-to');
            if (rf) { rf.value = pp[1]; }
            if (rt) { rt.value = pp[2]; }
        } else {
            state.period = 'all';
        }
        state.source = window.__crmSource || '';
        highlightPeriod();

        // Sana panelidan tashqariga bosilganda uni yopamiz.
        document.addEventListener('click', function (e) {
            var picker = document.getElementById('dash-range');
            var rb = document.getElementById('dperiod-range-btn');
            if (!picker || picker.hasAttribute('hidden')) { return; }
            if (picker.contains(e.target) || (rb && rb.contains(e.target))) { return; }
            picker.setAttribute('hidden', '');
        });

        // Sahifa server tomonidan render qilingan — faqat initlarni ishga tushiramiz.
        initDashBody();

        // Avto-yangilanish — AI panel ochiq bo'lmasa.
        setInterval(function () {
            if (!state.busy && !hasActiveAI() &&
                document.visibilityState === 'visible') {
                loadDashboard({ silent: true });
            }
        }, AUTO_REFRESH_MS);
    });
})();
