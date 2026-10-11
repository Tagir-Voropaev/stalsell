// ================== АВТОКОМПЛИТ ==================
const DEBOUNCE_MS = 180;
const SUGGEST_LIMIT = 8;

let _suggestions = [];
let _activeIndex = -1;
let _debounceTimer = null;
let _lastQuery = "";
let _searchBox = null;
let _searchInput = null;

function initSearch(inputId, boxId) {
    _searchBox = document.getElementById(boxId);
    _searchInput = document.getElementById(inputId);
    if (!_searchInput || !_searchBox) return;

    _searchInput.addEventListener("input", onSearchInput);
    _searchInput.addEventListener("keydown", onSearchKeydown);
    _searchInput.addEventListener("focus", onSearchFocus);

    document.addEventListener("click", (e) => {
        const wrapper = _searchInput.closest(".hero-search, .search-wrapper, #searchContainer");
        if (wrapper && !wrapper.contains(e.target)) {
            hideSuggestions();
        }
    });
}

function onSearchInput() {
    const q = _searchInput.value.trim();
    if (_debounceTimer) clearTimeout(_debounceTimer);
    if (!q) { hideSuggestions(); return; }
    if (q === _lastQuery && _suggestions.length) { renderSuggestions(); return; }
    showLoading();
    _debounceTimer = setTimeout(() => fetchSuggestions(q), DEBOUNCE_MS);
}

function onSearchFocus() {
    const q = _searchInput.value.trim();
    if (q && _suggestions.length) renderSuggestions();
}

function onSearchKeydown(e) {
    if (e.key === "Escape") { hideSuggestions(); _searchInput.blur(); return; }
    if (e.key === "Enter") {
        e.preventDefault();
        if (_activeIndex >= 0 && _suggestions[_activeIndex]) {
            goToItem(_suggestions[_activeIndex]);
        } else if (_suggestions.length > 0) {
            goToItem(_suggestions[0]);
        }
        return;
    }
    if (e.key === "ArrowDown") {
        e.preventDefault();
        if (!_suggestions.length) return;
        setActiveIndex(Math.min(_activeIndex + 1, _suggestions.length - 1));
    }
    if (e.key === "ArrowUp") {
        e.preventDefault();
        if (!_suggestions.length) return;
        setActiveIndex(Math.max(_activeIndex - 1, 0));
    }
}

async function fetchSuggestions(query) {
    try {
        const url = `/api/items/search?q=${encodeURIComponent(query)}&limit=${SUGGEST_LIMIT}`;
        const items = await (await fetch(url)).json();
        _lastQuery = query;
        _suggestions = items || [];
        _activeIndex = -1;
        if (!_suggestions.length) { showEmpty(); return; }
        renderSuggestions();
    } catch (e) { hideSuggestions(); }
}

function renderSuggestions() {
    if (!_searchBox) return;
    _searchBox.innerHTML = "";

    _suggestions.forEach((item, i) => {
        const row = document.createElement("div");
        row.className = "suggestion-item";

        // Краткие названия категорий
        const catLabels = {
            "artefact": "Артефакт",
            "weapon": "Оружие",
            "armor": "Броня",
            "other": "Прочее",
        };
        const catLabel = item.category ? (catLabels[item.category] || item.category) : "";

        row.innerHTML = `
            <span class="suggestion-name">${item.name}</span>
            ${catLabel ? `<span class="suggestion-cat">${catLabel}</span>` : `<span class="suggestion-id">${item.id}</span>`}
        `;
        row.addEventListener("click", () => goToItem(item));
        row.addEventListener("mouseenter", () => setActiveIndex(i));
        _searchBox.appendChild(row);
    });

    _searchBox.style.display = "block";
}

function setActiveIndex(i) {
    _activeIndex = i;
    document.querySelectorAll(".suggestion-item").forEach((el, idx) => {
        el.classList.toggle("active", idx === i);
    });
}

function showLoading() {
    if (!_searchBox) return;
    _searchBox.innerHTML = '<div class="suggestion-loading">Поиск...</div>';
    _searchBox.style.display = "block";
}

function showEmpty() {
    if (!_searchBox) return;
    _searchBox.innerHTML = '<div class="suggestion-empty">Ничего не найдено</div>';
    _searchBox.style.display = "block";
}

function hideSuggestions() {
    if (_searchBox) _searchBox.style.display = "none";
    _activeIndex = -1;
}

function goToItem(item) {
    if (!item || !item.id) return;
    window.location.href = `/static/item.html?id=${item.id}`;
}

function goToFirstSuggestion() {
    if (_suggestions.length > 0) {
        goToItem(_suggestions[_activeIndex >= 0 ? _activeIndex : 0]);
    } else if (_searchInput && _searchInput.value.trim()) {
        _searchInput.focus();
    }
}

function quickSearch(query) {
    if (!_searchInput) return;
    _searchInput.value = query;
    _lastQuery = "";
    _suggestions = [];
    onSearchInput();
    _searchInput.focus();
}
// ================== ПОИСК ПО КАТЕГОРИИ ==================
async function quickCategorySearch(category) {
    if (!_searchInput || !_searchBox) {
        console.warn('[StalSell] Search не инициализирован');
        return;
    }

    // Очищаем поле
    _searchInput.value = "";
    _lastQuery = "";
    _suggestions = [];
    _activeIndex = -1;

    // Показываем загрузку
    _searchBox.innerHTML = '<div class="suggestion-loading">Поиск...</div>';
    _searchBox.style.display = "block";

    try {
        const url = `/api/items/search?cat=${encodeURIComponent(category)}&limit=15`;
        console.log('[StalSell] Запрос категории:', url);

        const r = await fetch(url);
        console.log('[StalSell] Статус:', r.status);

        if (!r.ok) {
            _searchBox.innerHTML = `<div class="suggestion-empty">Ошибка: ${r.status}</div>`;
            return;
        }

        const items = await r.json();
        console.log('[StalSell] Получено предметов:', items.length);

        _suggestions = Array.isArray(items) ? items : [];

        if (!_suggestions.length) {
            _searchBox.innerHTML = '<div class="suggestion-empty">В этой категории ничего не найдено</div>';
            return;
        }

        renderSuggestions();
    } catch (e) {
        console.error('[StalSell] Ошибка:', e);
        _searchBox.innerHTML = '<div class="suggestion-empty">Ошибка поиска</div>';
    }
}