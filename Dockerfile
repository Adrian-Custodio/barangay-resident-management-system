# Online demo image (Hugging Face Spaces, Docker SDK). Unlike local dev,
# Django and DeepFace share one Python 3.11 interpreter here, so
# FACE_ENGINE_PYTHON just points back at the same python.
FROM python:3.11-slim

# OpenCV runtime libraries
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Spaces run the container as uid 1000
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    TF_CPP_MIN_LOG_LEVEL=2 \
    DEEPFACE_HOME=/home/user \
    FACE_ENGINE_PYTHON=/usr/local/bin/python \
    FACE_ENGINE_TIMEOUT=120
WORKDIR /home/user/app

COPY --chown=user requirements.txt recognition/requirements-face-engine.txt ./
RUN pip install --user -r requirements.txt -r requirements-face-engine.txt

# Bake the Facenet weights into the image instead of downloading on first scan
RUN python -c "from deepface import DeepFace; DeepFace.build_model('Facenet')"

COPY --chown=user . .
RUN DJANGO_SECRET_KEY=build-only DJANGO_DEBUG=0 python manage.py collectstatic --noinput

ENV DJANGO_DEBUG=0 \
    BRMS_DEMO_MODE=1 \
    BRMS_SERVE_MEDIA=1 \
    BRMS_FRAME_ANCESTORS=https://huggingface.co \
    DJANGO_ALLOWED_HOSTS=.hf.space,localhost,127.0.0.1 \
    DJANGO_CSRF_TRUSTED_ORIGINS=https://*.hf.space \
    PORT=7860
EXPOSE 7860

CMD ["./start.sh"]
