from rest_framework.routers import DefaultRouter
from django.urls import path
from .views import (
    StudentViewSet,
    ClassroomViewSet,
    EnrollmentViewSet,
    TeacherAssignmentViewSet,
    StudentTeacherViewSet,
    EvaluationViewSet,
    EvaluateQuestionnaireView,
)


router = DefaultRouter()
router.register(r"students", StudentViewSet, basename="student")
router.register(r"classrooms", ClassroomViewSet, basename="classroom")
router.register(r"enrollments", EnrollmentViewSet, basename="enrollment")
router.register(r"teacher-assignments", TeacherAssignmentViewSet, basename="teacher-assignment")
router.register(r"student-teachers", StudentTeacherViewSet, basename="student-teacher")
router.register(r"evaluations", EvaluationViewSet, basename="evaluation")

urlpatterns = router.urls + [
    path("ml/evaluate/", EvaluateQuestionnaireView.as_view(), name="ml-evaluate"),
]
