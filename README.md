# 🔥🍑 Fire or Cheeks

A live voting game for virtual meetings. The host shows an image or prompt, and participants vote:
- 🔥 **FIRE** — cool / good / approved
- 🍑 **CHEEKS** — terrible / bad / rejected

Built with FastAPI, Jinja2 templates, vanilla JS, SQLite, and WebSockets.

---

## Quick Start (Local)

### 1. Clone & install

```bash
git clone https://github.com/thejoestory/fire-or-cheeks.git
cd fire-or-cheeks
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure

```bash
cp .env.example .env
# Edit .env to set your HOST_PIN (default: 1234)
```

### 3. Run

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8028
```

Open `http://localhost:8028` in your browser.

---

## How to Play

### Host creates a game

1. Go to `http://localhost:8028`
2. Click **Host a Game**
3. Enter a title and your **Host PIN** (default: `1234`, set in `.env`)
4. You'll land on the **Host Dashboard** — share the join code with players

### Players join

1. Go to `http://localhost:8028` (or the server URL)
2. Click **Join a Game**, enter the game code and a display name
3. OR go directly to `/join?code=XXXXXX`

### Running a round

From the **Host Dashboard**:

1. **Upload an image** and/or type a **prompt/caption**
2. Click **Create Round** — all connected screens update immediately
3. Click **▶ Start Voting** — players can now cast votes (🔥 or 🍑)
4. Watch live vote counts update in real time
5. Click **⏹ Stop Voting** — voting closes for all players
6. Click **👁 Reveal Results** — everyone sees the final tally and verdict

**Verdicts:**
- `CERTIFIED FIRE 🔥` — fire wins clearly
- `ABSOLUTE CHEEKS 🍑` — cheeks wins clearly
- `CHAOS SPLIT` — within 10% either way

### Display screen

Open `/display/XXXXXX` for a big-screen mode — perfect for sharing your screen in Teams/Zoom. It auto-updates via WebSocket with no controls shown.

---

## Environment Variables

| Variable      | Default                        | Description                        |
|---------------|--------------------------------|------------------------------------|
| `DATABASE_URL`| `sqlite:///./fire_or_cheeks.db`| SQLite database path               |
| `UPLOAD_DIR`  | `app/static/uploads`           | Where uploaded images are stored   |
| `HOST_PIN`    | `1234`                         | PIN required to create/control games |
| `ROOT_PATH`   | *(empty)*                      | Set to `/fire-or-cheeks` when proxied under a subpath |

---

## Project Structure

```
fire-or-cheeks/
├── app/
│   ├── main.py             # FastAPI app, routes, WebSocket endpoint
│   ├── database.py         # SQLite connection, init_db()
│   ├── models.py           # Python dataclasses for DB rows
│   ├── schemas.py          # Pydantic validation schemas
│   ├── services.py         # DB queries / business logic
│   ├── websocket_manager.py# WebSocket connection manager
│   ├── templates/
│   │   ├── base.html
│   │   ├── home.html
│   │   ├── host_new.html
│   │   ├── host.html
│   │   ├── join.html
│   │   ├── play.html
│   │   └── display.html
│   └── static/
│       ├── styles.css
│       ├── app.js
│       └── uploads/        # Uploaded images go here
├── requirements.txt
├── .env.example
└── README.md
```

---

## Production Deployment (nginx + uvicorn + systemd)

### 1. systemd service

Create `/etc/systemd/system/fire-or-cheeks.service`:

```ini
[Unit]
Description=Fire or Cheeks
After=network.target

[Service]
User=www-data
WorkingDirectory=/var/www/fire-or-cheeks
EnvironmentFile=/var/www/fire-or-cheeks/.env
ExecStart=/var/www/fire-or-cheeks/venv/bin/uvicorn app.main:app \
    --host 127.0.0.1 \
    --port 8028 \
    --workers 1 \
    --proxy-headers \
    --forwarded-allow-ips='127.0.0.1'
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable fire-or-cheeks
sudo systemctl start fire-or-cheeks
```

### 2. .env for production

```env
DATABASE_URL=sqlite:////var/www/fire-or-cheeks/fire_or_cheeks.db
UPLOAD_DIR=/var/www/fire-or-cheeks/app/static/uploads
HOST_PIN=your-secret-pin
ROOT_PATH=/fire-or-cheeks
```

### 3. nginx config

Save as `/etc/nginx/sites-available/fire-or-cheeks`:

```nginx
# Upstream for the uvicorn process
upstream fire_or_cheeks {
    server 127.0.0.1:8028;
}

server {
    listen 443 ssl;
    server_name www.thejoestory.com;

    # SSL config (adjust paths as needed)
    ssl_certificate     /etc/letsencrypt/live/www.thejoestory.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/www.thejoestory.com/privkey.pem;

    # Serve uploaded images / static files directly via nginx for performance
    location /fire-or-cheeks/static/ {
        alias /var/www/fire-or-cheeks/app/static/;
        expires 7d;
        add_header Cache-Control "public, immutable";
    }

    # WebSocket support
    location /fire-or-cheeks/ws/ {
        proxy_pass         http://fire_or_cheeks;
        proxy_http_version 1.1;
        proxy_set_header   Upgrade $http_upgrade;
        proxy_set_header   Connection "upgrade";
        proxy_set_header   Host $host;
        proxy_set_header   X-Real-IP $remote_addr;
        proxy_set_header   X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto $scheme;
        proxy_read_timeout 86400;
    }

    # Everything else
    location /fire-or-cheeks/ {
        proxy_pass         http://fire_or_cheeks;
        proxy_set_header   Host $host;
        proxy_set_header   X-Real-IP $remote_addr;
        proxy_set_header   X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto $scheme;
        # Pass the script name so FastAPI knows its root path
        proxy_set_header   X-Forwarded-Prefix /fire-or-cheeks;
    }
}

# Redirect HTTP to HTTPS
server {
    listen 80;
    server_name www.thejoestory.com;
    return 301 https://$host$request_uri;
}
```

Enable and reload:

```bash
sudo ln -s /etc/nginx/sites-available/fire-or-cheeks /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

The app will be live at `https://www.thejoestory.com/fire-or-cheeks/`

---

## Notes

- **WebSockets under a subpath**: The JS constructs WebSocket URLs using `window.ROOT_PATH` (injected by the Jinja2 base template from FastAPI's `root_path`). This ensures `/ws/CODE` works correctly whether you're at `/` or `/fire-or-cheeks/`.
- **Images**: Stored in `app/static/uploads/`. Back these up separately in production.
- **Database**: Single SQLite file. For high traffic, swap in PostgreSQL with `databases` + asyncpg.
- **Auth**: Host PIN is intentionally simple — add proper auth if you expose this publicly.
