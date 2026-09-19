from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User

from accounts.models import UserProfile


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    extra = 0


class UserAdmin(BaseUserAdmin):
    """Custom User admin that shows the profile inline."""
    inlines = [UserProfileInline]
    list_display = (*BaseUserAdmin.list_display, "date_joined")
    list_filter = (*BaseUserAdmin.list_filter, "is_active", "date_joined")


admin.site.unregister(User)
admin.site.register(User, UserAdmin)