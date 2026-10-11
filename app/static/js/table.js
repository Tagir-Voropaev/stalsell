// ================== ТАБЛИЦА ==================
function toggleTable() {
    const t = document.getElementById("tableView");
    const btn = document.getElementById("toggleTableBtn");
    if (!t) return;

    const isHidden = t.style.display === "none";
    t.style.display = isHidden ? "block" : "none";

    if (btn) {
        btn.innerHTML = isHidden
            ? '<i class="bi bi-chevron-up"></i> Скрыть таблицу'
            : '<i class="bi bi-table"></i> Показать таблицу';
    }
    if (isHidden) t.scrollIntoView({ behavior: "smooth", block: "start" });
}

function renderTables() {
    // 🛡️ Защита: если блоков нет в HTML — просто выходим
    const lotsContainer = document.getElementById("lotsContainer");
    const histContainer = document.getElementById("historyContainer");

    if (!lotsContainer && !histContainer) return;  // нет ни одного — не наша забота

    if (lotsContainer) {
        if (!filteredLots.length) {
            lotsContainer.innerHTML = '<p class="empty">Нет лотов по фильтру.</p>';
        } else {
            lotsContainer.innerHTML = "";
            filteredLots.slice(0, 30).forEach(lot => lotsContainer.appendChild(renderRecord(lot, "lot")));
            if (filteredLots.length > 30) {
                lotsContainer.innerHTML += `<p class="empty">... ещё ${filteredLots.length - 30} лотов</p>`;
            }
        }
    }

    if (histContainer) {
        if (!filteredHistory.length) {
            histContainer.innerHTML = '<p class="empty">Нет продаж по фильтру.</p>';
        } else {
            histContainer.innerHTML = "";
            filteredHistory.slice(0, 30).forEach(rec => histContainer.appendChild(renderRecord(rec, "history")));
            if (filteredHistory.length > 30) {
                histContainer.innerHTML += `<p class="empty">... ещё ${filteredHistory.length - 30} записей</p>`;
            }
        }
    }
}

function renderRecord(rec, type) {
    const row = document.createElement("div");
    row.className = "record-row";

    const dateRaw = rec.date || rec.start_time;
    let dateStr = "—";
    if (dateRaw) {
        const date = new Date(dateRaw);
        if (!isNaN(date.getTime()) && date.getFullYear() > 2000) {
            dateStr = date.toLocaleString("ru-RU", {
                day: "2-digit", month: "2-digit", year: "numeric",
                hour: "2-digit", minute: "2-digit",
            });
        }
    }

    const q = getQualityInfo(rec.qlt);
    const qualityBadge = q
        ? `<span class="badge" style="background:${q.color}22; color:${q.color}; border:1px solid ${q.color}">${q.name}</span>` : "";
    const ptnBadge = (rec.ptn !== null && rec.ptn !== undefined)
        ? `<span class="badge badge-ptn">+${rec.ptn}</span>` : "";

    let bonusStr = "";
    if (rec.bonus_properties && rec.bonus_properties.length) {
        bonusStr = `<div class="bonuses">${rec.bonus_properties.map(b => `<span class="bonus">${b}</span>`).join("")}</div>`;
    }

    const price = type === "lot"
        ? (rec.buyout_price || rec.start_price || 0)
        : (rec.price || 0);
    const priceStr = price > 0 ? `${price.toLocaleString("ru-RU")} руб.` : "—";

    let endStr = "";
    if (type === "lot" && rec.end_time) {
        const endDate = new Date(rec.end_time);
        if (!isNaN(endDate.getTime()) && endDate.getFullYear() > 2000) {
            endStr = `<span class="end-time">до ${endDate.toLocaleString("ru-RU", {
                day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit",
            })}</span>`;
        }
    }

    const amountStr = rec.amount && rec.amount > 1 ? `<span class="amount">x${rec.amount}</span>` : "";

    row.innerHTML = `
        <div class="record-main">
            <div class="record-badges">${qualityBadge} ${ptnBadge}</div>
            <div class="record-info">
                <span class="record-date">${dateStr}</span>
                ${amountStr}
                ${endStr}
            </div>
            <div class="record-price">${priceStr}</div>
        </div>
        ${bonusStr}`;
    return row;
}