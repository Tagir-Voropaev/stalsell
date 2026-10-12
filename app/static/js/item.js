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

async function loadItemName() {
    try {
        const r = await fetch(`/api/items/${ITEM_ID}/info`);
        const data = await r.json();
        const name = data.name || ITEM_ID;
        document.title = `${name} — StalSell`;
        document.getElementById("itemTitle").textContent = name;

        // 🔑 Сохраняем категорию для последующей фильтрации UI
        window.ITEM_CATEGORY = data.category || "";
        applyCategoryVisibility();
    } catch (e) {
        document.getElementById("itemTitle").textContent = ITEM_ID;
        window.ITEM_CATEGORY = "";
    }
}

// 🆕 Скрываем фильтры редкости/заточки для не-артефактов
function applyCategoryVisibility() {
    const isArtefact = window.ITEM_CATEGORY === "artefact";

    const qualityBlock = document.querySelector('.filter-group:has(.quality-buttons)');
    const levelBlock = document.querySelector('.filter-group:has(.level-buttons)');

    const blocks = [
        document.querySelector(".quality-buttons")?.closest(".filter-group"),
        document.querySelector(".level-buttons")?.closest(".filter-group"),
    ];

    blocks.forEach(block => {
        if (!block) return;
        block.style.display = isArtefact ? "" : "none";
    });
}

function searchFromPage() {
    const q = document.getElementById("searchInput").value.trim();
    if (!q) return;
    window.location.href = `/static/index.html?q=${encodeURIComponent(q)}`;
}