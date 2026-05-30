(function () {
    'use strict';

    var API = {
        data:        '/api/v1/dashboard/data/',
        weekly:      '/api/v1/ai/report/weekly/',
        cardAnalyze: '/api/v1/ai/card/analyze/',
        cardRender:  '/api/v1/ai/card/render/',
    };

    var AUTO_REFRESH_MS = 60000;
    var CSRF = (document.querySelector('meta[name="csrf-token"]') || {}).content || '';

    var state = {
        period: 'all',
        source: window.__crmSource || '',
        busy: false,
    };

    var charts = {};

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

    function destroyCharts() {
        Object.keys(charts).forEach(function (k) {
            try { charts[k].destroy(); } catch (e) {  }
        });
        charts = {};
    }

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

    function initCardAI() {
        document.querySelectorAll('.dcard-ai-btn').forEach(function (btn) {
            btn.addEventListener('click', function () {
                toggleAiPanel(btn.dataset.card);
            });
        });
    }

    function toggleAiPanel(card, cardEl) {
        cardEl = cardEl || document.querySelector('.dash-card[data-card="' + card + '"]');
        if (!cardEl) { return; }
        var panel = cardEl.querySelector('.dcard-ai');
        if (panel) {
            if (panel.hasAttribute('hidden')) { panel.removeAttribute('hidden'); }
            else { panel.setAttribute('hidden', ''); }
            return;
        }
        panel = buildAiPanel(card);
        var head = cardEl.querySelector('.dash-card-head');
        head.insertAdjacentElement('afterend', panel);
    }

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

        panel.querySelectorAll('.dca-go').forEach(function (go) {
            go.addEventListener('click', function () {
                if (go.dataset.act === 'analyze') { runCardAnalyze(card, panel, go); }
                else { runCardRender(card, panel, go); }
            });
        });
        var input = panel.querySelector('.dca-input');
        input.addEventListener('keydown', function (e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                runCardRender(card, panel, panel.querySelector('.dca-go[data-act="render"]'));
            }
        });
        return panel;
    }

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

    function shortLabel(card, val) {
        if (card === 'daily' && /^\d{4}-\d{2}-\d{2}$/.test(val)) {
            var p = val.split('-');
            return p[2] + '.' + p[1];
        }
        return val;
    }

    function applyViewSpec(card, spec) {
        var customArr = getCustomCards();
        var existingCustom = customArr.find(function (it) {
            return it.spec && it.spec.card === card;
        });
        if (existingCustom) {
            var merged = Object.assign({}, existingCustom.spec, spec || {});
            merged.card = card;
            if (!spec || !spec.labels) { merged.labels = existingCustom.spec.labels; }
            if (!spec || !spec.datasets) { merged.datasets = existingCustom.spec.datasets; }
            existingCustom.spec = merged;
            setCustomCards(customArr);
            var oldEl = document.querySelector(
                '.dash-card-custom[data-custom-id="' + existingCustom.id + '"]');
            if (oldEl) { oldEl.remove(); }
            renderCustomCard(existingCustom);
            return;
        }
        var cardEl = document.querySelector('.dash-card[data-card="' + card + '"]');
        if (!cardEl) { return; }
        revertCard(card);

        Array.prototype.forEach.call(cardEl.children, function (ch) {
            if (ch.classList.contains('dash-card-head') ||
                ch.classList.contains('dcard-ai')) { return; }
            ch.classList.add('dcard-orig-hidden');
        });
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

    function renderSpecContent(card, spec, body) {
        var meta = CARD_META[card];
        var rows = cardRows(card);

        var metric = (card === 'finance' && (!spec.metric || !(spec.metric in (rows[0] || {}))))
                     ? 'value' : spec.metric;
        if (!rows.length || !(metric in rows[0])) { metric = defaultMetric(card); }

        var metrics = Array.isArray(spec.metrics) ? spec.metrics.slice() : [];
        metrics = metrics.filter(function (m) {
            return rows.length && (m in rows[0]);
        });
        if (!metrics.length) { metrics = [metric]; }

        if (spec.sortBy && rows.length && (spec.sortBy in rows[0])) {
            var dir = spec.sortDir === 'asc' ? 1 : -1;
            rows.sort(function (a, b) {
                return (Number(a[spec.sortBy]) - Number(b[spec.sortBy])) * dir;
            });
        }
        if (spec.limit && spec.limit > 0) { rows = rows.slice(0, spec.limit); }

        var labels = rows.map(function (r) {
            if (card === 'finance') { return r._label; }
            return shortLabel(card, r[meta.cat]);
        });

        var vt = spec.viewType;
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

    function metricColor(i) { return PALETTE[i % PALETTE.length]; }

    function drawSpecChart(card, canvas, viewType, labels, rows, metrics) {
        if (typeof Chart === 'undefined') { return; }
        var c = themeColors();
        var multi = metrics.length > 1;
        var cfg;

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

    function apiPeriod() {
        return state.period === 'all' ? '' : state.period;
    }

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
            .catch(function () {  })
            .finally(function () {
                state.busy = false;
                root.classList.remove('dash-loading');
            });
    }

    function initDashBody() {
        initDailyChart();
        initLossBars();
        initCardAI();
        applyHiddenFromStorage();
        rehydrateCustomCards();
        applyCardOrder();
        initDragAndDrop();
    }

    function stampUpdated(time) {
        var el = document.getElementById('dash-updated');
        if (el && time) { el.textContent = '⟳ ' + time; }
    }

    function hasActiveAI() {
        return !!document.querySelector('.dcard-custom') ||
               !!document.querySelector('.dcard-ai:not([hidden])');
    }

    function shortDate(iso) {
        var p = (iso || '').split('-');
        return p.length === 3 ? p[2] + '.' + p[1] : iso;
    }

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

    window.setPeriod = function (p) {
        state.period = p || 'all';
        closeRangePicker();
        highlightPeriod();
        syncPeriodUrl();
        loadDashboard();
    };

    window.toggleRangePicker = function () {
        var el = document.getElementById('dash-range');
        if (!el) { return; }
        if (el.hasAttribute('hidden')) { el.removeAttribute('hidden'); }
        else { el.setAttribute('hidden', ''); }
    };

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
        if (f > t) {
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

    window.setCrmSource = function (source) {
        source = source || '';
        state.source = source;
        if (source) { localStorage.setItem('crmSource', source); }
        else { localStorage.removeItem('crmSource'); }
        window.__crmSource = source;
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
        var url = new URL(window.location.href);
        if (source) { url.searchParams.set('source', source); }
        else { url.searchParams.delete('source'); }
        history.replaceState(null, '', url.toString());
        loadDashboard();
    };

    window.refreshDashboard = function () {
        var btn = document.getElementById('dash-refresh');
        if (btn) { btn.classList.add('dash-refresh-spin'); }
        loadDashboard();
        setTimeout(function () {
            if (btn) { btn.classList.remove('dash-refresh-spin'); }
        }, 700);
    };

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
        var rowsToReflow = [];
        getHiddenCards().forEach(function (card) {
            var el = document.querySelector('.dash-card[data-card="' + card + '"]');
            if (el) {
                el.classList.add('dash-card-hidden');
                el.style.display = 'none';
                var row = el.parentElement;
                if (row && rowsToReflow.indexOf(row) === -1) { rowsToReflow.push(row); }
            }
        });
        rowsToReflow.forEach(reflowRow);
    }

    function reflowRow(rowEl) {
        if (!rowEl || !rowEl.classList || !rowEl.classList.contains('dash-row')) { return; }
        var cards = rowEl.querySelectorAll(':scope > .dash-card[data-card]');
        if (!cards.length) { return; }
        var visible = 0;
        cards.forEach(function (c) {
            if (!c.classList.contains('dash-card-hidden') && c.style.display !== 'none') {
                visible++;
            }
        });
        if (visible === 0) {
            rowEl.style.display = 'none';
            rowEl.style.gridTemplateColumns = '';
        } else if (visible === cards.length) {
            rowEl.style.display = '';
            rowEl.style.gridTemplateColumns = '';
        } else {
            rowEl.style.display = '';
            rowEl.style.gridTemplateColumns = 'repeat(' + visible + ', 1fr)';
        }
    }

    var VIEW_NORMALIZE = {
        barChart: 'bar', bar: 'bar', columnChart: 'bar', columnBar: 'bar',
        groupedBar: 'bar', stackedBar: 'stacked', stacked: 'stacked',
        horizontalBar: 'horizontalBar', horizontalStackedBar: 'horizontalBar',
        percentBar: 'stacked', rangeBar: 'bar', bulletChart: 'horizontalBar',
        stepBar: 'bar', waterfallBar: 'bar', waterfallChart: 'bar',
        lineChart: 'line', line: 'line', smoothLine: 'line', splineLine: 'line',
        straightLine: 'line', steppedLine: 'line', stepChart: 'line',
        dashedLine: 'line', multiLine: 'line', pointLine: 'line',
        bumpChart: 'line', sparkline: 'line',
        areaChart: 'area', area: 'area', smoothArea: 'area',
        stackedArea: 'area', streamGraph: 'area', streamArea: 'area',
        percentArea: 'area', gradientArea: 'area',
        pieChart: 'pie', pie: 'pie', doughnutChart: 'doughnut',
        doughnut: 'doughnut', halfPie: 'pie', halfDoughnut: 'doughnut',
        semicircleDoughnut: 'doughnut', gaugeChart: 'doughnut',
        gauge: 'doughnut', polarArea: 'pie', nightingaleRose: 'pie',
        waffleChart: 'pie', sunburst: 'doughnut', marimekko: 'stacked',
        histogram: 'bar', boxPlot: 'bar', violinPlot: 'bar',
        dotPlot: 'bar', densityChart: 'line',
        scatterPlot: 'bar', scatter: 'bar', bubbleChart: 'bar', bubble: 'bar',
        connectedScatter: 'line', jitterScatter: 'bar', bubbleHeatmap: 'bar',
        heatmap: 'horizontalBar', correlationMatrix: 'horizontalBar',
        radarChart: 'bar', radar: 'bar', spiderChart: 'bar', spiderWeb: 'bar',
        filledRadar: 'bar', multiRadar: 'bar',
        choroplethMap: 'horizontalBar', bubbleMap: 'bar',
        flowMap: 'horizontalBar', geoHeatmap: 'horizontalBar',
        sankeyDiagram: 'horizontalBar', sankey: 'horizontalBar',
        funnelChart: 'horizontalBar', ganttChart: 'horizontalBar',
        gantt: 'horizontalBar', treemap: 'horizontalBar',
        networkGraph: 'bar', chordDiagram: 'pie', arcDiagram: 'line',
        barLine: 'bar', areaBar: 'area', dualAxisBar: 'bar',
        comboMultiAxis: 'bar',
        kpiCard: 'kpi', kpi: 'kpi', metricTile: 'kpi', numberCards: 'kpi',
        progressBar: 'horizontalBar', table: 'table',
    };

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
        var host = document.getElementById('dash-grid');
        if (!host) { return; }

        var cardTitle = item.spec.title || item.spec.card_label || 'Maxsus karta';
        var el = document.createElement('div');
        el.className = 'dash-card dash-card-custom';
        el.dataset.customId = item.id;
        el.dataset.baseCard = item.spec.card || '';
        el.setAttribute('data-w', '1');
        el.innerHTML =
            '<div class="dash-card-head">' +
                '<span class="dcard-drag-handle" title="Ko\'chirish uchun ushlab tashlang">⋮⋮</span>' +
                '<span class="dch-icon">✨</span>' +
                '<h2 class="dch-title">' + escapeHtml(cardTitle) + '</h2>' +
                '<div class="dch-actions">' +
                    '<button type="button" class="dcard-ai-btn" ' +
                        'title="AI tahlil va ko\'rinish">🤖 AI</button>' +
                    '<button type="button" class="dcard-del-btn" ' +
                        'title="Kartani o\'chirish">✖</button>' +
                '</div>' +
            '</div>' +
            '<div class="dash-chart-area" style="position:relative;min-height:280px;"></div>';
        host.appendChild(el);
        attachDragHandlers(el);
        updateCustomLayoutClass();

        var area = el.querySelector('.dash-chart-area');
        var aiBtn = el.querySelector('.dcard-ai-btn');
        var delBtn = el.querySelector('.dcard-del-btn');
        var baseCard = item.spec.card || item.id;
        aiBtn.addEventListener('click', function () {
            toggleAiPanel(baseCard, el);
        });
        delBtn.addEventListener('click', function () {
            removeCustomCard(item.id);
        });

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
        updateCustomLayoutClass();
        saveCardOrder();
    }

    function removeAllCustomCards() {
        setCustomCards([]);
        document.querySelectorAll('.dash-card-custom').forEach(function (el) {
            el.remove();
        });
        updateCustomLayoutClass();
        saveCardOrder();
    }

    function updateCustomLayoutClass() {
        var host = document.getElementById('dash-grid');
        if (!host) { return; }
        var customs = host.querySelectorAll('.dash-card-custom');
        host.classList.toggle('has-single-custom', customs.length === 1);
    }

    var ORDER_KEY = 'ai_dash_card_order_v1';

    function cardKey(el) {
        if (!el) { return null; }
        if (el.dataset.customId) { return 'c:' + el.dataset.customId; }
        if (el.dataset.card) { return 'd:' + el.dataset.card; }
        return null;
    }

    function getSavedOrder() {
        try { return JSON.parse(localStorage.getItem(ORDER_KEY)) || []; }
        catch (e) { return []; }
    }

    function saveCardOrder() {
        var host = document.getElementById('dash-grid');
        if (!host) { return; }
        var keys = [];
        host.querySelectorAll(':scope > .dash-card').forEach(function (el) {
            var k = cardKey(el);
            if (k) { keys.push(k); }
        });
        try { localStorage.setItem(ORDER_KEY, JSON.stringify(keys)); }
        catch (e) {}
    }

    function applyCardOrder() {
        var host = document.getElementById('dash-grid');
        if (!host) { return; }
        var saved = getSavedOrder();
        if (!saved.length) { return; }
        var byKey = {};
        host.querySelectorAll(':scope > .dash-card').forEach(function (el) {
            var k = cardKey(el);
            if (k) { byKey[k] = el; }
        });
        saved.forEach(function (k) {
            if (byKey[k]) {
                host.appendChild(byKey[k]);
                delete byKey[k];
            }
        });
    }

    var DRAG = { src: null };

    function ensureDragHandle(cardEl) {
        var head = cardEl.querySelector(':scope > .dash-card-head');
        if (!head) { return; }
        if (head.querySelector('.dcard-drag-handle')) { return; }
        var handle = document.createElement('span');
        handle.className = 'dcard-drag-handle';
        handle.title = 'Ko\'chirish uchun ushlab tashlang';
        handle.textContent = '⋮⋮';
        head.insertBefore(handle, head.firstChild);
    }

    function attachDragHandlers(cardEl) {
        if (!cardEl || cardEl.dataset.dragBound === '1') { return; }
        cardEl.dataset.dragBound = '1';
        cardEl.setAttribute('draggable', 'true');

        cardEl.addEventListener('dragstart', function (e) {
            var t = e.target;
            if (t && t !== cardEl && t.closest &&
                t.closest('button, input, select, textarea, a, table, canvas, .dcard-ai, .dash-toggle')) {
                e.preventDefault();
                return;
            }
            DRAG.src = cardEl;
            cardEl.classList.add('is-dragging');
            var host = document.getElementById('dash-grid');
            if (host) { host.classList.add('is-drag-mode'); }
            try {
                e.dataTransfer.effectAllowed = 'move';
                e.dataTransfer.setData('text/plain', cardKey(cardEl) || '');
            } catch (err) {}
        });

        cardEl.addEventListener('dragend', function () {
            cardEl.classList.remove('is-dragging');
            document.querySelectorAll('.dash-card.drop-target').forEach(function (el) {
                el.classList.remove('drop-target');
            });
            var host = document.getElementById('dash-grid');
            if (host) { host.classList.remove('is-drag-mode'); }
            DRAG.src = null;
            saveCardOrder();
        });

        cardEl.addEventListener('dragover', function (e) {
            if (!DRAG.src || DRAG.src === cardEl) { return; }
            e.preventDefault();
            try { e.dataTransfer.dropEffect = 'move'; } catch (err) {}
            cardEl.classList.add('drop-target');
        });

        cardEl.addEventListener('dragleave', function (e) {
            if (e.relatedTarget && cardEl.contains(e.relatedTarget)) { return; }
            cardEl.classList.remove('drop-target');
        });

        cardEl.addEventListener('drop', function (e) {
            if (!DRAG.src || DRAG.src === cardEl) { return; }
            e.preventDefault();
            cardEl.classList.remove('drop-target');
            var host = document.getElementById('dash-grid');
            if (!host) { return; }
            var rect = cardEl.getBoundingClientRect();
            var after = (e.clientY - rect.top) > rect.height / 2 ||
                        (e.clientX - rect.left) > rect.width / 2;
            if (after && cardEl.nextSibling) {
                host.insertBefore(DRAG.src, cardEl.nextSibling);
            } else if (after) {
                host.appendChild(DRAG.src);
            } else {
                host.insertBefore(DRAG.src, cardEl);
            }
        });
    }

    function initDragAndDrop() {
        var host = document.getElementById('dash-grid');
        if (!host) { return; }
        host.querySelectorAll(':scope > .dash-card').forEach(function (el) {
            ensureDragHandle(el);
            attachDragHandlers(el);
        });
    }

    function rebuildCustomSpec(item) {
        if (!item || !item.spec) { return item; }
        var card = item.spec.card;
        var meta = card && CARD_META[card];
        if (!meta) { return item; }
        var rows = cardRows(card);
        if (!rows.length) { return item; }

        var spec = item.spec;
        var first = rows[0];
        var metric = spec.metric;
        if (card === 'finance' && (!metric || !(metric in first))) { metric = 'value'; }
        if (!metric || !(metric in first)) { metric = defaultMetric(card); }

        var metrics = Array.isArray(spec.metrics) ? spec.metrics.slice() : [];
        metrics = metrics.filter(function (m) { return (m in first); });
        if (!metrics.length) { metrics = [metric]; }

        if (spec.sortBy && (spec.sortBy in first)) {
            var dir = spec.sortDir === 'asc' ? 1 : -1;
            rows.sort(function (a, b) {
                return (Number(a[spec.sortBy]) - Number(b[spec.sortBy])) * dir;
            });
        }
        if (spec.limit && spec.limit > 0) { rows = rows.slice(0, spec.limit); }

        var labels = rows.map(function (r) {
            if (card === 'finance') { return r._label; }
            return shortLabel(card, r[meta.cat]);
        });

        var newSpec = Object.assign({}, spec, {
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
        });
        return Object.assign({}, item, { spec: newSpec });
    }

    function rehydrateCustomCards() {
        var host = document.getElementById('dash-grid');
        if (!host) { return; }
        host.querySelectorAll('.dash-card-custom').forEach(function (el) {
            el.remove();
        });
        var items = getCustomCards();
        if (!items.length) { updateCustomLayoutClass(); return; }
        var refreshed = items.map(rebuildCustomSpec);
        setCustomCards(refreshed);
        refreshed.forEach(renderCustomCard);
    }

    function escapeHtml(s) {
        var d = document.createElement('div');
        d.textContent = (s == null ? '' : String(s));
        return d.innerHTML;
    }

    function hideAllMainCards() {
        var hidden = [];
        var rows = [];
        document.querySelectorAll('.dash-card[data-card]').forEach(function (el) {
            var key = el.getAttribute('data-card');
            el.style.display = 'none';
            el.classList.add('dash-card-hidden');
            if (hidden.indexOf(key) === -1) { hidden.push(key); }
            if (el.parentElement && rows.indexOf(el.parentElement) === -1) {
                rows.push(el.parentElement);
            }
        });
        setHiddenCards(hidden);
        rows.forEach(reflowRow);
    }

    function showAllMainCards() {
        var rows = [];
        document.querySelectorAll('.dash-card[data-card]').forEach(function (el) {
            el.style.display = '';
            el.classList.remove('dash-card-hidden');
            if (el.parentElement && rows.indexOf(el.parentElement) === -1) {
                rows.push(el.parentElement);
            }
        });
        setHiddenCards([]);
        rows.forEach(reflowRow);
    }

    window.addEventListener('dashboard:command', function (evt) {
        var cmd = (evt && evt.detail) || {};
        var action = cmd.action;
        var card = cmd.card;

        if (action === 'hide_card' && card) {
            var el = document.querySelector('.dash-card[data-card="' + card + '"]');
            if (el) {
                el.style.display = 'none';
                el.classList.add('dash-card-hidden');
                reflowRow(el.parentElement);
            }
            var hidden = getHiddenCards();
            if (hidden.indexOf(card) === -1) { hidden.push(card); setHiddenCards(hidden); }
            return;
        }
        if (action === 'show_card' && card) {
            var el2 = document.querySelector('.dash-card[data-card="' + card + '"]');
            if (el2) {
                el2.style.display = '';
                el2.classList.remove('dash-card-hidden');
                reflowRow(el2.parentElement);
            }
            setHiddenCards(getHiddenCards().filter(function (c) { return c !== card; }));
            return;
        }
        if (action === 'set_card_view' && card) {
            applySpecFromChat(card, cmd.spec);
            return;
        }
        if (action === 'add_custom_card' && cmd.spec) {
            var baseCard = cmd.card || cmd.spec.card || '';
            var item = { id: customCardId(baseCard || 'x'), spec: cmd.spec };
            var arr = getCustomCards();
            arr.push(item);
            setCustomCards(arr);
            renderCustomCard(item);
            saveCardOrder();
            return;
        }
        if (action === 'remove_custom_card' && card) {
            var arr2 = getCustomCards().filter(function (it) {
                return it.id !== card && it.spec.card !== card;
            });
            setCustomCards(arr2);
            document.querySelectorAll('.dash-card-custom').forEach(function (el) {
                if (el.dataset.customId === card ||
                    el.dataset.baseCard === card ||
                    (el.querySelector('.dch-title') &&
                     el.querySelector('.dch-title').textContent.indexOf(card) > -1)) {
                    el.remove();
                }
            });
            updateCustomLayoutClass();
            saveCardOrder();
            return;
        }
        if (action === 'remove_all_custom') { removeAllCustomCards(); return; }
        if (action === 'show_all_cards') { showAllMainCards(); return; }
        if (action === 'hide_all_cards') { hideAllMainCards(); return; }
        if (action === 'refresh_dashboard') { loadDashboard(); return; }
        if (action === 'open_ai_panel' && card) { toggleAiPanel(card); return; }
        if (action === 'set_period') {
            var p = (cmd.period || '').trim();
            if (typeof window.setPeriod === 'function') {
                window.setPeriod(p || 'all');
                if (typeof highlightPeriod === 'function') {
                    try { highlightPeriod(); } catch (e) {}
                }
            }
            return;
        }
        if (action === 'set_source') {
            var sv = (cmd.source || '').trim();
            if (typeof window.setCrmSource === 'function') {
                window.setCrmSource(sv);
            }
            return;
        }
    });

    document.addEventListener('DOMContentLoaded', function () {
        var params = new URLSearchParams(window.location.search);
        var p = params.get('period');
        var rangeRe = /^range:\d{4}-\d{2}-\d{2}:\d{4}-\d{2}-\d{2}$/;
        if (p === 'day' || p === 'week' || p === 'month') {
            state.period = p;
        } else if (p && rangeRe.test(p)) {
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

        document.addEventListener('click', function (e) {
            var picker = document.getElementById('dash-range');
            var rb = document.getElementById('dperiod-range-btn');
            if (!picker || picker.hasAttribute('hidden')) { return; }
            if (picker.contains(e.target) || (rb && rb.contains(e.target))) { return; }
            picker.setAttribute('hidden', '');
        });

        initDashBody();

        setInterval(function () {
            if (!state.busy && !hasActiveAI() &&
                document.visibilityState === 'visible') {
                loadDashboard({ silent: true });
            }
        }, AUTO_REFRESH_MS);
    });
})();
