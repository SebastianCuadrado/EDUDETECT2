from django.contrib import admin
from .models import Student, Classroom, Enrollment, TeacherAssignment, StudentTeacher, Evaluation


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ("id", "first_name", "last_name", "age", "gender", "created_at")
    search_fields = ("first_name", "last_name")


@admin.register(Classroom)
class ClassroomAdmin(admin.ModelAdmin):
    list_display = ("id", "school", "academic_year", "grade", "section")
    list_filter = ("academic_year", "grade", "section")


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ("id", "student", "classroom", "start_date", "end_date")
    list_filter = ("classroom__academic_year", "classroom__grade", "classroom__section")


@admin.register(TeacherAssignment)
class TeacherAssignmentAdmin(admin.ModelAdmin):
    list_display = ("id", "teacher", "classroom", "role", "start_date", "end_date")


@admin.register(StudentTeacher)
class StudentTeacherAdmin(admin.ModelAdmin):
    list_display = ("id", "student", "teacher", "academic_year", "created_at")


@admin.register(Evaluation)
class EvaluationAdmin(admin.ModelAdmin):
    list_display = ("id", "student", "evaluated_by", "evaluated_at", "diagnosis", "probability")
    list_filter = ("diagnosis", "evaluated_at")
    search_fields = ("student__first_name", "student__last_name", "evaluated_by__username")
