// ================== КОНСТАНТЫ ==================
const QUALITY_MAP = {
    0: { name: "Обычный", color: "#9e9e9e" },
    1: { name: "Необычный", color: "#4caf50" },
    2: { name: "Особый", color: "#2196f3" },
    3: { name: "Редкий", color: "#9c27b0" },
    4: { name: "Исключительный", color: "#f44336" },
    5: { name: "Легендарный", color: "#ffc107" },
};

const ACCENT = "#FF8C00";
const ACCENT_LIGHT = "#ffb74d";
const AXIS_LABEL_COLOR = "#FFB74D";
const AXIS_TICK_COLOR = "#C8C8C8";

const ZOOM_BASE = 1.0025;
const X_PADDING = 0.05;
const BASE_POINT_SIZE = 5;
const HOVER_POINT_SIZE = 9;

const QUICK_LIMIT = 1000;
const DEEP_LIMIT = 50000;
const DISPLAY_NO_FILTER = 1000;

const AUTO_LOAD_MIN_MATCHES = 50;
const AUTO_LOAD_MAX_TOTAL = 50000;
const AUTO_LOAD_STEP = 10000;
const AUTO_LOAD_MAX_EMPTY_STREAK = 20;

// ================== ГЛОБАЛЬНОЕ СОСТОЯНИЕ ==================
var params = new URLSearchParams(window.location.search);
var ITEM_ID = params.get("id");

var allLots = [];
var allHistory = [];
var filteredLots = [];
var filteredHistory = [];
var selectedQlt = null;
var selectedLevelRange = null;

var currentHistoryPoints = [];
var _globalYMin = 0, _globalYMax = 1000;
var _globalTMin = 0, _globalTMax = 1;

var _panDebounce = null;
var _wheelHandler = null, _wheelTarget = null;
var _pendingXRange = null, _pendingYRange = null, _rafId = null;

var _allHistoryLoaded = false;
var _loadingMore = false;
var _plotInitialized = false;

var _prefetchedRecords = null;
var _prefetchOffset = null;
var _prefetching = false;
var _clickCount = 0;

var _progressTimer = null;

var _autoLoading = false;
var _autoLoadGeneration = 0;

// ================== УТИЛИТЫ ==================
function getQualityInfo(qlt) {
    if (qlt === null || qlt === undefined) return null;
    return QUALITY_MAP[qlt] || { name: `Q${qlt}`, color: "#666" };
}

function computeYRange(points) {
    const ys = points.map(p => p.y).filter(y => y > 0);
    if (!ys.length) return [_globalYMin, _globalYMax];

    let min = Math.min(...ys), max = Math.max(...ys);

    if (min === max) {
        const base = Math.max(min * 0.05, 100);
        min = Math.max(0, min - base); max = max + base;
    }

    const pad = (max - min) * 0.08;
    min = Math.max(0, min - pad); max = max + pad;

    const fullRange = _globalYMax - _globalYMin;
    const minWindow = Math.max(fullRange * 0.25, 100);
    if (max - min < minWindow) {
        const c = (min + max) / 2;
        min = Math.max(0, c - minWindow / 2);
        max = c + minWindow / 2;
    }
    return [min, max];
}

function addXPad(range) {
    const [x0, x1] = range;
    const pad = (x1 - x0) * X_PADDING;
    return [x0 - pad, x1 + pad];
}

function getXRange(chartEl) {
    const r = chartEl.layout.xaxis.range;
    if (!r) return [_globalTMin, _globalTMax];
    return [new Date(r[0]).getTime(), new Date(r[1]).getTime()];
}

function matchFilters(rec) {
    if (selectedQlt !== null && rec.qlt !== selectedQlt) return false;
    if (selectedLevelRange !== null) {
        const ptn = rec.ptn;
        if (ptn === null || ptn === undefined) return false;
        if (ptn < selectedLevelRange.min || ptn > selectedLevelRange.max) return false;
    }
    return true;
}

function getFilterDescription() {
    const parts = [];
    if (selectedQlt !== null) {
        parts.push(QUALITY_MAP[selectedQlt]?.name || `Q${selectedQlt}`);
    }
    if (selectedLevelRange !== null) {
        parts.push(`+${selectedLevelRange.min}-${selectedLevelRange.max}`);
    }
    return parts.join(" ");
}