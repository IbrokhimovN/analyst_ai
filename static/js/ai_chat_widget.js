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

    // Chart.js uchun palitra (dashboard bilan bir xil).
    var CHART_PALETTE = ['#3b82f6', '#22c55e', '#f59e0b', '#ef4444', '#8b5cf6',
                         '#06b6d4', '#ec4899', '#14b8a6', '#f97316', '#a855f7'];

    function hexToRgba(hex, alpha) {
        var m = /^#?([0-9a-f]{6})$/i.exec(hex || '');
        if (!m) { return hex; }
        var n = parseInt(m[1], 16);
        var r = (n >> 16) & 255, g = (n >> 8) & 255, b = n & 255;
        return 'rgba(' + r + ',' + g + ',' + b + ',' + alpha + ')';
    }

    // Chart.js bilan native qo'llab-quvvatlanmaydigan turlar uchun fallback —
    // odatda eng yaqin native turga moslab beradi.
    var CHART_TYPE_MAP = {
        // ----- bar family -----
        bar: { base: 'bar' },
        columnBar: { base: 'bar' },
        groupedBar: { base: 'bar' },
        horizontalBar: { base: 'bar', indexAxis: 'y' },
        stackedBar: { base: 'bar', stacked: true },
        stacked: { base: 'bar', stacked: true },
        horizontalStackedBar: { base: 'bar', stacked: true, indexAxis: 'y' },
        percentBar: { base: 'bar', stacked: true, percent: true },
        stepBar: { base: 'bar', step: true },
        rangeBar: { base: 'bar', range: true },
        waterfallBar: { base: 'bar', waterfall: true },
        // ----- line family -----
        line: { base: 'line' },
        splineLine: { base: 'line', tension: 0.4 },
        smoothLine: { base: 'line', tension: 0.4 },
        straightLine: { base: 'line', tension: 0 },
        steppedLine: { base: 'line', stepped: true },
        dashedLine: { base: 'line', dashed: true },
        multiLine: { base: 'line' },
        pointLine: { base: 'line', showLine: false, pointRadius: 4 },
        // ----- area family -----
        area: { base: 'line', fill: true, tension: 0.4 },
        smoothArea: { base: 'line', fill: true, tension: 0.5 },
        stackedArea: { base: 'line', fill: true, stacked: true, tension: 0.3 },
        streamArea: { base: 'line', fill: true, stacked: true, tension: 0.5 },
        percentArea: { base: 'line', fill: true, stacked: true,
                        percent: true, tension: 0.3 },
        gradientArea: { base: 'line', fill: true, tension: 0.4, gradient: true },
        // ----- pie family -----
        pie: { base: 'pie' },
        doughnut: { base: 'doughnut' },
        halfPie: { base: 'pie', half: true },
        halfDoughnut: { base: 'doughnut', half: true },
        semicircleDoughnut: { base: 'doughnut', half: true, rotation: 270 },
        gauge: { base: 'doughnut', half: true, rotation: 270, cutout: '70%' },
        polarArea: { base: 'polarArea' },
        nightingaleRose: { base: 'polarArea' },
        // ----- radar -----
        radar: { base: 'radar' },
        filledRadar: { base: 'radar', fill: true },
        multiRadar: { base: 'radar' },
        spiderWeb: { base: 'radar' },
        // ----- scatter / bubble -----
        scatter: { base: 'scatter' },
        bubble: { base: 'bubble' },
        connectedScatter: { base: 'scatter', showLine: true },
        jitterScatter: { base: 'scatter', jitter: true },
        bubbleHeatmap: { base: 'bubble' },
        // ----- combo -----
        barLine: { base: 'bar', combo: 'bar+line' },
        areaBar: { base: 'bar', combo: 'bar+area' },
        dualAxisBar: { base: 'bar', dualAxis: true },
        comboMultiAxis: { base: 'bar', combo: 'bar+line', dualAxis: true },
        // ----- special (fallbacks) -----
        heatmap: { base: 'bar', heatmap: true, indexAxis: 'y' },
        funnelChart: { base: 'bar', funnel: true, indexAxis: 'y' },
        treemap: { base: 'bar', treemapFallback: true, indexAxis: 'y' },
        sankey: { base: 'bar', sankeyFallback: true, indexAxis: 'y' },
        gantt: { base: 'bar', range: true, indexAxis: 'y' },
    };

    // Numeric arrayni 100% normalizatsiya qiladi (percent stacked uchun).
    function toPercentDatasets(datasets) {
        var totals = [];
        (datasets[0] && datasets[0].data || []).forEach(function (_, i) {
            var sum = 0;
            datasets.forEach(function (d) { sum += Number(d.data[i]) || 0; });
            totals.push(sum || 1);
        });
        return datasets.map(function (d) {
            return Object.assign({}, d, {
                data: d.data.map(function (v, i) {
                    return totals[i] ? (Number(v) / totals[i]) * 100 : 0;
                }),
            });
        });
    }

    function makeGradient(ctx, color) {
        try {
            var g = ctx.createLinearGradient(0, 0, 0, ctx.canvas.height || 200);
            g.addColorStop(0, hexToRgba(color, 0.45));
            g.addColorStop(1, hexToRgba(color, 0.02));
            return g;
        } catch (e) { return hexToRgba(color, 0.18); }
    }

    // Server spec -> Chart.js config.
    function buildChartConfig(spec, canvas) {
        var vt = spec.viewType || 'bar';
        var def = CHART_TYPE_MAP[vt] || { base: 'bar' };
        var base = def.base;
        var labels = spec.labels || [];
        var dss = (spec.datasets || []).slice();
        var multi = dss.length > 1;
        var tickColor = '#94a3b8';
        var gridColor = 'rgba(255,255,255,0.08)';

        // Pie/Doughnut/PolarArea — faqat bitta dataset, ko'p rang.
        if (base === 'pie' || base === 'doughnut' || base === 'polarArea') {
            var first = dss[0] || { data: [], label: '' };
            var data = first.data || [];
            var cfg = {
                type: base,
                data: {
                    labels: labels,
                    datasets: [{
                        label: first.label,
                        data: data,
                        backgroundColor: labels.map(function (_, i) {
                            return CHART_PALETTE[i % CHART_PALETTE.length];
                        }),
                        borderColor: '#0F172A',
                        borderWidth: 2,
                    }],
                },
                options: {
                    responsive: true, maintainAspectRatio: false,
                    plugins: {
                        legend: { position: 'right',
                            labels: { color: tickColor, usePointStyle: true,
                                      font: { size: 11 } } },
                    },
                },
            };
            if (def.half) {
                cfg.options.circumference = 180;
                if (def.rotation != null) { cfg.options.rotation = def.rotation; }
                else { cfg.options.rotation = -90; }
            }
            if (def.cutout) { cfg.options.cutout = def.cutout; }
            return cfg;
        }

        // Radar — bir nechta dataset bo'lishi mumkin, har biri o'z rangi.
        if (base === 'radar') {
            var rds = dss.map(function (d, idx) {
                var color = CHART_PALETTE[idx % CHART_PALETTE.length];
                return {
                    label: d.label, data: d.data,
                    borderColor: color,
                    backgroundColor: def.fill ? hexToRgba(color, 0.2) : 'transparent',
                    pointBackgroundColor: color, borderWidth: 2,
                    fill: !!def.fill,
                };
            });
            return {
                type: 'radar',
                data: { labels: labels, datasets: rds },
                options: {
                    responsive: true, maintainAspectRatio: false,
                    plugins: { legend: { display: multi, labels: { color: tickColor } } },
                    scales: { r: {
                        ticks: { color: tickColor, backdropColor: 'transparent' },
                        grid: { color: gridColor },
                        angleLines: { color: gridColor },
                        pointLabels: { color: tickColor, font: { size: 11 } },
                    } },
                },
            };
        }

        // Scatter / Bubble — data {x,y} formatida.
        if (base === 'scatter' || base === 'bubble') {
            var sds = dss.map(function (d, idx) {
                var color = CHART_PALETTE[idx % CHART_PALETTE.length];
                var jitter = def.jitter ? (Math.random() - 0.5) * 0.4 : 0;
                var pts = d.data.map(function (v, i) {
                    if (base === 'bubble') {
                        return { x: i + 1 + jitter, y: Number(v) || 0,
                                 r: Math.max(4, Math.min(20, Math.sqrt(Math.abs(v) || 1))) };
                    }
                    return { x: i + 1 + jitter, y: Number(v) || 0 };
                });
                return {
                    label: d.label, data: pts,
                    backgroundColor: hexToRgba(color, 0.6),
                    borderColor: color, showLine: !!def.showLine,
                    borderWidth: 2, pointRadius: base === 'bubble' ? undefined : 5,
                };
            });
            return {
                type: base,
                data: { datasets: sds },
                options: {
                    responsive: true, maintainAspectRatio: false,
                    plugins: { legend: { display: multi, labels: { color: tickColor } } },
                    scales: {
                        x: { ticks: { color: tickColor }, grid: { color: gridColor } },
                        y: { ticks: { color: tickColor }, grid: { color: gridColor },
                             beginAtZero: true },
                    },
                },
            };
        }

        // Percent stacked uchun ma'lumotni normallashtiramiz.
        if (def.percent && dss.length > 1) { dss = toPercentDatasets(dss); }

        // Bar / Line / Area asoslari.
        var ctx2d = canvas && canvas.getContext ? canvas.getContext('2d') : null;
        var datasets = dss.map(function (d, idx) {
            var color = CHART_PALETTE[idx % CHART_PALETTE.length];
            var isLine = base === 'line';
            var ds = {
                type: isLine ? 'line' : 'bar',
                label: d.label,
                data: d.data,
                borderColor: color,
                borderWidth: isLine ? 2.5 : 0,
                borderRadius: isLine ? 0 : 6,
                tension: def.tension != null ? def.tension : (isLine ? 0.4 : 0),
                pointRadius: def.pointRadius != null ? def.pointRadius : 3,
                fill: !!def.fill,
            };
            if (def.showLine === false) { ds.showLine = false; }
            if (def.stepped) { ds.stepped = true; }
            if (def.dashed) { ds.borderDash = [6, 4]; }
            if (def.gradient && ctx2d) {
                ds.backgroundColor = makeGradient(ctx2d, color);
            } else if (def.fill) {
                ds.backgroundColor = hexToRgba(color, 0.22);
            } else {
                ds.backgroundColor = isLine ? color
                    : (multi ? color
                        : labels.map(function (_, i) {
                            return CHART_PALETTE[i % CHART_PALETTE.length];
                          }));
            }
            // Combo: ikkinchi datasetni line qilamiz.
            if (def.combo === 'bar+line' && idx === 1) {
                ds.type = 'line'; ds.fill = false;
                ds.backgroundColor = color; ds.borderColor = color;
                ds.borderWidth = 2.5; ds.tension = 0.4; ds.pointRadius = 3;
            }
            if (def.combo === 'bar+area' && idx === 1) {
                ds.type = 'line'; ds.fill = true;
                ds.backgroundColor = hexToRgba(color, 0.25);
                ds.borderColor = color; ds.borderWidth = 2; ds.tension = 0.4;
            }
            if (def.dualAxis && idx > 0) { ds.yAxisID = 'y1'; }
            // Funnel / heatmap / waterfall — vizual fallback: rang gradatsiyasi.
            if (def.funnel || def.heatmap || def.treemapFallback ||
                def.sankeyFallback) {
                var max = Math.max.apply(null, d.data.map(function (v) {
                    return Number(v) || 0; })) || 1;
                ds.backgroundColor = d.data.map(function (v) {
                    var a = 0.25 + 0.7 * ((Number(v) || 0) / max);
                    return hexToRgba(color, Math.min(0.95, a));
                });
            }
            return ds;
        });

        var chartType = base;
        var opts = {
            responsive: true, maintainAspectRatio: false,
            plugins: {
                legend: { display: multi, position: 'top',
                    labels: { color: tickColor, usePointStyle: true,
                              font: { size: 11 } } },
                tooltip: { callbacks: def.percent ? {
                    label: function (ct) {
                        return ct.dataset.label + ': ' +
                               (Number(ct.parsed.y || ct.parsed.x) || 0).toFixed(1) + '%';
                    },
                } : {} },
            },
            scales: {
                x: { ticks: { color: tickColor }, grid: { display: false } },
                y: { beginAtZero: true, ticks: { color: tickColor },
                     grid: { color: gridColor } },
            },
        };
        if (def.indexAxis === 'y') { opts.indexAxis = 'y'; }
        if (def.stacked) {
            opts.scales.x.stacked = true;
            opts.scales.y.stacked = true;
        }
        if (def.percent) {
            opts.scales.y.max = 100;
            opts.scales.y.ticks.callback = function (v) { return v + '%'; };
        }
        if (def.dualAxis) {
            opts.scales.y1 = {
                position: 'right', beginAtZero: true,
                ticks: { color: tickColor },
                grid: { drawOnChartArea: false },
            };
        }

        return { type: chartType,
                 data: { labels: labels, datasets: datasets },
                 options: opts };
    }

    function renderTable(targetEl, spec) {
        var wrap = document.createElement('div');
        wrap.className = 'table-wrap';
        var headCells = (spec.datasets || []).map(function (d) {
            return '<th>' + esc(d.label) + '</th>';
        }).join('');
        var rowsHtml = (spec.labels || []).map(function (lbl, i) {
            var cells = (spec.datasets || []).map(function (d) {
                return '<td>' + fmtNum(d.data[i]) + '</td>';
            }).join('');
            return '<tr><td>' + esc(lbl) + '</td>' + cells + '</tr>';
        }).join('');
        wrap.innerHTML = '<table><thead><tr><th>Nomi</th>' + headCells +
                          '</tr></thead><tbody>' + rowsHtml +
                          '</tbody></table>';
        targetEl.appendChild(wrap);
    }

    function renderKpi(targetEl, spec) {
        var d0 = (spec.datasets && spec.datasets[0]) || { data: [] };
        var box = document.createElement('div');
        box.style.cssText = 'display:grid;grid-template-columns:repeat(auto-fit,minmax(110px,1fr));gap:8px;margin-top:6px;';
        (spec.labels || []).forEach(function (lbl, i) {
            var item = document.createElement('div');
            item.style.cssText = 'background:#1E293B;border:1px solid rgba(99,102,241,.25);border-radius:10px;padding:10px;text-align:center;';
            item.innerHTML = '<div style="font-size:20px;font-weight:800;color:#C7D2FE;">' +
                fmtNum(d0.data[i]) + '</div>' +
                '<div style="font-size:11px;opacity:.7;margin-top:3px;">' + esc(lbl) + '</div>';
            box.appendChild(item);
        });
        targetEl.appendChild(box);
    }

    function renderProgressBars(targetEl, spec) {
        var d0 = (spec.datasets && spec.datasets[0]) || { data: [] };
        var max = Math.max.apply(null, d0.data.map(function (v) { return Number(v) || 0; })) || 1;
        var box = document.createElement('div');
        box.style.cssText = 'display:flex;flex-direction:column;gap:8px;margin-top:6px;';
        (spec.labels || []).forEach(function (lbl, i) {
            var v = Number(d0.data[i]) || 0;
            var pct = (v / max) * 100;
            var row = document.createElement('div');
            row.innerHTML =
                '<div style="display:flex;justify-content:space-between;font-size:11.5px;margin-bottom:3px;">' +
                  '<span>' + esc(lbl) + '</span><span style="opacity:.7;">' + fmtNum(v) + '</span>' +
                '</div>' +
                '<div style="height:8px;background:rgba(255,255,255,.08);border-radius:4px;overflow:hidden;">' +
                  '<div style="height:100%;width:' + pct + '%;background:linear-gradient(90deg,#6366F1,#8B5CF6);"></div>' +
                '</div>';
            box.appendChild(row);
        });
        targetEl.appendChild(box);
    }

    // Spec asosida bubble ichida grafik chizadi.
    function appendChart(targetEl, spec) {
        var box = document.createElement('div');
        box.className = 'chart-box';

        var title = document.createElement('div');
        title.className = 'chart-title';
        title.textContent = '📊 ' + (spec.title || spec.card_label || 'Grafik') +
            '  ·  ' + (spec.viewType || 'bar');
        box.appendChild(title);
        targetEl.appendChild(box);

        var vt = spec.viewType || 'bar';

        if (vt === 'table') { renderTable(box, spec); return; }
        if (vt === 'kpi' || vt === 'numberCards') { renderKpi(box, spec); return; }
        if (vt === 'progressBar') { renderProgressBars(box, spec); return; }

        var cwrap = document.createElement('div');
        cwrap.className = 'chart-canvas-wrap';
        if (vt === 'sparkline') { cwrap.style.height = '80px'; }
        var canvas = document.createElement('canvas');
        cwrap.appendChild(canvas);
        box.appendChild(cwrap);

        if (typeof window.Chart === 'function') {
            try {
                var cfg = buildChartConfig(spec, canvas);
                if (vt === 'sparkline') {
                    cfg.type = 'line';
                    cfg.options = cfg.options || {};
                    cfg.options.plugins = { legend: { display: false } };
                    cfg.options.scales = {
                        x: { display: false }, y: { display: false },
                    };
                    (cfg.data.datasets || []).forEach(function (d) {
                        d.pointRadius = 0; d.borderWidth = 2;
                    });
                }
                new window.Chart(canvas, cfg);
            } catch (e) {
                title.textContent += ' (chart xato: ' + e.message + ')';
            }
        } else {
            title.textContent += ' (Chart.js topilmadi)';
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
        };
        var what = labels[cmd.action] || cmd.action;
        p.textContent = icon + ' ' + (cmd.card ? cmd.card + ' — ' : '') + what;
        targetEl.appendChild(p);
    }

    // Buyruqni dashboard'ga uzatamiz — sahifa darajasidagi listener
    // (dashboard_dynamic.js) qabul qiladi.
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

                    // Grafiklarni bubble ichiga chizamiz.
                    var charts = Array.isArray(data.charts) ? data.charts : [];
                    charts.forEach(function (spec) { appendChart(thinking, spec); });

                    // Dashboard buyruqlarini yuboramiz.
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
