from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponseRedirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from accounts.mixins import AdminRequiredMixin
from audit.models import AuditLog
from audit.services import log_action

from .forms import ResidentForm
from .models import Resident
from .search import fuzzy_search_residents


class ResidentListView(LoginRequiredMixin, ListView):
    """
    Soft-deleted residents (is_active=False) are excluded from the default
    list -- staff searching for "who lives here" shouldn't see records
    that were retired, even though those rows still exist for
    IssuedDocument/audit history to point back to.
    """

    model = Resident
    template_name = "residents/resident_list.html"
    context_object_name = "residents"
    paginate_by = 25

    def get_queryset(self):
        queryset = Resident.objects.filter(is_active=True)
        query = self.request.GET.get("q", "").strip()
        if not query:
            return queryset
        return fuzzy_search_residents(query, queryset)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["query"] = self.request.GET.get("q", "").strip()
        return context


class ResidentDetailView(LoginRequiredMixin, DetailView):
    # Soft-deleted residents can still be looked up directly (e.g. from an
    # IssuedDocument history link) -- only the list view hides them.
    model = Resident
    template_name = "residents/resident_detail.html"
    context_object_name = "resident"


class ResidentCreateView(LoginRequiredMixin, CreateView):
    model = Resident
    form_class = ResidentForm
    template_name = "residents/resident_form.html"

    def form_valid(self, form):
        response = super().form_valid(form)
        log_action(self.request.user, AuditLog.Action.CREATE, self.object)
        messages.success(self.request, f"Added resident {self.object.full_name}.")
        return response

    def get_success_url(self):
        return reverse_lazy("residents:resident_detail", kwargs={"pk": self.object.pk})


class ResidentUpdateView(LoginRequiredMixin, UpdateView):
    model = Resident
    form_class = ResidentForm
    template_name = "residents/resident_form.html"

    def form_valid(self, form):
        response = super().form_valid(form)
        log_action(self.request.user, AuditLog.Action.UPDATE, self.object)
        messages.success(self.request, f"Updated {self.object.full_name}.")
        return response

    def get_success_url(self):
        return reverse_lazy("residents:resident_detail", kwargs={"pk": self.object.pk})


class ResidentDeleteView(AdminRequiredMixin, DeleteView):
    """
    "Delete" flips is_active rather than removing the row. A hard delete
    would either cascade-destroy every IssuedDocument/audit entry pointing
    at this resident or be rejected outright by the on_delete=PROTECT on
    IssuedDocument.resident -- neither is acceptable for records a barangay
    is required to keep. DeleteView's confirm-page flow (GET shows a
    confirmation, POST performs the action) is still the right shape for
    this UX even though the underlying operation isn't a real deletion, so
    we keep the view and only override what actually happens on POST.

    AdminRequiredMixin, not LoginRequiredMixin: removing a resident from
    the active roll is exactly the kind of action the ADMIN/ENCODER split
    exists for -- an encoder can create and update residents day-to-day,
    but taking someone off the roll is an administrative decision.
    """

    model = Resident
    template_name = "residents/resident_confirm_delete.html"
    context_object_name = "resident"
    success_url = reverse_lazy("residents:resident_list")

    def form_valid(self, form):
        # Deliberately not calling super().form_valid(), which would run
        # self.object.delete() -- that's the one line of DeleteView's
        # behavior this subclass exists to replace.
        self.object.is_active = False
        self.object.save(update_fields=["is_active", "updated_at"])
        log_action(self.request.user, AuditLog.Action.DELETE, self.object, detail="Soft delete (is_active=False)")
        messages.success(self.request, f"Removed {self.object.full_name} from the active roll.")
        return HttpResponseRedirect(self.get_success_url())
