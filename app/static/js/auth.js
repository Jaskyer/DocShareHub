// =============== Auth Management ===============
let currentUser = null;
let _authPromise = null;

async function checkAuth() {
    if (_authPromise) return _authPromise;
    _authPromise = _doCheckAuth();
    return _authPromise;
}

async function _doCheckAuth() {
    // Use server-rendered user data when available (no fetch needed)
    if (window.__INITIAL_USER__) {
        currentUser = window.__INITIAL_USER__;
        updateUIForAuth(currentUser);
        window.__INITIAL_USER__ = null; // consume so it's not reused on re-check
        return { authenticated: true, user: currentUser };
    }
    try {
        const data = await API.get('/api/auth/status');
        if (data.authenticated && data.user) {
            currentUser = data.user;
            updateUIForAuth(data.user);
        } else {
            currentUser = null;
            updateUIForGuest();
        }
        return data;
    } catch (err) {
        currentUser = null;
        updateUIForGuest();
        return { authenticated: false, user: null };
    }
}

function updateUIForAuth(user) {
    const userInfo = document.getElementById('userInfo');
    const loginBtn = document.getElementById('loginBtn');
    const navMyProjects = document.getElementById('navMyProjects');
    const navFavorites = document.getElementById('navFavorites');

    if (userInfo) {
        userInfo.style.display = 'flex';
        const avatar = document.getElementById('userAvatar');
        const name = document.getElementById('userName');
        if (avatar) avatar.src = user.avatar_url || '/static/img/default-avatar.svg';
        if (name) name.textContent = user.feishu_name || 'User';
    }
    if (loginBtn) loginBtn.style.display = 'none';
    if (navMyProjects) navMyProjects.style.display = 'inline-flex';
    if (navFavorites) navFavorites.style.display = 'inline-flex';
}

function updateUIForGuest() {
    const userInfo = document.getElementById('userInfo');
    const loginBtn = document.getElementById('loginBtn');
    const navMyProjects = document.getElementById('navMyProjects');
    const navFavorites = document.getElementById('navFavorites');

    if (userInfo) userInfo.style.display = 'none';
    if (loginBtn) loginBtn.style.display = 'inline-flex';
    if (navMyProjects) navMyProjects.style.display = 'none';
    if (navFavorites) navFavorites.style.display = 'none';
}

async function logout() {
    try {
        _authPromise = null;
        await API.get('/api/auth/logout');
        currentUser = null;
        updateUIForGuest();
        showToast('已退出登录', 'info');
        window.location.href = '/';
    } catch (err) {
        showToast('退出失败', 'error');
    }
}

async function requireAuth() {
    if (!currentUser) {
        await checkAuth();
        if (!currentUser) {
            window.location.href = '/login?next=' + encodeURIComponent(window.location.pathname + window.location.search);
            return false;
        }
    }
    return true;
}
