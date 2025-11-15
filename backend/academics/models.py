from django.conf import settings
from django.db import models


User = settings.AUTH_USER_MODEL


class Student(models.Model):
    GENDER_CHOICES = (
        ("M", "Masculino"),
        ("F", "Femenino"),
        ("O", "Otro"),
    )

    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    age = models.PositiveSmallIntegerField(null=True, blank=True)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["last_name", "first_name"]),
        ]

    def __str__(self):
        return f"{self.first_name} {self.last_name}".strip()


class Classroom(models.Model):
    name = models.CharField(max_length=100, blank=True, default="")
    school = models.CharField(max_length=255, blank=True)
    academic_year = models.PositiveIntegerField()
    grade = models.PositiveSmallIntegerField()
    section = models.CharField(max_length=5)

    class Meta:
        unique_together = ("school", "academic_year", "grade", "section")

    def __str__(self):
        base = f"{self.academic_year} - {self.grade}{self.section}"
        return (self.name or base)


class Enrollment(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="enrollments")
    classroom = models.ForeignKey(Classroom, on_delete=models.CASCADE, related_name="enrollments")
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["student", "classroom"]),
        ]


class TeacherAssignment(models.Model):
    ROLE_CHOICES = (
        ("TITULAR", "Titular"),
        ("APOYO", "Apoyo"),
    )

    teacher = models.ForeignKey(User, on_delete=models.CASCADE, related_name="classroom_assignments")
    classroom = models.ForeignKey(Classroom, on_delete=models.CASCADE, related_name="teacher_assignments")
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default="TITULAR")
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["teacher", "classroom"]),
        ]


class StudentTeacher(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="teacher_links")
    teacher = models.ForeignKey(User, on_delete=models.CASCADE, related_name="student_links")
    academic_year = models.PositiveIntegerField()
    note = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("student", "teacher", "academic_year")


class Evaluation(models.Model):
    DIAG_CHOICES = (
        ("BAJO", "Menos del 60% (Nivel Bajo)"),
        ("MEDIO", "Entre 60% - 85% (Nivel Medio)"),
        ("ALTO", "Más del 85% (Nivel Alto)"),
    )

    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="evaluations")
    evaluated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="evaluations_made")
    evaluated_at = models.DateField()
    diagnosis = models.CharField(max_length=20, choices=DIAG_CHOICES)
    probability = models.FloatField(null=True, blank=True)
    notes = models.TextField(blank=True)
    model_version = models.CharField(max_length=50, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["student", "evaluated_at"]),
        ]
