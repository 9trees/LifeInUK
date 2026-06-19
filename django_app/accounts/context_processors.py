def active_window(request):
    user = getattr(request, "user", None)
    if user is not None and user.is_authenticated and not user.is_superuser:
        return {
            "remaining_days": user.get_remaining_days(),
            "membership_active": user.is_membership_active,
        }
    return {"remaining_days": None, "membership_active": None}
