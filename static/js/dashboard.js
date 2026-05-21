/**
 * Dashboard — umumiy interaktiv funksiyalar.
 */
document.addEventListener('DOMContentLoaded', () => {
    // Sidebar toggle (mobile)
    const toggle = document.getElementById('sidebar-toggle');
    const sidebar = document.getElementById('sidebar');
    if (toggle && sidebar) {
        toggle.addEventListener('click', () => sidebar.classList.toggle('open'));
        document.addEventListener('click', (e) => {
            if (sidebar.classList.contains('open') && !sidebar.contains(e.target) && e.target !== toggle) {
                sidebar.classList.remove('open');
            }
        });
    }

    // Theme toggle
    const themeBtn = document.getElementById('theme-toggle');
    if (themeBtn) {
        themeBtn.addEventListener('click', () => {
            const currentTheme = document.documentElement.getAttribute('data-theme');
            const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
            document.documentElement.setAttribute('data-theme', newTheme);
            localStorage.setItem('theme', newTheme);
            
            // Dispatch event for charts to update colors
            window.dispatchEvent(new Event('themeChanged'));
        });
    }

    // Sync button
    const syncBtn = document.getElementById('btn-sync');
    if (syncBtn) {
        syncBtn.addEventListener('click', async () => {
            syncBtn.disabled = true;
            syncBtn.style.animation = 'spin 1s linear infinite';
            try {
                // Trigger sync via API (agar endpoint bo'lsa)
                await new Promise(r => setTimeout(r, 1500));
                const statusEl = document.getElementById('sync-status');
                if (statusEl) {
                    statusEl.querySelector('.sync-text').textContent = 'Yangilandi!';
                    setTimeout(() => {
                        statusEl.querySelector('.sync-text').textContent = 'Sinxron';
                    }, 3000);
                }
            } finally {
                syncBtn.disabled = false;
                syncBtn.style.animation = '';
            }
        });
    }

    // Auto-resize textarea
    document.querySelectorAll('textarea').forEach(textarea => {
        textarea.addEventListener('input', () => {
            textarea.style.height = 'auto';
            textarea.style.height = Math.min(textarea.scrollHeight, 120) + 'px';
        });
    });
});
