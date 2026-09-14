from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from accounts.models import UserProfile

class EmployeeInline(admin.StackedInline):
    model = UserProfile
    can_delete = False



class UserAdmin(BaseUserAdmin):
    inlines = [EmployeeInline]


admin.site.unregister(User)
admin.site.register(User, UserAdmin)