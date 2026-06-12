import re
from datetime import date, timedelta

from django.contrib.auth import get_user_model
from rest_framework import serializers
from .models import Student, Classroom, Enrollment, TeacherAssignment, StudentTeacher, Evaluation


User = get_user_model()


class ClassroomSerializer(serializers.ModelSerializer):
    class Meta:
        model = Classroom
        fields = ["id", "name", "school", "academic_year", "grade", "section"]
        extra_kwargs = {
            "school": {"required": False, "allow_blank": True},
        }

    def validate_name(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError(
                "El nombre del salón debe contener al menos una letra y no puede estar compuesto solo por números o caracteres especiales."
            )
        if not re.search(r"[a-zA-ZáéíóúÁÉÍÓÚüÜñÑ]", value.strip()):
            raise serializers.ValidationError(
                "El nombre del salón debe contener al menos una letra y no puede estar compuesto solo por números o caracteres especiales."
            )
        return value

    def validate_section(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("La sección solo debe contener letras y números.")
        if not re.match(r"^[a-zA-Z0-9]+$", value.strip()):
            raise serializers.ValidationError("La sección solo debe contener letras y números.")
        return value

    def validate_academic_year(self, value):
        if value < date.today().year:
            raise serializers.ValidationError(
                "El año académico no puede ser anterior al año actual."
            )
        return value


class StudentSerializer(serializers.ModelSerializer):
    last_evaluation = serializers.SerializerMethodField(read_only=True)
    current_grade = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Student
        fields = ["id", "first_name", "last_name", "age", "gender", "last_evaluation", "current_grade"]

    def validate_gender(self, value):
        valid = {code for code, _ in Student.GENDER_CHOICES}
        if not value or value not in valid:
            raise serializers.ValidationError("Debe seleccionar el género del estudiante.")
        return value

    def get_last_evaluation(self, obj):
        ev = obj.evaluations.order_by("-evaluated_at", "-id").first()
        if not ev:
            return None
        return {
            "evaluated_at": ev.evaluated_at,
            "diagnosis": ev.diagnosis,
            "probability": ev.probability,
            "evaluated_by": getattr(ev.evaluated_by, "username", None),
        }

    def get_current_grade(self, obj):
        enrollment = (
            obj.enrollments.filter(classroom__isnull=False, end_date__isnull=True)
            .order_by("-start_date", "-id")
            .first()
        )
        if enrollment and enrollment.classroom:
            return enrollment.classroom.grade
        return None


class EvaluationSerializer(serializers.ModelSerializer):
    student_name = serializers.SerializerMethodField(read_only=True)
    evaluated_by_name = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Evaluation
        fields = [
            "id",
            "student",
            "student_name",
            "evaluated_by",
            "evaluated_by_name",
            "evaluated_at",
            "diagnosis",
            "probability",
            "notes",
            "model_version",
            "answers",
            "student_grade",
            "student_age",
        ]
        read_only_fields = ["evaluated_by"]
        extra_kwargs = {
            "probability": {"required": False, "allow_null": True},
            "answers": {"required": False, "allow_null": True},
            "student_grade": {"required": False, "allow_null": True},
            "student_age": {"required": False, "allow_null": True},
        }

    def get_student_name(self, obj):
        try:
            return str(obj.student)
        except Exception:
            return None

    def get_evaluated_by_name(self, obj):
        return getattr(obj.evaluated_by, "username", None)

    def create(self, validated_data):
        request = self.context.get("request")
        if request and request.user and request.user.is_authenticated:
            validated_data["evaluated_by"] = request.user
        return super().create(validated_data)


class EnrollmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Enrollment
        fields = ["id", "student", "classroom", "start_date", "end_date"]

    def validate(self, attrs):
        start_date = attrs.get("start_date")
        student = attrs.get("student")
        age = getattr(student, "age", None) if student else None

        if start_date and age:
            today = date.today()
            try:
                min_start_date = date(today.year - age - 1, today.month, today.day)
            except ValueError:
                min_start_date = date(today.year - age - 1, today.month, 28)
            min_start_date += timedelta(days=1)

            if start_date < min_start_date:
                raise serializers.ValidationError({
                    "start_date": "La fecha de inicio de matrícula no puede ser anterior al nacimiento estimado del alumno."
                })

        return attrs


class TeacherAssignmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = TeacherAssignment
        fields = ["id", "teacher", "classroom", "role", "start_date", "end_date"]
    
    def validate(self, attrs):
        teacher = attrs.get("teacher")
        if self.instance is None and teacher and not getattr(teacher, "is_active", True):
            raise serializers.ValidationError(
                "No se pueden asignar salones a un docente inhabilitado."
            )

        start_date = attrs.get("start_date")
        classroom = attrs.get("classroom")
        if start_date and classroom:
            try:
                acad_year = int(classroom.academic_year)
            except Exception:
                acad_year = None
            if acad_year and start_date.year != acad_year:
                raise serializers.ValidationError({
                    "start_date": "La fecha de inicio de asignación debe corresponder al periodo académico del salón seleccionado."
                })
        # Validar duplicados: un mismo docente no puede tener más de una asignación para el mismo salón
        if classroom and teacher:
            qs = TeacherAssignment.objects.filter(teacher=teacher, classroom=classroom)
            if self.instance is None:
                # Creación: no debe existir ninguna asignación previa
                if qs.exists():
                    raise serializers.ValidationError({
                        "classroom": "El docente ya tiene una asignación registrada para el salón seleccionado."
                    })
            else:
                # Actualización: permitir si la única asignación existente es la misma instancia
                if qs.exclude(id=self.instance.id).exists():
                    raise serializers.ValidationError({
                        "classroom": "El docente ya tiene una asignación registrada para el salón seleccionado."
                    })
        return attrs


class StudentTeacherSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudentTeacher
        fields = ["id", "student", "teacher", "academic_year", "note", "created_at"]
        read_only_fields = ["created_at"]


class EvaluationInferenceSerializer(serializers.Serializer):
    student = serializers.IntegerField()
    answers = serializers.ListField(
        child=serializers.ChoiceField(choices=[
            "NUNCA", "RARA VEZ", "A VECES", "FRECUENTEMENTE", "SIEMPRE"
        ]),
        min_length=30,
        max_length=30,
    )
    notes = serializers.CharField(allow_blank=True, required=False)
    grade = serializers.IntegerField(required=False, allow_null=True, min_value=1, max_value=12)
