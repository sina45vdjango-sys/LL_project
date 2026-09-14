from django.contrib.auth.models import User
from django.db import models

class UserProfile(models.Model):
    """Extending django's User model"""

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="profile"
    )
    current_level = models.ForeignKey(
        "lessons.LanguageLevel",
        on_delete=models.SET_NULL,
        related_name="user_profiles",
        blank=True,
        null=True,
    )
    native_language = models.CharField(max_length=10, default="fa")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Profile of {self.user.username}"