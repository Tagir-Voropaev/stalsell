// ================== ФИЛЬТРЫ ==================
function setupFilters() {
    document.querySelectorAll(".q-btn").forEach(btn => {
        btn.addEventListener("click", () => {
            const qlt = parseInt(btn.dataset.qlt);
            if (selectedQlt === qlt) {
                selectedQlt = null;
                btn.classList.remove("active");
            } else {
                selectedQlt = qlt;
                document.querySelectorAll(".q-btn").forEach(b => b.classList.remove("active"));
                btn.classList.add("active");
            }
            applyFilters();
            renderTables();
        });
    });

    document.querySelectorAll(".lvl-btn").forEach(btn => {
        btn.addEventListener("click", () => {
            const min = parseInt(btn.dataset.min);
            const max = parseInt(btn.dataset.max);
            const isSame = selectedLevelRange &&
                selectedLevelRange.min === min && selectedLevelRange.max === max;

            if (isSame) {
                selectedLevelRange = null;
                btn.classList.remove("active");
            } else {
                selectedLevelRange = { min, max };
                document.querySelectorAll(".lvl-btn").forEach(b => b.classList.remove("active"));
                btn.classList.add("active");
            }
            applyFilters();
            renderTables();
        });
    });
}

function resetFilters() {
    selectedQlt = null;
    selectedLevelRange = null;
    document.querySelectorAll(".q-btn, .lvl-btn").forEach(b => b.classList.remove("active"));
    applyFilters();
    renderTables();
}

function applyFilters() {
    filteredLots = allLots.filter(matchFilters);
    filteredHistory = allHistory.filter(matchFilters);

    // 🆕 Без фильтров — показываем только последние DISPLAY_NO_FILTER записей
    const hasFilter = selectedQlt !== null || selectedLevelRange !== null;
    if (!hasFilter) {
        filteredHistory = filteredHistory.slice(0, DISPLAY_NO_FILTER);
    }

    renderChart();
    updateStats();
    updateEmptyFilterMessage();

    _autoLoadGeneration++;
    maybeAutoLoadForFilter(_autoLoadGeneration);
}

// ================== СТАТИСТИКА ==================
function updateStats() {
    const prices = filteredHistory.map(r => r.price).filter(p => p > 0);
    const avgEl = document.getElementById("statAvg");
    const maxEl = document.getElementById("statMax");
    const minEl = document.getElementById("statMin");

    if (!prices.length) {
        [avgEl, maxEl, minEl].forEach(el => { if (el) el.textContent = "—"; });
        return;
    }

    const min = Math.min(...prices);
    const max = Math.max(...prices);
    const avg = prices.reduce((s, p) => s + p, 0) / prices.length;

    if (avgEl) avgEl.textContent = Math.round(avg).toLocaleString("ru-RU");
    if (maxEl) maxEl.textContent = max.toLocaleString("ru-RU");
    if (minEl) minEl.textContent = min.toLocaleString("ru-RU");
}

// ================== ПУСТОЙ ФИЛЬТР ==================
function updateEmptyFilterMessage() {
    const hasFilter = selectedQlt !== null || selectedLevelRange !== null;
    const isEmpty = filteredHistory.length === 0 && filteredLots.length === 0;
    const msgBox = document.getElementById("emptyFilterMsg");

    if (!msgBox) return;

    if (!hasFilter || !isEmpty) {
        msgBox.style.display = "none";
        return;
    }

    const filterLabel = getFilterDescription();

    if (_autoLoading) {
        msgBox.innerHTML = `
            <div class="empty-filter-icon pulse">🔍</div>
            <h3>Ищем редкие продажи...</h3>
            <p>Проверено ${allHistory.length} записей</p>
            <p class="empty-filter-hint">Это может занять до минуты</p>
        `;
    } else if (_allHistoryLoaded || allHistory.length >= AUTO_LOAD_MAX_TOTAL) {
        msgBox.innerHTML = `
            <div class="empty-filter-icon">🔍</div>
            <h3>В истории нет предметов этой категории</h3>
            <p>Фильтр: «${filterLabel}»</p>
            <p class="empty-filter-hint">Проверено ${allHistory.length} записей</p>
        `;
    } else {
        msgBox.innerHTML = `
            <div class="empty-filter-icon">🔍</div>
            <h3>Среди последних ${allHistory.length} продаж</h3>
            <p>нет предложений «${filterLabel}»</p>
        `;
    }

    msgBox.style.display = "flex";
}

// ================== АВТОДОГРУЗКА ПОД ФИЛЬТР ==================
async function maybeAutoLoadForFilter(generation) {
    const hasFilter = selectedQlt !== null || selectedLevelRange !== null;
    if (!hasFilter) return;
    if (filteredHistory.length >= AUTO_LOAD_MIN_MATCHES) return;
    if (_allHistoryLoaded) return;
    if (allHistory.length >= AUTO_LOAD_MAX_TOTAL) return;
    if (_autoLoading) return;

    _autoLoading = true;
    const info = document.getElementById("loadMoreChartInfo");
    const startedAt = Date.now();

    if (info) {
        info.textContent = `Ищем редкие продажи... проверено ${allHistory.length}, найдено ${filteredHistory.length}`;
        info.style.color = "var(--accent)";
    }
    updateEmptyFilterMessage();

    try {
        let prevCount = filteredHistory.length;
        let emptyStreak = 0;

        while (
            !_allHistoryLoaded &&
            allHistory.length < AUTO_LOAD_MAX_TOTAL &&
            emptyStreak < AUTO_LOAD_MAX_EMPTY_STREAK &&
            generation === _autoLoadGeneration
        ) {
            const targetLimit = Math.min(
                allHistory.length + AUTO_LOAD_STEP,
                AUTO_LOAD_MAX_TOTAL
            );

            if (info) {
                const elapsed = Math.round((Date.now() - startedAt) / 1000);
                info.textContent = `Проверено ${allHistory.length} из ${AUTO_LOAD_MAX_TOTAL} · найдено ${filteredHistory.length} · ${elapsed}с`;
                info.style.color = "var(--accent)";
            }

            try {
                const r = await fetch(`/api/items/${ITEM_ID}/history/deep?limit=${targetLimit}`);
                const data = r.ok ? await r.json() : [];

                if (!Array.isArray(data) || !data.length || data.length <= allHistory.length) {
                    _allHistoryLoaded = true;
                    break;
                }

                allHistory = data;
                _allHistoryLoaded = data.length < targetLimit;

                filteredLots = allLots.filter(matchFilters);
                filteredHistory = allHistory.filter(matchFilters);

                // 🔑 Рендерим график только если фильтр вернул новые точки
                const prevFiltered = prevCount;
                const newFiltered = filteredHistory.length;

                if (newFiltered !== prevFiltered || newFiltered < 20) {
                    renderChart();
                    updateStats();
                }
                updateEmptyFilterMessage();

                const newCount = filteredHistory.length;
                if (newCount === prevCount) {
                    emptyStreak++;
                } else {
                    emptyStreak = 0;
                }
                prevCount = newCount;

                if (allHistory.length >= AUTO_LOAD_MAX_TOTAL) break;

            } catch (e) {
                console.error("[StalSell] Ошибка автодогрузки:", e);
                break;
            }
        }

        // Финальный статус
        if (info) {
            const total = allHistory.length;
            if (filteredHistory.length === 0) {
                info.textContent = `В истории нет предметов этой категории (проверено ${total})`;
                info.style.color = "var(--text-dim)";
            } else {
                info.textContent = `Найдено ${filteredHistory.length} записей «${getFilterDescription()}» (проверено ${total})`;
                info.style.color = "#4caf50";
            }
        }

        updateEmptyFilterMessage();
    } finally {
        _autoLoading = false;
    }
}