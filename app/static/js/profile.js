// ================== ПРОФИЛЬ ==================
document.addEventListener('DOMContentLoaded', loadProfile);

async function loadProfile() {
    const token = localStorage.getItem('access_token');

    if (!token) {
        window.location.href = '/static/login.html';
        return;
    }

    try {
        const response = await fetch('/api/auth/me', {
            headers: { 'Authorization': `Bearer ${token}` }
        });

        if (response.status === 401) {
            // Токен просрочен или недействителен
            localStorage.removeItem('access_token');
            localStorage.removeItem('username');
            window.location.href = '/static/login.html';
            return;
        }

        const data = await response.json();

        document.getElementById('profileUsername').textContent = data.username;
        document.getElementById('profileEmail').textContent = data.email;
        document.getElementById('profileId').textContent = `#${data.id}`;

        document.getElementById('profileLogoutBtn').addEventListener('click', () => {
            localStorage.removeItem('access_token');
            localStorage.removeItem('username');
            window.location.href = '/static/index.html';
        });
    } catch (e) {
        console.error('[StalSell] Ошибка загрузки профиля:', e);
        document.getElementById('profileUsername').textContent = 'Ошибка загрузки';
    }
}