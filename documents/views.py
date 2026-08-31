import io

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views.generic import CreateView, DetailView, ListView, UpdateView
from django.views.generic.detail import SingleObjectMixin
from django.views import View
from xhtml2pdf import pisa

from accounts.mixins import AdminRequiredMixin
from audit.models import AuditLog
from audit.services import log_action
from residents.models import Resident
from residents.search import fuzzy_search_residents

from .forms import (
    DocumentReviewForm,
    DocumentTypeForm,
    IssueDocumentForm,
    WalkInDocumentReviewForm,
    WalkInIssueForm,
)
from .models import DocumentType, IssuedDocument
from .numbering import issue_document
from .rendering import WalkInSubject, build_subject, render_document_body, render_preview


class DocumentTypeListView(LoginRequiredMixin, ListView):
    model = DocumentType
    template_name = "documents/documenttype_list.html"
    context_object_name = "document_types"
    ordering = ["name"]


class DocumentTypeCreateView(AdminRequiredMixin, CreateView):
    """
    AdminRequiredMixin: a DocumentType's template_body is rendered
    directly into every document generated from it (see rendering.py) --
    letting any encoder edit that text is effectively letting them control
    the wording of official barangay documents, which belongs with the
    same role that can remove a resident from the roll.
    """

    model = DocumentType
    form_class = DocumentTypeForm
    template_name = "documents/documenttype_form.html"
    success_url = reverse_lazy("documents:documenttype_list")

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f"Added document type {self.object.name}.")
        return response


class DocumentTypeUpdateView(AdminRequiredMixin, UpdateView):
    model = DocumentType
    form_class = DocumentTypeForm
    template_name = "documents/documenttype_form.html"
    success_url = reverse_lazy("documents:documenttype_list")

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f"Updated {self.object.name}.")
        return response


class IssueDocumentView(LoginRequiredMixin, View):
    """
    Resident is fixed by URL (issued from that resident's detail page),
    mirroring how face enrollment/verification are scoped -- an encoder's
    starting point is always "this resident", never a document floating
    free of one.

    Two-phase, both POSTs to this same URL:
      1. Choose a document type + purpose -> auto-populate a preview and
         hand it to DocumentReviewForm for editing. Nothing is saved yet.
      2. Confirm the (possibly edited) review form -> this is the one
         moment issue_document() actually runs, assigning a real control
         number. Distinguished from phase 1 by the presence of
         "body_text" in POST data, which only the review form ever sends.
    """

    template_name = "documents/issue_document.html"
    review_template_name = "documents/document_review.html"

    def get(self, request, pk):
        resident = get_object_or_404(Resident, pk=pk)
        return render(request, self.template_name, {"resident": resident, "form": IssueDocumentForm()})

    def post(self, request, pk):
        resident = get_object_or_404(Resident, pk=pk)
        if "body_text" in request.POST:
            return self._finalize(request, resident)
        return self._preview(request, resident)

    def _preview(self, request, resident):
        form = IssueDocumentForm(request.POST)
        if not form.is_valid():
            return render(request, self.template_name, {"resident": resident, "form": form})

        document_type = form.cleaned_data["document_type"]
        purpose = form.cleaned_data["purpose"]
        review_form = DocumentReviewForm(initial={
            "document_type": document_type.pk,
            "purpose": purpose,
            "document_date": timezone.localdate(),
            "body_text": render_preview(document_type, resident=resident, purpose=purpose),
        })
        return render(request, self.review_template_name, {
            "resident": resident,
            "document_type": document_type,
            "recipient_label": resident.full_name,
            "cancel_url": reverse("residents:resident_detail", args=[resident.pk]),
            "form": review_form,
        })

    def _finalize(self, request, resident):
        form = DocumentReviewForm(request.POST)
        if not form.is_valid():
            document_type = form.cleaned_data.get("document_type") or DocumentType.objects.filter(pk=request.POST.get("document_type")).first()
            return render(request, self.review_template_name, {
                "resident": resident,
                "document_type": document_type,
                "recipient_label": resident.full_name,
                "cancel_url": reverse("residents:resident_detail", args=[resident.pk]),
                "form": form,
            })

        issued_document = issue_document(
            resident=resident,
            document_type=form.cleaned_data["document_type"],
            purpose=form.cleaned_data["purpose"],
            document_date=form.cleaned_data["document_date"],
            body_text=form.cleaned_data["body_text"],
            issued_by=request.user,
        )
        log_action(
            request.user, AuditLog.Action.DOCUMENT_ISSUED, issued_document,
            detail=f"{issued_document.document_type.name} for {resident.full_name}",
        )
        messages.success(
            request,
            f"Issued {issued_document.document_type.name} "
            f"({issued_document.control_number}) to {resident.full_name}.",
        )
        return redirect("documents:issued_document_detail", pk=issued_document.pk)


class WalkInIssueView(LoginRequiredMixin, View):
    """
    "Print without an account": issuing a document to someone without
    going through resident registration first. Two paths from the one
    page:

    1. Type a name -> if it fuzzy-matches an existing resident, hand off
       to the normal IssueDocumentView so the document links to their
       real record. Chosen deliberately over "autofill but never link":
       someone who already has an account shouldn't end up with a second,
       unlinked paper trail just because the front-desk flow started from
       the walk-in page instead of their resident page.
    2. No match (or the encoder confirms this really is a first-time
       walk-in) -> a fully manual form with no Resident behind it at all;
       renders through a WalkInSubject built from whatever was typed (see
       rendering.py), never a row in the residents app.
    """

    template_name = "documents/walk_in_issue.html"
    review_template_name = "documents/document_review.html"

    def get(self, request):
        query = request.GET.get("q", "").strip()
        manual = request.GET.get("manual") == "1" or bool(query)
        matches = self._search(query) if query else []
        context = {
            "query": query,
            "matches": matches,
            "manual": manual,
            "form": WalkInIssueForm(initial={"full_name": query} if query else None),
        }
        return render(request, self.template_name, context)

    def post(self, request):
        if "body_text" in request.POST:
            return self._finalize(request)
        return self._preview(request)

    def _preview(self, request):
        form = WalkInIssueForm(request.POST)
        if not form.is_valid():
            query = request.POST.get("full_name", "")
            context = {"query": query, "matches": self._search(query), "manual": True, "form": form}
            return render(request, self.template_name, context)

        document_type = form.cleaned_data["document_type"]
        purpose = form.cleaned_data["purpose"]
        walk_in_details = form.walk_in_details()
        subject = WalkInSubject(**{k: v for k, v in walk_in_details.items()})

        review_form = WalkInDocumentReviewForm(initial={
            "document_type": document_type.pk,
            "purpose": purpose,
            "document_date": timezone.localdate(),
            "body_text": render_preview(document_type, resident=subject, purpose=purpose),
            **walk_in_details,
        })
        return render(request, self.review_template_name, {
            "document_type": document_type,
            "recipient_label": f"{walk_in_details['full_name']} (no account)",
            "cancel_url": reverse("documents:walk_in_issue"),
            "form": review_form,
        })

    def _finalize(self, request):
        form = WalkInDocumentReviewForm(request.POST)
        if not form.is_valid():
            document_type = form.cleaned_data.get("document_type") or DocumentType.objects.filter(pk=request.POST.get("document_type")).first()
            return render(request, self.review_template_name, {
                "document_type": document_type,
                "recipient_label": request.POST.get("full_name", ""),
                "cancel_url": reverse("documents:walk_in_issue"),
                "form": form,
            })

        walk_in_details = form.walk_in_details()
        issued_document = issue_document(
            walk_in_details=walk_in_details,
            document_type=form.cleaned_data["document_type"],
            purpose=form.cleaned_data["purpose"],
            document_date=form.cleaned_data["document_date"],
            body_text=form.cleaned_data["body_text"],
            issued_by=request.user,
        )
        log_action(
            request.user, AuditLog.Action.DOCUMENT_ISSUED, issued_document,
            detail=f"{issued_document.document_type.name} for walk-in {walk_in_details['full_name']} (no account)",
        )
        messages.success(
            request,
            f"Issued {issued_document.document_type.name} ({issued_document.control_number}) "
            f"to {walk_in_details['full_name']} (no account).",
        )
        return redirect("documents:issued_document_detail", pk=issued_document.pk)

    @staticmethod
    def _search(query):
        return list(fuzzy_search_residents(query, Resident.objects.filter(is_active=True), limit=5))


class _RenderedDocumentMixin(SingleObjectMixin):
    model = IssuedDocument

    def get_rendered_body(self, issued_document):
        if issued_document.body_text:
            return issued_document.body_text
        # Rows issued before body_text was captured at issuance time have
        # none stored -- fall back to live-rendering from the current
        # document_type.template_body so old records don't break. This is
        # exactly the drift body_text exists to prevent going forward: an
        # old row's displayed text can still change if its DocumentType's
        # template is edited later, a new row's cannot.
        return render_document_body(
            issued_document.document_type,
            resident=build_subject(issued_document),
            issued_document=issued_document,
        )


class IssuedDocumentDetailView(LoginRequiredMixin, _RenderedDocumentMixin, DetailView):
    template_name = "documents/issued_document_detail.html"
    context_object_name = "issued_document"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["rendered_body"] = self.get_rendered_body(self.object)
        return context


class IssuedDocumentPdfView(LoginRequiredMixin, _RenderedDocumentMixin, View):
    """
    Renders the same template used for the on-screen printable view
    through xhtml2pdf, so the PDF and the "print this page" view can
    never drift apart into two different layouts.

    xhtml2pdf over WeasyPrint: it's pure-Python (no Pango/Cairo/GDK-pixbuf
    system libraries to install), which matters directly for this
    project's eventual PyInstaller/Windows packaging -- a system library
    dependency is exactly the kind of thing that's easy in development
    and painful to bundle for an offline Windows executable.
    """

    def get(self, request, pk):
        issued_document = self.get_object()
        html = render_to_string(
            "documents/issued_document_pdf.html",
            {"issued_document": issued_document, "rendered_body": self.get_rendered_body(issued_document)},
        )
        buffer = io.BytesIO()
        result = pisa.CreatePDF(html, dest=buffer)
        if result.err:
            return HttpResponse("Could not generate PDF.", status=500)

        response = HttpResponse(buffer.getvalue(), content_type="application/pdf")
        response["Content-Disposition"] = f'inline; filename="{issued_document.control_number}.pdf"'
        return response
