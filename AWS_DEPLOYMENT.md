# AWS Deployment Documentation

**Last Updated:** 2025-12-27
**Status:** ✅ Live and Operational

---

## Live Endpoints

### Backend (AWS App Runner)
- **Service URL:** https://7d2majjsda.us-east-1.awsapprunner.com
- **Health Check:** https://7d2majjsda.us-east-1.awsapprunner.com/health
- **API Docs:** https://7d2majjsda.us-east-1.awsapprunner.com/docs
- **Region:** us-east-1
- **Service Name:** forge-backend
- **Container:** 620206954964.dkr.ecr.us-east-1.amazonaws.com/forge-backend:latest

### Frontend (AWS Amplify)
- **App URL:** https://main.d29wnhazysxdb8.amplifyapp.com
- **App Name:** forge-console
- **App ID:** d29wnhazysxdb8
- **Branch:** main (auto-deploy enabled)
- **Repository:** https://github.com/carbonadoarrow-lgtm/forge-console

---

## D.12-A API Endpoints (Live)

All D.12-A endpoints are now deployed and operational:

### 1. List Runs
```bash
GET https://7d2majjsda.us-east-1.awsapprunner.com/api/autonomy/v2/runs
Query Parameters:
  - env (optional)
  - lane (optional)
  - status (optional)
  - requested_by (optional)
  - limit (optional, default: 50, max: 200)
  - cursor (optional, for pagination)

Response:
{
  "items": [...],
  "next_cursor": "..." (null if no more results)
}
```

### 2. Get Run Details
```bash
GET https://7d2majjsda.us-east-1.awsapprunner.com/api/autonomy/v2/runs/{run_id}

Response:
{
  "run_id": "...",
  "status": "...",
  "env": "...",
  "lane": "...",
  ...
}

Error Response (404):
{
  "error": {
    "code": "RUN_NOT_FOUND",
    "message": "Run ... not found"
  }
}
```

### 3. Get Run Events
```bash
GET https://7d2majjsda.us-east-1.awsapprunner.com/api/autonomy/v2/runs/{run_id}/events
Query Parameters:
  - limit (optional, default: 200, max: 500)
  - cursor (optional, for pagination)

Response:
{
  "items": [...],
  "next_cursor": "..." (null if no more results)
}
```

---

## Testing Commands

### Backend Health Check
```bash
curl https://7d2majjsda.us-east-1.awsapprunner.com/health
```

### Test D.12-A List Runs
```bash
curl "https://7d2majjsda.us-east-1.awsapprunner.com/api/autonomy/v2/runs?limit=10" | python -m json.tool
```

### Test D.12-A Get Run (replace {run_id})
```bash
curl "https://7d2majjsda.us-east-1.awsapprunner.com/api/autonomy/v2/runs/{run_id}" | python -m json.tool
```

### Test D.12-A Get Events (replace {run_id})
```bash
curl "https://7d2majjsda.us-east-1.awsapprunner.com/api/autonomy/v2/runs/{run_id}/events?limit=20" | python -m json.tool
```

---

## Deployment Process

### Backend Deployment (App Runner)

1. **Build Docker Image**
```bash
cd forge-backend
docker build -t forge-backend:latest -t 620206954964.dkr.ecr.us-east-1.amazonaws.com/forge-backend:latest .
```

2. **Login to ECR**
```bash
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 620206954964.dkr.ecr.us-east-1.amazonaws.com
```

3. **Push to ECR**
```bash
docker push 620206954964.dkr.ecr.us-east-1.amazonaws.com/forge-backend:latest
```

4. **Trigger App Runner Deployment**
```bash
aws apprunner start-deployment --service-arn $(aws apprunner list-services --query "ServiceSummaryList[?ServiceName=='forge-backend'].ServiceArn" --output text)
```

5. **Monitor Deployment**
```bash
aws apprunner list-operations --service-arn $(aws apprunner list-services --query "ServiceSummaryList[?ServiceName=='forge-backend'].ServiceArn" --output text) --max-results 1
```

### Frontend Deployment (Amplify)

Amplify auto-deploys from GitHub on push to main branch.

**Manual Trigger (if needed):**
```bash
aws amplify start-job --app-id d29wnhazysxdb8 --branch-name main --job-type RELEASE
```

**Check Deployment Status:**
```bash
aws amplify list-jobs --app-id d29wnhazysxdb8 --branch-name main --max-results 3
```

---

## Architecture Changes (December 27, 2025)

### Backend Integration
- **Change:** Unified `src/main.py` to use `forge/app.py`'s `create_app()` function
- **Reason:** D.12-A endpoints require V2 state objects (RunStoreV2, EventBusV2, etc.) initialized by `forge/app.py`
- **Result:** All V2 routers now properly initialized on startup

### Dockerfile Updates
- **Added:** `COPY forge/ ./forge/` to include D.12-A API code
- **Added:** `COPY scripts/ ./scripts/` to include migration scripts

### Router Registration
- **Added:** `from forge.autonomy.api_v2 import router as autonomy_v2_router`
- **Registered:** D.12-A endpoints at `/api/autonomy/v2/*`

---

## Environment Variables

### Backend (App Runner)
Set via AWS App Runner service configuration:
- `DATABASE_URL` - SQLite database path (default: sqlite:///data/forge.db)
- `FORGE_BACKEND_MODE` - Deployment mode (file/memory)
- `CORS_ORIGINS` - Allowed CORS origins
- `ADMIN_TOKEN` - Admin authentication token (secret)

### Frontend (Amplify)
Set via Amplify environment variables:
- `NEXT_PUBLIC_API_URL` - https://7d2majjsda.us-east-1.awsapprunner.com
- `NEXT_PUBLIC_API_BASE_URL` - https://7d2majjsda.us-east-1.awsapprunner.com/api

---

## CI/CD Status

### Backend CI
- **File:** `.github/workflows/ci.yml`
- **Tests:** 20/20 passing (D.8 + D.11 + D.12-A)
- **Coverage:** Enabled with pytest-cov
- **Migrations:** Auto-applied before tests

### Frontend CI
- **File:** `.github/workflows/ci.yml`
- **Lint:** ✅ Passing (ESLint configured)
- **Build:** ✅ Passing (Next.js production build)
- **Boundary Guard:** ✅ Passing (no backend imports in UI)

---

## Verification

### Backend Verification (2025-12-27 22:11 EST)
```bash
$ curl https://7d2majjsda.us-east-1.awsapprunner.com/health
{
  "status": "healthy",
  "service": "Forge Backend",
  "version": "1.0.0",
  "mode": "file"
}

$ curl "https://7d2majjsda.us-east-1.awsapprunner.com/api/autonomy/v2/runs?limit=3"
{
  "runs": []
}
```

### Frontend Verification (2025-12-27)
```bash
$ curl -I https://main.d29wnhazysxdb8.amplifyapp.com
HTTP/1.1 200 OK
Content-Type: text/html

✅ UI loads successfully
✅ Cockpit V2 page accessible at /cockpit-v2
```

---

## Troubleshooting

### Backend Issues

**Symptom:** 404 on D.12-A endpoints
**Cause:** Router not registered in main.py
**Fix:** Ensure `app.include_router(autonomy_v2_router)` in src/main.py

**Symptom:** "'State' object has no attribute 'run_store_v2'"
**Cause:** Using src/main.py without forge/app.py initialization
**Fix:** Use `from forge.app import create_app; app = create_app()`

### Frontend Issues

**Symptom:** 404 on Amplify URL
**Cause:** No recent deployment or build failure
**Fix:** Check Amplify build logs, trigger manual deployment if needed

**Symptom:** CORS errors from UI to backend
**Cause:** CORS_ORIGINS not configured on backend
**Fix:** Set CORS_ORIGINS in App Runner environment variables

---

## AWS Resources

### ECR Repository
- **Repository:** 620206954964.dkr.ecr.us-east-1.amazonaws.com/forge-backend
- **Latest Tag:** latest
- **Latest Digest:** sha256:be520819cbbf7a784c32b300dd04df928f95446d35b1105d75163739aa4a0646

### App Runner Service
- **Service ARN:** Check with `aws apprunner list-services`
- **Auto-scaling:** Enabled
- **Health Check:** /health endpoint

### Amplify App
- **App ARN:** Check with `aws amplify get-app --app-id d29wnhazysxdb8`
- **Auto-deploy:** Enabled on main branch
- **Build Command:** `npm run build`

---

## Next Steps

1. ✅ Backend deployed with D.12-A endpoints
2. ✅ Frontend deployed with D.12-B UI polish
3. ✅ All endpoints tested and verified
4. **TODO:** Monitor production usage and performance
5. **TODO:** Set up CloudWatch alarms for App Runner service
6. **TODO:** Configure custom domain (if needed)

---

## Contact

For deployment issues, check:
1. AWS App Runner logs: CloudWatch Logs for forge-backend service
2. Amplify build logs: AWS Amplify Console build history
3. GitHub Actions: CI/CD workflow runs
