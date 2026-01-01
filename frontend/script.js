const EDITABLE_COLS = ["ticker", "shares", "price_bought"];
const STORAGE_DB = "riskSheet";
const STORAGE_STORE = "rows";

// ============ Real-Time Sync Setup with Polling (Vercel Compatible) ============
let lastSyncTimestamp = 0;
const SYNC_INTERVAL_ROW_COUNT = 5000; // Check for added/deleted rows every 5 seconds
const SYNC_INTERVAL_PRICES = 60000; // Update prices/ATR every 1 minute (60 seconds)
let isUserEditing = false; // Flag to pause polling while user edits
let lastKnownRowCount = 0; // Track row count to detect additions/deletions

function initRealtimeSync() {
  console.log("Initializing real-time sync with smart polling (Vercel compatible)");
  
  // Poll for row count changes only (detect add/delete) - every 5 seconds
  setInterval(async () => {
    if (isUserEditing) return; // Skip polling while user is editing
    
    try {
      const fresh = await loadFromBackend();
      const freshCount = fresh.length;
      
      // Only reload if row count changed (user added/deleted)
      if (freshCount !== lastKnownRowCount) {
        console.log(`[Sync] Row count changed: ${lastKnownRowCount} → ${freshCount}`);
        lastKnownRowCount = freshCount;
        
        // Reload data but preserve user's order
        hot.loadData(fresh.map((r, idx) => ({ __row: idx + 1, ...r })), { source: 'loadData' });
        updateRowNumbers();
        recalc();
      }
    } catch (e) {
      console.error("[Sync] Row count polling error:", e);
    }
  }, SYNC_INTERVAL_ROW_COUNT);
  
  // Poll for price updates ONLY - every 1 minute (60 seconds)
  // Only update current_price and position_value columns
  setInterval(async () => {
    if (isUserEditing) return; // Skip polling while user is editing
    
    try {
      // Fetch fresh prices by calling recalculate endpoint
      const res = await fetch('/recalculate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          rows: hot.getSourceData()
            .filter(r => r && r.ticker)
            .map(r => ({
              ticker: r.ticker,
              shares: r.shares,
              price_bought: r.price_bought
            }))
        })
      });
      
      if (!res.ok) return;
      
      const freshData = await res.json();
      const currentData = hot.getSourceData();
      
      // Update all fields from fresh data (soft updates only if changed)
      if (freshData.rows) {
        for (let i = 0; i < Math.min(currentData.length, freshData.rows.length); i++) {
          const currentRow = currentData[i];
          const freshRow = freshData.rows[i];
          
          if (!currentRow || !freshRow || !currentRow.ticker) continue;
          
          // Update ALL calculated fields that might change with price updates
          // These are the fields that depend on current market prices
          const fieldsToUpdate = ['current_price', 'position_value', 'pct_change', 'value_paid',
                                  'entry_atr', 'no_atrs', 'take_profit', 'stop_loss', 'current_tp', 'current_sl',
                                  'weight', 'beta_weighted', 'var'];
          
          for (const field of fieldsToUpdate) {
            const newVal = freshRow[field];
            if (currentRow[field] !== newVal && newVal !== undefined) {
              const colIdx = hot.propToCol(field);
              if (colIdx >= 0) {
                hot.setDataAtCell(i, colIdx, newVal, 'priceUpdate');
              }
            }
          }
        }
      }
    } catch (e) {
      console.error("[Sync] Price polling error:", e);
    }
  }, SYNC_INTERVAL_PRICES);
}

// Initialize polling when the page loads
window.addEventListener('load', () => {
  setTimeout(() => {
    // Set initial row count from current data
    const currentData = hot.getSourceData().filter(r => r && r.ticker);
    lastKnownRowCount = currentData.length;
    console.log(`[Init] Setting initial row count: ${lastKnownRowCount}`);
    
    initRealtimeSync();
  }, 500);
});
// ============ End Real-Time Sync Setup ============

function rowNumberRenderer(instance, td, row, col, prop, value, cellProperties) {
  Handsontable.renderers.TextRenderer.apply(this, arguments);
  td.innerHTML = `<div class="row-number-cell"><span class="row-num-text">${value}</span><button class="remove-row-btn" data-row="${row}">-</button></div>`;
  td.style.position = 'relative';
  td.style.padding = '0';
  td.className = 'htCenter htMiddle locked';
}

const columns = [
  { data: "__row", readOnly: true, renderer: rowNumberRenderer },
  { data: "date_bought", type: "date", dateFormat: "YYYY-MM-DD", correctFormat: true, readOnly: true },
  { data: "sector", type: "text", readOnly: true },
  { data: "ticker", type: "text" },
  { 
    data: "shares", 
    type: "numeric", 
    numericFormat: { pattern: "0,0" },
    validator: function(value, callback) {
      if (value === null || value === undefined || value === "") {
        callback(true);
        return;
      }
      const num = Number(value);
      if (isNaN(num)) {
        callback(false);
        return;
      }
      // Check if integer
      if (!Number.isInteger(num)) {
        callback(false);
        return;
      }
      callback(true);
    }
  },
  { data: "price_bought", type: "numeric", numericFormat: { pattern: "$0,0.00" } },
  { data: "value_paid", type: "numeric", readOnly: true, numericFormat: { pattern: "$0,0.00" } },
  { data: "current_price", type: "numeric", readOnly: true, numericFormat: { pattern: "$0,0.00" } },
  { data: "position_value", type: "numeric", readOnly: true, numericFormat: { pattern: "$0,0.00" } },
  { data: "pct_change", type: "numeric", readOnly: true, numericFormat: { pattern: "0.00%" } },
  { data: "entry_atr", type: "numeric", readOnly: true, numericFormat: { pattern: "0,0.0000" } },
  { data: "no_atrs", type: "numeric", readOnly: true, numericFormat: { pattern: "0,0.0000" } },
  { data: "take_profit", type: "numeric", readOnly: true, numericFormat: { pattern: "$0,0.00" } },
  { data: "stop_loss", type: "numeric", readOnly: true, numericFormat: { pattern: "$0,0.00" } },
  { data: "current_tp", type: "numeric", readOnly: true, numericFormat: { pattern: "$0,0.00" } }, // Placeholder
  { data: "current_sl", type: "numeric", readOnly: true, numericFormat: { pattern: "$0,0.00" } }, // Placeholder
  { data: "beta", type: "numeric", readOnly: true, numericFormat: { pattern: "0,0.00" } },
  { data: "weight", type: "numeric", readOnly: true, numericFormat: { pattern: "0.00%" } },
  { data: "beta_weighted", type: "numeric", readOnly: true, numericFormat: { pattern: "0,0.0000" } },
  { data: "expected_return", type: "numeric", readOnly: true, numericFormat: { pattern: "0.00%" } },
  { data: "weighted_expected_return", type: "numeric", readOnly: true, numericFormat: { pattern: "0.00%" } },
  { data: "var", type: "numeric", readOnly: true, numericFormat: { pattern: "$0,0.00" } },
  { data: "iv", type: "numeric", readOnly: true, numericFormat: { pattern: "0.00%" } },
  { data: "holding_period", type: "numeric", readOnly: true },
  { data: "market_cap", type: "numeric", readOnly: true, numericFormat: { pattern: "$0,0" } },
  { data: "cap_formatted", type: "text", readOnly: true },
];

const colHeaders = [
  "Row #",
  "Date Bought",
  "Sector",
  "Ticker",
  "Shares",
  "Price Bought",
  "Value Paid",
  "Current Price",
  "Current Value",
  "% Profit / Loss",
  "Entry ATR",
  "No. ATRs",
  "Take Profit",
  "Stop Loss",
  "Take Profit",
  "Stop Loss",
  "Beta",
  "% Weight",
  "Beta * W",
  "Expected Rate of Return",
  "% Expected Return",
  "VaR",
  "Implied Volatility",
  "Period (Days)",
  "Market Cap",
  "Cap",
];

const sheetEl = document.getElementById("sheet");
const sheet2El = document.getElementById("sheet2");
const sheet3El = document.getElementById("sheet3");
let cachedCash = 0;

const hot = new Handsontable(sheetEl, {
  data: [],
  colHeaders,
  columns,
  rowHeaders: false,
  height: "auto",
  width: "100%",
  licenseKey: "non-commercial-and-evaluation",
  manualColumnMove: false,
  manualColumnResize: true,
  contextMenu: false,
  fillHandle: false,
  filters: false,
  dropdownMenu: false,
  allowInsertColumn: false,
  allowRemoveColumn: false,
  // stretchH: "all", // Removed to allow horizontal scrolling
  outsideClickDeselects: false,
  comments: true, // Enable comments for validation messages
  cells(row, col) {
    const prop = this.instance.colToProp(col);
    
    if (prop === "__row") {
      return { readOnly: true, className: "locked htCenter htMiddle" };
    }
    if (EDITABLE_COLS.includes(prop)) {
      return { readOnly: false, className: "editable htCenter htMiddle" };
    }
    return { readOnly: true, className: "locked htCenter htMiddle" };
  },
  afterValidate: function(isValid, value, row, prop) {
    if (prop === 'shares' && !isValid) {
      const val = Number(value);
      const used = isNaN(val) ? 0 : Math.floor(val);
      this.setCellMeta(row, this.propToCol(prop), 'comment', {value: `Shares must be an integer (no decimals). We will use ${used} until fixed.`});
    } else if (prop === 'shares' && isValid) {
      this.removeCellMeta(row, this.propToCol(prop), 'comment');
    }
  },
  afterCreateRow: updateRowNumbers,
  afterRemoveRow: updateRowNumbers,
  beforeEdit: () => {
    // Pause polling while user is actively editing
    isUserEditing = true;
  },
  afterEdit: () => {
    // Resume polling after user finishes editing (with slight delay)
    setTimeout(() => { isUserEditing = false; }, 500);
  },
  afterChange: (changes, source) => {
    if (!changes || source === "loadData" || source === "syncData" || source === "priceUpdate" || source === "recalcUpdate") return;
    
    // Save individual position changes to Supabase
    savePositionChanges(changes);
    
    // Trigger recalculation for UI updates
    debounceRecalc();
  },
  beforeChange: (changes, source) => {
    if (!changes) return;
    changes.forEach((change) => {
      // change: [row, prop, oldValue, newValue]
      if (change[1] === 'ticker' && typeof change[3] === 'string') {
        change[3] = change[3].toUpperCase();
      }
    });
  },
  beforeKeyDown: (event) => {
    // Handle Enter key for navigation
    if (event.key === 'Enter') {
      const selected = hot.getSelected();
      if (!selected || selected.length === 0) return;
      
      const [row, col] = selected[0];
      const prop = hot.colToProp(col);
      
      // If on price_bought column, show message
      if (prop === 'price_bought') {
        alert('⚠️ Price is read-only. Click to verify before confirming.');
        event.preventDefault();
        return;
      }
      
      // If on current_price or position_value, prevent edit
      if (prop === 'current_price' || prop === 'position_value') {
        alert('⚠️ This column is read-only and updates automatically.');
        event.preventDefault();
        return;
      }
      
      // Navigate to next editable column on Enter
      const editableCols = ['ticker', 'shares', 'price_bought'];
      const colIndex = hot.propToCol(prop);
      const currentColIndex = editableCols.indexOf(prop);
      
      if (currentColIndex !== -1 && currentColIndex < editableCols.length - 1) {
        const nextProp = editableCols[currentColIndex + 1];
        const nextCol = hot.propToCol(nextProp);
        hot.selectCell(row, nextCol);
        event.preventDefault();
      }
    }
  },
});

const hot2 = new Handsontable(sheet2El, {
  data: [
    { category: "Mega Cap", count: 0, pct: 0 },
    { category: "Large Cap", count: 0, pct: 0 },
    { category: "Mid Cap", count: 0, pct: 0 },
    { category: "Small Cap", count: 0, pct: 0 },
    { category: "Micro Cap", count: 0, pct: 0 },
    { category: "Total", count: 0, pct: 0 },
  ],
  colHeaders: ["Category", "Count", "Percentage"],
  columns: [
    { data: "category", readOnly: true },
    { data: "count", type: "numeric", readOnly: true },
    { data: "pct", type: "numeric", numericFormat: { pattern: "0.00%" }, readOnly: true }
  ],
  rowHeaders: false,
  height: "auto",
  width: "100%",
  licenseKey: "non-commercial-and-evaluation",
  manualColumnResize: true,
  cells(row, col) {
    return { readOnly: true, className: "locked htCenter htMiddle" };
  }
});

const hot3 = new Handsontable(sheet3El, {
  data: [
    { metric: "Cash", value: 0 },
    { metric: "Total Invested", value: 0 },
    { metric: "Total Portfolio Value", value: 0 }
  ],
  colHeaders: ["Metric", "Value"],
  columns: [
    { data: "metric", readOnly: true },
    { data: "value", type: "numeric", numericFormat: { pattern: "$0,0.00" } }
  ],
  rowHeaders: false,
  height: "auto",
  width: "100%",
  licenseKey: "non-commercial-and-evaluation",
  manualColumnResize: true,
  cells(row, col) {
    const prop = this.instance.colToProp(col);
    if (row === 0 && prop === "value") {
        return { readOnly: false, className: "editable htCenter htMiddle" };
    }
    return { readOnly: true, className: "locked htCenter htMiddle" };
  },
  beforeEdit: () => {
    isUserEditing = true;
  },
  afterEdit: () => {
    setTimeout(() => { isUserEditing = false; }, 500);
  },
  afterChange: (changes, source) => {
    if (!changes || source === "loadData" || source === "updatePortfolioSummary") return;
    
    changes.forEach(([row, prop, oldVal, newVal]) => {
        if (row === 0 && prop === "value") {
            cachedCash = Number(newVal) || 0;
            updatePortfolioSummary();
            saveCashValue();
        }
    });
  }
});

const sheet4El = document.getElementById("sheet4");
let cachedAllocations = {};
let cachedMarketWeights = {};

const ALL_SECTORS = [
  "Basic Materials",
  "Communication Services",
  "Consumer Cyclical",
  "Consumer Defensive",
  "Energy",
  "Financial Services",
  "Healthcare",
  "Industrials",
  "Real Estate",
  "Technology",
  "Utilities"
];

const hot4 = new Handsontable(sheet4El, {
  data: [],
  colHeaders: [
    "Sector", "Number of Stocks", "Total Value", "% Weight", 
    "Set Allocation", "Allocation Goal", "Market Weight"
  ],
  columns: [
    { data: "sector", readOnly: true },
    { data: "count", type: "numeric", readOnly: true },
    { data: "total_value", type: "numeric", numericFormat: { pattern: "$0,0.00" }, readOnly: true },
    { data: "weight", type: "numeric", numericFormat: { pattern: "0.00%" }, readOnly: true },
    { data: "set_allocation", type: "numeric", numericFormat: { pattern: "0.00%" } },
    { data: "allocation_goal", type: "numeric", numericFormat: { pattern: "$0,0.00" }, readOnly: true },
    { data: "market_weight", type: "numeric", numericFormat: { pattern: "0.00%" }, readOnly: true }
  ],
  rowHeaders: false,
  height: "auto",
  width: "100%",
  stretchH: "all", // Added to fit width
  licenseKey: "non-commercial-and-evaluation",
  manualColumnResize: true,
  cells(row, col) {
    const prop = this.instance.colToProp(col);
    if (prop === "set_allocation") {
      return { readOnly: false, className: "editable htCenter htMiddle" };
    }
    return { readOnly: true, className: "locked htCenter htMiddle" };
  },
  beforeEdit: () => {
    isUserEditing = true;
  },
  afterEdit: () => {
    setTimeout(() => { isUserEditing = false; }, 500);
  },
  beforeChange: (changes, source) => {
    if (!changes || source === "loadData") return;
    changes.forEach((change) => {
      if (change[1] === 'set_allocation') {
        const val = parseFloat(change[3]);
        if (!isNaN(val) && Math.abs(val) > 1) {
          change[3] = val / 100;
        }
      }
    });
  },
  afterChange: (changes, source) => {
    if (!changes || source === "loadData" || source === "updateSectorTable") return;
    
    // Update cachedAllocations
    changes.forEach(([row, prop, oldVal, newVal]) => {
        if (prop === 'set_allocation') {
            const rowData = hot4.getSourceDataAtRow(row);
            if (rowData && rowData.sector) {
                cachedAllocations[rowData.sector] = Number(newVal) || 0;
            }
        }
    });

    updateSectorGoals();
    saveSectorAllocations();
  }
});

function updateSectorGoals() {
  const totalPortfolioValue = hot.getSourceData().reduce((sum, r) => sum + (Number(r.position_value) || 0), 0);
  const sectorData = hot4.getSourceData();
  
  const updated = sectorData.map(row => {
    const alloc = Number(row.set_allocation) || 0;
    return {
      ...row,
      allocation_goal: totalPortfolioValue * alloc
    };
  });
  
  // We use loadData to refresh, but we want to keep the source structure
  hot4.loadData(updated);
}

function getMarketWeight(sectorName) {
  if (!cachedMarketWeights) return 0;
  
  // Try exact match
  if (cachedMarketWeights[sectorName] !== undefined) return cachedMarketWeights[sectorName];
  
  // Try lowercase
  const lower = sectorName.toLowerCase();
  if (cachedMarketWeights[lower] !== undefined) return cachedMarketWeights[lower];
  
  // Try snake_case (replace spaces with underscores)
  const snake = lower.replace(/ /g, '_');
  if (cachedMarketWeights[snake] !== undefined) return cachedMarketWeights[snake];
  
  // Try no spaces (e.g. realestate)
  const nospace = lower.replace(/ /g, '');
  if (cachedMarketWeights[nospace] !== undefined) return cachedMarketWeights[nospace];
  
  return 0;
}

function updateSectorTable() {
  const rows = hot.getSourceData();
  const totalPortfolioValue = rows.reduce((sum, r) => sum + (Number(r.position_value) || 0), 0);
  
  const sectorMap = {};
  
  rows.forEach(r => {
    if (r.sector && !r.error) {
      const s = r.sector.trim();
      if (!s) return;
      
      if (!sectorMap[s]) sectorMap[s] = { tickers: new Set(), value: 0 };
      
      if (r.ticker) {
        sectorMap[s].tickers.add(r.ticker);
      }
      sectorMap[s].value += (Number(r.position_value) || 0);
    }
  });

  // Combine ALL_SECTORS with any other sectors found in the portfolio
  const allSectorsSet = new Set(ALL_SECTORS);
  Object.keys(sectorMap).forEach(s => allSectorsSet.add(s));
  const uniqueSectors = Array.from(allSectorsSet).sort();

  const data = uniqueSectors.map(s => {
    const info = sectorMap[s] || { tickers: new Set(), value: 0 };
    const weight = totalPortfolioValue ? (info.value / totalPortfolioValue) : 0;
    const setAlloc = cachedAllocations[s] || 0;
    const mktWeight = getMarketWeight(s);
    
    return {
      sector: s,
      count: info.tickers.size,
      total_value: info.value,
      weight: weight,
      set_allocation: setAlloc,
      allocation_goal: totalPortfolioValue * setAlloc,
      market_weight: mktWeight 
    };
  });
  
  hot4.loadData(data);
}

function updateTable2() {
  const rows = hot.getSourceData();
  let megaCount = 0, largeCount = 0, midCount = 0, smallCount = 0, microCount = 0, totalCount = 0;
  let megaWeight = 0, largeWeight = 0, midWeight = 0, smallWeight = 0, microWeight = 0;

  rows.forEach(r => {
    // Only count rows that have a valid market_cap and no error
    if (r.market_cap && !r.error && typeof r.market_cap === 'number') {
      const cap = r.market_cap;
      const weight = Number(r.weight) || 0;

      if (cap >= 100_000_000_000) {
        megaCount++;
        megaWeight += weight;
      } else if (cap >= 10_000_000_000) {
        largeCount++;
        largeWeight += weight;
      } else if (cap >= 2_000_000_000) {
        midCount++;
        midWeight += weight;
      } else if (cap >= 500_000_000) {
        smallCount++;
        smallWeight += weight;
      } else {
        microCount++;
        microWeight += weight;
      }
      totalCount++;
    }
  });

  const totalWeight = megaWeight + largeWeight + midWeight + smallWeight + microWeight;

  const data = [
    { category: "Mega Cap", count: megaCount, pct: megaWeight },
    { category: "Large Cap", count: largeCount, pct: largeWeight },
    { category: "Mid Cap", count: midCount, pct: midWeight },
    { category: "Small Cap", count: smallCount, pct: smallWeight },
    { category: "Micro Cap", count: microCount, pct: microWeight },
    { category: "Total", count: totalCount, pct: totalWeight },
  ];
  hot2.loadData(data);
}

function updatePortfolioSummary() {
    const rows = hot.getSourceData();
    const totalInvested = rows.reduce((sum, r) => sum + (Number(r.position_value) || 0), 0);
    const totalPortfolio = totalInvested + cachedCash;

    const data = [
        { metric: "Cash", value: cachedCash },
        { metric: "Total Invested", value: totalInvested },
        { metric: "Total Portfolio Value", value: totalPortfolio }
    ];
    
    hot3.loadData(data);
}

function updateRowNumbers() {
  const data = hot.getSourceData();
  data.forEach((row, idx) => (row.__row = idx + 1));
  hot.render();
}

function getUserRows() {
  return hot
    .getSourceData()
    .filter((r) => r && (r.ticker || r.shares || r.price_bought))
    .map((r) => ({
      ticker: (r.ticker || "").toString().trim(),
      shares: Number(r.shares) || 0,
      price_bought: Number(r.price_bought) || 0,
      date_bought: (r.date_bought || "").toString().trim(),
    }));
}

async function recalc() {
  const rawRows = getUserRows();
  // Use floor of shares for calculation, but keep raw value in UI/Storage
  const payload = { 
    rows: rawRows.map(r => ({
      ...r,
      shares: Math.floor(r.shares)
    }))
  };

  if (!payload.rows.length) {
    hot.loadData([]);
    updateRowNumbers();
    return;
  }
  try {
    const res = await fetch("/recalculate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok) throw new Error(`Backend error: ${res.status}`);
    const data = await res.json();
    
    if (data.market_sector_weights) {
        cachedMarketWeights = data.market_sector_weights;
    }

    // IMPORTANT: Keep original row order - the backend returns rows in same order as we sent
    // So we should match by index, not by ticker
    const currentData = hot.getSourceData();
    let needsFullReload = false;

    // Update each row in place, preserving order - match by index, not ticker
    if (data.rows && data.rows.length > 0) {
      for (let i = 0; i < currentData.length && i < data.rows.length; i++) {
        const currentRow = currentData[i];
        const responseRow = data.rows[i];
        
        if (!currentRow) continue;
        
        // Skip empty rows (no ticker)
        if (!currentRow.ticker) continue;
        
        if (!responseRow) continue;

        // Update ALL fields from response (soft update - only if changed)
        // Get all possible field names from the response
        const fieldsToUpdate = Object.keys(responseRow).filter(field => 
          field !== 'ticker' && field !== 'shares' && field !== 'price_bought' && field !== 'date_bought'
        );

        for (const field of fieldsToUpdate) {
          const newVal = responseRow[field];
          
          // Skip if field doesn't exist in current row or if values are the same
          if (!(field in currentRow) || currentRow[field] === newVal) {
            continue;
          }
          
          const colIdx = hot.propToCol(field);
          if (colIdx >= 0) {
            // Soft update - only update the cell if it changed
            hot.setDataAtCell(i, colIdx, newVal, 'recalcUpdate');
          }
        }
      }
    } else {
      needsFullReload = true;
    }

    // Only call these if data structure didn't change
    if (!needsFullReload) {
      updateTable2();
      updatePortfolioSummary();
      updateSectorTable();
      
      // Calculate and save sector allocations to Supabase
      const rows = hot.getSourceData().filter(r => r && r.ticker);
      const totalPortfolioValue = rows.reduce((sum, r) => sum + (Number(r.position_value) || 0), 0);
      
      if (totalPortfolioValue > 0) {
        // Calculate current sector weights from the portfolio
        const sectorWeights = {};
        rows.forEach(r => {
          if (r.sector && r.sector.trim()) {
            const s = r.sector.trim();
            sectorWeights[s] = (sectorWeights[s] || 0) + (Number(r.position_value) || 0) / totalPortfolioValue;
          }
        });
        
        // Update cachedAllocations with calculated weights and persist to Supabase
        for (const [sector, weight] of Object.entries(sectorWeights)) {
          cachedAllocations[sector] = Math.round(weight * 100) / 100; // Round to 2 decimals
        }
        
        // Persist all sector allocations to Supabase
        await saveSectorAllocations();
      }
      
      // Re-validate and apply backend errors
      hot.validateCells(() => {
        const tickerCol = hot.propToCol('ticker');
        for (let i = 0; i < currentData.length; i++) {
          const row = currentData[i];
          if (row && row.error) {
            hot.setCellMeta(i, tickerCol, 'valid', false);
            hot.setCellMeta(i, tickerCol, 'comment', { value: row.error });
          }
        }
      });
    } else {
      // If row count changed, do full reload
      const merged = data.rows.map((r, idx) => {
        const originalShare = rawRows[idx] ? rawRows[idx].shares : r.shares;
        
        if (r.error) {
          return {
            __row: idx + 1,
            ...r,
            shares: originalShare,
            current_price: "Err",
            position_value: "Err",
            sector: "", 
          };
        }
        return { 
          __row: idx + 1, 
          ...r,
          shares: originalShare
        };
      });
      hot.loadData(merged);
      updateRowNumbers();
      updateTable2();
      updatePortfolioSummary();
      updateSectorTable();
    }
    
    hot.render();
  } catch (err) {
    console.error(err);
    const rows = rawRows.map((r, idx) => ({
      __row: idx + 1,
      ...r,
      current_price: "Err",
      position_value: "Err",
      value_paid: "Err",
      pct_change: "Err",
      entry_atr: "Err",
      no_atrs: "Err",
      take_profit: "Err",
      stop_loss: "Err",
      beta: "Err",
      weight: "Err",
      beta_weighted: "Err",
      expected_return: "Err",
      weighted_expected_return: "Err",
      var: "Err",
      iv: "Err",
      holding_period: "Err",
      market_cap: "Err",
      cap_formatted: "Err",
      sector: "Err",
    }));
    hot.loadData(rows);
    updateRowNumbers();
    hot.validateCells();
    updateTable2();
    updatePortfolioSummary();
    updateSectorTable();
  }
}

let recalcTimer = null;
function debounceRecalc() {
  clearTimeout(recalcTimer);
  recalcTimer = setTimeout(recalc, 600);
}

document.getElementById("addRow").addEventListener("click", () => {
  hot.alter("insert_row_above", hot.countRows());
  updateRowNumbers();
});

// Global listener for remove buttons
document.getElementById("sheet").addEventListener("click", (e) => {
  if (e.target && e.target.classList.contains("remove-row-btn")) {
    const row = parseInt(e.target.getAttribute("data-row"), 10);
    if (!isNaN(row)) {
      // Get ticker before deleting the row
      const rowData = hot.getSourceDataAtRow(row);
      if (rowData && rowData.ticker) {
        // Delete from Supabase first, then remove from UI
        deletePosition(rowData.ticker).then(() => {
          hot.alter("remove_row", row);
          updateRowNumbers();
        }).catch((err) => {
          console.error("Failed to delete position:", err);
          alert(`Failed to delete ${rowData.ticker}: ${err.message}`);
        });
      } else {
        // No ticker, just remove the row
        hot.alter("remove_row", row);
        updateRowNumbers();
      }
    }
  }
});

document.getElementById("recalc").addEventListener("click", () => {
  recalc();
  // saveToIndexedDB(); // Removed as persistence is now handled by hooks
});

// Tab switching logic
document.querySelectorAll('.tab').forEach(tab => {
  tab.addEventListener('click', () => {
    // Remove active class from all tabs and contents
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
    
    // Add active class to clicked tab
    tab.classList.add('active');
    
    // Show corresponding content
    const targetId = tab.getAttribute('data-target');
    document.getElementById(targetId).classList.add('active');
    
    // Refresh Handsontable if it's the Stock ATR tab (to fix rendering issues when hidden)
    if (targetId === 'tab-stock-atr' && hot) {
      hot.render();
    }
    if (targetId === 'tab-sector-allocation') {
      if (hot4) hot4.render();
    }
        if (targetId === 'tab-allocation') {
            renderAllocationTab('table');
        }
      });
    });

    const sheetAllocationEl = document.getElementById("sheetAllocation");
    let allocationChart = null;

    const hotAllocation = new Handsontable(sheetAllocationEl, {
      data: [],
      colHeaders: ["Sector", "% Weight"],
      columns: [
        { data: "sector", readOnly: true },
        { data: "weight", type: "numeric", numericFormat: { pattern: "0.00%" }, readOnly: true }
      ],
      rowHeaders: false,
      height: "auto",
      width: "100%",
      stretchH: "all",
      licenseKey: "non-commercial-and-evaluation",
      manualColumnResize: false,
      cells(row, col) {
        return { readOnly: true, className: "locked htCenter htMiddle" };
      }
    });

    function getAllocationData() {
        const rows = hot.getSourceData();
        const totalPortfolioValue = rows.reduce((sum, r) => sum + (Number(r.position_value) || 0), 0);
        const sectorMap = {};

        // Initialize with ALL_SECTORS
        ALL_SECTORS.forEach(s => {
            sectorMap[s] = 0;
        });

        rows.forEach(r => {
            if (r.sector && !r.error) {
                const s = r.sector.trim();
                if (!s) return;
                if (!sectorMap.hasOwnProperty(s)) sectorMap[s] = 0;
                sectorMap[s] += (Number(r.position_value) || 0);
            }
        });

        const data = Object.keys(sectorMap).map(s => ({
            sector: s,
            weight: totalPortfolioValue ? (sectorMap[s] / totalPortfolioValue) : 0,
            value: sectorMap[s]
        })).sort((a, b) => b.weight - a.weight);

        return data;
    }

    function updateAllocationChart(type) {
        const ctx = document.getElementById('allocationChart').getContext('2d');
        const data = getAllocationData();
        
        if (allocationChart) {
            allocationChart.destroy();
        }

        const labels = data.map(d => d.sector);
        const values = data.map(d => d.weight * 100);
        const backgroundColors = [
            '#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF', '#FF9F40',
            '#e6194b', '#3cb44b', '#ffe119', '#4363d8', '#f58231', '#911eb4'
        ];
        
        let datasetConfig = {
            label: 'Sector Allocation (%)',
            data: values,
            borderWidth: 1
        };

        if (type === 'radar') {
            datasetConfig = {
                ...datasetConfig,
                backgroundColor: 'rgba(54, 162, 235, 0.2)',
                borderColor: 'rgb(54, 162, 235)',
                pointBackgroundColor: backgroundColors,
                pointBorderColor: '#fff',
                pointHoverBackgroundColor: '#fff',
                pointHoverBorderColor: backgroundColors,
                fill: true
            };
        } else {
            datasetConfig.backgroundColor = backgroundColors;
        }

        // Animation Configuration
        let animationConfig = {
            duration: 1200,
            easing: 'easeOutQuart'
        };

        if (type === 'bar') {
            animationConfig = {
                ...animationConfig,
                y: {
                    from: 0
                },
                delay: (context) => {
                    if (context.type === 'data' && context.mode === 'default' && !context.dropped) {
                        return context.dataIndex * 100;
                    }
                    return 0;
                }
            };
        } else if (type === 'pie') {
            animationConfig = {
                ...animationConfig,
                animateScale: true,
                animateRotate: true
            };
        } else if (type === 'radar') {
             animationConfig = {
                ...animationConfig,
                // Radar chart "expand from center" effect
                onProgress: function(animation) {
                    // Custom logic if needed
                }
            };
        }

        const config = {
            type: type,
            data: {
                labels: labels,
                datasets: [datasetConfig]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                animation: animationConfig,
                plugins: {
                    legend: {
                        display: type !== 'radar',
                        position: type === 'radar' ? 'top' : 'right',
                        labels: {
                            generateLabels: function(chart) {
                                if (chart.config.type === 'bar' || chart.config.type === 'radar' || chart.config.type === 'pie') {
                                    const data = chart.data;
                                    return data.labels.map((label, i) => {
                                        const ds = data.datasets[0];
                                        let bgColor = Array.isArray(ds.backgroundColor) ? ds.backgroundColor[i] : ds.backgroundColor;
                                        
                                        if (chart.config.type === 'radar') {
                                            bgColor = Array.isArray(ds.pointBackgroundColor) ? ds.pointBackgroundColor[i] : ds.pointBackgroundColor;
                                        }

                                        return {
                                            text: label,
                                            fillStyle: bgColor,
                                            strokeStyle: bgColor,
                                            lineWidth: 0,
                                            hidden: !chart.getDataVisibility(i),
                                            index: i
                                        };
                                    });
                                }
                                return Chart.defaults.plugins.legend.labels.generateLabels(chart);
                            }
                        },
                        onClick: function(e, legendItem, legend) {
                            if (legend.chart.config.type === 'bar' || legend.chart.config.type === 'radar' || legend.chart.config.type === 'pie') {
                                legend.chart.toggleDataVisibility(legendItem.index);
                                legend.chart.update();
                            } else {
                                Chart.defaults.plugins.legend.onClick(e, legendItem, legend);
                            }
                        }
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                return context.label + ': ' + context.raw.toFixed(2) + '%';
                            }
                        }
                    }
                }
            }
        };
        
        if (type === 'radar') {
            config.options.scales = {
                r: {
                    angleLines: {
                        display: true
                    },
                    suggestedMin: 0,
                    ticks: {
                        backdropColor: 'transparent',
                        callback: function(value) {
                            return value + '%';
                        }
                    }
                }
            };
        }

        allocationChart = new Chart(ctx, config);
    }

    function renderAllocationTab(type) {
        const chartWrapper = document.getElementById('chart-wrapper');
        const tableWrapper = document.getElementById('allocation-table-wrapper');
        const data = getAllocationData();
        
        // Update active button state
        document.querySelectorAll('.chart-btn').forEach(btn => {
            if (btn.getAttribute('data-type') === type) {
                btn.classList.add('active');
            } else {
                btn.classList.remove('active');
            }
        });

        hotAllocation.loadData(data);
        
        if (type === 'table') {
            chartWrapper.classList.remove('chart-wrapper-visible');
            setTimeout(() => {
                chartWrapper.style.display = 'none';
                tableWrapper.style.width = '100%';
                tableWrapper.style.flex = 'none';
                hotAllocation.render();
            }, 300);
        } else {
            const wasHidden = chartWrapper.style.display === 'none' || chartWrapper.style.display === '';
            
            if (wasHidden) {
                chartWrapper.style.display = 'block';
                chartWrapper.style.width = '65%';
                chartWrapper.style.height = '500px';
                
                tableWrapper.style.width = '30%';
                tableWrapper.style.flex = 'none';
                tableWrapper.style.minWidth = '250px';
                
                updateAllocationChart(type);
                
                // Trigger reflow
                void chartWrapper.offsetWidth;
                chartWrapper.classList.add('chart-wrapper-visible');
            } else {
                // Fade out, switch, fade in
                chartWrapper.classList.remove('chart-wrapper-visible');
                setTimeout(() => {
                    updateAllocationChart(type);
                    chartWrapper.classList.add('chart-wrapper-visible');
                }, 300);
            }
        }
        hotAllocation.render();
    }

    document.querySelectorAll('.chart-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const type = e.target.getAttribute('data-type');
            renderAllocationTab(type);
        });
    });

function openDb() {
  // Deprecated: IndexedDB replaced by Backend API
  return Promise.resolve();
}

async function loadFromBackend() {
  try {
    const res = await fetch('/positions');
    if (!res.ok) return [];
    return await res.json();
  } catch (e) {
    console.error("Failed to load positions:", e);
    return [];
  }
}

async function savePositionChanges(changes) {
  /**
   * Save individual position changes to Supabase.
   * Called whenever a position cell is edited.
   * changes: array of [row, prop, oldValue, newValue]
   */
  if (!changes || changes.length === 0) return;
  
  try {
    const rows = hot.getSourceData();
    
    for (const [rowIdx, prop, oldVal, newVal] of changes) {
      // Only save if one of the persistent fields changed
      if (!['ticker', 'shares', 'price_bought', 'date_bought'].includes(prop)) {
        continue;
      }
      
      const row = rows[rowIdx];
      if (!row || !row.ticker) continue; // Skip empty rows
      
      // Save the entire row to Supabase via the backend
      await savePosition(row);
    }
  } catch (e) {
    console.error("Error saving position changes:", e);
  }
}

async function savePosition(row) {
  try {
    const ticker = (row.ticker || "").toString().trim().toUpperCase();
    console.log("Saving position:", ticker, row);
    const payload = {
      ticker,
      shares: parseFloat(row.shares) || 0,
      price_bought: parseFloat(row.price_bought) || 0,
      date_bought: row.date_bought || null
    };
    const res = await fetch('/positions', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    if (res.ok) {
        const data = await res.json();
        console.log("Saved position:", data);
        // Polling will automatically detect the change
        return data;
    } else {
        const errorText = await res.text();
        console.error("Save failed with status:", res.status, errorText);
    }
  } catch (e) { console.error("Save failed:", e); }
  return null;
}

async function deletePosition(ticker) {
  try {
    await fetch(`/positions/${ticker}`, { method: 'DELETE' });
  } catch (e) { console.error("Delete failed:", e); }
}

async function saveSectorAllocations() {
  // Save each sector allocation
  try {
    for (const [sector, allocation] of Object.entries(cachedAllocations)) {
      const res = await fetch('/sector-allocations', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ sector, allocation })
      });
      // Polling will automatically detect the change
      if (!res.ok) {
        console.warn(`Failed to save ${sector} allocation`);
      }
    }
  } catch (e) {
    console.warn("Sector persistence failed", e);
  }
}

async function loadSectorAllocations() {
  try {
    const res = await fetch('/sector-allocations');
    if (!res.ok) return {};
    return await res.json();
  } catch (e) {
    return {};
  }
}

async function saveCashValue() {
  try {
    const res = await fetch('/cash', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ amount: cachedCash })
    });
    // Polling will automatically detect the change
    if (!res.ok) {
      console.warn("Cash save failed");
    }
  } catch (e) {
    console.warn("Cash persistence failed", e);
  }
}

async function loadCashValue() {
  try {
    const res = await fetch('/cash');
    if (!res.ok) return 0;
    const data = await res.json();
    return data.amount;
  } catch (e) {
    return 0;
  }
}

// --- Handsontable Hooks for Persistence ---

hot.addHook('afterChange', async (changes, source) => {
  if (source === 'loadData' || !changes) return;
  
  // Handle Ticker Changes: Delete old ticker if it existed
  for (const [row, prop, oldVal, newVal] of changes) {
    if (prop === 'ticker' && oldVal && oldVal.toString().trim().length > 0) {
       const oldTicker = oldVal.toString().trim();
       // Only delete if it's actually different
       if (oldTicker !== (newVal || "").toString().trim()) {
           console.log(`Ticker changed from ${oldTicker} to ${newVal}. Deleting old record.`);
           await deletePosition(oldTicker);
       }
    }
  }
  
  // Identify unique rows that were modified
  const modifiedRows = new Set();
  changes.forEach(([row, prop]) => {
    if (['ticker', 'shares', 'price_bought', 'date_bought'].includes(prop)) {
      modifiedRows.add(row);
    }
  });

  for (const row of modifiedRows) {
    const physicalRow = hot.toPhysicalRow(row);
    const rowData = hot.getSourceDataAtRow(physicalRow);
    
    if (!rowData) continue;

    // Helper to check for valid number (not empty, not NaN)
    const isNum = (v) => v !== null && v !== undefined && v !== '' && !isNaN(Number(v));
    
    const hasTicker = rowData.ticker && rowData.ticker.toString().trim().length > 0;
    const hasShares = isNum(rowData.shares);
    const hasPrice = isNum(rowData.price_bought);

    // If all 3 columns are filled, set flag and save (upsert)
    if (hasTicker && hasShares && hasPrice) {
      rowData._is_ready = true;
      await savePosition(rowData);
      // savePosition() already broadcasts via WebSocket when successful
    }
  }
});

hot.addHook('beforeRemoveRow', async (index, amount) => {
  for (let i = 0; i < amount; i++) {
    const visualRow = index + i;
    const physicalRow = hot.toPhysicalRow(visualRow);
    const row = hot.getSourceDataAtRow(physicalRow);
    if (row && row.ticker) {
      await deletePosition(row.ticker);
    }
  }
});


(async function init() {
  const saved = await loadFromBackend();
  cachedAllocations = await loadSectorAllocations();
  cachedCash = await loadCashValue();
  
  // Map saved data to include __row for display
  hot.loadData(saved.map((r, idx) => ({ __row: idx + 1, ...r })));
  updateRowNumbers();
  updatePortfolioSummary();
  if (saved.length) {
    recalc();
  } else {
    hot.alter("insert_row_above", 0);
    updateRowNumbers();
  }
})();

function saveToIndexedDB() {
  // Placeholder to prevent errors if old code calls this
  console.warn("saveToIndexedDB called but deprecated");
}
