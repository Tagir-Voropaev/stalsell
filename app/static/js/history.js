// ================== ЗАГРУЗКА ИСТОРИИ ==================
// ================== ЗАГРУЗКА ИСТОРИИ ==================
async function loadHistoryData() {
    const statusEl = document.getElementById("skeletonStatusText");
    const setStatus = (text) => { if (statusEl) statusEl.textContent = text; };

    startProgressBar();

    try {
        setStatus("Загружаем данные о предмете...");

        // 🚀 Грузим сразу QUICK_LIMIT (1000) — для обычного просмотра достаточно
        const [lotsResp, histResp] = await Promise.all([
            fetch(`/api/items/${ITEM_ID}/lots`).then(r => r.ok ? r.json() : []).catch(() => []),
            fetch(`/api/items/${ITEM_ID}/history?limit=${QUICK_LIMIT}`).then(r => r.ok ? r.json() : []).catch(() => []),
        ]);

        allLots = Array.isArray(lotsResp) ? lotsResp : [];
        allHistory = Array.isArray(histResp) ? histResp : [];
        _allHistoryLoaded = allHistory.length < QUICK_LIMIT;

        allLots.sort((a, b) => {
            const pa = a.buyout_price || a.start_price || 0;
            const pb = b.buyout_price || b.start_price || 0;
            return pa - pb;
        });

        finishProgressBar();
        setTimeout(hideProgressBar, 400);

        applyFilters();
        updateRefreshTime();
        renderTables();

        const info = document.getElementById("loadMoreChartInfo");
        if (info) {
            info.textContent = `Загружено ${allHistory.length} записей`;
            info.style.color = "";
        }
    } catch (e) {
        console.error("[StalSell] Ошибка загрузки:", e);
        setStatus("Ошибка загрузки. Обновите страницу.");
        finishProgressBar();
    }
}

// ================== ПРОГРЕСС-БАР ==================
function startProgressBar() {
    const bar = document.querySelector(".load-more-progress-bar");
    const wrap = document.getElementById("loadMoreProgress");
    if (!bar || !wrap) return;
    wrap.style.display = "block";
    bar.style.width = "0%";
    let progress = 0;
    _progressTimer = setInterval(() => {
        if (progress < 40) progress += 5;
        else if (progress < 75) progress += 2;
        else progress += 0.5;
        if (progress > 92) progress = 92;
        bar.style.width = progress + "%";
    }, 100);
}

function finishProgressBar() {
    const bar = document.querySelector(".load-more-progress-bar");
    if (!bar) return;
    if (_progressTimer) { clearInterval(_progressTimer); _progressTimer = null; }
    bar.style.width = "100%";
}

function hideProgressBar() {
    const wrap = document.getElementById("loadMoreProgress");
    const bar = document.querySelector(".load-more-progress-bar");
    if (wrap) wrap.style.display = "none";
    if (bar) bar.style.width = "0%";
}

// ================== ИНФОРМАЦИЯ ==================
function updateHistoryInfo() {
    const info = document.getElementById("historyInfo");
    const count = document.getElementById("historyCount");
    if (!info) return;

    if (!allHistory.length) {
        info.textContent = "";
        if (count) count.textContent = "";
        return;
    }

    const dates = allHistory
        .map(r => new Date(r.date).getTime())
        .filter(t => !isNaN(t))
        .sort((a, b) => a - b);

    const fmt = (d) => d.toLocaleDateString("ru-RU", {
        day: "2-digit", month: "2-digit", year: "numeric"
    });

    if (dates.length) {
        const first = new Date(dates[0]);
        const last = new Date(dates[dates.length - 1]);
        const days = Math.max(1, Math.round((last - first) / (1000 * 60 * 60 * 24)));
        info.textContent = `Загружено ${allHistory.length} продаж за период ${fmt(first)} — ${fmt(last)} (${days} дн.)`;
    } else {
        info.textContent = `Загружено ${allHistory.length} продаж`;
    }
    if (count) count.textContent = `(${allHistory.length})`;
}

function updateRefreshTime() {
    const now = new Date();
    const el = document.getElementById("refreshTime");
    if (el) {
        el.textContent = "Данные обновлены: " + now.toLocaleString("ru-RU", {
            day: "2-digit", month: "2-digit", year: "numeric",
            hour: "2-digit", minute: "2-digit",
        });
    }
}

// 🆕 Догрузка максимума в фоне (если бэкенд вернул меньше)
async function refreshHistoryInBackground() {
    // Ждём 5 секунд — даём серверу время догрузить остальное в фоне
    await new Promise(res => setTimeout(res, 5000));

    try {
        const r = await fetch(`/api/items/${ITEM_ID}/history/deep?limit=${DEEP_LIMIT}`);
        const data = r.ok ? await r.json() : [];

        if (Array.isArray(data) && data.length > allHistory.length) {
            const growth = data.length - allHistory.length;
            const growthPercent = growth / allHistory.length;

            allHistory = data;
            _allHistoryLoaded = data.length < DEEP_LIMIT;

            // 🔑 Рендерим только если прирост > 5%
            if (growthPercent > 0.05 || allHistory.length < 500) {
                applyFilters();
                renderTables();
            }
        } else {
            _allHistoryLoaded = true;
        }
    } catch (e) {
        console.warn("[StalSell] Фоновая догрузка не удалась", e);
    }
}

// ================== ПРОГРЕСС-БАР ==================
function startProgressBar() {
    const bar = document.querySelector(".load-more-progress-bar");
    const wrap = document.getElementById("loadMoreProgress");
    if (!bar || !wrap) return;
    wrap.style.display = "block";
    bar.style.width = "0%";
    let progress = 0;
    _progressTimer = setInterval(() => {
        if (progress < 40) progress += 5;
        else if (progress < 75) progress += 2;
        else progress += 0.5;
        if (progress > 92) progress = 92;
        bar.style.width = progress + "%";
    }, 100);
}

function finishProgressBar() {
    const bar = document.querySelector(".load-more-progress-bar");
    if (!bar) return;
    if (_progressTimer) { clearInterval(_progressTimer); _progressTimer = null; }
    bar.style.width = "100%";
}

function hideProgressBar() {
    const wrap = document.getElementById("loadMoreProgress");
    const bar = document.querySelector(".load-more-progress-bar");
    if (wrap) wrap.style.display = "none";
    if (bar) bar.style.width = "0%";
}

// ================== ИНФОРМАЦИЯ ==================
function updateHistoryInfo() {
    const info = document.getElementById("historyInfo");
    const count = document.getElementById("historyCount");
    if (!info) return;

    if (!allHistory.length) {
        info.textContent = "";
        if (count) count.textContent = "";
        return;
    }

    const dates = allHistory
        .map(r => new Date(r.date).getTime())
        .filter(t => !isNaN(t))
        .sort((a, b) => a - b);

    const fmt = (d) => d.toLocaleDateString("ru-RU", {
        day: "2-digit", month: "2-digit", year: "numeric"
    });

    if (dates.length) {
        const first = new Date(dates[0]);
        const last = new Date(dates[dates.length - 1]);
        const days = Math.max(1, Math.round((last - first) / (1000 * 60 * 60 * 24)));
        info.textContent = `Загружено ${allHistory.length} продаж за период ${fmt(first)} — ${fmt(last)} (${days} дн.)`;
    } else {
        info.textContent = `Загружено ${allHistory.length} продаж`;
    }
    if (count) count.textContent = `(${allHistory.length})`;
}

function updateRefreshTime() {
    const now = new Date();
    const el = document.getElementById("refreshTime");
    if (el) {
        el.textContent = "Данные обновлены: " + now.toLocaleString("ru-RU", {
            day: "2-digit", month: "2-digit", year: "numeric",
            hour: "2-digit", minute: "2-digit",
        });
    }
}