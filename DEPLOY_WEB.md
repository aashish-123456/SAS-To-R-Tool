# Deploy To The Public Web

This app now supports single-service deployment (frontend + backend in one container).

## Option 1: Render (recommended)

1. Push this repo to GitHub.
2. In Render, create a new **Web Service** from the repo.
3. Choose:
   - Runtime: `Docker`
   - Branch: your branch (for example `main`)
4. Add environment variable:
   - `ALLOWED_ORIGINS` = `*` (or set your exact domain later)
5. Deploy.
6. Open the generated Render URL and share it.

## Option 2: Railway

1. Push this repo to GitHub.
2. In Railway, create a new project from the repo.
3. Railway will detect `Dockerfile` and build automatically.
4. Add env var:
   - `ALLOWED_ORIGINS` = `*`
5. Deploy and share the public Railway domain.

## Local production-like test

From repository root:

```powershell
docker build -t sas-r-converter .
docker run -p 8000:8000 sas-r-converter
```

Then open `http://localhost:8000`.
