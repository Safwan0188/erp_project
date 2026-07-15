from django.contrib import admin
from .models import AppUser


@admin.register(AppUser)
class AppUserAdmin(admin.ModelAdmin):
    list_display = ('name', 'role', 'is_active', 'created_at')
    list_filter  = ('role', 'is_active')
    search_fields = ('name',)