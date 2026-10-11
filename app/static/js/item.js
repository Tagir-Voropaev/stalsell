// ================== ИНИЦИАЛИЗАЦИЯ ==================
document.addEventListener("DOMContentLoaded", async () => {
    console.log("[StalSell] DOMContentLoaded");
    console.log("[StalSell] ITEM_ID:", ITEM_ID);

    if (!ITEM_ID) {
        document.getElementById("itemTitle").textContent = "Предмет не найден";
        return;
    }

    checkAuth();
    setupFilters();

    if (typeof initSearch === "function") {
        initSearch("searchInput", "suggestions");
    }

    await loadItemName();
    await loadHistoryData();
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
    }
}

async function loadItemName() {
    try {
        const r = await fetch(`/api/items/${ITEM_ID}/info`);
        const data = await r.json();
        const name = data.name || ITEM_ID;
        document.title = `${name} — StalSell`;
        document.getElementById("itemTitle").textContent = name;
    } catch (e) {
        document.getElementById("itemTitle").textContent = ITEM_ID;
    }
}

function searchFromPage() {
    const q = document.getElementById("searchInput").value.trim();
    if (!q) return;
    window.location.href = `/static/index.html?q=${encodeURIComponent(q)}`;
}