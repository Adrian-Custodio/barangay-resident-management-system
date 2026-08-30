# Barangay Resident Management System (BRMS)

A Django-based resident management system built for barangays, featuring face recognition-based resident identification and digital document issuance.

This is an in-progress build of an earlier working version of the system.

## Tech Stack

- **Backend:** Python, Django 5.2
- **Database:** SQLite
- **Face Recognition (planned):** DeepFace (Facenet)
- **Fuzzy Search (planned):** thefuzz
- **Deployment (planned):** Waitress + PyInstaller (Windows-packaged executable)

## Architecture

The system is split into five Django apps, each with a single responsibility:

| App | Responsibility |
|---|---|
| `accounts` | User roles (Administrator / Encoder) via a `Profile` extending Django's built-in `User` |
| `residents` | Core resident records — the entity every other app relates back to |
| `recognition` | Face enrollment and verification, storing facial embeddings (not raw photos) |
| `documents` | Catalog of issuable document types and records of documents actually issued |
| `audit` | A single, generic action log shared across all apps, using Django's `GenericForeignKey` |

Deployment target is a single-machine, offline-capable barangay office setup — this shaped decisions like SQLite over a client-server database, and Waitress (pure-Python WSGI server) over Gunicorn for eventual Windows packaging.

## Current Status

**Done**
- Project scaffolding: 5-app structure with clear domain boundaries
- Full data model layer:
  - `Resident` — core resident record with separated name fields for accurate document formatting
  - `Profile` — two-tier role system (Administrator / Encoder)
  - `FaceProfile` / `FaceVerificationAttempt` — face embedding storage and verification history, decoupled from raw images
  - `DocumentType` / `IssuedDocument` — catalog vs. transaction pattern for the 23 barangay document types
  - `AuditLog` — polymorphic action logging via `GenericForeignKey`, with zero dependency on the apps it logs
- Migrations generated and verified against a clean SQLite database
- Django admin registered for all models (manual data entry/inspection during development)
- Login-gated resident CRUD (`residents` app), with fuzzy name search (`thefuzz`) and soft delete (`is_active`)
- Face enrollment/verification (`recognition` app) via DeepFace/Facenet — see **Face recognition environment** below, it needs a second Python interpreter
- Document generation (`documents` app): DocumentType management, resident-scoped issuance with auto-generated `{BARANGAY_CODE}-{year}-{sequence}` control numbers, a printable HTML view, and PDF export via `xhtml2pdf`

**Soon**
- Authentication-aware permissions per role
- Audit log wiring
- Deployment packaging (Waitress + PyInstaller)

## Setup

\`\`\`bash
python3 -m venv venv
source venv/bin/activate        # Windows: venv\\Scripts\\activate
pip install django thefuzz Pillow
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
\`\`\`

\`http://127.0.0.1:8000/\`

## Face recognition environment

DeepFace depends on TensorFlow, which — as of this writing — has no build
for Python 3.14 (the version the rest of this project runs on, on Ubuntu
26.04). Rather than downgrade the whole project, face embedding extraction
runs in a **separate Python 3.11 environment**, invoked as a subprocess per
photo (see `recognition/face_engine.py` for the full rationale).

To set it up:

\`\`\`bash
# Anaconda/Miniconda, because Ubuntu 26.04's own apt repos don't carry
# python3.11 and the deadsnakes PPA didn't have a build for it either at
# the time this was set up:
curl -sL -o miniconda.sh https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
bash miniconda.sh -b -p ~/miniconda3
~/miniconda3/bin/conda create -y -n brms-face python=3.11
~/miniconda3/envs/brms-face/bin/pip install deepface tf-keras "opencv-python==4.10.0.84"
\`\`\`

(`opencv-python` is pinned to 4.10 — the current 5.x release restructured
its bundled data files and breaks DeepFace's OpenCV face detector, which
expects the old `cv2/data/haarcascade_*.xml` path.)

By default the app looks for that interpreter at
\`~/miniconda3/envs/brms-face/bin/python\`. Override with the
\`FACE_ENGINE_PYTHON\` environment variable if yours lives elsewhere.

Each enrollment/verification call pays TensorFlow's cold-start cost
(observed ~5s on this machine) since the subprocess isn't kept warm
between requests — acceptable for a low-volume, human-triggered flow like
this; see the docstring in `face_engine.py` for the trade-off.


