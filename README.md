# OTA ReelFlow Agent

AI-powered YouTube Shorts sequential uploader from Google Drive.

## Setup

1. **Install dependencies:**
```bash
pip install -r requirements.txt
```

2. **Configure environment:**
```bash
cp .env.example .env
# Edit .env with your credentials
```

3. **Google Cloud Setup:**
   - Enable Google Drive API and YouTube Data API v3
   - Create OAuth 2.0 credentials
   - Download `google_credentials.json` to `credentials/`

4. **Run the agent:**
```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| POST | `/upload/trigger` | Trigger manual upload |
| GET | `/status` | Get system status |
| GET | `/logs` | Get upload logs |
| POST | `/scheduler/pause` | Pause scheduler |
| POST | `/scheduler/resume` | Resume scheduler |

## Deployment (Render)

- **Build Command:** `pip install -r requirements.txt`
- **Start Command:** `uvicorn main:app --host 0.0.0.0 --port $PORT`