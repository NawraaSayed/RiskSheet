# Real-Time Sync - Complete Flow

## Updated Architecture (No Manual Refresh Needed)

### Flow 1: Position Editing/Adding
```
┌─────────────────────────────────────────────────────────────────┐
│ USER A: Edits ticker "AAPL" → "MSFT"                            │
└──────────────┬──────────────────────────────────────────────────┘
               │
               ├─→ [Frontend] afterChange hook triggered
               │
               ├─→ [Frontend] savePosition() called
               │   ├─→ API POST /positions with new data
               │   │
               │   ├─→ [Backend] Receives POST request
               │   │   └─→ Inserts/Updates position in database
               │   │
               │   ├─→ [Frontend] API success → send WebSocket
               │   │   └─→ ws.send({type: 'position_saved', ticker: 'MSFT'})
               │   │
               │   └─→ [Backend] Receives WebSocket message
               │       └─→ manager.broadcast({type: 'data_updated'})
               │
               ├─→ [Backend] Broadcasts to ALL connected clients
               │
               └─→ [USER B's Browser] Receives WebSocket message
                   ├─→ ws.onmessage({type: 'data_updated'})
                   │
                   ├─→ recalc() is triggered (200ms delay)
                   │
                   ├─→ Fetches updated data from /recalculate
                   │
                   └─→ Table updates automatically
                       ✓ New ticker shows
                       ✓ New price fetched
                       ✓ All metrics recalculated
                       ✓ NO REFRESH NEEDED!
```

### Flow 2: Cash Value Update
```
USER A: Edits Cash from $100,000 → $150,000
   │
   ├─→ [Frontend] Cash table afterChange fires
   │   ├─→ cachedCash = 150000
   │   ├─→ updatePortfolioSummary()
   │   └─→ saveCashValue()
   │       ├─→ API PUT /cash
   │       │
   │       ├─→ [Backend] Updates cash in database
   │       │
   │       └─→ [Frontend] On success: ws.send({type: 'cash_saved', amount: 150000})
   │           └─→ [Backend] Receives and broadcasts
   │
   └─→ [USER B's Browser] 
       ├─→ Receives {type: 'data_updated', reason: 'cash_saved'}
       ├─→ Calls recalc()
       └─→ Sees cash update + portfolio summary recalculates
           ✓ Cash: $150,000
           ✓ Total Portfolio Value: Updated
           ✓ Percentages: Recalculated
```

### Flow 3: Sector Allocation Update
```
USER A: Changes Tech allocation 30% → 40%
   │
   ├─→ [Frontend] Sector table afterChange fires
   │   ├─→ cachedAllocations['Technology'] = 0.40
   │   ├─→ updateSectorTable()
   │   └─→ saveSectorAllocations()
   │       ├─→ API PUT /sector-allocations
   │       │
   │       ├─→ [Backend] Updates allocation in database
   │       │
   │       └─→ [Frontend] On success: ws.send({type: 'allocation_saved'})
   │           └─→ [Backend] Receives and broadcasts
   │
   └─→ [USER B's Browser]
       ├─→ Receives {type: 'data_updated', reason: 'allocation_saved'}
       ├─→ Calls recalc()
       └─→ Sector allocation table updates
           ✓ Tech allocation_goal: Updated
           ✓ Visual indicators refresh
```

## WebSocket Message Types (Updated)

### 1. data_updated (NEW - For any backend change)
```json
{
  "type": "data_updated",
  "reason": "position_saved|cash_saved|allocation_saved",
  "ticker": "MSFT",  // optional, for position_saved
  "amount": 150000,  // optional, for cash_saved
  "sector": "Technology",  // optional, for allocation_saved
  "allocation": 0.40,  // optional, for allocation_saved
  "timestamp": "2025-12-31T12:34:56.789Z"
}
```

### 2. cell_updated (For real-time cell sync)
```json
{
  "type": "cell_updated",
  "ticker": "AAPL",
  "field": "shares",
  "value": 150,
  "row": 0,
  "timestamp": "2025-12-31T12:34:56.789Z"
}
```

### 3. position_added (From API broadcast)
```json
{
  "type": "position_added",
  "ticker": "TSLA",
  "shares": 50,
  "price_bought": 250,
  "date_bought": "2025-12-31"
}
```

### 4. position_deleted (From API broadcast)
```json
{
  "type": "position_deleted",
  "ticker": "AAPL"
}
```

## User Experience (Updated)

### Before (Need to Refresh)
1. User A edits something
2. User B sees no change
3. User B must refresh page
4. Data appears

### After (Real-Time Sync)
1. User A edits something
2. Change is saved to backend
3. Backend broadcasts to User B
4. User B sees change **INSTANTLY** ✓
5. All calculated metrics update automatically ✓
6. **NO REFRESH NEEDED** ✓

## Implementation Details

### Frontend Changes:
1. **broadcastCellChange()** - Sends cell edits via WebSocket
2. **updateCellFromRemote()** - Applies remote cell updates locally
3. **savePosition()** - Now broadcasts after API success
4. **saveCashValue()** - Now broadcasts after API success
5. **saveSectorAllocations()** - Now broadcasts after API success
6. **ws.onmessage()** - Enhanced to handle `data_updated` type
   - Triggers `recalc()` with 200ms delay
   - Fetches fresh data from backend
   - Updates all tables automatically

### Backend Changes:
1. **WebSocket endpoint** - Now handles and broadcasts:
   - `position_saved` → `data_updated`
   - `cash_saved` → `data_updated`
   - `allocation_saved` → `data_updated`
   - `cell_updated` → forwarded to all clients
2. **manager.broadcast()** - Sends messages to all connected clients

## Testing the Real-Time Sync

### Test Scenario 1: Edit Position
1. Open two browser windows to RiskSheet
2. Log in on both
3. In Window A: Edit a ticker (e.g., AAPL → MSFT)
4. **Result**: Window B updates automatically ✓
   - Ticker changes
   - Current price updates
   - All calculations refresh

### Test Scenario 2: Edit Cash
1. In Window A: Edit cash value
2. **Result**: Window B updates automatically ✓
   - Cash value changes
   - Portfolio summary refreshes
   - Percentages recalculate

### Test Scenario 3: Edit Sector Allocation
1. In Window A: Change sector allocation percentage
2. **Result**: Window B updates automatically ✓
   - Allocation goal updates
   - Visual indicators refresh

### Debug Verification
1. Open DevTools (F12) on both windows
2. Check Console tab for messages like:
   ```
   WebSocket message received: {type: 'data_updated', reason: 'position_saved'}
   Data updated: position_saved
   [Remote Update] Ticker: MSFT, Field: ticker, Value: MSFT
   [Remote Update] Updated field: AAPL → MSFT
   ```
3. Network tab shows:
   - WebSocket frames being sent
   - /recalculate API call after message received

## Performance

- **Latency**: ~100-500ms from User A's save to User B seeing the change
- **Message Size**: ~100-200 bytes per WebSocket message
- **Server Load**: Minimal - broadcasts use efficient JSON serialization
- **Bandwidth**: Negligible - only metadata sent, not full data

## Known Limitations

1. **No offline support** - Changes require WebSocket connection
2. **No conflict resolution** - Last write wins if simultaneous edits
3. **No user identification** - Can't see which user made the change
4. **No audit trail** - Changes not logged with timestamps/users

## Future Enhancements

- [ ] Add user identification to messages
- [ ] Implement change timestamps
- [ ] Add audit logging
- [ ] Implement selective refresh (only affected tables)
- [ ] Add user presence indicators
- [ ] Implement change history/undo
