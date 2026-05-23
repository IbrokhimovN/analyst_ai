/**
 * chart_render.js — 43 ta canonical chart turi uchun yagona renderer.
 *
 * Ham AI chat widget (Shadow DOM ichida), ham asosiy dashboard kartalari
 * shu modulni chaqiradi. `window.AIChartRender.renderInto(targetEl, spec)`
 * deb chaqiriladi. Inline style ishlatadi — CSS class bog'liqligi yo'q.
 *
 * Spec sxemasi (backend `_build_chat_chart_spec` qaytaradigan):
 *   {
 *     card, card_label, viewType, metric, metrics,
 *     labels: string[],
 *     datasets: [{label, metric, data: number[]}],
 *     title, sortBy, sortDir, limit
 *   }
 */
(function (root) {
    'use strict';

    var PALETTE = ['#3b82f6', '#22c55e', '#f59e0b', '#ef4444', '#8b5cf6',
                   '#06b6d4', '#ec4899', '#14b8a6', '#f97316', '#a855f7'];

    function colorByIndex(i) { return PALETTE[i % PALETTE.length]; }

    function hexToRgba(hex, alpha) {
        var m = /^#?([0-9a-f]{6})$/i.exec(hex || '');
        if (!m) { return hex; }
        var n = parseInt(m[1], 16);
        var r = (n >> 16) & 255, g = (n >> 8) & 255, b = n & 255;
        return 'rgba(' + r + ',' + g + ',' + b + ',' + alpha + ')';
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

    function makeGradient(ctx, color) {
        try {
            var g = ctx.createLinearGradient(0, 0, 0, ctx.canvas.height || 200);
            g.addColorStop(0, hexToRgba(color, 0.45));
            g.addColorStop(1, hexToRgba(color, 0.02));
            return g;
        } catch (e) { return hexToRgba(color, 0.18); }
    }

    function flatValues(spec) {
        var d0 = (spec.datasets && spec.datasets[0]) || { data: [] };
        return (d0.data || []).map(Number);
    }

    // -----------------------------------------------------------------------
    // CHART_TYPE_MAP — 43 ta canonical tur + aliaslar uchun konfiguratsiya.
    // `customRenderer` belgilangan turlar Chart.js o'rniga maxsus
    // canvas/SVG funktsiyasi tomonidan chiziladi.
    // -----------------------------------------------------------------------
    var CHART_TYPE_MAP = {
        // ----- 1. Bar family -----
        barChart: { base: 'bar' },
        bar: { base: 'bar' },
        columnChart: { base: 'bar' },
        columnBar: { base: 'bar' },
        groupedBar: { base: 'bar' },
        stackedBar: { base: 'bar', stacked: true },
        stacked: { base: 'bar', stacked: true },
        horizontalBar: { base: 'bar', indexAxis: 'y' },
        horizontalStackedBar: { base: 'bar', stacked: true, indexAxis: 'y' },
        percentBar: { base: 'bar', stacked: true, percent: true },
        rangeBar: { base: 'bar', range: true },
        bulletChart: { customRenderer: 'bullet' },
        stepBar: { base: 'bar', step: true },
        waterfallBar: { base: 'bar', waterfall: true },
        waterfallChart: { base: 'bar', waterfall: true },
        // ----- 2. Line / Area family -----
        lineChart: { base: 'line' },
        line: { base: 'line' },
        smoothLine: { base: 'line', tension: 0.4 },
        splineLine: { base: 'line', tension: 0.4 },
        straightLine: { base: 'line', tension: 0 },
        steppedLine: { base: 'line', stepped: true },
        stepChart: { base: 'line', stepped: true },
        dashedLine: { base: 'line', dashed: true },
        multiLine: { base: 'line' },
        pointLine: { base: 'line', showLine: false, pointRadius: 4 },
        bumpChart: { customRenderer: 'bump' },
        sparkline: { base: 'line', sparkline: true },
        areaChart: { base: 'line', fill: true, tension: 0.4 },
        area: { base: 'line', fill: true, tension: 0.4 },
        smoothArea: { base: 'line', fill: true, tension: 0.5 },
        stackedArea: { base: 'line', fill: true, stacked: true, tension: 0.3 },
        streamGraph: { customRenderer: 'streamGraph' },
        streamArea: { customRenderer: 'streamGraph' },
        percentArea: { base: 'line', fill: true, stacked: true,
                        percent: true, tension: 0.3 },
        gradientArea: { base: 'line', fill: true, tension: 0.4, gradient: true },
        // ----- 3. Pie / Radial family -----
        pieChart: { base: 'pie' },
        pie: { base: 'pie' },
        doughnutChart: { base: 'doughnut' },
        doughnut: { base: 'doughnut' },
        halfPie: { base: 'pie', half: true },
        halfDoughnut: { base: 'doughnut', half: true },
        semicircleDoughnut: { base: 'doughnut', half: true, rotation: 270 },
        gaugeChart: { base: 'doughnut', half: true, rotation: 270, cutout: '70%' },
        gauge: { base: 'doughnut', half: true, rotation: 270, cutout: '70%' },
        polarArea: { base: 'polarArea' },
        nightingaleRose: { base: 'polarArea' },
        waffleChart: { customRenderer: 'waffle' },
        sunburst: { customRenderer: 'sunburst' },
        marimekko: { customRenderer: 'marimekko' },
        // ----- 4. Distribution -----
        histogram: { customRenderer: 'histogram' },
        boxPlot: { base: 'boxplot' },
        violinPlot: { base: 'violin' },
        dotPlot: { customRenderer: 'dotPlot' },
        densityChart: { customRenderer: 'density' },
        // ----- 5. Scatter / Correlation -----
        scatterPlot: { base: 'scatter' },
        scatter: { base: 'scatter' },
        bubbleChart: { base: 'bubble' },
        bubble: { base: 'bubble' },
        connectedScatter: { base: 'scatter', showLine: true },
        jitterScatter: { base: 'scatter', jitter: true },
        bubbleHeatmap: { base: 'bubble' },
        heatmap: { base: 'matrix' },
        correlationMatrix: { base: 'matrix' },
        // ----- 6. Radar / Spider -----
        radarChart: { base: 'radar' },
        radar: { base: 'radar' },
        spiderChart: { base: 'radar' },
        spiderWeb: { base: 'radar' },
        filledRadar: { base: 'radar', fill: true },
        multiRadar: { base: 'radar' },
        // ----- 7. Geo -----
        choroplethMap: { customRenderer: 'geoNotice' },
        bubbleMap: { customRenderer: 'geoNotice' },
        flowMap: { customRenderer: 'geoNotice' },
        geoHeatmap: { customRenderer: 'geoNotice' },
        // ----- 8. Flow / Hierarchy -----
        sankeyDiagram: { base: 'sankey' },
        sankey: { base: 'sankey' },
        funnelChart: { customRenderer: 'funnel' },
        ganttChart: { customRenderer: 'gantt' },
        gantt: { customRenderer: 'gantt' },
        treemap: { base: 'treemap' },
        // ----- 9. Network -----
        networkGraph: { customRenderer: 'network' },
        chordDiagram: { customRenderer: 'chord' },
        arcDiagram: { customRenderer: 'arc' },
        // ----- 10. Combo -----
        barLine: { base: 'bar', combo: 'bar+line' },
        areaBar: { base: 'bar', combo: 'bar+area' },
        dualAxisBar: { base: 'bar', dualAxis: true },
        comboMultiAxis: { base: 'bar', combo: 'bar+line', dualAxis: true },
        // ----- Display -----
        kpiCard: { customRenderer: 'kpi' },
        kpi: { customRenderer: 'kpi' },
        metricTile: { customRenderer: 'metricTile' },
        numberCards: { customRenderer: 'kpi' },
        progressBar: { customRenderer: 'progressBar' },
        table: { customRenderer: 'table' },
    };

    // -----------------------------------------------------------------------
    // Chart.js config builder — base = bar/line/pie/doughnut/polarArea/radar/
    // scatter/bubble/boxplot/violin/matrix/sankey/treemap.
    // -----------------------------------------------------------------------
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

    function buildChartConfig(spec, canvas) {
        var vt = spec.viewType || 'bar';
        var def = CHART_TYPE_MAP[vt] || { base: 'bar' };
        var base = def.base;
        var labels = spec.labels || [];
        var dss = (spec.datasets || []).slice();
        var multi = dss.length > 1;
        var tickColor = '#94a3b8';
        var gridColor = 'rgba(255,255,255,0.08)';

        // -- Boxplot / Violin --
        if (base === 'boxplot' || base === 'violin') {
            function boxStats(arr) {
                var s = (arr || []).slice().map(Number)
                    .filter(function (v) { return !isNaN(v); })
                    .sort(function (a, b) { return a - b; });
                if (!s.length) {
                    return { min: 0, q1: 0, median: 0, q3: 0, max: 0, items: [] };
                }
                function q(p) {
                    var i = (s.length - 1) * p;
                    var lo = Math.floor(i), hi = Math.ceil(i), w = i - lo;
                    return s[lo] * (1 - w) + s[hi] * w;
                }
                return { min: s[0], q1: q(0.25), median: q(0.5),
                         q3: q(0.75), max: s[s.length - 1], items: s };
            }
            var bData = dss.map(function (d) { return boxStats(d.data); });
            return {
                type: base,
                data: {
                    labels: dss.map(function (d) { return d.label; }),
                    datasets: [{
                        label: 'Taqsimot', data: bData,
                        backgroundColor: hexToRgba(PALETTE[0], 0.4),
                        borderColor: PALETTE[0], borderWidth: 1.5,
                        outlierColor: PALETTE[3],
                    }],
                },
                options: {
                    responsive: true, maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                    scales: {
                        x: { ticks: { color: tickColor } },
                        y: { ticks: { color: tickColor },
                             grid: { color: gridColor } },
                    },
                },
            };
        }

        // -- Matrix (heatmap / correlation) --
        if (base === 'matrix') {
            var cells = [];
            var maxV = 0;
            dss.forEach(function (d, y) {
                (d.data || []).forEach(function (v, x) {
                    var val = Number(v) || 0;
                    if (val > maxV) { maxV = val; }
                    cells.push({ x: labels[x] || x, y: d.label || y, v: val });
                });
            });
            maxV = maxV || 1;
            return {
                type: 'matrix',
                data: { datasets: [{
                    label: 'Heatmap', data: cells,
                    backgroundColor: function (ctx) {
                        var v = (ctx.raw && ctx.raw.v) || 0;
                        var a = Math.max(0.08, Math.min(0.95, v / maxV));
                        return hexToRgba(PALETTE[0], a);
                    },
                    borderColor: 'rgba(255,255,255,.06)',
                    borderWidth: 1,
                    width: function (ctx) {
                        var a = ctx.chart.chartArea;
                        return a ? a.width / Math.max(1, labels.length) - 2 : 20;
                    },
                    height: function (ctx) {
                        var a = ctx.chart.chartArea;
                        return a ? a.height / Math.max(1, dss.length) - 2 : 20;
                    },
                }] },
                options: {
                    responsive: true, maintainAspectRatio: false,
                    plugins: { legend: { display: false },
                        tooltip: { callbacks: {
                            title: function () { return ''; },
                            label: function (ctx) {
                                var r = ctx.raw || {};
                                return r.y + ' × ' + r.x + ': ' + fmtNum(r.v);
                            },
                        } } },
                    scales: {
                        x: { type: 'category', labels: labels,
                             ticks: { color: tickColor },
                             grid: { display: false } },
                        y: { type: 'category',
                             labels: dss.map(function (d) { return d.label; }),
                             ticks: { color: tickColor },
                             grid: { display: false }, offset: true },
                    },
                },
            };
        }

        // -- Sankey --
        if (base === 'sankey') {
            var flows = [];
            var d0 = (dss[0] && dss[0].data) || [];
            for (var i = 0; i < d0.length - 1; i++) {
                flows.push({ from: labels[i] || ('S' + i),
                             to: labels[i + 1] || ('S' + (i + 1)),
                             flow: Number(d0[i + 1]) || Number(d0[i]) || 0 });
            }
            if (!flows.length && labels.length) {
                flows.push({ from: labels[0], to: labels[0],
                             flow: Number(d0[0]) || 1 });
            }
            return {
                type: 'sankey',
                data: { datasets: [{ data: flows,
                    colorFrom: function (c) {
                        return PALETTE[c.dataIndex % PALETTE.length];
                    },
                    colorTo: function (c) {
                        return PALETTE[(c.dataIndex + 1) % PALETTE.length];
                    },
                    colorMode: 'gradient', alpha: 0.6,
                }] },
                options: {
                    responsive: true, maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                },
            };
        }

        // -- Treemap --
        if (base === 'treemap') {
            var d0t = (dss[0] && dss[0].data) || [];
            var tdata = d0t.map(function (v, i) {
                return { _name: labels[i] || ('R' + i), v: Number(v) || 0 };
            });
            return {
                type: 'treemap',
                data: { datasets: [{
                    tree: tdata, key: 'v',
                    labels: { display: true, color: '#fff',
                              font: { size: 11, weight: 'bold' },
                              formatter: function (ctx) {
                                  return (ctx.raw && ctx.raw._data &&
                                          ctx.raw._data._name) || '';
                              } },
                    backgroundColor: function (ctx) {
                        return PALETTE[(ctx.dataIndex || 0) % PALETTE.length];
                    },
                    borderColor: '#0F172A', borderWidth: 2, spacing: 2,
                }] },
                options: {
                    responsive: true, maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                },
            };
        }

        // -- Pie / Doughnut / PolarArea --
        if (base === 'pie' || base === 'doughnut' || base === 'polarArea') {
            var first = dss[0] || { data: [], label: '' };
            var data = first.data || [];
            var cfg = {
                type: base,
                data: {
                    labels: labels,
                    datasets: [{
                        label: first.label, data: data,
                        backgroundColor: labels.map(function (_, i) { return colorByIndex(i); }),
                        borderColor: '#0F172A', borderWidth: 2,
                    }],
                },
                options: {
                    responsive: true, maintainAspectRatio: false,
                    plugins: { legend: { position: 'right',
                        labels: { color: tickColor, usePointStyle: true,
                                  font: { size: 11 } } } },
                },
            };
            if (def.half) {
                cfg.options.circumference = 180;
                cfg.options.rotation = def.rotation != null ? def.rotation : -90;
            }
            if (def.cutout) { cfg.options.cutout = def.cutout; }
            return cfg;
        }

        // -- Radar --
        if (base === 'radar') {
            var rds = dss.map(function (d, idx) {
                var color = colorByIndex(idx);
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
                    plugins: { legend: { display: multi,
                        labels: { color: tickColor } } },
                    scales: { r: {
                        ticks: { color: tickColor, backdropColor: 'transparent' },
                        grid: { color: gridColor },
                        angleLines: { color: gridColor },
                        pointLabels: { color: tickColor, font: { size: 11 } },
                    } },
                },
            };
        }

        // -- Scatter / Bubble --
        if (base === 'scatter' || base === 'bubble') {
            var sds = dss.map(function (d, idx) {
                var color = colorByIndex(idx);
                var jitter = def.jitter ? (Math.random() - 0.5) * 0.4 : 0;
                var pts = d.data.map(function (v, i) {
                    if (base === 'bubble') {
                        return { x: i + 1 + jitter, y: Number(v) || 0,
                                 r: Math.max(4, Math.min(20,
                                    Math.sqrt(Math.abs(v) || 1))) };
                    }
                    return { x: i + 1 + jitter, y: Number(v) || 0 };
                });
                return {
                    label: d.label, data: pts,
                    backgroundColor: hexToRgba(color, 0.6),
                    borderColor: color, showLine: !!def.showLine,
                    borderWidth: 2,
                    pointRadius: base === 'bubble' ? undefined : 5,
                };
            });
            return {
                type: base, data: { datasets: sds },
                options: {
                    responsive: true, maintainAspectRatio: false,
                    plugins: { legend: { display: multi,
                        labels: { color: tickColor } } },
                    scales: {
                        x: { ticks: { color: tickColor },
                             grid: { color: gridColor } },
                        y: { ticks: { color: tickColor },
                             grid: { color: gridColor }, beginAtZero: true },
                    },
                },
            };
        }

        // -- Percent stacked: ma'lumotni normallashtirish --
        if (def.percent && dss.length > 1) { dss = toPercentDatasets(dss); }

        // -- Bar / Line / Area --
        var ctx2d = canvas && canvas.getContext ? canvas.getContext('2d') : null;
        var datasets = dss.map(function (d, idx) {
            var color = colorByIndex(idx);
            var isLine = base === 'line';
            var ds = {
                type: isLine ? 'line' : 'bar',
                label: d.label, data: d.data,
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
                        : (d.data || []).map(function (_, i) {
                            return colorByIndex(i);
                          }));
            }
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
            return ds;
        });

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
            opts.scales.x.stacked = true; opts.scales.y.stacked = true;
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

        return { type: base,
                 data: { labels: labels, datasets: datasets },
                 options: opts };
    }

    // -----------------------------------------------------------------------
    // Custom renderlar — 15 ta tur.
    // -----------------------------------------------------------------------

    function renderTable(targetEl, spec) {
        var wrap = document.createElement('div');
        wrap.style.cssText = 'max-width:100%;overflow-x:auto;margin:6px 0;';
        var headCells = (spec.datasets || []).map(function (d) {
            return '<th style="border:1px solid rgba(255,255,255,.15);padding:4px 8px;text-align:left;">' + esc(d.label) + '</th>';
        }).join('');
        var rowsHtml = (spec.labels || []).map(function (lbl, i) {
            var cells = (spec.datasets || []).map(function (d) {
                return '<td style="border:1px solid rgba(255,255,255,.15);padding:4px 8px;">' + fmtNum(d.data[i]) + '</td>';
            }).join('');
            return '<tr><td style="border:1px solid rgba(255,255,255,.15);padding:4px 8px;">' + esc(lbl) + '</td>' + cells + '</tr>';
        }).join('');
        wrap.innerHTML = '<table style="border-collapse:collapse;font-size:12px;margin:0;width:100%;"><thead><tr>' +
                          '<th style="border:1px solid rgba(255,255,255,.15);padding:4px 8px;">Nomi</th>' +
                          headCells + '</tr></thead><tbody>' + rowsHtml + '</tbody></table>';
        targetEl.appendChild(wrap);
    }

    function renderKpi(targetEl, spec) {
        var d0 = (spec.datasets && spec.datasets[0]) || { data: [] };
        var box = document.createElement('div');
        box.style.cssText = 'display:grid;grid-template-columns:repeat(auto-fit,minmax(110px,1fr));gap:8px;margin-top:6px;';
        (spec.labels || []).forEach(function (lbl, i) {
            var item = document.createElement('div');
            item.style.cssText = 'background:rgba(30,41,59,.6);border:1px solid rgba(99,102,241,.25);border-radius:10px;padding:10px;text-align:center;';
            item.innerHTML = '<div style="font-size:20px;font-weight:800;color:#C7D2FE;">' +
                fmtNum(d0.data[i]) + '</div>' +
                '<div style="font-size:11px;opacity:.7;margin-top:3px;color:#cbd5e1;">' + esc(lbl) + '</div>';
            box.appendChild(item);
        });
        targetEl.appendChild(box);
    }

    function renderMetricTile(targetEl, spec) {
        var d0 = (spec.datasets && spec.datasets[0]) || { data: [] };
        var box = document.createElement('div');
        box.style.cssText = 'display:flex;flex-direction:column;gap:6px;margin-top:6px;';
        (spec.labels || []).forEach(function (l, i) {
            var tile = document.createElement('div');
            tile.style.cssText = 'background:linear-gradient(135deg,rgba(99,102,241,.18),rgba(139,92,246,.08));border:1px solid rgba(99,102,241,.3);border-radius:10px;padding:10px 14px;display:flex;justify-content:space-between;align-items:center;';
            tile.innerHTML =
                '<span style="font-size:12px;color:#cbd5e1;">' + esc(l) + '</span>' +
                '<span style="font-size:18px;font-weight:700;color:#C7D2FE;">' + fmtNum(d0.data[i]) + '</span>';
            box.appendChild(tile);
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
                '<div style="display:flex;justify-content:space-between;font-size:11.5px;margin-bottom:3px;color:#cbd5e1;">' +
                  '<span>' + esc(lbl) + '</span><span style="opacity:.7;">' + fmtNum(v) + '</span>' +
                '</div>' +
                '<div style="height:8px;background:rgba(255,255,255,.08);border-radius:4px;overflow:hidden;">' +
                  '<div style="height:100%;width:' + pct + '%;background:linear-gradient(90deg,#6366F1,#8B5CF6);"></div>' +
                '</div>';
            box.appendChild(row);
        });
        targetEl.appendChild(box);
    }

    function renderWaffle(targetEl, spec) {
        var vals = flatValues(spec);
        var labels = spec.labels || [];
        var total = vals.reduce(function (a, b) { return a + (b || 0); }, 0) || 1;
        var counts = vals.map(function (v) { return Math.round((v / total) * 100); });
        var sum = counts.reduce(function (a, b) { return a + b; }, 0);
        if (counts.length) { counts[0] += (100 - sum); }
        var cells = [];
        counts.forEach(function (n, i) {
            for (var k = 0; k < n; k++) { cells.push(i); }
        });
        while (cells.length < 100) { cells.push(-1); }
        var grid = document.createElement('div');
        grid.style.cssText = 'display:grid;grid-template-columns:repeat(10,1fr);gap:3px;margin-top:6px;max-width:240px;';
        cells.slice(0, 100).forEach(function (i) {
            var c = document.createElement('div');
            c.style.cssText = 'aspect-ratio:1;border-radius:3px;background:' +
                (i < 0 ? 'rgba(255,255,255,.06)' : colorByIndex(i)) + ';';
            grid.appendChild(c);
        });
        targetEl.appendChild(grid);
        var legend = document.createElement('div');
        legend.style.cssText = 'display:flex;flex-wrap:wrap;gap:8px;margin-top:8px;font-size:11.5px;color:#cbd5e1;';
        labels.forEach(function (l, i) {
            legend.innerHTML += '<span style="display:inline-flex;align-items:center;gap:4px;"><span style="width:10px;height:10px;background:' +
                colorByIndex(i) + ';border-radius:2px;display:inline-block;"></span>' +
                esc(l) + ' (' + counts[i] + '%)</span>';
        });
        targetEl.appendChild(legend);
    }

    function renderBullet(targetEl, spec) {
        var d0 = (spec.datasets && spec.datasets[0]) || { data: [] };
        var d1 = (spec.datasets && spec.datasets[1]) || null;
        var labels = spec.labels || [];
        var max = Math.max.apply(null, (d0.data || []).map(Number).concat(
            d1 ? d1.data.map(Number) : [])) || 1;
        var wrap = document.createElement('div');
        wrap.style.cssText = 'display:flex;flex-direction:column;gap:10px;margin-top:6px;';
        labels.forEach(function (l, i) {
            var v = Number(d0.data[i]) || 0;
            var t = d1 ? Number(d1.data[i]) || 0 : v * 1.2;
            var pct = (v / max) * 100;
            var tpct = (t / max) * 100;
            var row = document.createElement('div');
            row.innerHTML =
                '<div style="display:flex;justify-content:space-between;font-size:11.5px;margin-bottom:2px;color:#cbd5e1;">' +
                  '<span>' + esc(l) + '</span><span style="opacity:.7;">' + fmtNum(v) + ' / target ' + fmtNum(t) + '</span>' +
                '</div>' +
                '<div style="position:relative;height:14px;background:rgba(255,255,255,.06);border-radius:3px;">' +
                  '<div style="height:100%;width:' + pct + '%;background:' + colorByIndex(i) + ';border-radius:3px;"></div>' +
                  '<div style="position:absolute;top:-3px;bottom:-3px;left:' + tpct + '%;width:2px;background:#ef4444;"></div>' +
                '</div>';
            wrap.appendChild(row);
        });
        targetEl.appendChild(wrap);
    }

    function ensureCanvas(targetEl, h) {
        var wrap = document.createElement('div');
        wrap.style.cssText = 'position:relative;width:100%;height:' + (h || 240) + 'px;';
        var canvas = document.createElement('canvas');
        wrap.appendChild(canvas);
        targetEl.appendChild(wrap);
        return canvas;
    }

    function renderBump(targetEl, spec) {
        if (typeof window.Chart !== 'function') { return; }
        var labels = spec.labels || [];
        var dss = (spec.datasets || []);
        var ranks = dss.map(function (d) { return labels.map(function () { return 0; }); });
        labels.forEach(function (_, i) {
            var arr = dss.map(function (d, k) { return { k: k, v: Number(d.data[i]) || 0 }; });
            arr.sort(function (a, b) { return b.v - a.v; });
            arr.forEach(function (it, rank) { ranks[it.k][i] = rank + 1; });
        });
        var canvas = ensureCanvas(targetEl);
        new window.Chart(canvas, {
            type: 'line',
            data: { labels: labels, datasets: dss.map(function (d, k) {
                return {
                    label: d.label, data: ranks[k],
                    borderColor: colorByIndex(k),
                    backgroundColor: colorByIndex(k),
                    borderWidth: 2.5, tension: 0.4, pointRadius: 4,
                };
            }) },
            options: {
                responsive: true, maintainAspectRatio: false,
                plugins: { legend: { labels: { color: '#94a3b8' } } },
                scales: {
                    y: { reverse: true, ticks: { stepSize: 1, color: '#94a3b8',
                         callback: function (v) { return '#' + v; } },
                         grid: { color: 'rgba(255,255,255,.08)' } },
                    x: { ticks: { color: '#94a3b8' }, grid: { display: false } },
                },
            },
        });
    }

    function renderDotPlot(targetEl, spec) {
        if (typeof window.Chart !== 'function') { return; }
        var labels = spec.labels || [];
        var dss = (spec.datasets || []);
        var canvas = ensureCanvas(targetEl);
        new window.Chart(canvas, {
            type: 'scatter',
            data: { datasets: dss.map(function (d, k) {
                return {
                    label: d.label,
                    data: d.data.map(function (v, i) { return { x: i, y: Number(v) || 0 }; }),
                    backgroundColor: colorByIndex(k),
                    pointRadius: 6, pointHoverRadius: 8,
                };
            }) },
            options: {
                responsive: true, maintainAspectRatio: false,
                plugins: { legend: { display: dss.length > 1,
                    labels: { color: '#94a3b8' } } },
                scales: {
                    x: { type: 'linear', min: -0.5, max: labels.length - 0.5,
                         ticks: { color: '#94a3b8', stepSize: 1,
                                  callback: function (v) {
                                      return labels[v] != null ? labels[v] : '';
                                  } },
                         grid: { display: false } },
                    y: { beginAtZero: true, ticks: { color: '#94a3b8' },
                         grid: { color: 'rgba(255,255,255,.08)' } },
                },
            },
        });
    }

    function renderHistogram(targetEl, spec) {
        if (typeof window.Chart !== 'function') { return; }
        var d0 = (spec.datasets && spec.datasets[0]) || { data: [] };
        var vals = (d0.data || []).map(Number).filter(function (v) { return !isNaN(v); });
        if (!vals.length) {
            targetEl.textContent = 'Histogram uchun ma\'lumot yo\'q';
            return;
        }
        var min = Math.min.apply(null, vals);
        var max = Math.max.apply(null, vals);
        var nbins = Math.min(10, Math.max(3, Math.ceil(Math.sqrt(vals.length))));
        var step = (max - min) / nbins || 1;
        var bins = new Array(nbins).fill(0);
        var lbls = [];
        for (var i = 0; i < nbins; i++) {
            lbls.push(Math.round(min + step * i) + '..' + Math.round(min + step * (i + 1)));
        }
        vals.forEach(function (v) {
            var idx = Math.min(nbins - 1, Math.floor((v - min) / step));
            bins[idx]++;
        });
        var canvas = ensureCanvas(targetEl);
        new window.Chart(canvas, {
            type: 'bar',
            data: { labels: lbls, datasets: [{
                label: 'Chastota', data: bins,
                backgroundColor: colorByIndex(0),
                borderRadius: 4, barPercentage: 1.0, categoryPercentage: 1.0,
            }] },
            options: {
                responsive: true, maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    x: { ticks: { color: '#94a3b8' }, grid: { display: false } },
                    y: { beginAtZero: true, ticks: { color: '#94a3b8' },
                         grid: { color: 'rgba(255,255,255,.08)' } },
                },
            },
        });
    }

    function renderDensity(targetEl, spec) {
        if (typeof window.Chart !== 'function') { return; }
        var d0 = (spec.datasets && spec.datasets[0]) || { data: [] };
        var vals = (d0.data || []).map(Number).filter(function (v) { return !isNaN(v); });
        if (vals.length < 2) {
            targetEl.textContent = 'Density uchun yetarli ma\'lumot yo\'q';
            return;
        }
        var min = Math.min.apply(null, vals), max = Math.max.apply(null, vals);
        var n = 60, h = (max - min) / 5 || 1;
        var xs = [], ys = [];
        for (var i = 0; i < n; i++) {
            var x = min + (max - min) * (i / (n - 1));
            var y = 0;
            vals.forEach(function (v) {
                var u = (x - v) / h;
                y += Math.exp(-0.5 * u * u);
            });
            xs.push(x.toFixed(1));
            ys.push(y / (vals.length * h * Math.sqrt(2 * Math.PI)));
        }
        var canvas = ensureCanvas(targetEl);
        var ctx = canvas.getContext('2d');
        new window.Chart(canvas, {
            type: 'line',
            data: { labels: xs, datasets: [{
                label: 'Zichlik', data: ys,
                borderColor: colorByIndex(0),
                backgroundColor: makeGradient(ctx, colorByIndex(0)),
                fill: true, tension: 0.45, pointRadius: 0, borderWidth: 2,
            }] },
            options: {
                responsive: true, maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    x: { ticks: { color: '#94a3b8' }, grid: { display: false } },
                    y: { beginAtZero: true, ticks: { color: '#94a3b8' },
                         grid: { color: 'rgba(255,255,255,.08)' } },
                },
            },
        });
    }

    function renderStreamGraph(targetEl, spec) {
        if (typeof window.Chart !== 'function') { return; }
        var labels = spec.labels || [];
        var dss = (spec.datasets || []);
        var totals = labels.map(function (_, i) {
            var s = 0; dss.forEach(function (d) { s += Number(d.data[i]) || 0; });
            return s;
        });
        var below = labels.map(function () { return 0; });
        var datasets = dss.map(function (d, k) {
            var data = d.data.map(function (v, i) {
                var val = Number(v) || 0;
                var bottom = -totals[i] / 2 + below[i];
                var top = bottom + val;
                below[i] += val;
                return top;
            });
            return {
                label: d.label, data: data,
                borderColor: colorByIndex(k),
                backgroundColor: hexToRgba(colorByIndex(k), 0.55),
                fill: k === 0 ? 'origin' : '-1',
                tension: 0.55, pointRadius: 0, borderWidth: 1.5,
            };
        });
        var canvas = ensureCanvas(targetEl);
        new window.Chart(canvas, {
            type: 'line',
            data: { labels: labels, datasets: datasets },
            options: {
                responsive: true, maintainAspectRatio: false,
                plugins: { legend: { labels: { color: '#94a3b8' } } },
                scales: {
                    x: { ticks: { color: '#94a3b8' }, grid: { display: false } },
                    y: { display: false },
                },
            },
        });
    }

    function renderSunburst(targetEl, spec) {
        if (typeof window.Chart !== 'function') { return; }
        var labels = spec.labels || [];
        var d0 = (spec.datasets && spec.datasets[0]) || { data: [] };
        var values = (d0.data || []).map(Number);
        var inner = values.map(function (v) { return v; });
        var outerLabels = [], outerValues = [], outerColors = [];
        values.forEach(function (v, i) {
            outerLabels.push(labels[i] + ' A');
            outerLabels.push(labels[i] + ' B');
            outerValues.push(v * 0.55);
            outerValues.push(v * 0.45);
            outerColors.push(hexToRgba(colorByIndex(i), 0.85));
            outerColors.push(hexToRgba(colorByIndex(i), 0.45));
        });
        var canvas = ensureCanvas(targetEl, 260);
        new window.Chart(canvas, {
            type: 'doughnut',
            data: {
                labels: labels.concat(outerLabels),
                datasets: [
                    { data: inner, backgroundColor: labels.map(function (_, i) {
                        return colorByIndex(i); }),
                      borderColor: '#0F172A', borderWidth: 2, weight: 1 },
                    { data: outerValues, backgroundColor: outerColors,
                      borderColor: '#0F172A', borderWidth: 1, weight: 1 },
                ],
            },
            options: {
                responsive: true, maintainAspectRatio: false, cutout: '30%',
                plugins: { legend: { position: 'right',
                    labels: { color: '#94a3b8', font: { size: 10 } } } },
            },
        });
    }

    function renderMarimekko(targetEl, spec) {
        var labels = spec.labels || [];
        var dss = (spec.datasets || []);
        if (!labels.length || !dss.length) { return; }
        var colTotals = labels.map(function (_, i) {
            var s = 0; dss.forEach(function (d) { s += Number(d.data[i]) || 0; });
            return s;
        });
        var grand = colTotals.reduce(function (a, b) { return a + b; }, 0) || 1;
        var W = 360, H = 240, padTop = 6, padBot = 24;
        var svg = '<svg viewBox="0 0 ' + W + ' ' + H + '" width="100%" height="' + H + '">';
        var x = 0;
        labels.forEach(function (lbl, i) {
            var w = (colTotals[i] / grand) * W;
            var y = padTop;
            dss.forEach(function (d, k) {
                var v = Number(d.data[i]) || 0;
                var hSeg = colTotals[i] ? ((v / colTotals[i]) * (H - padTop - padBot)) : 0;
                svg += '<rect x="' + x + '" y="' + y + '" width="' + Math.max(0, w - 1) +
                       '" height="' + hSeg + '" fill="' + colorByIndex(k) + '" opacity="0.85"/>';
                y += hSeg;
            });
            svg += '<text x="' + (x + w / 2) + '" y="' + (H - 8) +
                   '" fill="#94a3b8" font-size="10" text-anchor="middle">' +
                   esc(String(lbl).slice(0, 8)) + '</text>';
            x += w;
        });
        svg += '</svg>';
        var box = document.createElement('div');
        box.innerHTML = svg;
        targetEl.appendChild(box);
        var legend = document.createElement('div');
        legend.style.cssText = 'display:flex;flex-wrap:wrap;gap:8px;margin-top:6px;font-size:11.5px;color:#cbd5e1;';
        dss.forEach(function (d, k) {
            legend.innerHTML += '<span style="display:inline-flex;align-items:center;gap:4px;"><span style="width:10px;height:10px;background:' +
                colorByIndex(k) + ';border-radius:2px;"></span>' + esc(d.label) + '</span>';
        });
        targetEl.appendChild(legend);
    }

    function renderFunnel(targetEl, spec) {
        var labels = spec.labels || [];
        var vals = flatValues(spec);
        var max = Math.max.apply(null, vals) || 1;
        var wrap = document.createElement('div');
        wrap.style.cssText = 'display:flex;flex-direction:column;gap:4px;margin-top:6px;';
        labels.forEach(function (l, i) {
            var w = (vals[i] / max) * 100;
            var row = document.createElement('div');
            row.style.cssText = 'display:flex;justify-content:center;';
            row.innerHTML =
                '<div style="width:' + w + '%;min-width:40px;background:' +
                colorByIndex(i) + ';color:#fff;padding:6px 10px;border-radius:4px;' +
                'font-size:11.5px;text-align:center;font-weight:600;">' +
                esc(l) + ': ' + fmtNum(vals[i]) + '</div>';
            wrap.appendChild(row);
        });
        targetEl.appendChild(wrap);
    }

    function renderGantt(targetEl, spec) {
        var labels = spec.labels || [];
        var dss = (spec.datasets || []);
        var starts = (dss[0] && dss[0].data) || [];
        var durations = (dss[1] && dss[1].data) ||
            starts.map(function (s) { return Number(s) * 0.5 + 1; });
        var ends = starts.map(function (s, i) {
            return Number(s) + Number(durations[i] || 0);
        });
        var min = Math.min.apply(null, starts.map(Number));
        var max = Math.max.apply(null, ends.map(Number));
        var range = (max - min) || 1;
        var wrap = document.createElement('div');
        wrap.style.cssText = 'display:flex;flex-direction:column;gap:6px;margin-top:6px;';
        labels.forEach(function (l, i) {
            var left = ((Number(starts[i]) - min) / range) * 100;
            var w = ((Number(durations[i]) || 0) / range) * 100;
            var row = document.createElement('div');
            row.innerHTML =
                '<div style="font-size:11px;margin-bottom:2px;color:#cbd5e1;">' + esc(l) + '</div>' +
                '<div style="height:14px;background:rgba(255,255,255,.05);border-radius:3px;position:relative;">' +
                  '<div style="position:absolute;left:' + left + '%;width:' + Math.max(2, w) +
                  '%;height:100%;background:' + colorByIndex(i) + ';border-radius:3px;"></div>' +
                '</div>';
            wrap.appendChild(row);
        });
        targetEl.appendChild(wrap);
    }

    function renderNetwork(targetEl, spec) {
        var labels = spec.labels || [];
        var vals = flatValues(spec);
        var n = labels.length;
        if (!n) { return; }
        var W = 360, H = 260, cx = W / 2, cy = H / 2, R = Math.min(W, H) / 2 - 28;
        var positions = labels.map(function (_, i) {
            var a = (i / n) * Math.PI * 2 - Math.PI / 2;
            return { x: cx + R * Math.cos(a), y: cy + R * Math.sin(a) };
        });
        var maxV = Math.max.apply(null, vals) || 1;
        var svg = '<svg viewBox="0 0 ' + W + ' ' + H + '" width="100%" height="' + H + '">';
        for (var i = 0; i < n; i++) {
            var j = (i + 1) % n;
            var w = 0.5 + (vals[i] / maxV) * 3;
            svg += '<line x1="' + positions[i].x + '" y1="' + positions[i].y +
                   '" x2="' + positions[j].x + '" y2="' + positions[j].y +
                   '" stroke="' + colorByIndex(i) + '" stroke-opacity="0.5" stroke-width="' + w + '"/>';
        }
        positions.forEach(function (p, i) {
            var r = 8 + (vals[i] / maxV) * 12;
            svg += '<circle cx="' + p.x + '" cy="' + p.y + '" r="' + r +
                   '" fill="' + colorByIndex(i) + '" stroke="#0F172A" stroke-width="2"/>';
            svg += '<text x="' + p.x + '" y="' + (p.y + r + 12) +
                   '" fill="#cbd5e1" font-size="10" text-anchor="middle">' +
                   esc(String(labels[i]).slice(0, 10)) + '</text>';
        });
        svg += '</svg>';
        var box = document.createElement('div');
        box.innerHTML = svg;
        targetEl.appendChild(box);
    }

    function renderChord(targetEl, spec) {
        var labels = spec.labels || [];
        var vals = flatValues(spec);
        var n = labels.length;
        if (!n) { return; }
        var W = 320, H = 320, cx = W / 2, cy = H / 2, R = 130, r = 110;
        var total = vals.reduce(function (a, b) { return a + (b || 0); }, 0) || 1;
        var svg = '<svg viewBox="0 0 ' + W + ' ' + H + '" width="100%" height="' + H + '">';
        var ang = -Math.PI / 2;
        var arcs = [];
        labels.forEach(function (l, i) {
            var span = (vals[i] / total) * Math.PI * 2;
            var a0 = ang, a1 = ang + span;
            arcs.push({ a0: a0, a1: a1, mid: (a0 + a1) / 2 });
            var large = span > Math.PI ? 1 : 0;
            var x0 = cx + R * Math.cos(a0), y0 = cy + R * Math.sin(a0);
            var x1 = cx + R * Math.cos(a1), y1 = cy + R * Math.sin(a1);
            var rx0 = cx + r * Math.cos(a1), ry0 = cy + r * Math.sin(a1);
            var rx1 = cx + r * Math.cos(a0), ry1 = cy + r * Math.sin(a0);
            svg += '<path d="M' + x0 + ',' + y0 + ' A' + R + ',' + R + ' 0 ' + large +
                   ',1 ' + x1 + ',' + y1 + ' L' + rx0 + ',' + ry0 + ' A' + r + ',' + r +
                   ' 0 ' + large + ',0 ' + rx1 + ',' + ry1 + ' Z" fill="' + colorByIndex(i) + '"/>';
            var lx = cx + (R + 14) * Math.cos((a0 + a1) / 2);
            var ly = cy + (R + 14) * Math.sin((a0 + a1) / 2);
            svg += '<text x="' + lx + '" y="' + ly + '" fill="#cbd5e1" font-size="10" text-anchor="middle">' +
                   esc(String(l).slice(0, 8)) + '</text>';
            ang = a1;
        });
        var maxV = Math.max.apply(null, vals) || 1;
        for (var i = 0; i < n; i++) {
            var a = arcs[i].mid;
            var b = arcs[(i + 1) % n].mid;
            var sx = cx + r * Math.cos(a), sy = cy + r * Math.sin(a);
            var ex = cx + r * Math.cos(b), ey = cy + r * Math.sin(b);
            svg += '<path d="M' + sx + ',' + sy + ' Q' + cx + ',' + cy + ' ' + ex + ',' + ey +
                   '" stroke="' + colorByIndex(i) + '" stroke-opacity="0.35" stroke-width="' +
                   (1 + (vals[i] / maxV) * 4) + '" fill="none"/>';
        }
        svg += '</svg>';
        var box = document.createElement('div');
        box.innerHTML = svg;
        targetEl.appendChild(box);
    }

    function renderArc(targetEl, spec) {
        var labels = spec.labels || [];
        var vals = flatValues(spec);
        var n = labels.length;
        if (!n) { return; }
        var W = 380, H = 200, padX = 30, baseY = H - 30;
        var step = (W - padX * 2) / Math.max(1, n - 1);
        var maxV = Math.max.apply(null, vals) || 1;
        var svg = '<svg viewBox="0 0 ' + W + ' ' + H + '" width="100%" height="' + H + '">';
        for (var i = 0; i < n - 1; i++) {
            var x1 = padX + i * step, x2 = padX + (i + 1) * step;
            var mid = (x1 + x2) / 2;
            var h = 20 + (vals[i] / maxV) * (H - 80);
            var d = 'M ' + x1 + ' ' + baseY + ' Q ' + mid + ' ' + (baseY - h) + ' ' + x2 + ' ' + baseY;
            svg += '<path d="' + d + '" fill="none" stroke="' + colorByIndex(i) +
                   '" stroke-opacity="0.55" stroke-width="2"/>';
        }
        for (var i = 0; i < n; i++) {
            var x = padX + i * step;
            svg += '<circle cx="' + x + '" cy="' + baseY + '" r="5" fill="' + colorByIndex(i) + '"/>';
            svg += '<text x="' + x + '" y="' + (baseY + 18) +
                   '" fill="#cbd5e1" font-size="10" text-anchor="middle">' +
                   esc(String(labels[i]).slice(0, 8)) + '</text>';
        }
        svg += '</svg>';
        var box = document.createElement('div');
        box.innerHTML = svg;
        targetEl.appendChild(box);
    }

    function renderGeoNotice(targetEl, spec) {
        var box = document.createElement('div');
        box.style.cssText = 'background:rgba(245,158,11,.12);border:1px dashed rgba(245,158,11,.35);padding:10px;border-radius:8px;font-size:12px;margin-top:6px;color:#fbbf24;';
        box.innerHTML =
            '🗺️ <strong>' + esc(spec.viewType) + '</strong> — geografik ma\'lumot ' +
            'kerak. Hozircha bubble chart fallback ko\'rsatamiz.';
        targetEl.appendChild(box);
        var fallback = Object.assign({}, spec, { viewType: 'bubble' });
        var canvas = ensureCanvas(targetEl);
        if (typeof window.Chart === 'function') {
            try { new window.Chart(canvas, buildChartConfig(fallback, canvas)); }
            catch (e) {}
        }
    }

    var CUSTOM_RENDERERS = {
        table: renderTable,
        kpi: renderKpi,
        metricTile: renderMetricTile,
        progressBar: renderProgressBars,
        waffle: renderWaffle,
        bullet: renderBullet,
        bump: renderBump,
        dotPlot: renderDotPlot,
        histogram: renderHistogram,
        density: renderDensity,
        streamGraph: renderStreamGraph,
        sunburst: renderSunburst,
        marimekko: renderMarimekko,
        funnel: renderFunnel,
        gantt: renderGantt,
        network: renderNetwork,
        chord: renderChord,
        arc: renderArc,
        geoNotice: renderGeoNotice,
    };

    /**
     * Spec asosida targetEl ichiga grafikni chizadi.
     *
     * @param {Element} targetEl - chiqish konteyneri.
     * @param {Object} spec - backend spec (viewType, labels, datasets, ...).
     * @returns {void}
     */
    function renderInto(targetEl, spec) {
        if (!targetEl || !spec) { return; }
        var vt = spec.viewType || 'bar';
        var def = CHART_TYPE_MAP[vt] || { base: 'bar' };

        if (def.customRenderer && CUSTOM_RENDERERS[def.customRenderer]) {
            try { CUSTOM_RENDERERS[def.customRenderer](targetEl, spec); }
            catch (e) {
                var err = document.createElement('div');
                err.style.cssText = 'color:#fca5a5;font-size:12px;';
                err.textContent = 'Renderer xato (' + def.customRenderer + '): ' + e.message;
                targetEl.appendChild(err);
            }
            return;
        }

        // Chart.js (core yoki plagin).
        var h = (vt === 'sparkline') ? 80 : 240;
        var canvas = ensureCanvas(targetEl, h);
        if (typeof window.Chart !== 'function') {
            var err = document.createElement('div');
            err.style.cssText = 'color:#fca5a5;font-size:12px;';
            err.textContent = 'Chart.js topilmadi';
            targetEl.appendChild(err);
            return;
        }
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
            var err2 = document.createElement('div');
            err2.style.cssText = 'color:#fca5a5;font-size:12px;';
            err2.textContent = 'Chart xato (' + vt + '): ' + e.message;
            targetEl.appendChild(err2);
        }
    }

    root.AIChartRender = {
        renderInto: renderInto,
        buildChartConfig: buildChartConfig,
        CHART_TYPE_MAP: CHART_TYPE_MAP,
        PALETTE: PALETTE,
    };
}(window));
