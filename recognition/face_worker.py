"""
Runs under the DeepFace-capable Python 3.11 interpreter (see
FACE_ENGINE_PYTHON in settings), never under the Django process's own
interpreter -- DeepFace/TensorFlow don't install on the Python version the
rest of this project runs on. This script is only ever invoked as a
subprocess (`python face_worker.py embed`); it is not imported by Django.

Protocol: raw image bytes on stdin, one JSON object on stdout.
    embed success -> {"embedding": [...], "model_name": "Facenet"}
    any failure    -> {"error": "..."}

The input photo is decoded straight into an in-memory array and never
written to disk -- it exists only for this process's lifetime and is
discarded when it exits, matching FaceProfile's "store the embedding, not
the photo" design.
"""
import io
import json
import sys


def _read_image_from_stdin():
    import numpy as np
    from PIL import Image

    raw = sys.stdin.buffer.read()
    image = Image.open(io.BytesIO(raw)).convert("RGB")
    return np.array(image)


def cmd_embed():
    from deepface import DeepFace

    img = _read_image_from_stdin()
    result = DeepFace.represent(
        img_path=img,
        model_name="Facenet",
        detector_backend="opencv",
        enforce_detection=True,
    )
    # represent() returns one entry per detected face. Enrollment and
    # verification both assume a single-subject ID photo; more than one
    # face is an input problem for the user to fix (retake the photo),
    # not something this endpoint should guess its way through.
    if len(result) != 1:
        print(json.dumps({"error": f"Expected exactly one face in the photo, found {len(result)}."}))
        return
    print(json.dumps({"embedding": result[0]["embedding"], "model_name": "Facenet"}))


def main():
    command = sys.argv[1] if len(sys.argv) > 1 else ""
    try:
        if command == "embed":
            cmd_embed()
        else:
            print(json.dumps({"error": f"Unknown command {command!r}."}))
    except ValueError as exc:
        # DeepFace raises ValueError (via its face detector) when no face
        # is found in the photo at all -- the single most common failure
        # mode for this endpoint, so it gets its own message rather than
        # falling into the generic handler below.
        print(json.dumps({"error": f"No face detected in the photo: {exc}"}))
    except Exception as exc:  # noqa: BLE001 -- any failure must come back as
        # parseable JSON, not a raw traceback the caller (a different Python
        # process, possibly a different Python version) has no way to read.
        print(json.dumps({"error": f"{type(exc).__name__}: {exc}"}))


if __name__ == "__main__":
    main()
