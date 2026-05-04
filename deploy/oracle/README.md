# Oracle Cloud Always Free VM Deployment

This deploys the FastAPI backend on an Oracle Cloud VM with Docker Compose.
The frontend can stay on Vercel. Caddy provides HTTPS and proxies traffic to
the backend container.

## 1. Create the VM

In Oracle Cloud Console:

1. Create an Always Free eligible VM in your home region.
2. Prefer `VM.Standard.A1.Flex` with 1-2 OCPUs and 6-12 GB RAM.
3. Use Ubuntu as the image.
4. Keep the boot volume at 50 GB or larger.
5. Assign a public IPv4 address.
6. Add your SSH public key.

Open inbound ports in the VM's security list or NSG:

- TCP `22` from your IP
- TCP `80` from `0.0.0.0/0`
- TCP `443` from `0.0.0.0/0`

Do not expose port `8000`; only Caddy should reach the backend container.

## 2. Point a Domain

For a real domain, create an `A` record:

```text
api.example.com -> ORACLE_VM_PUBLIC_IP
```

For a quick free demo without buying a domain, use `sslip.io`:

```text
129.154.12.34.sslip.io
```

Replace `129.154.12.34` with your VM public IP.

## 3. Install Docker on the VM

SSH into the VM:

```bash
ssh ubuntu@ORACLE_VM_PUBLIC_IP
```

Install Git, clone the repo, and run the Docker installer:

```bash
sudo apt-get update
sudo apt-get install -y git
git clone YOUR_REPO_URL insightx
cd insightx
bash deploy/oracle/install-docker-ubuntu.sh
newgrp docker
```

## 4. Deploy

Go to the deploy folder:

```bash
cd ~/insightx/deploy/oracle
cp .env.example .env
nano .env
```

Set:

- `BACKEND_DOMAIN`
- `CORS_ORIGINS`
- `ANTHROPIC_API_KEY`
- `SECRET_KEY`

Generate a fresh secret:

```bash
openssl rand -hex 32
```

Create the persistent data directory:

```bash
sudo mkdir -p /opt/insightx/data
```

Start the backend:

```bash
docker compose up -d --build
docker compose logs -f backend caddy
```

Check health:

```bash
set -a
. ./.env
set +a
curl -i "https://${BACKEND_DOMAIN}/api/health"
```

Expected response:

```json
{"status":"ok","version":"1.0.0"}
```

## 5. Update Vercel

In Vercel Project Settings, set:

```text
BACKEND_URL=https://YOUR_BACKEND_DOMAIN
```

Redeploy the frontend after setting the env var.

## Useful Commands

```bash
cd ~/insightx/deploy/oracle
docker compose ps
docker compose logs -f backend
docker compose logs -f caddy
docker compose pull
docker compose up -d --build
```

Back up DuckDB/uploads:

```bash
sudo tar -czf insightx-data-backup.tgz /opt/insightx/data
```
