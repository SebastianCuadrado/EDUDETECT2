from rest_framework.routers import DefaultRouter
from django.urls import path
from .views import UserViewSet
from .api_auth import LoginView, MeView


router = DefaultRouter()
router.register(r"users", UserViewSet, basename="user")

urlpatterns = router.urls

# Auth endpoints
urlpatterns += [
    path("auth/login/", LoginView.as_view(), name="auth-login"),
    path("auth/me/", MeView.as_view(), name="auth-me"),
]
