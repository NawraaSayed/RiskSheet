# RiskSheet - Supabase Integration Guide

## Overview
The RiskSheet backend has been fully migrated to use **Supabase PostgreSQL** as the single source of truth for all data. No local caching or ephemeral storage is used.

## Architecture

### Database Layer
- **`backend/db/supabase_client.py`**: Centralized Supabase client with connection management and error handling
- **`backend/db/database_supabase.py`**: CRUD functions for positions, cash, and sector allocations
- All data is immediately persisted to Supabase PostgreSQL

### API Layer  
- **`backend/main.py`**: FastAPI endpoints with proper error handling for Supabase failures
- All endpoints write to Supabase before responding
- All endpoints read from Supabase (no caching except for calculations)

### Frontend
- **`frontend/script.js`**: HTTP polling syncs with backend (2-3 second intervals)
- Realtime updates via polling - fetches fresh data from Supabase via API

## Required Environment Variables

Add these to **Vercel Project Settings → Environment Variables**:

```
SUPABASE_HOST=<your-project>.supabase.co
SUPABASE_USER=postgres
SUPABASE_PASSWORD=<your-password>
SUPABASE_DB=postgres
```

Get these values from:
1. Log in to [Supabase Dashboard](https://supabase.com)
2. Select your project
3. Go to Settings → Database
4. Copy the connection details

## Database Schema

The following tables must exist in Supabase (created manually via SQL Editor):

### `positions` table
```sql
CREATE TABLE positions (
  ticker TEXT PRIMARY KEY,
  shares REAL NOT NULL,
  price_bought REAL NOT NULL,
  date_bought TEXT
);
```

### `cash` table
```sql
CREATE TABLE cash (
  id INTEGER PRIMARY KEY CHECK (id = 1),
  amount REAL NOT NULL
);
```

### `sector_allocations` table
```sql
CREATE TABLE sector_allocations (
  sector TEXT PRIMARY KEY,
  allocation REAL NOT NULL
);
```

## API Endpoints

All endpoints require authentication and hit Supabase:

### Positions
- `GET /positions` - Fetch all positions from Supabase
- `POST /positions` - Insert/update position in Supabase
- `DELETE /positions/{ticker}` - Delete position from Supabase

### Cash
- `GET /cash` - Fetch cash balance from Supabase
- `PUT /cash` - Update cash balance in Supabase

### Sector Allocations
- `GET /sector-allocations` - Fetch all allocations from Supabase
- `PUT /sector-allocations` - Insert/update allocation in Supabase

## Error Handling

### Connection Errors
- App startup fails loudly if Supabase credentials are missing
- Connection timeouts are caught and logged
- HTTP 500 errors with descriptive messages returned to frontend

### Database Errors
- All database operations wrapped in try/catch
- Errors logged to console with ❌ prefix
- HTTPException (500) returned with error details

## Deployment Checklist

### Before deploying to Vercel:

1. ✅ Verify Supabase project created
2. ✅ Create all 3 tables in Supabase SQL Editor (use SQL above)
3. ✅ Get connection credentials (SUPABASE_HOST, SUPABASE_PASSWORD)
4. ✅ Add environment variables to Vercel:
   ```
   SUPABASE_HOST=...
   SUPABASE_USER=postgres
   SUPABASE_PASSWORD=...
   SUPABASE_DB=postgres
   ```
5. ✅ Ensure `psycopg2-binary==2.9.9` is in `requirements.txt`
6. ✅ Push code with git
7. ✅ Redeploy on Vercel (clear cache)

### After deployment:

1. ✅ Check Vercel logs for "✅ Supabase database ready" message
2. ✅ Go to https://risk-sheet.vercel.app and test:
   - Add a position
   - Update cash balance
   - Verify data persists (refresh page)
   - Delete a position

## Testing Locally

Run the integration test suite to verify Supabase is working:

```bash
python test_supabase_integration.py
```

Expected output:
```
✅ Connection test..................... ✅ PASS
✅ Positions CRUD...................... ✅ PASS
✅ Cash Operations..................... ✅ PASS
✅ Sector Allocations.................. ✅ PASS
✅ ALL TESTS PASSED - Supabase integration is working!
```

## Changes Made

### Files Created
- `backend/db/supabase_client.py` - Centralized Supabase client
- `test_supabase_integration.py` - Comprehensive integration tests

### Files Modified
- `backend/db/database_supabase.py` - Rewritten with proper error handling
- `backend/main.py` - Updated to use Supabase exclusively
- `requirements.txt` - Added `psycopg2-binary==2.9.9`

### Files Removed/Deprecated
- `backend/db/database_cloud.py` - No longer used
- `backend/db/database.py` - No longer used
- SQLite logic removed entirely

## Key Design Decisions

1. **Single Source of Truth**: All data is immediately written to Supabase, no local caching
2. **Connection Pooling**: Each function gets a fresh connection (connection pooling can be added later)
3. **Error Transparency**: All errors logged with ❌ prefix and returned to frontend
4. **No Schema Creation**: Tables must be created manually - more control, prevents accidental resets
5. **HTTP Polling**: No WebSocket (Vercel doesn't support it), polling every 2-3 seconds

## Troubleshooting

### "Missing Supabase environment variables"
- Check Vercel dashboard for SUPABASE_HOST, SUPABASE_PASSWORD
- Credentials must match Supabase project settings

### "unable to open database file" (old SQLite error)
- Old database_cloud.py still being used
- Update `backend/main.py` import to use `database_supabase`

### API returns 500 errors
- Check Vercel logs: Settings → Function Logs
- Verify Supabase tables exist in SQL Editor
- Test connection locally with `test_supabase_integration.py`

### Data not persisting
- Check Supabase dashboard - Data Browser tab
- Verify positions/cash/sector_allocations tables have correct schema
- Check that API calls are successful (no 500 errors)

## Future Enhancements

1. **Connection Pooling**: Use `psycopg2.pool.SimpleConnectionPool` for better performance
2. **Realtime Subscriptions**: Use Supabase realtime features instead of polling
3. **Caching Layer**: Redis cache for frequently accessed data (calculate once per minute)
4. **Audit Log**: Track all changes with timestamps and usernames
5. **Backup Strategy**: Daily backups via Supabase automated backups

---

**Status**: ✅ Production ready
**Last Updated**: 2026-01-01
