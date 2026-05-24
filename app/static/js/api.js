// =============== API Client ===============
const API = {
    async request(method, path, options = {}) {
        const { body, params, formData } = options;
        let url = path;
        if (params) {
            const qs = new URLSearchParams(params).toString();
            if (qs) url += '?' + qs;
        }

        const fetchOpts = {
            method,
            headers: {},
            credentials: 'same-origin',
        };

        if (formData) {
            fetchOpts.body = formData;
            // Don't set Content-Type for FormData - browser sets it with boundary
        } else if (body) {
            fetchOpts.headers['Content-Type'] = 'application/json';
            fetchOpts.body = JSON.stringify(body);
        }

        try {
            const res = await fetch(url, fetchOpts);
            const data = await res.json().catch(() => null);

            if (!res.ok) {
                const msg = data?.detail || `Request failed (${res.status})`;
                throw { status: res.status, message: msg, data };
            }
            return data;
        } catch (err) {
            if (err.status) throw err;
            throw { status: 0, message: err.message || 'Network error', data: null };
        }
    },

    get(path, params) {
        return this.request('GET', path, { params });
    },
    post(path, body) {
        return this.request('POST', path, { body });
    },
    put(path, body) {
        return this.request('PUT', path, { body });
    },
    delete(path) {
        return this.request('DELETE', path);
    },
    upload(path, formData) {
        return this.request('POST', path, { formData });
    },
};
