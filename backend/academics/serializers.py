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
            "name": {"required": False, "allow_blank": True},
        }


class StudentSerializer(serializers.ModelSerializer):
    last_evaluation = serializers.SerializerMethodField(read_only=True)
    current_grade = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Student
        fields = ["id", "first_name", "last_name", "age", "gender", "last_evaluation", "current_grade"]

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
        # Tomar cualquier matrícula con salón; prioriza la más reciente por fecha (o id)
        enrollment = (
            obj.enrollments.filter(classroom__isnull=False).order_by("-start_date", "-id").first()
            or obj.enrollments.filter(classroom__isnull=False).order_by("-id").first()
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


class TeacherAssignmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = TeacherAssignment
        fields = ["id", "teacher", "classroom", "role", "start_date", "end_date"]


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
