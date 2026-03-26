# Manager Alert

Daily Israel alert report for Slack. Helps managers and colleagues outside Israel understand the security situation affecting their Israeli teammates.

Posts a compact English summary of rocket/siren alerts to a Slack channel via webhook, with overnight alert tracking to flag sleep disruption.

## Report Examples

**Heavy day with overnight alerts:**
```
🇮🇱 Israel Daily Vibe Check -- March 26, 2026
🔴 Heavy day — 803 sirens, including overnight

😴 Sleepy colleagues alert! 11 sirens overnight (22:00-07:00)
  Tel Aviv 3x · Haifa 4x · Ashdod 3x · Ramat Gan 1x
  Maybe go easy on the morning meetings.

📌 Sirens = take shelter for ~10 min. Most colleagues are safe but disrupted.

Central Israel
  Tel Aviv 12x · Ramat Gan 6x · Herzliya 6x · Rishon LeZion 4x
  Ra'anana 3x · Hod HaSharon 3x · Kfar Saba 2x
Haifa Area
  Haifa 5x · Kiryat Bialik 1x
Northern Israel
  Acre 4x · Nahariya 3x · Shlomi 3x

...and 695 sirens across 475 smaller communities

Full alert map | Source: Pikud HaOref
```

**Moderate day:**
```
🇮🇱 Israel Daily Vibe Check -- March 26, 2026
🟡 Moderate — 18 sirens

📌 Sirens = take shelter for ~10 min. Most colleagues are safe but disrupted.

Northern Israel
  Nahariya 6x · Acre 4x · Kiryat Shmona 3x

...and 5 sirens across 3 smaller communities

Full alert map | Source: Pikud HaOref
```

**Quiet day:**
```
🇮🇱 Israel Daily Vibe Check -- March 26, 2026
☕ All quiet! Your Israeli colleagues had a peaceful 24h. Business as usual.
```

## Quick Start

```bash
# Clone and install
git clone https://github.com/ohadlevy/manager-alert.git
cd manager-alert
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# Configure
cp .env.example .env
# Edit .env with your Slack webhook URL

# Collect alerts and send a report
python -m manager_alert collect
python -m manager_alert report --dry-run    # preview
python -m manager_alert report              # send to Slack
```

## Setup

### Slack Webhook (no bot approval needed)

1. In Slack, go to **Automations** → create a new Workflow
2. Set trigger to **"From a webhook"**
3. Add a variable called `report` (type: text)
4. Add step: **"Send a message to a channel"** → select your channel
5. Map `{{report}}` to the message body
6. Publish and copy the webhook URL to your `.env`

### Configuration

All settings via environment variables (see `.env.example`):

| Variable | Description | Default |
|----------|-------------|---------|
| `SLACK_WEBHOOK_URL` | Slack webhook URL | required |
| `OREF_CATEGORIES` | Alert categories to include | `1,2` (Missiles, UAV) |
| `ALERT_LOOKBACK_HOURS` | Hours of history in report | `24` |
| `NIGHT_START_HOUR` | Night period start | `22` |
| `NIGHT_END_HOUR` | Night period end | `7` |
| `LOG_LEVEL` | Logging level | `INFO` |

## Commands

```bash
python -m manager_alert serve                # run scheduler (collect + daily report)
python -m manager_alert collect              # poll oref API, store in SQLite
python -m manager_alert report               # send daily report
python -m manager_alert report --dry-run     # preview without sending
python -m manager_alert report --live        # fetch live from API (skip db)
```

## Container (Podman Compose)

```bash
# Start (builds + runs in background)
podman compose up -d --build

# View logs
podman compose logs -f

# Manual commands inside container
podman compose exec manager-alert python -m manager_alert report --dry-run

# Stop
podman compose down
```

Or pull the pre-built image:

```bash
podman run -d \
  --name manager-alert \
  --env-file .env \
  -v ./data:/app/data:Z \
  ghcr.io/ohadlevy/manager-alert:latest
```

The container must run from an Israeli IP (oref API is geo-restricted).

## Architecture

```
┌─────────────────────────────────────────┐
│  Container (UBI9 + Python 3.12)         │
│                                         │
│  scheduler (python process)             │
│    every 10min → collect                │
│                  └ oref API → SQLite    │
│    daily 13:00 → report                 │
│                  └ SQLite → report text │
│                    └ POST → Slack       │
│                                         │
│  data/alerts.db        (24h history)    │
└─────────────────────────────────────────┘
```

## How It Works

1. **Collector** polls the Pikud HaOref (Home Front Command) API every 10 minutes and stores alerts in SQLite. The API only keeps ~3h of history, so continuous polling builds a full 24h picture.

2. **Report** reads the last 24h from SQLite, groups alerts by city and region, highlights overnight alerts (22:00-07:00), and posts to Slack. The API provides English city names directly.

## Data Sources

- Alerts: [Pikud HaOref](https://www.oref.org.il/) (Israel Home Front Command)
- Alert map: [Tzevadom](https://tzevadom.com/)

## Tests

```bash
pip install pytest
pytest tests/ -v
```

## License

MIT
