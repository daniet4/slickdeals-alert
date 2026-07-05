# Fire Deals 100+ HTML Scraper

## Purpose
A separate script that scrapes the Slickdeals HTML search page for fire deals in
the last 7 days, finds those with thumb score >= 100, and sends Discord
notifications. Complements the existing RSS-based alert system which cannot
capture high-scoring deals due to RSS feed limits (~25 recent items).

## Files
- `scripts/check_fire_deals.py` — HTML scraper, Nuxt JSON parser, Discord
  notifier with verbose debug output
- `.github/workflows/check-fire-deals.yml` — separate workflow
  (`workflow_dispatch` only)
- `fire_deals_seen.json` — seen GUID cache (gitignored), separate from RSS
  cache

## Search URL
```
https://slickdeals.net/search?q=&searchtype=normal&sort=recent
  &filters[rating][]=firedeal
  &filters[date][]=7
```

Filters: fire deals only, last 7 days, sorted by most recent.

## Script Flow
1. Fetch HTML search page (page 1).
2. Extract `#__NUXT_DATA__` JSON from `<script>` tag.
3. Resolve Nuxt's flat-array-with-references format to get deal objects.
4. Read pagination info — if more pages exist, fetch and parse each.
5. For each deal, extract: `threadId` (dedup key), `dealTitle`, `dealThreadUrl`
   (prepend `https://slickdeals.net`), `dealImageUrl`, `socialVoteCount`,
   `threadIsoDatetime`, `storeName`, `authorUserName`.
6. Filter to `socialVoteCount >= 100`.
7. Cross-reference `threadId` against seen set from `fire_deals_seen.json`.
8. New unseen deals → send Discord embed.
9. Save all qualifying `threadId`s back to `fire_deals_seen.json`.

## First Run
Quiet — all qualifying GUIDs are added to the seen set. No notifications fire.

## Discord Embed
Same webhook URL and role ID as RSS alerts (repo secrets). Embed fields:
- Title → deal title, linked to full thread URL
- Thumbnail → deal image
- Fields: Feed name ("Fire Deals 100+"), Thumb Score, Store, Date (PST)
- Content: role ping (`<@&{DISCORD_ROLE_ID}>`)

## Workflow
```yaml
name: Check Fire Deals
on: workflow_dispatch
jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7
      - uses: actions/cache/restore@v5
        with:
          path: fire_deals_seen.json
          key: fire-deals-guids
      - run: python3 scripts/check_fire_deals.py
        env:
          DISCORD_WEBHOOK_URL: ${{ secrets.DISCORD_WEBHOOK_URL }}
          DISCORD_ROLE_ID: ${{ secrets.DISCORD_ROLE_ID }}
      - uses: actions/cache/save@v5
        with:
          path: fire_deals_seen.json
          key: fire-deals-guids
```

## Debug Output
The script includes verbose print statements:
- Fetch status for each page
- Number of deals found per page
- Parsed deal titles and scores
- Which deals qualify vs are filtered out
- Seen vs new counts
- Notification send status

## Configuration
Hardcoded in script: URL, threshold (100), date range (7 days). No separate
config file needed.
