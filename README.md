# Slickdeals Deal Alerts

Monitors Slickdeals RSS feeds for deals matching a search filter, filters by thumb score (community popularity), and sends Discord notifications with product images.

Runs on GitHub Actions every 15 minutes via cron-job.org — completely free, no local hardware needed, 24/7 uptime.

## How It Works

1. **cron-job.org** sends a POST to GitHub's API every 15 minutes
2. **GitHub Actions** runs `scripts/check_deals.py`
3. The script fetches each RSS feed from `config/feeds.json`, parses items, and extracts thumb scores from the HTML description
4. Items with thumb score >= the feed's threshold are kept
5. Already-seen items (tracked via `seen_guids.json`, cached between runs) are skipped
6. New qualifying deals are sent to Discord as embeds with a role ping

## Setup

### Prerequisites

- A GitHub account
- A Discord server where you can create webhooks

### 1. Create a Discord Webhook

1. Open your Discord server → **Server Settings → Integrations → Webhooks**
2. Click **New Webhook**
3. Name it (e.g. "Slickdeals Deals"), select a channel, click **Copy Webhook URL**
4. Save this URL — you'll need it in step 3

### 2. Push the Repo to GitHub

```bash
git init
git add .
git commit -m "Initial commit"
```

Create a new repository on GitHub, then:

```bash
git remote add origin https://github.com/YOUR_USER/YOUR_REPO.git
git branch -M main
git push -u origin main
```

### 3. Add GitHub Secrets

Go to your repo → **Settings → Secrets and variables → Actions → New repository secret** and add:

| Secret Name | Value |
|---|---|
| `DISCORD_WEBHOOK_URL` | The Discord webhook URL from step 1 |
| `DISCORD_ROLE_ID` | (Optional) A Discord role ID to ping — see below |

**Getting a Discord Role ID:**
- Create a role in Server Settings → Roles (e.g. @deals)
- Enable **Developer Mode** in Discord (User Settings → Advanced → Developer Mode)
- Right-click the role name in the roles list → **Copy ID**
- Add it as the `DISCORD_ROLE_ID` secret

### 4. Set Up cron-job.org

1. Go to [cron-job.org](https://cron-job.org) and create a free account
2. Click **Cronjobs → Create Cronjob**
3. Configure:

| Field | Value |
|---|---|
| Title | `Slickdeals Alert Trigger` |
| URL | `https://api.github.com/repos/YOUR_USER/YOUR_REPO/actions/workflows/check-deals.yml/dispatches` |
| Request method | `POST` |
| Content Type | `application/json` |
| Post Body | `{"ref": "main"}` |
| HTTP Headers | Add header: `Authorization` → `Bearer YOUR_GITHUB_PAT` |
| Schedule | Every 15 minutes at :00, :15, :30, :45 |

4. Click **Save**

**Getting a GitHub PAT:**
- Go to https://github.com/settings/tokens → **Generate new token → Fine-grained token**
- Repository access: only your repo
- Permissions → Actions: **Read and write**
- Generate and copy the token

### 5. Verify

After saving the cron-job, wait a few minutes. Check your Discord channel — you should see deal embeds appear. Check the repo's **Actions** tab to see workflow runs.

## Adding More Feeds

Edit `config/feeds.json`. Each feed has:

```json
{
  "name": "Your Feed Name",
  "url": "https://slickdeals.net/newsearch.php?q=...",
  "thumb_threshold": 5
}
```

- **name**: Displayed in Discord embed
- **url**: Any Slickdeals search URL. The `&rss=1` parameter is added automatically if missing
- **thumb_threshold**: Minimum thumb score (community votes). Items below this are ignored

You can also use a `filter` field instead of `url` — the script will URL-encode it and build the RSS URL:

```json
{
  "name": "MacBook Deals",
  "filter": "@title \"MacBook Air\" | \"MacBook Pro\""
}
```

Double quotes inside the filter use `\"` escaping per JSON syntax.

Commit and push changes. No other setup needed.

## File Structure

```
├── .github/workflows/check-deals.yml   — GitHub Actions workflow
├── config/feeds.json                    — Feed definitions
├── scripts/check_deals.py              — RSS fetcher, parser, Discord notifier
├── cronjob-config.md                   — cron-job.org reference
├── seen_guids.json                     — Cache of seen GUIDs (gitignored)
└── README.md
```
