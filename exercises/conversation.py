"""The lesson's own dialogue, played as a conversation.

Concepts 9 and 13 were delivered on top of an exercise's quiz questions, which is why the
pages read like a form in chat bubbles instead of a conversation: the content was
«واژهٔ hallo به چه معنی است؟» with four options, not «Wie heißt du?» answered by
«Ich heiße Anna». The course already contains the real conversation — ``LessonSentence``
rows whose role is ``DIALOGUE``, in their stored order, with the ``speaker`` the lesson
data names — and each line already has a Persian translation and a recording. This module
is what hands that to the page.

Which side the learner takes is the first person to speak, because these A1 dialogues open
with the person the rest of the scene revolves around; everyone else is the partner. The
learner's own lines are answered freely and then checked against the lesson's line, so
nothing here is graded and nothing is stored: the graded practice of the same lesson lives
on its exercise page, which every node still links to.
"""

from exercises.situations import get_situational_scenario
from lessons.models import LessonSentence


def conversation_turns(lesson):
    """The lesson's dialogue as turns, each marked whose line it is.

    Returns ``{"you": name, "partner": name, "turns": [...], "scenario": scenario}``.
    If a situational roleplay scenario is curated for this lesson (exercises/situations.py),
    it provides the scenario metadata and interactive branching turns.
    Otherwise, it reads standard LessonSentence rows.
    """
    scenario = get_situational_scenario(lesson)
    if scenario:
        return {
            "you": scenario["role_you"],
            "partner": scenario["role_partner"],
            "turns": scenario["turns"],
            "scenario": scenario,
        }

    rows = (
        LessonSentence.objects.filter(
            lesson=lesson,
            role=LessonSentence.Role.DIALOGUE,
            sentence__is_published=True,
        )
        .select_related("sentence")
        .order_by("order")
    )

    lines = list(rows)

    you = ""
    for row in lines:
        if row.speaker:
            you = row.speaker
            break

    turns = []
    partner = ""
    for row in lines:
        sentence = row.sentence
        mine = row.speaker == you
        if not mine and not partner:
            partner = row.speaker
        turns.append(
            {
                "speaker": row.speaker,
                "mine": mine,
                "text": sentence.text,
                "translation": sentence.translation_fa,
                "audio": sentence.audio,
            }
        )

    return {"you": you, "partner": partner, "turns": turns, "scenario": None}
