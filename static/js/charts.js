
const chartDefaults = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
        legend: {
            labels: { color: '#9898b8', font: { family: 'Inter', size: 12 } }
        }
    },
    scales: {
        x: {
            ticks: { color: '#6868a0', font: { size: 11 } },
            grid: { color: 'rgba(99,102,241,0.08)' }
        },
        y: {
            ticks: { color: '#6868a0', font: { size: 11 } },
            grid: { color: 'rgba(99,102,241,0.08)' }
        }
    }
};

let leadsTrendChart = null;
let revenueTrendChart = null;

async function loadLeadsTrend(days) {
    const data = await API.get(`/analytics/leads-trend/?days=${days}`);
    const ctx = document.getElementById('leadsTrendChart');
    if (!ctx) return;

    if (leadsTrendChart) leadsTrendChart.destroy();

    leadsTrendChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: data.map(d => {
                const date = new Date(d.date);
                return date.toLocaleDateString('uz-UZ', { day: 'numeric', month: 'short' });
            }),
            datasets: [{
                label: 'Yangi Leadlar',
                data: data.map(d => d.count),
                borderColor: '#6366F1',
                backgroundColor: 'rgba(99,102,241,0.1)',
                fill: true,
                tension: 0.4,
                borderWidth: 2,
                pointRadius: 3,
                pointHoverRadius: 6,
                pointBackgroundColor: '#6366F1',
            }]
        },
        options: {
            ...chartDefaults,
            plugins: { ...chartDefaults.plugins, legend: { display: false } },
        }
    });
}

async function loadRevenueTrend(days) {
    const data = await API.get(`/analytics/revenue-trend/?days=${days}`);
    const ctx = document.getElementById('revenueTrendChart');
    if (!ctx) return;

    if (revenueTrendChart) revenueTrendChart.destroy();

    revenueTrendChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: data.map(d => {
                const date = new Date(d.date);
                return date.toLocaleDateString('uz-UZ', { day: 'numeric', month: 'short' });
            }),
            datasets: [{
                label: 'Tushum',
                data: data.map(d => d.revenue),
                backgroundColor: 'rgba(16,185,129,0.6)',
                borderColor: '#10B981',
                borderWidth: 1,
                borderRadius: 6,
            }]
        },
        options: {
            ...chartDefaults,
            plugins: { ...chartDefaults.plugins, legend: { display: false } },
        }
    });
}

async function loadFunnel() {
    const data = await API.get('/analytics/funnel/');
    const container = document.getElementById('funnel-container');
    if (!container || !data.length) return;

    const maxCount = Math.max(...data.map(d => d.count));
    container.innerHTML = data.map(d => {
        const width = maxCount > 0 ? Math.max((d.count / maxCount) * 100, 5) : 5;
        return `
            <div class="funnel-item">
                <span class="funnel-label">${d.status_name}</span>
                <div class="funnel-bar" style="width:${width}%">${d.count}</div>
                <span class="funnel-count">${Number(d.total_value).toLocaleString('uz-UZ')}</span>
            </div>
        `;
    }).join('');
}
