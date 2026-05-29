from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from . import views

urlpatterns = [
    path('health/', views.health),
    path('auth/token/', TokenObtainPairView.as_view()),
    path('auth/token/refresh/', TokenRefreshView.as_view()),
    path('upload/', views.BatchUploadView.as_view()),
    path('batches/', views.BatchListView.as_view()),
    path('batches/<int:pk>/', views.BatchDetailView.as_view()),
    path('records/', views.EmissionRecordListView.as_view()),
    path('records/<int:pk>/', views.EmissionRecordDetailView.as_view()),
    path('records/<int:pk>/review/', views.RecordReviewView.as_view()),
    path('records/bulk-review/', views.BulkReviewView.as_view()),
    path('dashboard/', views.DashboardStatsView.as_view()),
]
