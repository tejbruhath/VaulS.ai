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
from rag_api.api.advanced_views import (
    query_with_citations,
    explain_query,
    compare_retrieval_strategies,
    get_query_analytics,
    suggest_improvements,
)

router = DefaultRouter()
router.register(r'repositories', RepositoryViewSet, basename='repository')
router.register(r'documents', DocumentViewSet, basename='document')
router.register(r'chunks', ChunkViewSet, basename='chunk')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include(router.urls)),
    path('api/query/stream/', query_stream, name='query-stream'),
    path('api/query/citations/', query_with_citations, name='query-citations'),
    path('api/query/explain/', explain_query, name='query-explain'),
    path('api/query/compare/', compare_retrieval_strategies, name='query-compare'),
    path('api/analytics/queries/', get_query_analytics, name='analytics-queries'),
    path('api/suggest/improvements/', suggest_improvements, name='suggest-improvements'),
    path('api/health/', health_check, name='health-check'),
]
