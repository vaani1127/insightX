# Hugging Face Spaces Backend Deployment

Use this when you need a no-credit-card free deployment for the backend.
The frontend can stay on Vercel.

Important limitation: free Hugging Face Spaces disk is ephemeral, so uploaded
files and the DuckDB database can be lost when the Space restarts or sleeps.
This is good for demos, not for durable production data.

## 1. Create the Space

1. Go to <https://huggingface.co/spaces>.
2. Click **Create new Space**.
3. Name it `insightx-backend`.
4. Select **Docker** as the SDK.
5. Select **CPU Basic** hardware.
6. Create the Space.

## 2. Add Variables and Secrets

In the Space, open **Settings**.

Add these as **Secrets**:

```text
ANTHROPIC_API_KEY=your-rotated-anthropic-key
SECRET_KEY=your-new-secret-key
```

Generate `SECRET_KEY` locally with:

```powershell
openssl rand -hex 32
```

Add these as **Variables**:

```text
PORT=7860
ENVIRONMENT=prod
DUCKDB_PATH=/tmp/insightx.duckdb
UPLOADS_DIR=/tmp/insightx-uploads
ACCESS_TOKEN_EXPIRE_MINUTES=1440
CORS_ORIGINS=["https://natwest-zeta.vercel.app"]
CLAUDE_MODEL=claude-sonnet-4-6
```

## 3. Push Backend Files to the Space

Clone the Space repository next to this project:

```powershell
cd "D:\My Workspace\NATWEST"
git clone https://huggingface.co/spaces/YOUR_HF_USERNAME/insightx-backend hf-insightx-backend
```

Copy the backend files into it:

```powershell
Copy-Item -Recurse -Force ".\Natwest\backend\*" ".\hf-insightx-backend\"
Copy-Item -Force ".\Natwest\deploy\huggingface\Space.README.md" ".\hf-insightx-backend\README.md"
```

Commit and push:

```powershell
cd ".\hf-insightx-backend"
git add .
git commit -m "Deploy InsightX backend"
git push
```

Hugging Face will build the Docker image automatically.

## 4. Test the Backend

After the Space status says **Running**, test:

```powershell
curl.exe -i https://YOUR_HF_USERNAME-insightx-backend.hf.space/api/health
```

Expected response:

```json
{"status":"ok","version":"1.0.0"}
```

## 5. Update Vercel

In Vercel project settings, set:

```text
BACKEND_URL=https://YOUR_HF_USERNAME-insightx-backend.hf.space
```

Redeploy the frontend.
