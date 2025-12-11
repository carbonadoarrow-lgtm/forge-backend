# Forge Console Backend

FastAPI backend for the Forge Console operator interface.

## Features

- **Forge OS API**: Infrastructure and runtime management endpoints
- **Orunmila API**: XAU trading intelligence and state management
- **File-based storage**: JSON-backed data layer (Phase 2)
- **CORS enabled**: Ready for frontend integration
- **OpenAPI docs**: Auto-generated at `/api/docs`

## Quick Start

### 1. Install Dependencies

```bash
# Create virtual environment (recommended)
python -m venv .venv

# Activate on Windows
.venv\Scripts\activate

# Activate on macOS/Linux
source .venv/bin/activate

# Install packages
pip install -r requirements.txt
```

### 2. Run the Server

```bash
uvicorn src.main:app --reload --port 8000
```

The API will be available at:
- API Base: `http://localhost:8000/api`
- Interactive Docs: `http://localhost:8000/api/docs`
- ReDoc: `http://localhost:8000/api/redoc`
- Health Check: `http://localhost:8000/healthz`

### 3. Test the API

```bash
# Get Forge skills
curl http://localhost:8000/api/forge/skills

# Get Orunmila daily state
curl http://localhost:8000/api/orunmila/state/daily

# Trigger a skill run
curl -X POST http://localhost:8000/api/forge/skills/skill-1/run \
  -H "Content-Type: application/json" \
  -d '{"triggerSource": "manual"}'
```

## Project Structure

```
forge-backend/
├── src/
│   ├── main.py              # FastAPI app with routes
│   ├── config.py            # Configuration settings
│   ├── schemas.py           # Pydantic models
│   ├── storage.py           # File-based storage layer
│   └── routers/
│       ├── forge.py         # Forge API routes
│       └── orunmila.py      # Orunmila API routes
├── data/                    # JSON data files
│   ├── forge_skills.json
│   ├── forge_missions.json
│   ├── forge_runs.json
│   ├── forge_reports.json
│   ├── forge_artifacts.json
│   ├── forge_system_status.json
│   ├── orunmila_skills.json
│   ├── orunmila_missions.json
│   ├── orunmila_runs.json
│   ├── orunmila_reports.json
│   ├── orunmila_daily_state.json
│   ├── orunmila_cycle4w_state.json
│   └── orunmila_structural_state.json
├── requirements.txt
└── README.md
```

## API Endpoints

### Forge OS

- `GET /api/forge/skills` - List all skills
- `GET /api/forge/skills/{id}` - Get skill details
- `POST /api/forge/skills/{id}/run` - Trigger skill run
- `GET /api/forge/missions` - List all missions
- `POST /api/forge/missions/{id}/run` - Trigger mission run
- `GET /api/forge/runs` - List all runs
- `GET /api/forge/reports` - List all reports
- `GET /api/forge/artifacts` - List all artifacts
- `GET /api/forge/system/status` - Get system status

### Orunmila

- `GET /api/orunmila/skills` - List all skills
- `POST /api/orunmila/skills/{id}/run` - Trigger skill run
- `GET /api/orunmila/missions` - List all missions
- `POST /api/orunmila/missions/{id}/run` - Trigger mission run
- `GET /api/orunmila/runs` - List all runs
- `GET /api/orunmila/reports` - List all reports
- `GET /api/orunmila/state/daily` - Get daily state
- `GET /api/orunmila/state/cycle-4w` - Get cycle state
- `GET /api/orunmila/state/structural` - Get structural state
- `GET /api/orunmila/oracle/dashboard` - Get consolidated dashboard

## Configuration

Environment variables (optional, create `.env` file):

```env
FORGE_BACKEND_MODE=file    # file | sandbox | prod
FORGE_DATA_DIR=data
FORGE_CORS_ORIGINS=["http://localhost:3000"]
```

## Frontend Integration

Point your frontend to this backend:

```bash
# In forge-console/.env.local
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api
NEXT_PUBLIC_USE_MOCK_DATA=false
```

## Development

### Run with Auto-reload

```bash
uvicorn src.main:app --reload --port 8000
```

### View API Documentation

Open http://localhost:8000/api/docs in your browser for interactive API docs.

### Testing POST Endpoints

```bash
# Run a Forge skill
curl -X POST http://localhost:8000/api/forge/skills/skill-1/run \
  -H "Content-Type: application/json"

# Run an Orunmila mission
curl -X POST http://localhost:8000/api/orunmila/missions/xau-mission-1/run \
  -H "Content-Type: application/json" \
  -d '{"triggerSource": "manual"}'
```

## Next Steps

### Phase 3: Connect to Real Data

Replace file-based storage with adapters:

1. Create `src/adapters/forge_registry.py`
2. Create `src/adapters/orunmila_state.py`
3. Update routes to use adapters instead of `load_list()`

### Phase 4: Add Authentication

1. Install: `pip install python-jose[cryptography] passlib[bcrypt]`
2. Create `src/auth.py` with JWT handling
3. Add authentication middleware
4. Protect POST endpoints

### Phase 5: Add WebSocket Support

For real-time log streaming:

```bash
pip install websockets
```

## Roadmap

- [x] Phase 1: API Contracts
- [x] Phase 2: File-based Backend
- [ ] Phase 3: Real Data Adapters
- [ ] Phase 4: Authentication & Authorization
- [ ] Phase 5: WebSocket for Live Logs
- [ ] Phase 6: Production Deployment

## License

Internal use only.
