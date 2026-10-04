from django.conf import settings


class FrameAncestorsMiddleware:
    """
    Lets the origins in settings.FRAME_ANCESTORS embed the app (the Hugging
    Face Space page shows it in an iframe). X-Frame-Options can't express
    an allow-list, so it's dropped in favor of CSP frame-ancestors.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.policy = None
        if settings.FRAME_ANCESTORS:
            self.policy = "frame-ancestors 'self' " + " ".join(settings.FRAME_ANCESTORS)

    def __call__(self, request):
        response = self.get_response(request)
        if self.policy:
            response.headers.pop("X-Frame-Options", None)
            response.headers["Content-Security-Policy"] = self.policy
        return response
