// ================== ГРАФИК ==================
function renderChart() {
    let points = filteredHistory
        .filter(r => r.price > 0 && r.date)
        .map(r => ({ x: new Date(r.date), y: r.price, qlt: r.qlt, ptn: r.ptn }))
        .sort((a, b) => a.x - b.x);

    // Прореживание до 800 точек для SVG-рендера
    const MAX_CHART_POINTS = 800;
    if (points.length > MAX_CHART_POINTS) {
        const step = Math.ceil(points.length / MAX_CHART_POINTS);
        const thinned = [];
        for (let i = 0; i < points.length; i += step) {
            const chunk = points.slice(i, i + step);
            chunk.sort((a, b) => a.y - b.y);
            thinned.push(chunk[Math.floor(chunk.length / 2)]);
        }
        points = thinned;
    }

    currentHistoryPoints = points;

    if (currentHistoryPoints.length) {
        const times = currentHistoryPoints.map(p => p.x.getTime());
        const ys = currentHistoryPoints.map(p => p.y).filter(y => y > 0);
        _globalTMin = Math.min(...times);
        _globalTMax = Math.max(...times);
        _globalYMin = Math.min(...ys);
        _globalYMax = Math.max(...ys);
    }

    const traces = [];
    if (currentHistoryPoints.length) {
        const pointColors = currentHistoryPoints.map(p => {
            const q = getQualityInfo(p.qlt);
            return q ? q.color : "#888";
        });
        const baseSizes = currentHistoryPoints.map(() => BASE_POINT_SIZE);

        traces.push({
            x: currentHistoryPoints.map(p => p.x),
            y: currentHistoryPoints.map(p => p.y),
            mode: "markers",
            type: "scatter",
            name: "Продажи",
            cliponaxis: false,
            marker: {
                size: baseSizes,
                color: pointColors,
                opacity: 0.85,
                line: { width: 0, color: "rgba(0,0,0,0)" },
            },
            hoverinfo: "none",
            hovertemplate: "",
        });
    }

    const initialYRange = computeYRange(currentHistoryPoints);
    const initialXRange = _globalTMax > _globalTMin
        ? addXPad([_globalTMin, _globalTMax]) : undefined;

    const layout = {
        paper_bgcolor: "rgba(0,0,0,0)",
        plot_bgcolor: "rgba(0,0,0,0)",
        font: {
            color: "#dcdde3",
            family: "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
            size: 14,
        },
        xaxis: {
            gridcolor: "rgba(255,255,255,0.05)",
            title: {
                text: "Дата",
                font: { size: 15, color: AXIS_LABEL_COLOR, family: "Inter, sans-serif" },
                standoff: 15,
            },
            type: "date",
            range: initialXRange ? initialXRange.map(t => new Date(t)) : undefined,
            autorange: !initialXRange,
            fixedrange: false,
            tickfont: { size: 13, color: AXIS_TICK_COLOR, family: "Inter, sans-serif" },
            linecolor: "rgba(255,255,255,0.15)",
            zeroline: false,
            tickformat: "%d.%m.%y",
            tickangle: 0,
            automargin: true,
        },
        yaxis: {
            gridcolor: "rgba(255,255,255,0.05)",
            title: {
                text: "Цена, ₽",
                font: { size: 15, color: AXIS_LABEL_COLOR, family: "Inter, sans-serif" },
                standoff: 20,
            },
            type: "linear",
            range: initialYRange,
            fixedrange: true,
            autorange: false,
            tickfont: { size: 13, color: AXIS_TICK_COLOR, family: "Inter, sans-serif" },
            linecolor: "rgba(255,255,255,0.15)",
            tickformat: ",.0f",
            zeroline: false,
        },
        hovermode: "closest",
        hoverdistance: 10,
        hoverlabel: {
            bgcolor: "rgba(0,0,0,0)",
            bordercolor: "rgba(0,0,0,0)",
            font: { color: "rgba(0,0,0,0)", size: 1 },
        },
        margin: { l: 130, r: 25, t: 20, b: 90 },
        showlegend: false,
        dragmode: "pan",
        uirevision: ITEM_ID,
    };

    const config = {
        responsive: true,
        displayModeBar: false,
        scrollZoom: false,
        doubleClick: false,
        doubleClickDelay: 0,
    };

    const reattach = () => {
        setupManualWheelZoom();
        setupPanYTracker();
        setupCustomTooltip();
    };

    if (_plotInitialized) {
        Plotly.react("priceChart", traces, layout, config).then(reattach);
    } else {
        Plotly.newPlot("priceChart", traces, layout, config).then(() => {
            _plotInitialized = true;
            const skel = document.getElementById("chartSkeleton");
            if (skel) skel.classList.add("hidden");
            reattach();
        });
    }
}

// ================== КАСТОМНЫЙ ТУЛТИП ==================
function setupCustomTooltip() {
    const chartEl = document.getElementById("priceChart");
    const tooltip = document.getElementById("customTooltip");
    if (!chartEl || !tooltip) return;

    let hideTimer = null;

    chartEl.removeAllListeners("plotly_hover");
    chartEl.removeAllListeners("plotly_unhover");

    chartEl.on("plotly_hover", (data) => {
        if (!data.points || !data.points.length) return;
        if (hideTimer) { clearTimeout(hideTimer); hideTimer = null; }

        const p = data.points[0];
        const idx = p.pointNumber;

        // Берём qlt/ptn из исходного массива
        const sourcePoint = currentHistoryPoints[idx] || {};
        const qlt = sourcePoint.qlt;
        const ptn = sourcePoint.ptn;

        const q = getQualityInfo(qlt);
        const ptnStr = (ptn !== null && ptn !== undefined) ? `+${ptn}` : "";
        const qColor = q ? q.color : "#888";
        const qName = q ? q.name : "Без редкости";

        const date = new Date(p.x).toLocaleString("ru-RU", {
            day: "2-digit", month: "2-digit", year: "numeric",
            hour: "2-digit", minute: "2-digit",
        });

        tooltip.innerHTML = `
            <div class="tt-header">
                <span class="tt-quality-dot" style="background:${qColor};box-shadow:0 0 8px ${qColor}"></span>
                <span class="tt-quality" style="color:${qColor}">${qName}</span>
                ${ptnStr ? `<span class="tt-ptn">${ptnStr}</span>` : ""}
            </div>
            <div class="tt-price">${p.y.toLocaleString("ru-RU")} ₽</div>
            <div class="tt-date">${date}</div>
        `;

        tooltip.style.visibility = "hidden";
        tooltip.style.opacity = "0";
        tooltip.style.display = "block";
        tooltip.style.transform = "scale(0.95)";

        const tw = tooltip.offsetWidth;
        const th = tooltip.offsetHeight;

        const evt = data.event;
        const mouseX = evt.clientX;
        const mouseY = evt.clientY;

        // Слева от курсора, при нехватке места — справа
        let left = mouseX - tw - 20;
        let top = mouseY - th / 2;

        if (left < 10) left = mouseX + 20;
        if (top < 10) top = 10;
        if (top + th > window.innerHeight - 10) top = window.innerHeight - th - 10;

        tooltip.style.left = left + "px";
        tooltip.style.top = top + "px";
        tooltip.style.visibility = "visible";

        requestAnimationFrame(() => {
            tooltip.style.opacity = "1";
            tooltip.style.transform = "scale(1)";
        });
    });

    chartEl.on("plotly_unhover", () => {
        if (hideTimer) clearTimeout(hideTimer);
        hideTimer = setTimeout(() => {
            tooltip.style.opacity = "0";
            tooltip.style.transform = "scale(0.95)";
            setTimeout(() => {
                if (tooltip.style.opacity === "0") tooltip.style.display = "none";
            }, 180);
        }, 40);
    });
}

// ================== ЗУМ (колёсико) ==================
function setupManualWheelZoom() {
    const chartEl = document.getElementById("priceChart");
    const dragLayer = chartEl.querySelector(".nsewdrag") || chartEl;

    if (_wheelHandler && _wheelTarget) {
        _wheelTarget.removeEventListener("wheel", _wheelHandler);
    }
    _wheelHandler = (e) => { e.preventDefault(); e.stopPropagation(); queueZoom(e); };
    dragLayer.addEventListener("wheel", _wheelHandler, { passive: false });
    _wheelTarget = dragLayer;
}

function queueZoom(e) {
    const chartEl = document.getElementById("priceChart");
    if (!chartEl.layout || !chartEl.layout.xaxis.range) return;

    let delta = e.deltaY;
    if (e.deltaMode === 1) delta *= 16;
    else if (e.deltaMode === 2) delta *= 40;
    delta = Math.max(-120, Math.min(120, delta));

    const factor = Math.pow(ZOOM_BASE, delta);
    const [curX0, curX1] = _pendingXRange || getXRange(chartEl);

    const dragLayer = chartEl.querySelector(".nsewdrag") || chartEl;
    const rect = dragLayer.getBoundingClientRect();
    const relX = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
    const mouseT = curX0 + (curX1 - curX0) * relX;

    let newX0 = mouseT + (curX0 - mouseT) * factor;
    let newX1 = mouseT + (curX1 - mouseT) * factor;

    const fullSpan = (_globalTMax - _globalTMin) || 1;
    const pad = fullSpan * X_PADDING;
    const absMin = _globalTMin - pad;
    const absMax = _globalTMax + pad;
    const maxSpan = absMax - absMin;
    const minSpan = fullSpan * 0.01;

    if (newX1 - newX0 < minSpan) {
        const mid = (newX0 + newX1) / 2;
        newX0 = mid - minSpan / 2;
        newX1 = mid + minSpan / 2;
    }
    if (newX1 - newX0 > maxSpan) {
        const mid = (newX0 + newX1) / 2;
        newX0 = mid - maxSpan / 2;
        newX1 = mid + maxSpan / 2;
    }
    if (newX0 < absMin) { newX1 += (absMin - newX0); newX0 = absMin; }
    if (newX1 > absMax) { newX0 -= (newX1 - absMax); newX1 = absMax; }

    const hasPoints = currentHistoryPoints.some(p => {
        const t = p.x.getTime(); return t >= newX0 && t <= newX1;
    });
    if (!hasPoints) return;

    const visible = currentHistoryPoints.filter(p => {
        const t = p.x.getTime(); return t >= newX0 && t <= newX1;
    });

    _pendingXRange = [newX0, newX1];
    _pendingYRange = computeYRange(visible);

    if (!_rafId) _rafId = requestAnimationFrame(flushPendingZoom);
}

function flushPendingZoom() {
    _rafId = null;
    if (!_pendingXRange || !_pendingYRange) return;
    const chartEl = document.getElementById("priceChart");
    const xr = _pendingXRange, yr = _pendingYRange;
    _pendingXRange = null; _pendingYRange = null;
    Plotly.relayout(chartEl, {
        "xaxis.range": [new Date(xr[0]), new Date(xr[1])],
        "yaxis.range": yr,
    });
}

// ================== ПАНОРАМИРОВАНИЕ (ЛКМ) ==================
function setupPanYTracker() {
    const chartEl = document.getElementById("priceChart");
    if (!chartEl) return;
    chartEl.removeAllListeners("plotly_relayout");
    chartEl.on("plotly_relayout", onRelayout);
}

function onRelayout(eventData) {
    const hasX = eventData["xaxis.range[0]"] !== undefined
              || eventData["xaxis.range"] !== undefined
              || eventData["xaxis.autorange"] !== undefined;
    const hasY = eventData["yaxis.range[0]"] !== undefined
              || eventData["yaxis.range"] !== undefined;
    if ((hasX && hasY) || (hasY && !hasX)) return;

    const chartEl = document.getElementById("priceChart");
    if (!chartEl) return;

    const [x0, x1] = getXRange(chartEl);
    const fullSpan = (_globalTMax - _globalTMin) || 1;
    const pad = fullSpan * X_PADDING;
    const absMin = _globalTMin - pad;
    const absMax = _globalTMax + pad;
    const maxSpan = absMax - absMin;

    let c0 = x0, c1 = x1, needFix = false;
    if (x1 - x0 > maxSpan) {
        const c = (x0 + x1) / 2;
        c0 = c - maxSpan / 2; c1 = c + maxSpan / 2; needFix = true;
    }
    if (c0 < absMin) { c1 += (absMin - c0); c0 = absMin; needFix = true; }
    if (c1 > absMax) { c0 -= (c1 - absMax); c1 = absMax; needFix = true; }
    if (c0 < absMin) { c0 = absMin; c1 = Math.min(absMax, c0 + (x1 - x0)); needFix = true; }

    if (needFix) {
        const visible = currentHistoryPoints.filter(p => {
            const t = p.x.getTime(); return t >= c0 && t <= c1;
        });
        Plotly.relayout(chartEl, {
            "xaxis.range": [new Date(c0), new Date(c1)],
            "yaxis.range": visible.length ? computeYRange(visible) : chartEl.layout.yaxis.range,
        });
        return;
    }

    if (_panDebounce) clearTimeout(_panDebounce);
    _panDebounce = setTimeout(() => {
        _panDebounce = null;
        applyPanY(eventData);
    }, 50);
}

function applyPanY(eventData) {
    const chartEl = document.getElementById("priceChart");
    if (!chartEl) return;
    let newYRange = null;

    if (eventData["xaxis.autorange"]) {
        newYRange = computeYRange(currentHistoryPoints);
    } else {
        const [x0, x1] = getXRange(chartEl);
        const visible = currentHistoryPoints.filter(p => {
            const t = p.x.getTime(); return t >= x0 && t <= x1;
        });
        if (visible.length) newYRange = computeYRange(visible);
    }
    if (!newYRange) return;

    const curY = chartEl.layout.yaxis.range;
    if (curY && Math.abs(curY[0] - newYRange[0]) < 0.001 * newYRange[0]
             && Math.abs(curY[1] - newYRange[1]) < 0.001 * newYRange[1]) return;

    Plotly.relayout(chartEl, { "yaxis.range": newYRange });
}