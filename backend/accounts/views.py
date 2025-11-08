from django.contrib.auth import get_user_model
from rest_framework import viewsets, permissions, filters
from .serializers import UserSerializer


User = get_user_model()


class IsAdminUser(permissions.IsAdminUser):
    pass


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all().order_by("-id")
    serializer_class = UserSerializer
    permission_classes = [IsAdminUser]

    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = [
        "username",
        "first_name",
        "last_name",
        "email",
        "dni",
        "phone",
        "role",
    ]
    ordering_fields = ["id", "username", "email", "first_name", "last_name", "role"]

