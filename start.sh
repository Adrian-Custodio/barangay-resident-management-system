#!/bin/sh
set -e

# The Space's disk is ephemeral, so every start is a fresh demo database.
# Without a DJANGO_SECRET_KEY secret, generate one (sessions reset on restart anyway).
if [ -z "$DJANGO_SECRET_KEY" ]; then
    DJANGO_SECRET_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(50))")
    export DJANGO_SECRET_KEY
fi

python manage.py migrate --noinput
python manage.py seed_demo

# Long timeout: a cold face scan imports TensorFlow in a subprocess.
exec gunicorn config.wsgi:application \
    --bind "0.0.0.0:${PORT:-7860}" \
    --workers 2 --threads 4 \
    --timeout 180 \
    --access-logfile -
