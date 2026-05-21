/**
 * API — Fetch wrapper for REST API calls.
 */
const API = {
    baseUrl: '/api/v1',

    /**
     * CSRF tokenni cookie dan olish.
     */
    getCSRFToken() {
        const name = 'csrftoken';
        const cookies = document.cookie.split(';');
        for (let cookie of cookies) {
            cookie = cookie.trim();
            if (cookie.startsWith(name + '=')) {
                return cookie.substring(name.length + 1);
            }
        }
        // Fallback: meta tag dan olish
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
            // CSRF token — POST/PUT/PATCH/DELETE uchun kerak
            ...(csrfToken && method !== 'GET' ? { 'X-CSRFToken': csrfToken } : {}),
            ...(options.headers || {}),
        };

        const res = await fetch(this.baseUrl + path, {
            ...options,
            headers,
            credentials: 'same-origin',  // Session cookie yuborish uchun
        });

        if (res.status === 401) {
            // Session auth orqali ishlayotgan bo'lsa, login ga yuborish
            // window.location.href = '/admin/login/';
        }
        if (!res.ok) {
            const err = await res.json().catch(() => ({ detail: 'Xatolik yuz berdi' }));
            throw new Error(err.detail || err.error || 'Xatolik');
        }
        return res.json();
    },

    /**
     * GET so'rov — source parametrini avtomatik qo'shish.
     * window.__crmSource = '' | 'amocrm' | 'bitrix'
     */
    get(path, params = {}) {
        const source = window.__crmSource || '';
        let url = path;

        // URL ga source param qo'shish (agar allaqachon yo'q bo'lsa)
        if (source) {
            const sep = url.includes('?') ? '&' : '?';
            if (!url.includes('source=')) {
                url += sep + 'source=' + encodeURIComponent(source);
            }
        }

        // Qo'shimcha params
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
