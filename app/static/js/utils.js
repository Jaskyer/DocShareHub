// =============== Toast Notifications ===============
function showToast(message, type = 'info', duration = 3000) {
    const container = document.getElementById('toastContainer');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    container.appendChild(toast);
    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(100%)';
        toast.style.transition = 'all 0.3s ease';
        setTimeout(() => toast.remove(), 300);
    }, duration);
}

// =============== Formatting ===============
function formatDate(dateStr) {
    if (!dateStr) return '-';
    const d = new Date(dateStr);
    const pad = n => String(n).padStart(2, '0');
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

function formatSize(bytes) {
    if (!bytes || bytes === 0) return '-';
    const units = ['B', 'KB', 'MB', 'GB'];
    let i = 0;
    let size = bytes;
    while (size >= 1024 && i < units.length - 1) {
        size /= 1024;
        i++;
    }
    return `${size.toFixed(i === 0 ? 0 : 1)} ${units[i]}`;
}

function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

// =============== Confirm Dialog ===============
async function confirmDialog(message, title = '确认') {
    return new Promise((resolve) => {
        const overlay = document.createElement('div');
        overlay.className = 'modal-overlay active';
        overlay.innerHTML = `
            <div class="modal">
                <div class="modal-header">
                    <span class="modal-title">${escapeHtml(title)}</span>
                </div>
                <div class="modal-body">
                    <p>${escapeHtml(message)}</p>
                </div>
                <div class="modal-footer">
                    <button class="btn btn-ghost" onclick="this.closest('.modal-overlay').remove(); resolve(false)">取消</button>
                    <button class="btn btn-primary" onclick="this.closest('.modal-overlay').remove(); resolve(true)">确认</button>
                </div>
            </div>
        `;
        // Hack to make resolve available
        overlay.dataset._resolve = resolve;
        overlay.querySelector('.modal-footer').addEventListener('click', (e) => {
            if (e.target.tagName === 'BUTTON') {
                const isConfirm = e.target.classList.contains('btn-primary');
                // Need to recreate the resolve since the function reference is tricky
            }
        });
        document.body.appendChild(overlay);
    });
}

// Simple confirm - returns a promise resolved by inline onclick
window._confirmCallback = null;
function showConfirm(message, title = '确认') {
    const overlay = document.getElementById('confirmOverlay') || (() => {
        const el = document.createElement('div');
        el.id = 'confirmOverlay';
        el.className = 'modal-overlay';
        el.innerHTML = `
            <div class="modal">
                <div class="modal-header">
                    <span class="modal-title" id="confirmTitle">确认</span>
                </div>
                <div class="modal-body">
                    <p id="confirmMessage"></p>
                </div>
                <div class="modal-footer">
                    <button class="btn btn-ghost" onclick="closeConfirm(false)">取消</button>
                    <button class="btn btn-primary" onclick="closeConfirm(true)">确认</button>
                </div>
            </div>
        `;
        document.body.appendChild(el);
        return el;
    })();
    overlay.classList.add('active');
    document.getElementById('confirmTitle').textContent = title;
    document.getElementById('confirmMessage').textContent = message;
    return new Promise(resolve => { window._confirmCallback = resolve; });
}
function closeConfirm(result) {
    const overlay = document.getElementById('confirmOverlay');
    if (overlay) overlay.classList.remove('active');
    if (window._confirmCallback) {
        window._confirmCallback(result);
        window._confirmCallback = null;
    }
}
function showAlert(message, title = '提示') {
    const overlay = document.getElementById('alertOverlay') || (() => {
        const el = document.createElement('div');
        el.id = 'alertOverlay';
        el.className = 'modal-overlay';
        el.innerHTML = '\
            <div class="modal">\
                <div class="modal-header">\
                    <span class="modal-title" id="alertTitle"></span>\
                </div>\
                <div class="modal-body">\
                    <p id="alertMessage"></p>\
                </div>\
                <div class="modal-footer">\
                    <button class="btn btn-primary" onclick="closeAlert()">确认</button>\
                </div>\
            </div>\
        ';
        document.body.appendChild(el);
        return el;
    })();
    overlay.classList.add('active');
    document.getElementById('alertTitle').textContent = title;
    document.getElementById('alertMessage').textContent = message;
    return new Promise(resolve => { window._alertCallback = resolve; });
}
function closeAlert() {
    const overlay = document.getElementById('alertOverlay');
    if (overlay) overlay.classList.remove('active');
    if (window._alertCallback) {
        window._alertCallback(true);
        window._alertCallback = null;
    }
}
