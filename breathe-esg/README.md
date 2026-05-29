# BREATHE ESG

Professional, lightweight emission-data ingestion and review portal used for CSV-based uploads (SAP, Utility, Corporate Travel), record validation, and analyst review.

**Plan**
- 1) Describe project purpose and scope.
- 2) List prerequisites and recommended versions.
- 3) Provide step-by-step local setup for backend and frontend.
- 4) Explain common workflows: login, upload, delete, review.
- 5) Provide testing and deployment notes and contribution guidance.

**Project**
- Purpose: ingest CSV files from common enterprise sources, parse and normalize emission data, present records for analyst review and approval.
- Stack: Django REST backend (DRF) + SQLite for local dev, React + Vite frontend.

**Prerequisites**
- **Python:** 3.10+ installed (virtualenv recommended).
- **Node.js & npm:** Node 18+ (npm available).
- **OS:** Linux / macOS / Windows (instructions use cross-platform commands where possible).

**Quick Setup (Local)**
1. Create and activate a Python virtual environment (recommended):

```bash
python -m venv .venv
# Windows PowerShell
.\.venv\Scripts\Activate.ps1
# macOS / Linux
source .venv/bin/activate
```

2. Install Python dependencies:

```bash
pip install -r requirements.txt
```

3. Install frontend dependencies:

```bash
cd frontend
npm install
cd ..
```

4. Initialize database and create a superuser:

```bash
.venv\Scripts\python.exe manage.py migrate
.venv\Scripts\python.exe manage.py createsuperuser
```

5. (Optional) Load sample data:

```bash
# Sample CSVs are in sample_data/
# Use the frontend upload UI or send multipart POST to /api/upload/
```

**Run (Development)**
- Start the backend (binds to 127.0.0.1:8000):

```bash
.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000
```

- Start the frontend (Vite) (binds to 127.0.0.1:5178):

```bash
cd frontend
npm run dev -- --host 127.0.0.1 --port 5178
```

- Open the app in your browser: `http://127.0.0.1:5178`

**Auth & API**
- The frontend authenticates via JWT at `/api/auth/token/` and refreshes via `/api/auth/token/refresh/`.
- API base: `/api/` (proxied from the frontend dev server to `http://127.0.0.1:8000`).

**Key User Workflows**
- Login: use the `/login` page in the frontend (store tokens in `localStorage`).
- Upload CSV: go to the `Upload` page, pick source type and tenant slug, then `Upload & Ingest`.
- Review: access `Review` to examine parsed records and approve/reject/flag them.
- Delete upload batch (uploader-only): on the `Dashboard` recent batches list, a `Delete` button (appears only for the uploader) removes the batch and its records. Backend enforces uploader-only deletion.

**Developer Notes**
- Backend changes affecting serializers or views should include tests in `api/tests.py` and/or `ingestion/tests.py`.
- Recent work: `IngestionBatchSerializer` now exposes `is_mine` (frontend uses it to show the Delete button). See [api/serializers.py](api/serializers.py#L1).
- `BatchDetailView` supports `DELETE` with uploader-only permission. See [api/views.py](api/views.py#L1).
- Frontend dashboard UI updated in [frontend/src/pages/DashboardPage.jsx](frontend/src/pages/DashboardPage.jsx#L1) to show Delete button and call `DELETE /api/batches/<id>/`.

**Testing**
- Run backend tests:

```bash
.venv\Scripts\python.exe manage.py test
```

**Commit & Push to GitHub**
- Example commands to push this repo to GitHub:

```bash
git init
git add .
git commit -m "Initial breathe-esg import and README"
git remote add origin git@github.com:YOUR_USERNAME/YOUR_REPO.git
git push -u origin main
```

**Troubleshooting**
- If the frontend cannot reach the API, ensure Vite dev server is started with `--host 127.0.0.1` and the backend is running on `127.0.0.1:8000`.
- If binary packages (numpy/pandas) raise C-extension import errors, recreate the virtualenv and reinstall pinned versions from `requirements.txt`.

**Contributing**
- Fork, create a feature branch, implement changes, add tests, and open a PR describing the change.

**License & Contact**
- Add your preferred license at the repository root.
- For questions or handoff details, contact the maintainer.

---

If you want, I can:
- Add a short `CONTRIBUTING.md` and `CODE_OF_CONDUCT.md`.
- Create a GitHub Actions workflow to run tests on push.

Tell me which of those you want next.