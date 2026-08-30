import io

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse_lazy
from django.views.generic import CreateView, DetailView, ListView, UpdateView
from django.views.generic.detail import SingleObjectMixin
from django.views import View
from xhtml2pdf import pisa

from accounts.mixins import AdminRequiredMixin
from residents.models import Resident

from .forms import DocumentTypeForm, IssueDocumentForm
from .models import DocumentType, IssuedDocument
from .numbering import issue_document
from .rendering import render_document_body


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
    """

    template_name = "documents/issue_document.html"

    def get(self, request, pk):
        resident = get_object_or_404(Resident, pk=pk)
        return render(request, self.template_name, {"resident": resident, "form": IssueDocumentForm()})

    def post(self, request, pk):
        resident = get_object_or_404(Resident, pk=pk)
        form = IssueDocumentForm(request.POST)
        if not form.is_valid():
            return render(request, self.template_name, {"resident": resident, "form": form})

        issued_document = issue_document(
            resident=resident,
            document_type=form.cleaned_data["document_type"],
            purpose=form.cleaned_data["purpose"],
            issued_by=request.user,
        )
        messages.success(
            request,
            f"Issued {issued_document.document_type.name} "
            f"({issued_document.control_number}) to {resident.full_name}.",
        )
        return redirect("documents:issued_document_detail", pk=issued_document.pk)


class _RenderedDocumentMixin(SingleObjectMixin):
    model = IssuedDocument

    def get_rendered_body(self, issued_document):
        return render_document_body(
            issued_document.document_type,
            resident=issued_document.resident,
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
