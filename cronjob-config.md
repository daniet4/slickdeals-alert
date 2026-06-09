# Cron-job.org Configuration

- **Trigger URL**: `POST https://api.github.com/repos/daniet4/slickdeals-alert/actions/workflows/check-deals.yml/dispatches`
- **Headers**: `Authorization: Bearer <github_pat>`, `Content-Type: application/json`
- **Body**: `{"ref": "main"}`
- **Schedule**: Every 15 minutes
