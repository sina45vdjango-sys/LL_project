from django.db import models

class LanguageLevel(models.Model):
    """A1, A2, B1, B2, C1, C2"""
    level = models.CharField(max_length=2, unique=True)
    title = models.CharField(max_length=40)
    order = models.PositiveIntegerField(unique=True)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return self.level

class Course(models.Model):
    """Each level has 1 course"""
    language_level = models.OneToOneField(LanguageLevel, on_delete=models.CASCADE, related_name="course")
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    is_published = models.BooleanField(default=False)

    class Meta:
        ordering = ["language_level__order"]

    def __str__(self):
        return self.title

class Lesson(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="lessons")
    title = models.CharField(max_length=250)
    description = models.TextField(blank=True)
    is_published = models.BooleanField(default=False)
    order = models.PositiveIntegerField()
    estimated_time = models.PositiveIntegerField()

    class Meta:
        ordering = ["course", "order"]
        constraints = [
            models.UniqueConstraint(
                fields=["course", "order"],
                name="unique_lesson_order_per_course",
            )
        ]

    def __str__(self):
        return f"{self.course} – {self.title}"