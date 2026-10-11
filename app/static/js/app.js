// ================== ИНИЦИАЛИЗАЦИЯ ГЛАВНОЙ ==================
document.addEventListener("DOMContentLoaded", () => {
    checkAuth();

    // Автокомплит из search.js
    if (typeof initSearch === "function") {
        initSearch("searchInput", "suggestions");
    }
});

function checkAuth() {
    const userId = localStorage.getItem('user_id');
    const username = localStorage.getItem('username');
    const loginBtn = document.getElementById('loginBtn');
    const logoutBtn = document.getElementById('logoutBtn');

    if (userId && loginBtn && logoutBtn) {
        loginBtn.style.display = 'none';
        logoutBtn.style.display = 'inline-block';
        logoutBtn.textContent = `Выйти (${username})`;
        logoutBtn.addEventListener('click', (e) => {
            e.preventDefault();
            localStorage.clear();
            window.location.reload();
        });
    } else if (loginBtn) {
        loginBtn.style.display = 'inline-block';
    }
}