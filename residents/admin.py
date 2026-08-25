from django.contrib import admin
from .models import Resident

@admin.register(Resident)
class ResidentAdmin(admin.ModelAdmin):
    list_display = ("resident_id", "full_name", "birth_date", "sex", "is_active")
    search_fields = ("first_name", "last_name", "resident_id")
