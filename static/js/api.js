const API = {
    baseUrl: '/api/v1',

    getCSRFToken() {
        const name = 'csrftoken';
        const cookies = document.cookie.split(';');
        for (let cookie of cookies) {
            cookie = cookie.trim();
            if (cookie.startsWith(name + '=')) {
                return cookie.substring(name.length + 1);
            }
        }
        const meta = document.querySelector('meta[name="csrf-token"]');
        return meta ? meta.getAttribute('content') : '';
    },

    async request(path, options = {}) {
        const token = localStorage.getItem('access_token');
        const csrfToken = this.getCSRFToken();
        const method = (options.method || 'GET').toUpperCase();

        const headers = {
            'Content-Type': 'application/json',
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
            ...(csrfToken && method !== 'GET' ? { 'X-CSRFToken': csrfToken } : {}),
            ...(options.headers || {}),
        };

        const res = await fetch(this.baseUrl + path, {
            ...options,
            headers,
            credentials: 'same-origin',
        });

        if (res.status === 401) {
        }
        if (!res.ok) {
            const err = await res.json().catch(() => ({ detail: 'Xatolik yuz berdi' }));
            throw new Error(err.detail || err.error || 'Xatolik');
        }
        return res.json();
    },

    get(path, params = {}) {
        const source = window.__crmSource || '';
        let url = path;

        if (source) {
            const sep = url.includes('?') ? '&' : '?';
            if (!url.includes('source=')) {
                url += sep + 'source=' + encodeURIComponent(source);
            }
        }

        if (Object.keys(params).length) {
            const sep2 = url.includes('?') ? '&' : '?';
            const qs = new URLSearchParams(params).toString();
            url += sep2 + qs;
        }

        return this.request(url);
    },

    post(path, body) {
        return this.request(path, {
            method: 'POST',
            body: JSON.stringify(body),
        });
    },
};
