"""
Vector comparison for face embeddings -- pure math, no DeepFace/TensorFlow
dependency, so it runs directly in the main Django process (unlike
face_engine.py, which has to cross into a separate interpreter).

Cosine distance, not Euclidean, to match DeepFace's own published
threshold table for Facenet (see deepface.modules.verification): a
different metric would need a different threshold, and there's no reason
to derive one from scratch when the model's authors already published a
validated one for this exact model + metric combination.
"""
import math


def cosine_distance(a: list[float], b: list[float]) -> float:
    """
    0.0 = identical direction (same person), up to 2.0 = opposite.
    FACE_MATCH_THRESHOLD (settings) is the match/no-match cutoff.
    """
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 1.0  # a degenerate (all-zero) embedding can't match anything
    cosine_similarity = dot / (norm_a * norm_b)
    return 1 - cosine_similarity


def find_best_match(probe_embedding, face_profiles):
    """
    1:N identification: which enrolled FaceProfile (if any) is closest to
    probe_embedding. Used by the home-page camera scan, which doesn't know
    in advance whose face it's looking at -- unlike FaceVerifyView's 1:1
    check against one resident chosen ahead of time.

    Returns (best_profile, best_distance), both None if face_profiles is
    empty. Callers compare best_distance against FACE_MATCH_THRESHOLD
    themselves -- finding the closest profile and deciding whether it's
    close *enough* are different questions.

    A linear scan over every profile is fine at barangay scale (hundreds
    to a few thousand residents) -- the same complexity trade-off
    ResidentListView's fuzzy search already makes, for the same reason.
    """
    best_profile = None
    best_distance = None
    for profile in face_profiles:
        distance = cosine_distance(probe_embedding, profile.embedding)
        if best_distance is None or distance < best_distance:
            best_distance = distance
            best_profile = profile
    return best_profile, best_distance
