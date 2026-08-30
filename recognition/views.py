from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View

from audit.models import AuditLog
from audit.services import log_action
from residents.models import Resident

from .face_engine import FaceEngineError, NoFaceDetectedError, extract_embedding
from .forms import FacePhotoForm
from .matching import cosine_distance
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
