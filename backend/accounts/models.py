from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Roles(models.TextChoices):
        ADMIN = "ADMIN", "Admin"
        DOCENTE = "DOCENTE", "Docente"

    # Override email to enforce uniqueness
    email = models.EmailField("email address", unique=True)

    dni = models.CharField(max_length=15, unique=True)
    phone = models.CharField(max_length=20, blank=True)
    role = models.CharField(max_length=20, choices=Roles.choices, default=Roles.DOCENTE)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.username

