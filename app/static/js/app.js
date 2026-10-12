// ================== ИНИЦИАЛИЗАЦИЯ ГЛАВНОЙ ==================
document.addEventListener("DOMContentLoaded", () => {
    checkAuth();

    if (typeof initSearch === "function") {
        initSearch("searchInput", "suggestions");
    }
});

function checkAuth() {
    const token = localStorage.getItem('access_token');
    const username = localStorage.getItem('username');
    const loginBtn = document.getElementById('loginBtn');
    const logoutBtn = document.getElementById('logoutBtn');
    const profileBtn = document.getElementById('profileBtn');

    if (token && loginBtn && logoutBtn) {
        loginBtn.style.display = 'none';
        logoutBtn.style.display = 'inline-block';
        logoutBtn.textContent = `Выйти (${username})`;
        if (profileBtn) profileBtn.style.display = 'inline-block';

        logoutBtn.addEventListener('click', (e) => {
            e.preventDefault();
            localStorage.removeItem('access_token');
            localStorage.removeItem('username');
            window.location.reload();
        });
    } else if (loginBtn) {
        loginBtn.style.display = 'inline-block';
        if (logoutBtn) logoutBtn.style.display = 'none';
        if (profileBtn) profileBtn.style.display = 'none';
    }
}