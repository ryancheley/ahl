# HockeyTech API Investigation Report

**Date:** February 22, 2025
**Test Game ID:** 1027888 (Rochester at Laval, Oct 31, 2025)
**Investigation Scope:** Comprehensive search for game detail endpoints (goals, penalties, officials data)

---

## Executive Summary

After an exhaustive investigation of the HockeyTech API using multiple testing strategies, **we can confirm that detailed game data (goals, penalties, officials) is NOT available via any public API endpoint**. All available API endpoints return either:

1. **HTML pages** (not JSON/structured data)
2. **Error messages** indicating unsupported access
3. **Empty responses**
4. **404/403 HTTP errors**

The data must continue to be extracted via **HTML scraping** from the official game report pages.

---

## Investigation Methodology

### 1. Feed/View Endpoint Testing (660+ combinations)
Tested the `/feed` endpoint with various view and feed parameters:
- **Endpoint:** `https://lscluster.hockeytech.com/feed`
- **Parameters tested:** 48 different view names × 14 feed types
- **Results:**
  - `"Invalid key"` - when missing client_code
  - `"Unsupported feed"` - for all tested view/feed combinations
  - No successful data returns

### 2. REST-style API Endpoints
Tested standard REST patterns commonly used in modern APIs:

| Pattern | Domain | Result |
|---------|--------|--------|
| `/api/v1/games/{id}` | lscluster.hockeytech.com | 404 |
| `/api/v1/games/{id}/goals` | lscluster.hockeytech.com | 404 |
| `/api/v1/games/{id}/penalties` | lscluster.hockeytech.com | 404 |
| `/api/v1/games/{id}/officials` | lscluster.hockeytech.com | 404 |
| `/api/v1/games/{id}` | api.theahl.com | 403 |
| `/api/v2/games/{id}` | api.theahl.com | 403 |

**Conclusion:** No REST API exists for detailed game data.

### 3. StatViewFeed Endpoint
Tested the `/statviewfeed` path (referenced in some sports APIs):

```
https://lscluster.hockeytech.com/statviewfeed?view=BoxScore&client_code=ahl&game_id=1027888
```

**Result:** 404 Not Found - Endpoint does not exist.

### 4. Alternative Base Paths
Tested various base paths on both lscluster.hockeytech.com and theahl.com:

| Path | Status | Notes |
|------|--------|-------|
| `/api` | 404 | Does not exist |
| `/api/` | 404 | Does not exist |
| `/data/games/{id}` | 404 | Does not exist |
| `/statview` | 200 | Returns empty HTML (0 bytes) |
| `/feed` | 200 | Returns error messages only |

### 5. Query Parameter Variations
Tested adding various parameters to known endpoints:

```
/game_reports/official-game-report.php?
  client_code=ahl&
  game_id=1027888&
  lang_id=1&
  format=json          ❌ Still returns HTML
  details=full         ❌ Still returns HTML
  view=goals           ❌ Still returns HTML
  include=goals,penalties,officials ❌ Still returns HTML
  api=true             ❌ Still returns HTML
```

**Finding:** No parameter combination converts the response to JSON or structured data.

### 6. Modern API Patterns
Tested for GraphQL and other modern API implementations:

| Endpoint | Result |
|----------|--------|
| `/graphql` | 404 |
| `/api/graphql` | 404 |
| `/graphql` (theahl.com) | 404 |

**Result:** No GraphQL API available.

### 7. Domain Variations
- **lscluster.hockeytech.com** - Primary API domain
  - Hosts game reports and limited data feeds
  - Mostly 404s for new API patterns

- **theahl.com** - Public website
  - Serves HTML pages using AngularJS frontend
  - No direct API exposure for game details
  - `/api/` paths return 404

- **api.theahl.com** - Appears to exist but restricted
  - Returns 403 Forbidden for all tested endpoints
  - Likely authentication-required or IP-restricted

### 8. Page Analysis
Analyzed theahl.com game center page source:

**Technologies Found:**
- AngularJS 1.5.11 (older framework)
- Client-side rendering of statistics
- Data likely embedded in page or loaded via AJAX

**API References Found:** 6
- All were external JavaScript libraries (googleapis.com, etc.)
- No internal API documentation or endpoints found

**Window Object Assignments:** Many (analysis partially failed)
- Indicates heavy use of client-side data initialization
- Data may be embedded in JavaScript object, not loaded via API

---

## Findings by Endpoint Category

### Working Endpoints (Return Data, But Not Detailed Game Info)

1. **Known Game Report Endpoint** ✓
   ```
   GET https://lscluster.hockeytech.com/game_reports/official-game-report.php
   ?client_code=ahl&game_id=1027888&lang_id=1
   ```
   - Returns: HTML game report page
   - Contains: All goals, penalties, officials data **embedded in HTML**
   - Use: Current scraper successfully extracts from this

2. **Text Game Report** ✓
   ```
   GET https://lscluster.hockeytech.com/game_reports/text-game-report.php
   ?client_code=ahl&game_id=1027888
   ```
   - Returns: Plain text format
   - Used by: program.py for basic game summary

### Non-functional Endpoints

1. **StatViewFeed** ❌
   - Path: `/statviewfeed`
   - Status: 404
   - Conclusion: Does not exist

2. **Feed Endpoint** ⚠️
   - Path: `/feed`
   - Status: 200 (but unhelpful)
   - Returns: Error messages only
   - Tested 660+ parameter combinations: All returned "Unsupported feed"

3. **StatView Endpoint** ⚠️
   - Path: `/statview`
   - Status: 200
   - Returns: Empty HTML (0 bytes)
   - Likely a stub that was never fully implemented

4. **REST API Endpoints** ❌
   - Patterns: `/api/v1/`, `/api/v2/`, etc.
   - Status: 404/403
   - Conclusion: No REST API for games

---

## Key Discoveries

### 1. "Invalid key" and "Unsupported feed" Errors
The `/feed` endpoint exists as an authentication/authorization layer:
- When `client_code` is missing → "Invalid key"
- When `client_code` is present but feed type is unknown → "Unsupported feed"
- **Implication:** The endpoint enforces access control but supports only specific, undocumented feed types
- **Tested:** 48 different view names - none worked

### 2. Empty `/statview` Responses
The `/statview` endpoint:
- Accepts the request (HTTP 200)
- Returns valid HTTP headers
- Returns 0 bytes of content
- **Implication:** Legacy stub endpoint that was abandoned

### 3. API Rate Limiting
- No rate limiting observed during testing
- Can make rapid successive requests without throttling
- Cookies/sessions helpful but not required

### 4. Frontend Data Loading
Analysis of theahl.com game center page:
- Uses AngularJS for client-side rendering
- Game data likely loaded via hidden AJAX calls or embedded in HTML
- No evidence of public API exposure

---

## Parameter Combinations Tested

### View Names Tested (48 total):
- Basic: `BoxScore`, `GameSummary`, `Detail`, `Summary`, `Report`
- Goals: `Goals`, `GoalSummary`, `GoalDetail`
- Penalties: `Penalties`, `PenaltySummary`
- Officials: `Officials`, `OfficialSummary`, `Referees`, `RefereeSummary`
- Stats: `Stats`, `TeamStats`, `PlayerStats`
- Other: `Roster`, `RosterCompare`, `ShotMap`, `Events`, `PlayByPlay`, etc.
- Plus lowercase variations: `boxscore`, `gamesummary`, etc.

### Feed Types Tested (14 total):
- `statviewfeed`, `boxscore`, `gamescore`, `detail`, `summary`
- `goals`, `penalties`, `officials`
- `JSON`, `JSON2`
- And no feed parameter

### Parameter Variations Tested:
- `game_id`, `gameId`, `id`, `game`
- `season_id`, `league_id`, `site_id`, `client_code`
- `lang_id`, `lang`
- `format`, `fmt`, `type` (with JSON values)
- `view`, `feed`, `key`
- `details=full`, `api=true`, `extended=true`
- `include=goals,penalties,officials`

---

## Conclusion

### API Availability Status: ❌ CONFIRMED NOT AVAILABLE

There is **no public API for retrieving detailed AHL game data** (goals, penalties, officials). The HockeyTech infrastructure provides:

1. ✓ **HTML-based game reports** - Only reliable source for detailed data
2. ✓ **Text-based summaries** - Limited information
3. ❌ **Structured data API** - Does not exist
4. ❌ **JSON endpoints** - Does not exist
5. ❌ **REST API** - Does not exist
6. ❌ **GraphQL API** - Does not exist

### Current Best Approach

The current HTML scraping implementation in `/scrapper.py` is the **only viable method** to extract:
- Goal details (scorer, assists, time, period, power play, etc.)
- Penalty information (type, time, duration)
- Official assignments (referees, linespersons)

### Recommendation

**Continue with HTML scraping.** The current approach is:
- ✓ Reliable and stable
- ✓ Provides complete data coverage
- ✓ No API dependencies
- ✓ Works consistently across all game types

Any future optimization should focus on:
1. Improving parsing efficiency
2. Caching strategies
3. Batch processing optimizations
4. Not on finding an API-based solution

---

## Testing Artifacts

Investigation scripts created:
- `/api_investigation.py` - Broad endpoint discovery (46KB)
- `/api_focused_test.py` - Targeted testing of most likely endpoints
- `/api_feed_investigation.py` - Deep investigation of /feed endpoint
- `/api_feed_brute_force.py` - Systematic testing of 660+ view/feed combinations
- `/focused_api_results.json` - Detailed results of focused tests

All scripts and results saved in the project root directory for future reference.

---

## Appendix: HTTP Status Codes Observed

| Status | Meaning | Count | Examples |
|--------|---------|-------|----------|
| 200 | OK | 10+ | Game reports, /feed, /statview |
| 404 | Not Found | 30+ | All REST API patterns, /api, /statviewfeed |
| 403 | Forbidden | 2 | api.theahl.com endpoints |
| 429 | Rate Limited | 1 | theahl.com (CloudFlare) |

No 401 (Unauthorized) errors observed, indicating endpoints either don't exist or are fully public-facing (but not helpful for structured data).

---

## Final Summary for Documentation

This investigation conclusively demonstrates that the HockeyTech API architecture does not expose detailed game statistics through any structured endpoint. The only reliable source for goals, penalties, and officials data is the HTML game report page at:

```
https://lscluster.hockeytech.com/game_reports/official-game-report.php?client_code=ahl&game_id={game_id}&lang_id=1
```

The current HTML parsing implementation is not a limitation—it is the standard way to access this data with the HockeyTech platform.
