"""
Bridge between the main Django process and DeepFace.

DeepFace requires TensorFlow, which had no compatible build for this
project's Python version (3.14) at the time this was written. Rather than
downgrade the whole project, face extraction runs in a separate
interpreter -- a Python 3.11 environment with DeepFace/TensorFlow
installed -- invoked as a short-lived subprocess per photo. face_worker.py
is the half of this that runs there; this module is the half that runs in
the normal Django process and never imports DeepFace/TensorFlow itself.

This is a deliberate trade-off, not a workaround glossed over:
  (+) doesn't force the rest of the project onto an older Python just to
      satisfy one dependency
  (+) a crash or hang inside TensorFlow can't take the web process down
      with it
  (-) every call pays TensorFlow's import + model-load cost (several
      seconds) because nothing is kept warm between requests
That cost is acceptable here because enrollment and verification are rare,
human-triggered actions -- an encoder registering a resident, a one-off ID
check -- not a high-throughput API. A production system with heavier
volume would replace the subprocess with a long-running worker process
(e.g. a small local HTTP service) that keeps the model loaded; that's a
reasonable next step, not something this design forecloses.
"""
import json
import subprocess
from pathlib import Path

from django.conf import settings

_WORKER_SCRIPT = Path(__file__).resolve().parent / "face_worker.py"


class FaceEngineError(Exception):
    """The worker process failed, timed out, or returned something unusable."""


class NoFaceDetectedError(FaceEngineError):
    """The photo didn't contain (exactly) one recognizable face."""


def extract_embedding(image_bytes: bytes) -> list[float]:
    """
    Run DeepFace/Facenet on `image_bytes` in the dedicated interpreter and
    return the embedding vector. Raises NoFaceDetectedError for a bad
    photo (no face / more than one face), FaceEngineError for anything
    else that went wrong (missing interpreter, timeout, crash).
    """
    try:
        completed = subprocess.run(
            [settings.FACE_ENGINE_PYTHON, str(_WORKER_SCRIPT), "embed"],
            input=image_bytes,
            capture_output=True,
            timeout=settings.FACE_ENGINE_TIMEOUT,
        )
    except FileNotFoundError as exc:
        raise FaceEngineError(
            f"Face recognition interpreter not found at "
            f"{settings.FACE_ENGINE_PYTHON!r}. See README for how to set up "
            f"the recognition environment (a Python 3.11 venv/conda env with "
            f"deepface installed)."
        ) from exc
    except subprocess.TimeoutExpired as exc:
        raise FaceEngineError(
            f"Face recognition timed out after {settings.FACE_ENGINE_TIMEOUT}s."
        ) from exc

    if not completed.stdout:
        stderr_tail = completed.stderr.decode(errors="replace")[-2000:]
        raise FaceEngineError(
            f"Face recognition worker produced no output "
            f"(exit code {completed.returncode}): {stderr_tail}"
        )

    try:
        # The worker's stdout may have trailing newlines/whitespace but
        # should be exactly one JSON object -- it never prints anything
        # else to stdout (library log noise from TensorFlow/DeepFace goes
        # to stderr, which we only surface on error).
        payload = json.loads(completed.stdout.decode().strip())
    except json.JSONDecodeError as exc:
        raise FaceEngineError(
            f"Face recognition worker returned malformed output: "
            f"{completed.stdout[:500]!r}"
        ) from exc

    if "error" in payload:
        message = payload["error"]
        if "face" in message.lower():
            raise NoFaceDetectedError(message)
        raise FaceEngineError(message)

    return payload["embedding"]
