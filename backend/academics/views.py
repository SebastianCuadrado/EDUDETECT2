from django.contrib.auth import get_user_model
from django.db import models
from django.db.models import OuterRef, Exists
from rest_framework import viewsets, permissions, filters
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.response import Response
from rest_framework.decorators import action

from .models import Student, Classroom, Enrollment, TeacherAssignment, StudentTeacher, Evaluation
from .serializers import (
    StudentSerializer,
    ClassroomSerializer,
    EnrollmentSerializer,
    TeacherAssignmentSerializer,
    StudentTeacherSerializer,
    EvaluationSerializer,
    EvaluationInferenceSerializer,
)
from .services.ml_inference import predict as ml_predict


User = get_user_model()


def scoped_students_qs(user):
    if getattr(user, "role", None) == "ADMIN" or getattr(user, "is_superuser", False):
        return Student.objects.all()

    # Subquery: enrollment activo (end_date IS NULL) cuyo salón tenga una
    # asignación activa (end_date IS NULL) para este docente.
    # Usar Exists + OuterRef garantiza que las tres condiciones aplican sobre
    # la MISMA fila de Enrollment, evitando el cross-join que ocurre en
    # PostgreSQL cuando se encadenan múltiples lookups a la misma relación
    # dentro de un único .filter().
    active_enrollment = Enrollment.objects.filter(
        student=OuterRef("pk"),
        end_date__isnull=True,
        classroom__teacher_assignments__teacher=user,
        classroom__teacher_assignments__end_date__isnull=True,
    )
    return Student.objects.filter(Exists(active_enrollment))


def scoped_classrooms_qs(user):
    if getattr(user, "role", None) == "ADMIN" or getattr(user, "is_superuser", False):
        return Classroom.objects.all()

    return (
        Classroom.objects.filter(
            teacher_assignments__teacher=user,
            teacher_assignments__end_date__isnull=True,
        )
        .distinct()
    )

def current_student_grade(student_id: int):
    enrollment = (
        Enrollment.objects.filter(student_id=student_id, end_date__isnull=True)
        .order_by("-start_date", "-id")
        .first()
    )
    if enrollment and enrollment.classroom:
        return enrollment.classroom.grade
    return None


class IsAdminOrTeacher(permissions.BasePermission):
    """Mantiene compatibilidad para evaluaciones y otras vistas.
    Autenticado: acceso; objeto: debe estar en alcance o ser ADMIN.
    """
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        role = getattr(request.user, "role", None)
        if role == "ADMIN" or request.user.is_superuser:
            return True
        if isinstance(obj, Student):
            return scoped_students_qs(request.user).filter(id=obj.id).exists()
        if isinstance(obj, Evaluation):
            return scoped_students_qs(request.user).filter(id=obj.student_id).exists()
        return False


class IsAdminOrScopedReadOnly(permissions.BasePermission):
    """Solo ADMIN puede escribir; docentes pueden leer objetos dentro de su alcance."""
    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if request.method in permissions.SAFE_METHODS:
            return True
        role = getattr(user, "role", None)
        return bool(role == "ADMIN" or user.is_superuser)

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            role = getattr(request.user, "role", None)
            if role == "ADMIN" or request.user.is_superuser:
                return True
            scoped = scoped_students_qs(request.user)
            if isinstance(obj, Student):
                return scoped.filter(id=obj.id).exists()
            if isinstance(obj, Evaluation):
                return scoped.filter(id=obj.student_id).exists()
            if isinstance(obj, Enrollment):
                return scoped.filter(id=obj.student_id).exists()
            if isinstance(obj, Classroom):
                return scoped_classrooms_qs(request.user).filter(id=obj.id).exists()
            return False
        # Es escritura: ya pasó por has_permission (ADMIN)
        return True


class StudentViewSet(viewsets.ModelViewSet):
    serializer_class = StudentSerializer
    permission_classes = [IsAdminOrScopedReadOnly]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["first_name", "last_name"]
    ordering_fields = ["id", "last_name", "first_name"]

    def get_queryset(self):
        qs = scoped_students_qs(self.request.user)
        # Filtros opcionales por salón (útiles para docentes)
        year = self.request.query_params.get("year")
        grade = self.request.query_params.get("grade")
        section = self.request.query_params.get("section")
        if year:
            qs = qs.filter(
                enrollments__classroom__academic_year=year,
                enrollments__end_date__isnull=True,
            )

        if grade:
            qs = qs.filter(
                enrollments__classroom__grade=grade,
                enrollments__end_date__isnull=True,
        )

        if section:
            qs = qs.filter(
                enrollments__classroom__section=section,
                enrollments__end_date__isnull=True,
        )
        return qs.order_by("-id").distinct()

    @action(detail=False, methods=["get"], url_path="evaluated")
    def evaluated(self, request):
        qs = scoped_students_qs(request.user).filter(evaluations__isnull=False)

        # Optional filters
        q = request.query_params.get("search")
        if q:
            qs = qs.filter(
                models.Q(first_name__icontains=q)
                | models.Q(last_name__icontains=q)
            )

        year = request.query_params.get("year")
        grade = request.query_params.get("grade")
        section = request.query_params.get("section")
        if year:
            qs = qs.filter(
                enrollments__classroom__academic_year=year,
                enrollments__end_date__isnull=True,
            )

        if grade:
            qs = qs.filter(
                enrollments__classroom__grade=grade,
                enrollments__end_date__isnull=True,
            )

        if section:
            qs = qs.filter(
                enrollments__classroom__section=section,
                enrollments__end_date__isnull=True,
            )

        # Ordenar por última evaluación y evitar duplicados por JOIN
        # Usamos distinct() genérico para compatibilidad con SQLite/MySQL.
        qs = qs.order_by("-evaluations__evaluated_at", "-evaluations__id").distinct()

        page = self.paginate_queryset(qs)
        serializer = self.get_serializer(page or qs, many=True)
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)


class ClassroomViewSet(viewsets.ModelViewSet):
    serializer_class = ClassroomSerializer
    permission_classes = [IsAdminOrScopedReadOnly]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["school", "section"]
    ordering_fields = ["academic_year", "grade", "section"]

    def get_queryset(self):
        qs = scoped_classrooms_qs(self.request.user)
        school = self.request.query_params.get("school")
        section = self.request.query_params.get("section")
        if school:
            qs = qs.filter(school__icontains=school)
        if section:
            qs = qs.filter(section__icontains=section)
        return qs.order_by("-academic_year", "grade", "section")


class EnrollmentViewSet(viewsets.ModelViewSet):
    serializer_class = EnrollmentSerializer
    permission_classes = [IsAdminOrScopedReadOnly]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ["id", "start_date", "end_date"]

    def get_queryset(self):
        user = self.request.user
        qs = Enrollment.objects.all()
        role = getattr(user, "role", None)
        if role != "ADMIN" and not user.is_superuser:
            qs = qs.filter(student__in=scoped_students_qs(user))
        classroom = self.request.query_params.get("classroom")
        student = self.request.query_params.get("student")
        if classroom:
            qs = qs.filter(classroom_id=classroom)
        if student:
            qs = qs.filter(student_id=student)
        return qs.order_by("-id")


class TeacherAssignmentViewSet(viewsets.ModelViewSet):
    serializer_class = TeacherAssignmentSerializer
    permission_classes = [permissions.IsAdminUser]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ["id", "start_date", "end_date"]

    def get_queryset(self):
        qs = TeacherAssignment.objects.all()
        classroom = self.request.query_params.get("classroom")
        teacher = self.request.query_params.get("teacher")
        if classroom:
            qs = qs.filter(classroom_id=classroom)
        if teacher:
            qs = qs.filter(teacher_id=teacher)
        return qs.order_by("-id")


class StudentTeacherViewSet(viewsets.ModelViewSet):
    queryset = StudentTeacher.objects.all()
    serializer_class = StudentTeacherSerializer
    permission_classes = [permissions.IsAdminUser]


class EvaluationViewSet(viewsets.ModelViewSet):
    serializer_class = EvaluationSerializer
    permission_classes = [IsAdminOrTeacher]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ["evaluated_at", "probability", "id"]

    def get_queryset(self):
        # Solo evaluaciones de alumnos dentro del alcance del usuario
        student_ids = scoped_students_qs(self.request.user).values_list("id", flat=True)
        qs = Evaluation.objects.filter(student_id__in=student_ids)
        student = self.request.query_params.get("student")
        if student:
            qs = qs.filter(student_id=student)
        # Filtrar solo las evaluaciones hechas por el usuario autenticado
        mine = self.request.query_params.get("mine")
        if mine and str(mine).lower() in ("1", "true", "yes"): 
            qs = qs.filter(evaluated_by=self.request.user)
        return qs.order_by("-evaluated_at", "-id")

    def perform_create(self, serializer):
        # Completar grado/edad si no vienen en el payload
        student = serializer.validated_data.get("student")
        grade = serializer.validated_data.get("student_grade")
        age = serializer.validated_data.get("student_age")
        if not grade and student:
            grade = current_student_grade(student.id)
        if age in (None, "") and student:
            age = getattr(student, "age", None)
        serializer.save(
            evaluated_by=self.request.user if self.request and self.request.user.is_authenticated else None,
            student_grade=grade,
            student_age=age,
        )


class EvaluateQuestionnaireView(APIView):
    permission_classes = [IsAdminOrTeacher]

    def post(self, request, *args, **kwargs):
        ser = EvaluationInferenceSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data
        # Alcance: el estudiante debe estar en el scope del usuario
        try:
            student = Student.objects.get(id=data["student"]) 
        except Student.DoesNotExist:
            return Response({"detail": "Alumno no encontrado"}, status=status.HTTP_404_NOT_FOUND)
        if not scoped_students_qs(request.user).filter(id=student.id).exists():
            return Response({"detail": "Sin permiso para evaluar a este alumno"}, status=status.HTTP_403_FORBIDDEN)

        grade = data.get("grade")
        if grade is None:
            grade = current_student_grade(student.id)

        try:
            diagnosis, probability, version = ml_predict(
                data["answers"],
                age=getattr(student, "age", None),
                grade=grade,
            )
        except Exception as e:
            return Response({"detail": f"Error de inferencia: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        def diag_label(code: str) -> str:
            return {
                "BAJO": "Menos del 60% (Nivel Bajo)",
                "MEDIO": "Entre 60% - 85% (Nivel Medio)",
                "ALTO": "Más del 85% (Nivel Alto)",
            }.get(code, code)

        return Response({
            "diagnosis": diagnosis,  # código BAJO/MEDIO/ALTO
            "diagnosis_label": diag_label(diagnosis),
            "probability": probability,
            "model_version": version,
        })
