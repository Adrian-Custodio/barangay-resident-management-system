# Barangay Resident Management System (BRMS)

A Django-based resident management system built for a partner barangay (Lupi, Camarines Sur), featuring face recognition-based resident identification and digital document issuance.

This is an in-progress rebuild of an earlier working version of the system, developed step by step with a focus on clean architecture and clear separation of concerns.

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

**✅ Done**
- Project scaffolding: 5-app structure with clear domain boundaries
- Full data model layer:
  - `Resident` — core resident record with separated name fields for accurate document formatting
  - `Profile` — two-tier role system (Administrator / Encoder)
  - `FaceProfile` / `FaceVerificationAttempt` — face embedding storage and verification history, decoupled from raw images
  - `DocumentType` / `IssuedDocument` — catalog vs. transaction pattern for the 23 barangay document types
  - `AuditLog` — polymorphic action logging via `GenericForeignKey`, with zero dependency on the apps it logs
- Migrations generated and verified against a clean SQLite database
- Django admin registered for all models (manual data entry/inspection during development)

**🚧 Not yet built**
- Custom views/forms for residents (currently only accessible via Django admin)
- Fuzzy name search (`thefuzz` integration)
- Face recognition enrollment/verification logic (DeepFace integration)
- Document generation/templating and PDF output
- Authentication-aware permissions per role
- Deployment packaging (Waitress + PyInstaller)

## Setup

\`\`\`bash
python3 -m venv venv
source venv/bin/activate        # Windows: venv\\Scripts\\activate
pip install django==5.2
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
\`\`\`

Visit \`http://127.0.0.1:8000/admin\` and log in to browse/manage the current data model.

## License

TBD
