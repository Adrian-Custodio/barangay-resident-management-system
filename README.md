---
title: BRMS Demo
colorFrom: blue
colorTo: gray
sdk: docker
app_port: 7860
pinned: false
short_description: Barangay resident records, face ID and document issuance
---

# Barangay Resident Management System (BRMS)

A Django-based resident management system built for barangays, featuring face recognition-based resident identification and digital document issuance.

This is an in-progress build of an earlier working version of the system.

## Tech Stack

- **Backend:** Python, Django 5.2
- **Database:** SQLite
- **Face Recognition (planned):** DeepFace (Facenet)
- **Fuzzy Search (planned):** thefuzz
- **Online demo:** Docker on Hugging Face Spaces (gunicorn + whitenoise)
- **Offline deployment (planned):** Waitress + PyInstaller (Windows-packaged executable)

## Architecture

The system is split into six Django apps, each with a single responsibility:

| App | Responsibility |
|---|---|
| `accounts` | User roles (Administrator / Encoder) via a `Profile` extending Django's built-in `User`, plus `AdminRequiredMixin` for gating admin-only views |
| `residents` | Core resident records — the entity every other app relates back to — with fuzzy name search |
| `recognition` | Face enrollment, 1:1 verification, and 1:N identification, storing facial embeddings (not raw photos) |
| `documents` | Catalog of issuable document types and records of documents actually issued, including walk-in issuance with no resident account |
| `audit` | A single, generic action log shared across all apps, using Django's `GenericForeignKey` |
| `core` | The post-login home page: camera-scan resident identification, the officials directory, and site display settings |

Deployment target is a single-machine, offline-capable barangay office setup — this shaped decisions like SQLite over a client-server database, and Waitress (pure-Python WSGI server) over Gunicorn for eventual Windows packaging.

## Current Status

**Done**
- Project scaffolding: 6-app structure with clear domain boundaries
- Full data model layer, migrated and verified against a clean SQLite database
- Login-gated resident CRUD (`residents` app), with fuzzy name search (`thefuzz`) and soft delete (`is_active`)
- Face enrollment, 1:1 verification, and 1:N identification (`recognition` app) via DeepFace/Facenet — see **Face recognition environment** below, it needs a second Python interpreter
- Document generation (`documents` app): 12 common barangay document types seeded out of the box (Barangay Clearance, Certificate of Residency, Certificate of Indigency, and more — editable/extendable by an admin), resident-scoped issuance with auto-generated `{BARANGAY_CODE}-{year}-{sequence}` control numbers, walk-in issuance for people with no resident account, an editable review step (text and document date) before a document is finalized and numbered, a printable HTML view, and PDF export via `xhtml2pdf`
- Home page (`core` app): click-to-capture camera scan that identifies a resident and hands off to document issuance, with manual search and walk-in printing as first-class alternatives; an officials directory (elected/appointed) and an admin-editable background image
- Role enforcement: `AdminRequiredMixin` restricts deleting residents and managing DocumentTypes/officials/site settings to `Profile.role == ADMIN`; everything else is open to any logged-in encoder
- Audit logging wired into resident create/update/soft-delete, document issuance (including walk-in), and face verification/identification attempts (success and failure)
- Django admin registered for all models (manual data entry/inspection during development)

- Online demo build: `Dockerfile` for Hugging Face Spaces with fictional seed data (`manage.py seed_demo`), see **Online demo** below

**Soon**
- Offline deployment packaging (Waitress + PyInstaller)

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

## Online demo

The `Dockerfile` builds a self-contained demo for a
[Hugging Face Space](https://huggingface.co/docs/hub/spaces-sdks-docker)
(free CPU tier, 16 GB RAM -- enough for TensorFlow). Inside the image,
Django and DeepFace share one Python 3.11 interpreter, so the two-environment
setup above is only needed for local development.

On every start, `start.sh` migrates a fresh SQLite database, runs
`manage.py seed_demo` (fictional residents, officials, and two logins:
`demo_admin` and `demo_encoder`, password `brms-demo` unless
`BRMS_DEMO_PASSWORD` is set), and starts gunicorn on port 7860. The Space's
disk is ephemeral, so all data -- including any enrolled faces -- resets
whenever it restarts or rebuilds.

Deploying:

1. Create a Space at https://huggingface.co/new-space with the **Docker**
   SDK (blank template), e.g. `your-hf-username/brms-demo`.
2. In the Space's settings, add a secret `DJANGO_SECRET_KEY` (optional --
   one is generated per start if missing).
3. Push this repo to the Space; it rebuilds from the `Dockerfile`:
   `git push https://huggingface.co/spaces/your-hf-username/brms-demo main`
   (use a Hugging Face access token with write access as the password).

The app is served at `https://your-hf-username-brms-demo.hf.space`.
Production settings are environment-driven (`DJANGO_DEBUG`,
`DJANGO_SECRET_KEY`, `DJANGO_ALLOWED_HOSTS`, `DJANGO_CSRF_TRUSTED_ORIGINS`,
`BRMS_DEMO_MODE`, `BRMS_FRAME_ANCESTORS`, ...); the Dockerfile sets the ones
a Space needs. Local development needs none of them.
