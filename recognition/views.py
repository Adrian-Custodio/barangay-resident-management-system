from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views import View

from audit.models import AuditLog
from audit.services import log_action
from residents.models import Resident

from .face_engine import FaceEngineError, NoFaceDetectedError, extract_embedding
from .forms import FacePhotoForm
from .matching import cosine_distance, find_best_match
from .models import FaceProfile, FaceVerificationAttempt


class FaceEnrollView(LoginRequiredMixin, View):
    """
    Capture a resident's photo, extract its embedding via the face engine,
    and save it as their FaceProfile. Re-enrolling replaces the previous
    embedding (FaceProfile.resident is a OneToOneField) -- there is
    deliberately no history of past embeddings kept; only the current one
    is meaningful for matching against.
    """

    template_name = "recognition/face_enroll.html"

    def get(self, request, pk):
        resident = get_object_or_404(Resident, pk=pk)
        return render(request, self.template_name, {
            "resident": resident,
            "form": FacePhotoForm(),
            "has_profile": hasattr(resident, "face_profile"),
        })

    def post(self, request, pk):
        resident = get_object_or_404(Resident, pk=pk)
        form = FacePhotoForm(request.POST, request.FILES)
        context = {"resident": resident, "form": form, "has_profile": hasattr(resident, "face_profile")}
        if not form.is_valid():
            return render(request, self.template_name, context)

        image_bytes = form.cleaned_data["photo"].read()
        try:
            embedding = extract_embedding(image_bytes)
        except NoFaceDetectedError as exc:
            form.add_error("photo", str(exc))
            return render(request, self.template_name, context)
        except FaceEngineError as exc:
            form.add_error(None, f"Face recognition is unavailable right now: {exc}")
            return render(request, self.template_name, context)

        FaceProfile.objects.update_or_create(
            resident=resident,
            defaults={"embedding": embedding, "model_name": "Facenet"},
        )
        messages.success(request, f"Enrolled face profile for {resident.full_name}.")
        return redirect("residents:resident_detail", pk=resident.pk)


class FaceVerifyView(LoginRequiredMixin, View):
    """
    Compare a freshly captured photo against a resident's enrolled
    FaceProfile. Every attempt is recorded as a FaceVerificationAttempt,
    match or not -- the point is a verification history an office can
    later review, not just a one-off yes/no on screen.
    """

    template_name = "recognition/face_verify.html"

    def get(self, request, pk):
        resident = get_object_or_404(Resident, pk=pk)
        return render(request, self.template_name, {
            "resident": resident,
            "form": FacePhotoForm(),
            "has_profile": hasattr(resident, "face_profile"),
        })

    def post(self, request, pk):
        resident = get_object_or_404(Resident, pk=pk)
        has_profile = hasattr(resident, "face_profile")
        form = FacePhotoForm(request.POST, request.FILES)
        context = {"resident": resident, "form": form, "has_profile": has_profile}

        if not has_profile:
            form.add_error(None, "This resident has no enrolled face profile yet.")
            return render(request, self.template_name, context)
        if not form.is_valid():
            return render(request, self.template_name, context)

        image_bytes = form.cleaned_data["photo"].read()
        try:
            probe_embedding = extract_embedding(image_bytes)
        except NoFaceDetectedError as exc:
            form.add_error("photo", str(exc))
            return render(request, self.template_name, context)
        except FaceEngineError as exc:
            form.add_error(None, f"Face recognition is unavailable right now: {exc}")
            return render(request, self.template_name, context)

        distance = cosine_distance(probe_embedding, resident.face_profile.embedding)
        threshold = settings.FACE_MATCH_THRESHOLD
        matched = distance <= threshold

        attempt = FaceVerificationAttempt.objects.create(
            resident=resident, distance=distance, threshold=threshold, matched=matched,
        )
        log_action(
            request.user,
            AuditLog.Action.FACE_VERIFY_SUCCESS if matched else AuditLog.Action.FACE_VERIFY_FAIL,
            attempt,
            detail=f"{resident.full_name}: distance={distance:.4f}, threshold={threshold}",
        )

        if matched:
            messages.success(request, f"Face verified: matches {resident.full_name}.")
        else:
            messages.error(request, "Face does not match this resident's enrolled profile.")

        context.update({"form": FacePhotoForm(), "attempt": attempt})
        return render(request, self.template_name, context)


class FaceIdentifyView(LoginRequiredMixin, View):
    """
    1:N identification for the home-page camera scan: "who is this?"
    rather than FaceVerifyView's "is this the resident I already picked?".
    A JSON endpoint (called via fetch() from core/home.html's JS), not a
    full page -- the home page reacts to the result inline instead of
    navigating away and back.

    Only a successful identification is recorded (FaceVerificationAttempt
    + AuditLog). A "matched nobody" scan has no resident to attach a
    record to under the current schema (both FaceVerificationAttempt.resident
    and AuditLog's GenericForeignKey require a real target) -- and unlike a
    failed 1:1 check against one specific resident, it isn't itself a
    security-relevant event; it just means "use Search manually instead",
    which the UI already offers right there.
    """

    def post(self, request):
        photo = request.FILES.get("photo")
        if not photo:
            return JsonResponse({"matched": False, "error": "No photo provided."}, status=400)

        try:
            probe_embedding = extract_embedding(photo.read())
        except NoFaceDetectedError as exc:
            return JsonResponse({"matched": False, "error": str(exc)})
        except FaceEngineError as exc:
            return JsonResponse({"matched": False, "error": str(exc)}, status=503)

        profiles = FaceProfile.objects.filter(resident__is_active=True).select_related("resident")
        best_profile, best_distance = find_best_match(probe_embedding, profiles)
        threshold = settings.FACE_MATCH_THRESHOLD
        matched = best_profile is not None and best_distance <= threshold

        if not matched:
            return JsonResponse({
                "matched": False,
                "distance": round(best_distance, 4) if best_distance is not None else None,
            })

        resident = best_profile.resident
        attempt = FaceVerificationAttempt.objects.create(
            resident=resident, distance=best_distance, threshold=threshold, matched=True,
        )
        log_action(
            request.user, AuditLog.Action.FACE_VERIFY_SUCCESS, attempt,
            detail=f"Identified via home-page scan: {resident.full_name}, distance={best_distance:.4f}",
        )
        return JsonResponse({
            "matched": True,
            "resident_id": resident.pk,
            "resident_name": resident.full_name,
            "distance": round(best_distance, 4),
            "detail_url": reverse("residents:resident_detail", args=[resident.pk]),
            "issue_url": reverse("documents:issue_document", args=[resident.pk]),
        })
