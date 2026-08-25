from django.contrib import admin
from .models import DocumentType, IssuedDocument

admin.site.register(DocumentType)
admin.site.register(IssuedDocument)
