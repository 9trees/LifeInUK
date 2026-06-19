from django.contrib import messages
from django.contrib.auth import logout
from django.shortcuts import redirect
from django.urls import reverse


class ActiveWindowMiddleware:
    """Logs out users whose 30-day active window has expired."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        if user is not None and user.is_authenticated and not user.is_superuser:
            if not user.is_membership_active:
                logout(request)
                messages.warning(
                    request,
                    "Your 30-day active window has expired. Please register again to continue.",
                )
                if not request.path.startswith("/accounts/"):
                    return redirect(reverse("accounts:login"))
        return self.get_response(request)
