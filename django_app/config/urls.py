from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", RedirectView.as_view(pattern_name="analytics:dashboard"), name="home"),
    path("accounts/", include("accounts.urls")),
    path("dashboard/", include("analytics.urls")),
    path("study/", include("study.urls")),
    path("practice/", include("practice.urls")),
    path("mock/", include("mocktest.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
