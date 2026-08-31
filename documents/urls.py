from django.urls import path

from . import views

app_name = 'documents'

urlpatterns = [
    path('types/', views.DocumentTypeListView.as_view(), name='documenttype_list'),
    path('types/new/', views.DocumentTypeCreateView.as_view(), name='documenttype_create'),
    path('types/<int:pk>/edit/', views.DocumentTypeUpdateView.as_view(), name='documenttype_update'),
    path('residents/<int:pk>/issue/', views.IssueDocumentView.as_view(), name='issue_document'),
    path('print-without-account/', views.WalkInIssueView.as_view(), name='walk_in_issue'),
    path('<int:pk>/', views.IssuedDocumentDetailView.as_view(), name='issued_document_detail'),
    path('<int:pk>/pdf/', views.IssuedDocumentPdfView.as_view(), name='issued_document_pdf'),
]
