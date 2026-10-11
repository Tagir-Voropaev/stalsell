// --- РЕГИСТРАЦИЯ ---
const registerForm = document.getElementById('registerForm');
if (registerForm) {
    registerForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const username = document.getElementById('regUsername').value;
        const email = document.getElementById('regEmail').value;
        const password = document.getElementById('regPassword').value;
        const messageEl = document.getElementById('registerMessage');

        try {
            const response = await fetch('/api/auth/register', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, email, password })
            });
            const data = await response.json();

            if (response.ok) {
                messageEl.style.color = '#4CAF50';
                messageEl.textContent = 'Успех! Перенаправление на вход...';
                setTimeout(() => window.location.href = '/static/login.html', 1500);
            } else {
                messageEl.style.color = '#FF8C00';
                messageEl.textContent = data.detail || 'Ошибка регистрации';
            }
        } catch (error) {
            messageEl.textContent = 'Ошибка соединения с сервером';
        }
    });
}

// --- ВХОД ---
const loginForm = document.getElementById('loginForm');
if (loginForm) {
    loginForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const username = document.getElementById('loginUsername').value;
        const password = document.getElementById('loginPassword').value;
        const messageEl = document.getElementById('loginMessage');

        try {
            const response = await fetch('/api/auth/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, password })
            });
            const data = await response.json();

            if (response.ok) {
                messageEl.style.color = '#4CAF50';
                messageEl.textContent = 'Вход выполнен! Перенаправление...';
                // Сохраняем имя пользователя в память браузера
                localStorage.setItem('username', data.username);
                localStorage.setItem('user_id', data.user_id); // <-- Добавляем эту строку
                setTimeout(() => window.location.href = '/static/index.html', 1000);
            } else {
                messageEl.style.color = '#FF8C00';
                messageEl.textContent = data.detail || 'Неверный логин или пароль';
            }
        } catch (error) {
            messageEl.textContent = 'Ошибка соединения с сервером';
        }
    });
}