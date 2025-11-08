from rest_framework.routers import DefaultRouter
from .views import (
    StudentViewSet,
    ClassroomViewSet,
    EnrollmentViewSet,
    TeacherAssignmentViewSet,
    StudentTeacherViewSet,
    EvaluationViewSet,
)


router = DefaultRouter()
router.register(r"students", StudentViewSet, basename="student")
router.register(r"classrooms", ClassroomViewSet, basename="classroom")
router.register(r"enrollments", EnrollmentViewSet, basename="enrollment")
router.register(r"teacher-assignments", TeacherAssignmentViewSet, basename="teacher-assignment")
router.register(r"student-teachers", StudentTeacherViewSet, basename="student-teacher")
router.register(r"evaluations", EvaluationViewSet, basename="evaluation")

urlpatterns = router.urls

