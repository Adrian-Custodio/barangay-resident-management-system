from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin


class AdminRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """
    Drop-in replacement for LoginRequiredMixin on views restricted to
    Profile.role == ADMIN (deleting residents, managing DocumentTypes).

    Inherits from LoginRequiredMixin *and* UserPassesTestMixin, in that
    order, rather than UserPassesTestMixin alone: an anonymous user would
    otherwise fail test_func() (AnonymousUser has no .profile) and get a
    generic 403, when the correct response is "log in first", not
    "you're not allowed". With LoginRequiredMixin first in the MRO,
    Django's own dispatch chain handles the split automatically --
    AccessMixin.handle_no_permission() redirects to login for anonymous
    users but raises PermissionDenied (403) once request.user.is_authenticated
    is True, which is exactly the anonymous-vs-logged-in-but-not-admin
    distinction this needs.
    """

    def test_func(self):
        return self.request.user.profile.is_admin
