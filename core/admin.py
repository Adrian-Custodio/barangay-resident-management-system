from django.contrib import admin

from .models import Official, SiteSettings


@admin.register(Official)
class OfficialAdmin(admin.ModelAdmin):
    list_display = ("name", "position", "category", "display_order", "is_active")
    list_filter = ("category", "is_active")


admin.site.register(SiteSettings)
