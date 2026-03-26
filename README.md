# Manager Alert

Daily Israel alert report for Slack. Helps managers and colleagues outside Israel understand the security situation affecting their Israeli teammates.

Posts a compact English summary of rocket/siren alerts to a Slack channel via webhook, with overnight alert tracking to flag sleep disruption.

## Report Examples

**Typical day:**
```
🇮🇱 Israel Daily Vibe Check -- March 26, 2026
18 sirens across 7 areas in the last 24h
😴 Sleepy colleagues alert! 11 sirens went off overnight (22:00-07:00) in 5 areas. Maybe go easy on the morning meetings.

Tel Aviv (תל אביב)  5x Missiles/UAV  02:15-11:15 😴
Haifa (חיפה)  4x Missiles  01:15-14:15 😴
Ashdod (אשדוד)  3x Missiles  02:15-05:15 😴
Herzliya (הרצליה)  2x Missiles  10:15-11:15
...
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
python -m manager_alert watch "תל אביב"     # add city to watchlist
python -m manager_alert unwatch "חיפה"       # remove city
python -m manager_alert list                 # show watched cities
```

## Container (Podman Compose)

```bash
# Start (builds + runs in background)
podman compose up -d --build

# View logs
podman compose logs -f

# Manual commands inside container
podman compose exec manager-alert python -m manager_alert report --dry-run
podman compose exec manager-alert python -m manager_alert watch "תל אביב"

# Stop
podman compose down
```

Or without compose:

```bash
podman build -t manager-alert -f Containerfile .
podman run -d \
  --name manager-alert \
  --env-file .env \
  -v ./data:/app/data:Z \
  manager-alert
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
│  data/subscribers.json (watchlist)      │
└─────────────────────────────────────────┘
```

## How It Works

1. **Collector** polls the Pikud HaOref (Home Front Command) API every 10 minutes and stores alerts in SQLite. The API only keeps ~3h of history, so continuous polling builds a full 24h picture.

2. **Report** reads the last 24h from SQLite, groups alerts by city, translates city names to English, highlights overnight alerts (22:00-07:00), and posts to Slack.

3. **City names** are translated to English for the ~80 most common Israeli cities. Unknown cities stay in Hebrew.

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
