# Prototype Frontend

This is a minimal static frontend for demo and judging.

## Local Run

1. Start backend:
   ```bash
   uv run python -m server.app
   ```
2. Serve this folder:
   ```bash
   cd prototype
   python3 -m http.server 4173
   ```
3. Open `http://localhost:4173`
4. Keep Backend URL as `http://localhost:8000`
5. Demo pages:
   - `http://localhost:4173/index.html`
   - `http://localhost:4173/events.html`

## Firebase Hosting (Recommended)

Use the repository deploy script so backend URL is injected automatically:

```bash
./scripts/deploy_firebase.sh <firebase_project_id> <cloud_run_url>
```

Manual option (if you do not use the script):

```bash
npm install -g firebase-tools
firebase login
firebase init hosting
# choose existing project
# public directory: prototype
# single-page app: no
firebase deploy
```

After deploy, set the backend URL in `prototype/config.js`.
