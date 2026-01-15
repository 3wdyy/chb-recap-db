# One-Shot Prompt: Build Executive KPI Dashboard from Scratch

Build a **single-file HTML KPI Dashboard** for executive performance review. The entire application (HTML, CSS, JavaScript) must be contained in ONE `kpi_dashboard.html` file with no external dependencies except SheetJS for Excel parsing.

---

## 1. PROJECT OVERVIEW

**Purpose:** Executive-level KPI dashboard for analyzing business performance across two modes:
- **MUSE Mode:** Loyalty program analytics (12 KPIs)
- **MC Mode:** Multi-channel retail analytics (22 KPIs)

**Key Features:**
- Dual CSV upload (one per mode) with drag-and-drop support
- Mode toggle between MUSE and MC dashboards
- Cascading filters (Market → Channel)
- Interactive SVG line charts with tooltips
- Year-over-Year comparisons (2025 vs 2024)
- Target variance tracking
- New vs Returning customer segmentation (MC mode)

---

## 2. TECHNICAL REQUIREMENTS

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Performance Review | KPI Dashboard</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/xlsx/0.18.5/xlsx.full.min.js"></script>
    <style>/* All CSS here */</style>
</head>
<body>
    <div id="app"></div>
    <div class="chart-tooltip" id="chartTooltip"></div>
    <script>/* All JavaScript here in IIFE */</script>
</body>
</html>
```

---

## 3. DESIGN SYSTEM (CSS Variables)

```css
:root {
    /* Colors */
    --navy: #1B365D;           /* Primary brand */
    --steel-blue: #8FAFD4;     /* Secondary */
    --light-steel: #B8D4E8;    /* Tertiary */
    --positive: #2E7D5A;       /* Green for good trends */
    --negative: #C4314B;       /* Red for bad trends */
    --neutral: #B8860B;        /* Gold/amber for neutral */
    --positive-soft: #3d9970;
    --negative-soft: #d35d6e;
    --neutral-soft: #D4A017;
    --white: #FFFFFF;
    --light-bg: #F8FAFC;
    --text-dark: #1B365D;
    --text-muted: #64748B;

    /* Typography Scale */
    --font-display: 48px;      /* Hero values */
    --font-h1: 26px;           /* Page title */
    --font-h2: 20px;           /* Section titles */
    --font-h3: 18px;           /* Chart titles */
    --font-value-xl: 32px;     /* Large card values */
    --font-value-lg: 26px;     /* Medium card values */
    --font-value-md: 20px;     /* Small card values */
    --font-value-sm: 16px;     /* Table cell values */
    --font-body-lg: 15px;
    --font-body: 14px;
    --font-body-sm: 13px;
    --font-caption: 12px;
    --font-label: 11px;
    --font-micro: 10px;
}

body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    background: var(--light-bg);
    color: var(--text-dark);
    line-height: 1.5;
}
```

---

## 4. DATA MODEL & CSV FORMAT

### CSV Structure (Both Modes)
```
Market,BU,Channel,Key/KPI,Month,YTD,LYTD,R12M,LMR12M,Target
```

**Fields:**
- `Market`: Geographic region (e.g., "All", "United Arab Emirates", "Saudi Arabia")
- `BU`: Business Unit ("MUSE", "MC", "All")
- `Channel`: Sales channel ("All", "Retail", "Ecom", etc.) - mainly for MC mode
- `Key`/`KPI`: KPI identifier
- `Month`: Month identifier (support multiple formats: "01 - Jan", "Jan-24", "JAN")
- `YTD`: Year-to-Date value (current year)
- `LYTD`: Last Year-to-Date value
- `R12M`: Rolling 12 months
- `LMR12M`: Last month R12M
- `Target`: Target value

### Application State
```javascript
let state = {
    mode: 'MUSE',              // 'MUSE' or 'MC'
    museData: null,            // Parsed MUSE data array
    mcData: null,              // Parsed MC data array
    museFileName: null,        // For upload screen display
    mcFileName: null,
    selectedMarket: null,      // null = use aggregate
    selectedChannel: null,     // null = use aggregate
    selectedKPI: null,
    activeTab: 'summary',      // Current tab
    dataLoaded: false          // Show upload vs dashboard
};
```

---

## 5. KPI CONFIGURATIONS

### MUSE Mode KPIs (12 total)
```javascript
const MUSE_KPI_CONFIG = {
    'SLS_TTL': { name: 'Total Sales', format: 'currency', good: 'up', hasShare: true },
    'SLS_PEN': { name: 'Sales Penetration', format: 'percent', good: 'up', hasShare: false },
    'MBR_TTL': { name: 'Transacting Members', format: 'number', good: 'up', hasShare: true },
    'MBR_NEW': { name: 'New Members', format: 'number', good: 'up', hasShare: true },
    'MBR_RTN': { name: 'Returning Members', format: 'number', good: 'up', hasShare: true },
    'AVG_ATF': { name: 'Avg Frequency', format: 'decimal', good: 'up', hasShare: false },
    'AVG_AOV': { name: 'Avg Order Value', format: 'currency_small', good: 'up', hasShare: false },
    'PCT_RDM': { name: 'Redeeming Members %', format: 'percent', good: 'up', loyalty: true, hasShare: false },
    'PCT_XBP': { name: 'Cross Brand Plus %', format: 'percent', good: 'up', loyalty: true, hasShare: false },
    'PCT_NBA': { name: 'New Brand Adopters %', format: 'percent', good: 'up', loyalty: true, hasShare: false },
    'AVG_BRD': { name: 'Avg Brands Shopped', format: 'decimal', good: 'up', hasShare: false },
    'PTS_BRN': { name: 'Points Burned Value', format: 'currency', good: 'up', hasShare: true }
};
```

### MC Mode KPIs (22 total)
```javascript
const MC_KPI_CONFIG = {
    'TOTAL OWN BRAND SALES': { name: 'Total Own Brand Sales', format: 'currency', good: 'up', hasShare: true, hero: true },
    'KNOWN SALES': { name: 'Known Sales', format: 'currency', good: 'up', hasShare: true },
    'NEW CUSTOMERS KNOWN SALES': { name: 'New Customers Sales', format: 'currency', good: 'up', hasShare: true },
    'RETURNING CUSTOMERS KNOWN SALES': { name: 'Returning Customers Sales', format: 'currency', good: 'up', hasShare: true },
    'CUSTOMER COUNT': { name: 'Customer Count', format: 'number', good: 'up', hasShare: true, hero: true },
    'NEW CUSTOMER COUNT': { name: 'New Customers', format: 'number', good: 'up', hasShare: true, hero: true },
    'RETURNING CUSTOMER COUNT': { name: 'Returning Customers', format: 'number', good: 'up', hasShare: true },
    'TRANSACTION COUNT': { name: 'Transaction Count', format: 'number', good: 'up', hasShare: true },
    'NEW CUSTOMERS TRANSACTION COUNT': { name: 'New Customers Transactions', format: 'number', good: 'up', hasShare: true },
    'RETURNING CUSTOMERS TRANSACTION COUNT': { name: 'Returning Customers Transactions', format: 'number', good: 'up', hasShare: true },
    'AOV': { name: 'Avg Order Value', format: 'currency_small', good: 'up', hasShare: false, hero: true },
    'NEW CUSTOMERS AOV': { name: 'New Customers AOV', format: 'currency_small', good: 'up', hasShare: false },
    'RETURNING CUSTOMERS AOV': { name: 'Returning Customers AOV', format: 'currency_small', good: 'up', hasShare: false },
    'ACV': { name: 'Avg Customer Value', format: 'currency_small', good: 'up', hasShare: false },
    'NEW CUSTOMERS ACV': { name: 'New Customers ACV', format: 'currency_small', good: 'up', hasShare: false },
    'RETURNING CUSTOMERS ACV': { name: 'Returning Customers ACV', format: 'currency_small', good: 'up', hasShare: false },
    'AVERAGE FREQUENCY': { name: 'Avg Frequency', format: 'decimal', good: 'up', hasShare: false, hero: true },
    'NEW CUSTOMERS AVERAGE FREQUENCY': { name: 'New Customers Frequency', format: 'decimal', good: 'up', hasShare: false },
    'RETURNING CUSTOMERS AVERAGE FREQUENCY': { name: 'Returning Customers Frequency', format: 'decimal', good: 'up', hasShare: false },
    'UPT': { name: 'Units Per Transaction', format: 'decimal', good: 'up', hasShare: false },
    'NEW CUSTOMERS UPT': { name: 'New Customers UPT', format: 'decimal', good: 'up', hasShare: false },
    'RETURNING CUSTOMERS UPT': { name: 'Returning Customers UPT', format: 'decimal', good: 'up', hasShare: false },
    'SALES LINKAGE': { name: 'Sales Linkage', format: 'percent', good: 'up', hasShare: false, hero: true }
};

// KPI Groups for organized dropdown in MC mode
const MC_KPI_GROUPS = [
    { name: 'Sales', kpis: ['TOTAL OWN BRAND SALES', 'KNOWN SALES', 'NEW CUSTOMERS KNOWN SALES', 'RETURNING CUSTOMERS KNOWN SALES'] },
    { name: 'Customers', kpis: ['CUSTOMER COUNT', 'NEW CUSTOMER COUNT', 'RETURNING CUSTOMER COUNT'] },
    { name: 'Transactions', kpis: ['TRANSACTION COUNT', 'NEW CUSTOMERS TRANSACTION COUNT', 'RETURNING CUSTOMERS TRANSACTION COUNT'] },
    { name: 'Average Order Value', kpis: ['AOV', 'NEW CUSTOMERS AOV', 'RETURNING CUSTOMERS AOV'] },
    { name: 'Average Customer Value', kpis: ['ACV', 'NEW CUSTOMERS ACV', 'RETURNING CUSTOMERS ACV'] },
    { name: 'Frequency', kpis: ['AVERAGE FREQUENCY', 'NEW CUSTOMERS AVERAGE FREQUENCY', 'RETURNING CUSTOMERS AVERAGE FREQUENCY'] },
    { name: 'Units Per Transaction', kpis: ['UPT', 'NEW CUSTOMERS UPT', 'RETURNING CUSTOMERS UPT'] },
    { name: 'Other', kpis: ['SALES LINKAGE'] }
];
```

### Constants
```javascript
const CURRENT_YEAR = 2025;
const PREVIOUS_YEAR = 2024;
const MONTHS = ['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN', 'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC'];

// Map various month input formats to standard 3-letter abbreviations
const MONTH_MAP = {
    '01 - Jan':'JAN', '02 - Feb':'FEB', /* ... all months ... */
    'Jan-24':'JAN', 'Jan-25':'JAN', /* year variants */
    'Jan':'JAN', '1':'JAN', 'JAN':'JAN' /* other formats */
};

const PREFERRED_MARKET_ORDER = ['All', 'All Markets', 'United Arab Emirates', 'Saudi Arabia', 'Kuwait', 'Bahrain', 'Qatar', 'Oman', 'Egypt', 'Jordan', 'Lebanon'];
```

---

## 6. UI STRUCTURE & COMPONENTS

### Screen Flow
1. **Upload Screen** (when `!state.dataLoaded`)
   - Logo display
   - Two dropzones: MUSE Data, MC Data
   - "Start Dashboard" button (enabled when at least one file loaded)
   - "Load Demo Data" button

2. **Main Dashboard** (when `state.dataLoaded`)
   - Header with logo, title, mode toggle (if both modes have data)
   - Navigation tabs (different per mode)
   - Tab content area

### Navigation Tabs
**MUSE Mode:**
- Executive Summary
- Market Analysis
- KPI Deep Dive

**MC Mode:**
- Executive Summary
- Customer Segments
- Market Analysis
- Channel Analysis
- KPI Deep Dive

### Component Hierarchy

```
.header
├── .header-left
│   ├── .logo-container
│   └── .header-text (h1 + subtitle)
└── .header-mode-switcher (.mode-toggle with buttons)

.nav-tabs
└── .nav-tab (multiple, one per tab)

.main
├── .section-header (.section-title + .section-subtitle)
├── .filter-row (.filter-group with label + select)
└── [Tab-specific content]
```

### CSS Classes for Card Components

**Metric Card** (`.metric-card`): Primary KPI display
- `.metric-header` (icon + label)
- `.metric-value` (large number)
- `.metric-target-row` (target comparison with badge)
- `.metric-vs-row` (vs LY with arrow)
- Border-left color indicates status: `.positive`, `.negative`, `.neutral`

**Share Tile** (`.share-tile`): KPI with New/Returning split
- Same header as metric card
- `.share-tile-split` with two `.share-split-item` columns

**Small Tile** (`.small-tile`): Compact KPI display
- Smaller padding, font sizes
- Used for secondary metrics row

**Table Components**
- `.chart-container` wrapper
- `.modern-table` with `.market-cell`, `.value-cell`, `.compare-cell`
- `.total-row` for aggregate rows (bold, background)

---

## 7. BUSINESS LOGIC & CALCULATIONS

### Value Formatting
```javascript
function formatValue(value, format) {
    if (value === null || value === undefined || isNaN(value)) return '—';
    switch(format) {
        case 'currency':
            if (value >= 1e9) return '$' + (value/1e9).toFixed(2) + 'B';
            if (value >= 1e6) return '$' + (value/1e6).toFixed(1) + 'M';
            if (value >= 1e3) return '$' + (value/1e3).toFixed(0) + 'K';
            return '$' + value.toFixed(0);
        case 'currency_small':
            return '$' + value.toFixed(0);
        case 'percent':
            return (value * 100).toFixed(1) + '%';
        case 'number':
            if (value >= 1e6) return (value/1e6).toFixed(2) + 'M';
            if (value >= 1e3) return (value/1e3).toFixed(0) + 'K';
            return value.toLocaleString();
        case 'decimal':
            return value.toFixed(2);
    }
}
```

### Change Calculations
```javascript
function calcChange(current, previous, format) {
    if (!current || !previous || previous === 0) return null;
    if (format === 'percent') {
        // For percentages, return difference in percentage points
        const curr = parseFloat((current * 100).toFixed(1));
        const prev = parseFloat((previous * 100).toFixed(1));
        return curr - prev;
    }
    // For other formats, return percentage change
    return ((current / previous) - 1) * 100;
}

function formatChange(change, format) {
    if (change === null) return '—';
    const sign = change >= 0 ? '+' : '';
    if (format === 'percent') {
        return sign + change.toFixed(1) + ' PP';  // Percentage points
    }
    return sign + change.toFixed(1) + '%';
}

function getChangeClass(change, format) {
    if (change === null) return '';
    // Threshold for "neutral" zone
    const threshold = format === 'percent' ? 0.1 : 1;
    if (Math.abs(change) < threshold) return 'neutral';
    return change >= 0 ? 'up' : 'down';
}
```

### Data Query Functions
```javascript
// Get current mode's data array
function getData() {
    return state.mode === 'MC' ? state.mcData : state.museData;
}

// Get unique markets from data (sorted: aggregates first, then preferred order)
function getMarkets() { /* ... */ }

// Get channels available for selected market (MC mode filter cascade)
function getChannels() { /* ... */ }

// Get available KPIs in current data
function getKPIs() { /* ... */ }

// Get latest (December) data for a specific market/kpi/channel combo
function getLatestData(market, kpiKey, channel = null) { /* ... */ }

// Get all monthly data for charts
function getMonthlyData(market, kpiKey, channel = null) { /* ... */ }

// Check if value is an aggregate ("All", "All Markets", etc.)
function isAggregateValue(value, dimension) { /* ... */ }

// Get the aggregate value name for a dimension from data
function getAggregateValue(dimension) { /* ... */ }
```

---

## 8. RENDER FUNCTIONS

### Main Render Flow
```javascript
function render() {
    const app = document.getElementById('app');
    if (!state.dataLoaded) {
        app.innerHTML = renderUpload();
    } else {
        app.innerHTML = renderDashboard();
    }
    attachEvents();
}
```

### Upload Screen
```javascript
function renderUpload() {
    // Returns upload overlay with:
    // - Logo
    // - Two .csv-upload-card elements (MUSE + MC)
    // - Each with .csv-upload-zone dropzone
    // - Start + Demo buttons
}
```

### Dashboard Components
```javascript
function renderDashboard() {
    // Header + nav tabs + main content based on activeTab
}

function renderSummaryTab() {
    // Switches between MUSE and MC summary
}

function renderMUSESummaryTab() {
    // 4-column grid of metric cards
    // Key insights panel
    // Market summary table
}

function renderMCSummaryTab() {
    // Top row: 3 main KPIs (metric cards)
    // Middle row: 3 KPIs with new/returning split (share tiles)
    // Bottom row: 4 smaller metrics (small tiles)
    // Market & Channel comparison tables
}

function renderSegmentationTab() { // MC only
    // 3 visual cards with split bars (Customers, Transactions, Sales)
    // Secondary comparison table (AOV, ACV, Frequency)
}

function renderMarketsTab() {
    // KPI dropdown
    // Market analysis table with YTD, LYTD, Target, Share columns
}

function renderChannelTab() { // MC only
    // Similar to Markets but for channels
}

function renderKPITab() {
    // Market/Channel/KPI selectors
    // Hero card with main value + comparisons
    // Breakdown cards (by market, by channel)
    // SVG line chart with monthly trend
    // Monthly trend badges
}
```

### Card Render Functions
```javascript
function renderMetricCard(market, kpiKey, channel = null) {
    // .metric-card with icon, label, value, target row, vs LY row
}

function renderShareTile(market, baseKpi, newKpi, returningKpi, channel = null) {
    // .share-tile with main value + new/returning split below
}

function renderSmallTile(market, kpiKey, channel = null) {
    // .small-tile compact version
}

function renderBreakdownCard(dimension, selectedValue, kpiKey, config, otherDimValue, totalValue) {
    // Horizontal bar breakdown by market or channel
}
```

---

## 9. SVG LINE CHART

Chart renders in `renderKPIDetail()`:
- Dimensions: 900x390 with margins (70 left, 30 right, 20 top, 40 bottom)
- X-axis: 12 months (JAN-DEC)
- Y-axis: Auto-scaled based on data range
- **Lines:**
  - Solid navy line for 2025 (YTD)
  - Dashed steel-blue line for 2024 (LYTD)
  - Dashed green line for Target (if exists)
- **Fill areas:** Color-coded regions between YTD and LYTD lines (green if above, red if below)
- **Data points:** Clickable circles with tooltips
- **Tooltips:** Show month, 2025 value, vs LY, vs Target

```javascript
// Chart tooltip attachment
function attachChartTooltips() {
    // mouseenter: parse data-info JSON, show tooltip
    // mousemove: position tooltip near cursor
    // mouseleave: hide tooltip
}
```

---

## 10. SVG ICONS

Include inline SVG icons for each KPI. Example:
```javascript
const METRIC_ICONS = {
    'SLS_TTL': '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="1" x2="12" y2="23"/><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/></svg>',
    'MBR_TTL': '<svg ...users icon...</svg>',
    'AVG_AOV': '<svg ...shopping cart icon...</svg>',
    'AVG_ATF': '<svg ...clock icon...</svg>',
    // ... icons for all KPIs
};
```

Arrow icons for trend indicators:
```javascript
const arrowUp = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M18 15l-6-6-6 6"/></svg>';
const arrowDown = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M6 9l6 6 6-6"/></svg>';
const arrowNeutral = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M5 12h14"/></svg>';
```

---

## 11. EVENT HANDLING

```javascript
function attachEvents() {
    // Upload screen events
    // - Dropzone click → trigger file input
    // - Dropzone drag/drop → load file
    // - File input change → load file
    // - Start button → set dataLoaded, render dashboard
    // - Demo button → fetch demo CSV

    // Dashboard events
    // - Mode toggle buttons → switch mode, reset filters, re-render
    // - Nav tabs → switch activeTab, re-render
    // - Market filter → update selectedMarket, reset channel, re-render
    // - Channel filter → update selectedChannel, re-render
    // - KPI dropdowns → update content without full re-render

    attachChartTooltips();
}
```

---

## 12. FILE PARSING

```javascript
function parseCSV(text, mode = 'MUSE') {
    // Split lines, parse headers
    // For each row:
    //   - Parse numeric fields (YTD, LYTD, R12M, LMR12M, Target)
    //   - Map KPI names (MUSE mode uses name→key mapping)
    //   - Normalize month format
    //   - Default BU and Channel if missing
}

function parseExcel(workbook) {
    // Check for 'MUSE' and 'MC' sheets
    // Parse each sheet to CSV, then parseCSV
}

function loadCSVFile(file, mode) {
    // FileReader to read as text
    // parseCSV with mode
    // Update state.museData or state.mcData
}
```

---

## 13. CSS COMPONENT STYLES (Key Classes)

```css
/* Layout */
.header { background: white; padding: 20px 48px; border-bottom: 3px solid var(--navy); display: flex; justify-content: space-between; }
.nav-tabs { display: flex; gap: 4px; padding: 0 48px; background: white; }
.nav-tab { padding: 16px 28px; cursor: pointer; border-bottom: 3px solid transparent; }
.nav-tab.active { color: var(--navy); border-bottom-color: var(--navy); font-weight: 600; }
.main { padding: 32px 48px; }

/* Grids */
.exec-summary { display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; }
.kpi-row-3 { display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; }
.kpi-row-4 { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; }

/* Cards */
.metric-card { background: white; border-radius: 12px; padding: 24px; border: 1px solid var(--light-steel); border-left: 4px solid var(--navy); }
.metric-card.positive { border-left-color: var(--positive); }
.metric-card.negative { border-left-color: var(--negative); }

/* Tables */
.modern-table { width: 100%; border-collapse: collapse; }
.modern-table th { background: var(--navy); color: white; padding: 12px 16px; text-align: left; }
.modern-table td { padding: 12px 16px; border-bottom: 1px solid var(--light-steel); }
.total-row { background: var(--light-bg); font-weight: 600; }

/* Change indicators */
.up { color: var(--positive); }
.down { color: var(--negative); }
.neutral { color: var(--neutral); }

/* Upload screen */
.upload-overlay { min-height: 100vh; display: flex; align-items: center; justify-content: center; background: var(--light-bg); }
.csv-upload-zone { border: 2px dashed var(--light-steel); border-radius: 8px; padding: 24px; text-align: center; cursor: pointer; }

/* Chart */
.chart-container { background: white; border-radius: 12px; padding: 24px; border: 1px solid var(--light-steel); }
.chart-tooltip { position: fixed; background: white; border: 1px solid var(--light-steel); border-radius: 8px; padding: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); opacity: 0; pointer-events: none; z-index: 1000; }
.chart-tooltip.visible { opacity: 1; }

/* Segmentation split bars */
.segment-split-bar { display: flex; height: 32px; border-radius: 4px; overflow: hidden; }
.segment-split-new { background: var(--positive); color: white; display: flex; align-items: center; justify-content: center; }
.segment-split-returning { background: var(--steel-blue); color: white; display: flex; align-items: center; justify-content: center; }
```

---

## 14. RESPONSIVE DESIGN

```css
@media (max-width: 1200px) {
    .segment-comparison-grid { grid-template-columns: 1fr; }
    /* Adjust multi-column layouts to single column */
}
```

---

## 15. LOGO HANDLING

```javascript
const LOGO_SVG = `<img src="logo.png" alt="Company Logo" style="height: 60px; width: auto;" onerror="this.style.display='none'">`;
```
- Logo loads from `logo.png` relative path
- Gracefully hides if file not found

---

## 16. INITIALIZATION

```javascript
(function() {
    // All code in IIFE
    // ...constants, state, functions...

    render();  // Initial render (shows upload screen)
})();
```

---

## SUMMARY

Build a self-contained HTML file that:
1. Shows dual CSV upload screen on load
2. Parses CSV/Excel data into in-memory arrays
3. Renders appropriate dashboard based on selected mode
4. Supports filtering by Market and Channel (cascade)
5. Displays KPIs in cards with YoY and Target comparisons
6. Shows interactive SVG charts with tooltips
7. Handles mode switching and tab navigation
8. Uses a clean, professional design system with navy/steel-blue theme

The entire application should work offline after loading (except for the SheetJS CDN), with all functionality contained in the single HTML file.
