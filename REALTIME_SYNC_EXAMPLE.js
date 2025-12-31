// Example: Real-time Synchronization Demo
// This file shows how the real-time collaboration features work

// ============================================================================
// SCENARIO 1: User A edits a ticker cell while User B is viewing
// ============================================================================

// USER A'S BROWSER:
// 1. User A clicks on cell and changes "AAPL" to "MSFT"
// 2. Frontend triggers afterChange hook:
//    hot.addHook('afterChange', async (changes, source) => {
//      // changes = [[ rowIndex, "ticker", "AAPL", "MSFT" ]]
//      // Broadcast to all users:
//      broadcastCellChange("AAPL", 0, "ticker", "MSFT");
//    });

// 3. WebSocket sends to backend:
//    {
//      "type": "cell_updated",
//      "ticker": "AAPL",
//      "row": 0,
//      "field": "ticker",
//      "value": "MSFT",
//      "timestamp": "2025-12-31T12:34:56.789Z"
//    }

// USER B'S BROWSER:
// 1. WebSocket receives the message:
//    ws.onmessage = (event) => {
//      const message = JSON.parse(event.data);
//      if (message.type === 'cell_updated') {
//        updateCellFromRemote(message);
//      }
//    }

// 2. updateCellFromRemote() updates User B's table:
//    function updateCellFromRemote(message) {
//      const rows = hot.getSourceData();
//      const rowIndex = rows.findIndex(r => r.ticker === message.ticker);
//      if (rowIndex !== -1) {
//        const rowData = rows[rowIndex];
//        rowData[message.field] = message.value;  // rowData.ticker = "MSFT"
//        hot.setSourceDataAtRow(rowIndex, rowData);
//        debounceRecalc();  // Recalculate all metrics
//      }
//    }

// 3. User B's table updates instantly with:
//    - New ticker symbol "MSFT"
//    - Updated current price (from new ticker)
//    - Updated position value, ATR, beta, etc.
//    - Updated portfolio metrics

// ============================================================================
// SCENARIO 2: User A edits shares while User B is viewing
// ============================================================================

// USER A:
// Edits shares from 100 to 150
// Broadcasts: { type: "cell_updated", ticker: "AAPL", field: "shares", value: 150 }

// USER B:
// Receives update, row for AAPL gets shares = 150
// Recalculation updates:
//   - position_value = 150 * current_price
//   - weight = position_value / total_portfolio_value
//   - VaR, beta_weighted, etc.
// Portfolio summary updates automatically

// ============================================================================
// SCENARIO 3: User A adds a new position while User B is viewing
// ============================================================================

// USER A:
// Adds new row with TSLA, 50 shares, $250 price
// API POST /positions triggers broadcast:
//   { type: "position_added", ticker: "TSLA", shares: 50, price_bought: 250 }

// USER B:
// Receives position_added message
// Automatically triggers recalc()
// New row appears in table with all calculated metrics
// Portfolio summary and sector table update

// ============================================================================
// SCENARIO 4: User A deletes a position while User B is viewing
// ============================================================================

// USER A:
// Clicks delete button on AAPL row
// API DELETE /positions/AAPL triggers broadcast:
//   { type: "position_deleted", ticker: "AAPL" }

// USER B:
// Receives position_deleted message
// Automatically triggers recalc()
// Row disappears from table
// Portfolio summary and sector table update

// ============================================================================
// SCENARIO 5: User A changes cash value while User B is viewing
// ============================================================================

// USER A (in Portfolio Summary table):
// Edits Cash value from $100,000 to $150,000
// API PUT /cash triggers broadcast:
//   { type: "cash_updated", amount: 150000 }

// USER B:
// Receives cash_updated message
// cachedCash updates to 150000
// Portfolio summary updates:
//   - Cash: $150,000
//   - Total Portfolio Value: Total Invested + $150,000
// All calculations update (e.g., cash as % of portfolio)

// ============================================================================
// SCENARIO 6: User A changes sector allocation while User B is viewing
// ============================================================================

// USER A (in Sector Allocation table):
// Changes Technology allocation from 30% to 40%
// API PUT /sector-allocations triggers broadcast:
//   { type: "sector_allocation_updated", sector: "Technology", allocation: 0.40 }

// USER B:
// Receives sector_allocation_updated message
// Sector Allocation table updates:
//   - Technology set_allocation = 40%
//   - Allocation goal = total_value * 0.40
//   - Visual indicator shows new goal
// Portfolio metrics update if relevant

// ============================================================================
// REAL-TIME FLOW DIAGRAM
// ============================================================================

/*
┌─────────────────┐                    ┌─────────────────┐
│   USER A        │                    │   USER B        │
│   (Browser)     │                    │   (Browser)     │
└────────┬────────┘                    └────────┬────────┘
         │                                      │
         │  EDITS TICKER CELL                   │
         │  "AAPL" → "MSFT"                     │
         │                                      │
         ├──→ afterChange hook                  │
         │    calls broadcastCellChange()       │
         │                                      │
         ├──→ sends WebSocket message           │
         │    to BACKEND                        │
         │                                      │
         │                    ┌──────────────┐  │
         │                    │   BACKEND    │  │
         │                    │   (Server)   │  │
         │                    └──────┬───────┘  │
         │                           │           │
         │                           │ broadcast │
         │                           │ to all    │
         │                           │ clients   │
         │                           │           │
         │                    ┌──────▼───────┐  │
         │                    │   Manager    │  │
         │                    │   broadcast  │  │
         │                    └──────┬───────┘  │
         │                           │           │
         │                           │ send      │
         │                           │ message   │
         │                           │ back to   │
         │                           │ all       │
         │                           ▼           │
         │                                      │ receives message
         │                                      │
         │                                      ├── ws.onmessage
         │                                      │
         │                                      ├── updateCellFromRemote()
         │                                      │
         │                                      ├── hot.setSourceDataAtRow()
         │                                      │
         │                                      ├── debounceRecalc()
         │                                      │
         │                                      ├── ALL TABLES UPDATE
         │                                      │
         │                                      ▼
         │                                  USER SEES CHANGES
         │                                  INSTANTLY!
         ▼

RESULT: Both users see consistent data in real-time with no manual refresh needed
*/

// ============================================================================
// WEBSOCKET MESSAGE FORMATS
// ============================================================================

// Message 1: Cell Update
const cellUpdateMessage = {
  type: "cell_updated",
  ticker: "AAPL",
  field: "shares",
  value: 150,
  row: 0,
  timestamp: "2025-12-31T12:34:56.789Z"
};

// Message 2: Position Added
const positionAddedMessage = {
  type: "position_added",
  ticker: "TSLA",
  shares: 50,
  price_bought: 250.00,
  date_bought: "2025-12-31"
};

// Message 3: Position Deleted
const positionDeletedMessage = {
  type: "position_deleted",
  ticker: "AAPL"
};

// Message 4: Cash Updated
const cashUpdatedMessage = {
  type: "cash_updated",
  amount: 150000
};

// Message 5: Sector Allocation Updated
const sectorAllocationMessage = {
  type: "sector_allocation_updated",
  sector: "Technology",
  allocation: 0.40
};

// ============================================================================
// DEBUGGING TIPS
// ============================================================================

// In browser console, check WebSocket status:
console.log("WebSocket state:", ws.readyState); // 1 = OPEN, 0 = CONNECTING, 2 = CLOSING, 3 = CLOSED

// Monitor all WebSocket messages:
const originalSend = WebSocket.prototype.send;
WebSocket.prototype.send = function(data) {
  console.log("Sending:", data);
  return originalSend.apply(this, arguments);
};

// Watch for incoming messages:
const originalOnMessage = ws.onmessage;
ws.onmessage = function(event) {
  console.log("Received:", event.data);
  return originalOnMessage.apply(this, arguments);
};

// Check if updates are being applied:
console.log("Current data:", hot.getSourceData());

// Verify broadcast function works:
broadcastCellChange("AAPL", 0, "ticker", "MSFT");

// ============================================================================
// TESTING REAL-TIME FEATURES
// ============================================================================

/*
STEP-BY-STEP TESTING GUIDE:

1. Open two browser windows/tabs to RiskSheet
2. Log in on both (can be same user or different)
3. Add a position in Window A (e.g., AAPL, 100 shares, $150)
4. Watch Window B - new row should appear automatically
5. In Window A, edit the shares to 200
6. Watch Window B - shares should update to 200
7. Watch the position value update automatically in Window B
8. In Window A, edit the ticker to MSFT
9. Watch Window B - ticker, current price, and all metrics update
10. In Window A, edit the cash value
11. Watch Window B - portfolio summary updates
12. Open browser DevTools (F12) on Window B
13. Go to Console tab
14. Watch for messages like:
    - "WebSocket connected"
    - "WebSocket message received: {type: 'cell_updated', ...}"
    - "Cell updated - Ticker: MSFT, Field: shares, Value: 200"
15. Network tab shows WebSocket frames being sent/received
16. Try rapid edits - all should sync instantly

If something doesn't work:
- Check console for errors
- Verify WebSocket is connected (ws.readyState === 1)
- Check that backend is running and accessible
- Try refreshing one window and edit in the other
- Check that both users are on same server (not load-balanced)
*/
