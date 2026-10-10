"""The one place the spoken-audio settings live.

Four commands synthesise German speech: ``import_a1_words`` for the words, and
``generate_sentence_audio``, ``generate_grammar_audio`` and
``generate_lesson_content_audio`` for the sentences, the grammar topics and the lesson
content blocks. Each used to carry its own copy of the voice name and its own call to
``edge_tts``, which is how the speaking rate ended up being whatever the library
defaults to. Reading both settings from here means the whole course is one speaker at
one speed, and that changing the speed is a one-line edit instead of four.

``RATE`` is a percentage relative to the voice's own pace, which is the form edge-tts
takes: ``-15%`` is "a sixth slower". The default pace is a news reader's, and a learner
hearing a new word for the first time cannot catch it at that speed. A small slow-down
is the fix; a large one (``-30%`` and beyond) is worse than the problem, because the
speaker turns singsong and a one-syllable word stretches until it stops sounding like a
word. ``-15%`` measured 6.6s -> 7.7s on a sample sentence, which is the kind of change a
learner notices without it sounding artificial.
"""

VOICE = "de-DE-KatjaNeural"

#: How much slower than the voice's natural pace the course is spoken.
RATE = "-15%"
