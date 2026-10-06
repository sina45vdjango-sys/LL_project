"""The three written sections, named in one place.

Two tables have to agree on these codes and they live in two apps:

* ``ExamRunQuestion.section`` stores which part of the paper a question was asked in, and
  has to stay readable after the content it came from is edited;
* ``Question.exam_section`` marks the curated content the paper is drawn from — see
  ``exercises/models.py``.

The exams app imports the exercises app, so the exercises app cannot import
``exams/models.py``. This module therefore imports nothing but Django's field helpers,
which is the whole reason it exists separately: the codes are the database's convention,
and a convention cannot live inside the module that the other side is not allowed to
import.
"""

from django.db import models


class Section(models.TextChoices):
    HOEREN = "HOEREN", "Hören"
    LESEN = "LESEN", "Lesen"
    SCHREIBEN = "SCHREIBEN", "Schreiben"
