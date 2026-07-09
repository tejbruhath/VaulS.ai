"""URL configuration for RAG API."""
from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rag_api.api.views import (
    RepositoryViewSet,
    DocumentViewSet,
    ChunkViewSet,
    query_stream,
    health_check,
)

router = DefaultRouter()
router.register(r'repositories', RepositoryViewSet, basename='repository')
router.register(r'documents', DocumentViewSet, basename='document')
router.register(r'chunks', ChunkViewSet, basename='chunk')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include(router.urls)),
    path('api/query/stream/', query_stream, name='query-stream'),
    path('api/health/', health_check, name='health-check'),
]
