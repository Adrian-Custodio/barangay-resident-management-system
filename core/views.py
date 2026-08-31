from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.views.generic import CreateView, ListView, TemplateView, UpdateView

from accounts.mixins import AdminRequiredMixin

from .forms import OfficialForm, SiteSettingsForm
from .models import Official, SiteSettings


class HomeView(LoginRequiredMixin, TemplateView):
    """
    The actual landing page after login -- this is where an encoder's
    workday starts (identify a resident, then print something for them),
    not the resident list. The resident list is still one click away via
    the nav for anyone who wants to browse/search directly.
    """

    template_name = "core/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["site_settings"] = SiteSettings.load()
        officials = Official.objects.filter(is_active=True)
        context["elected_officials"] = officials.filter(category=Official.Category.ELECTED)
        context["appointed_officials"] = officials.filter(category=Official.Category.APPOINTED)
        return context


class OfficialListView(AdminRequiredMixin, ListView):
    """
    Admin-only: this roster is what appears on every logged-in user's
    home page, so editing who's on it belongs with the same role that
    manages DocumentTypes -- a shared piece of configuration, not
    something any encoder should be able to change mid-shift.
    """

    model = Official
    template_name = "core/official_list.html"
    context_object_name = "officials"


class OfficialCreateView(AdminRequiredMixin, CreateView):
    model = Official
    form_class = OfficialForm
    template_name = "core/official_form.html"
    success_url = reverse_lazy("core:official_list")

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f"Added {self.object.name} to the officials roster.")
        return response


class OfficialUpdateView(AdminRequiredMixin, UpdateView):
    model = Official
    form_class = OfficialForm
    template_name = "core/official_form.html"
    success_url = reverse_lazy("core:official_list")

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f"Updated {self.object.name}.")
        return response


class SiteSettingsUpdateView(AdminRequiredMixin, UpdateView):
    """
    No pk in the URL -- there's exactly one SiteSettings row (see
    SiteSettings.load()), so "which one am I editing" isn't a question
    the URL needs to answer.
    """

    model = SiteSettings
    form_class = SiteSettingsForm
    template_name = "core/site_settings_form.html"
    success_url = reverse_lazy("core:home")

    def get_object(self, queryset=None):
        return SiteSettings.load()

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, "Updated the home page background.")
        return response
