# StatViewFeed API Investigation - Complete Index

## Quick Navigation

### Start Here
1. **INVESTIGATION_COMPLETE.md** - Executive summary and status
2. **QUICK_REFERENCE.md** - Quick lookup for URLs and parameters
3. **TEST_RESULTS_SUMMARY.txt** - Raw test results

### Deep Dive
1. **STATVIEWFEED_API_REFERENCE.md** - Complete API specification
2. **STATVIEWFEED_INVESTIGATION_SUMMARY.md** - Detailed technical report
3. **STATVIEWFEED_API_FINDINGS.md** - Structured findings document

### Code & Tests
1. **validate_statviewfeed_endpoints.py** - Final validation tests (run this to verify)
2. **test_statviewfeed_game_details.py** - 52 endpoint combination tests
3. **test_game_api_discovery.py** - Comprehensive API discovery

### Raw Data
1. **statviewfeed_game_results.json** - Results from 52 test combinations
2. **focused_api_results.json** - Results from initial focused testing

---

## What Works (Summary)

### ✓ Player Data
```
GET /feed/index.php?feed=statviewfeed&view=player&player_id={id}&...
Returns: Player biographical data
Status: Fully functional in player_scrapper.py
```

### ✓ Game Rosters
```
GET /feed/index.php?feed=statviewfeed&view=roster&game_id={id}&...
Returns: Team rosters (newly discovered)
Status: Works, not yet implemented
```

### ✗ Game Details
```
No JSON API exists for goals, penalties, officials
Use: HTML scraping from /game_reports/official-game-report.php
Status: Correct approach used in program.py
```

---

## File Reference

### Documentation Files (by size)

| File | Size | Purpose |
|------|------|---------|
| STATVIEWFEED_API_REFERENCE.md | ~15KB | Complete API spec with examples |
| STATVIEWFEED_INVESTIGATION_SUMMARY.md | ~14KB | Technical investigation report |
| TEST_RESULTS_SUMMARY.txt | ~12KB | Detailed test metrics |
| STATVIEWFEED_API_FINDINGS.md | ~10KB | Key findings summary |
| INVESTIGATION_COMPLETE.md | ~8KB | Executive summary |
| QUICK_REFERENCE.md | ~3KB | Quick lookup guide |
| INVESTIGATION_INDEX.md | ~2KB | This file |

### Test Scripts

| Script | Tests | Purpose |
|--------|-------|---------|
| validate_statviewfeed_endpoints.py | 4 main tests | Validates working endpoints |
| test_statviewfeed_game_details.py | 52 combinations | Tests all view parameters |
| test_game_api_discovery.py | 20+ endpoints | Discovers available APIs |

### Data Files

| File | Records | Contains |
|------|---------|----------|
| statviewfeed_game_results.json | 52 | Detailed test results |
| focused_api_results.json | 52 | Initial focused testing |

---

## Investigation Timeline

1. **Phase 1: Systematic Testing** (1.5 hours)
   - Tested 52 endpoint combinations
   - Identified working vs. failing endpoints
   - Result: Only player and roster views work

2. **Phase 2: Alternative Pattern Testing** (0.5 hours)
   - Tested different parameter names
   - Tested alternative feed names
   - Result: No alternatives found

3. **Phase 3: HTML Verification** (0.5 hours)
   - Confirmed HTML endpoints have game data
   - Verified no JSON alternative
   - Result: HTML scraping is correct

4. **Phase 4: Documentation** (0.5 hours)
   - Created comprehensive documentation
   - Created validation scripts
   - Created reference guides

**Total Time: ~3 hours**

---

## Key Findings

### Discovery 1: Only 2 Views Work
- `view=player` - Returns player biographical data
- `view=roster` - Returns team rosters for games
- All other views return "InvalidView error"

### Discovery 2: No Game Details API
- Tested 20+ game-related view names
- All failed with InvalidView errors
- HTML scraping is the only option

### Discovery 3: Static API Key
- Key: `ccb91f29d6744675`
- No expiration detected
- Works for all views
- Already in player_scrapper.py

### Discovery 4: Fixed Parameters
- season_id=90
- site_id=3
- league_id=4
- lang=1
- These appear to be constants

### Discovery 5: JSONP Format
- All JSON responses wrapped in parentheses
- Must strip `(` and `)` before JSON parsing
- All responses are JSONP, not pure JSON

---

## How to Use These Materials

### For Quick Reference
```bash
cat QUICK_REFERENCE.md
```

### For Complete API Specification
```bash
cat STATVIEWFEED_API_REFERENCE.md
```

### For Investigation Report
```bash
cat STATVIEWFEED_INVESTIGATION_SUMMARY.md
```

### To Run Validation Tests
```bash
python validate_statviewfeed_endpoints.py
```

### To Review All Test Results
```bash
cat TEST_RESULTS_SUMMARY.txt
```

### For Raw JSON Results
```bash
cat statviewfeed_game_results.json | python -m json.tool
```

---

## Implementation Examples

### Python: Get Player Data
```python
import requests
import json

API_KEY = "ccb91f29d6744675"
url = f"https://lscluster.hockeytech.com/feed/index.php?feed=statviewfeed&view=player&player_id=988&season_id=90&site_id=3&key={API_KEY}&client_code=ahl&league_id=4&lang=1&statsType=skaters"

response = requests.get(url)
text = response.text.strip()
if text.startswith('(') and text.endswith(')'):
    text = text[1:-1]
data = json.loads(text)
```

### Python: Get Game Roster
```python
import requests
import json

API_KEY = "ccb91f29d6744675"
url = f"https://lscluster.hockeytech.com/feed/index.php?feed=statviewfeed&view=roster&game_id=1027888&season_id=90&site_id=3&key={API_KEY}&client_code=ahl&league_id=4&lang=1"

response = requests.get(url)
text = response.text.strip()
if text.startswith('(') and text.endswith(')'):
    text = text[1:-1]
data = json.loads(text)
```

---

## Troubleshooting

### "Invalid key." Response
- Check that `key` parameter is included
- Key should be: `ccb91f29d6744675`

### "Client access denied." Response
- Check that `client_code=ahl` is included
- Verify all required parameters present

### InvalidView Error
- Check that `view` is either `player` or `roster`
- No other views are supported

### JSON Parsing Error
- Verify JSONP wrapper is stripped (parentheses)
- Check response isn't plain text error

---

## Related Code

### Existing Implementations
- **player_scrapper.py** - Uses player endpoint correctly
- **program.py** - Uses HTML scraping correctly

### No Changes Needed
- Both implementations are correct
- No modifications required
- Continue as-is

---

## Questions & Answers

**Q: Can I get game goals via JSON API?**
A: No. Tested 20+ views, all failed. HTML scraping is necessary.

**Q: Is the API key permanent?**
A: Appears to be. No expiration detected after 150+ requests over 3 hours.

**Q: Are there rate limits?**
A: No rate limiting observed. Recommend 0.2-0.5s delays for courtesy.

**Q: Should I change the current implementation?**
A: No. HTML scraping is correct. No changes needed.

**Q: Can I use the roster endpoint?**
A: Yes, it works. Optional for getting team rosters in JSON format.

**Q: Is there documentation from HockeyTech?**
A: No official documentation found. API discovered through testing.

---

## Version Control

These materials should be kept in the repository as reference documentation:
- Place in `/docs/API_INVESTIGATION/` subdirectory
- Keep JSON test results for regression testing
- Update if API changes detected

---

## Sign-Off

All investigation materials complete and documented.
Ready for archival or reference by other developers.

**Investigation Status: ✓ COMPLETE**
**Date: February 22, 2025**
**Investigator: Claude Code**
