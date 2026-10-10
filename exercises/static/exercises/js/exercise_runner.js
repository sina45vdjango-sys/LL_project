/* Exercise runner — the state module for one exercise page.
 *
 * The server rendered every question and its options; the correct answers are not in
 * the page at all. This file owns the run: which question is current, whether it has
 * been submitted, how long the learner took, what the feedback says, moving
 * forwards/backwards, and the result state at the end.
 *
 * Every submission goes to exercises:exercise-submit (the runner's `data-submit-url`),
 * which grades it — recording an ExerciseAttempt and the tested word's counters for a
 * signed-in learner — and answers with the verdict. That verdict is the only thing this
 * file trusts; it never decides for itself whether an answer is right.
 *
 * States per question: `submitted` (bool) and `outcome` ("correct" | "wrong" | null).
 * A question with no authored answer (`data-kind="none"`) is never submitted and is
 * left out of the score.
 */
(() => {
  'use strict';

  const runner = document.querySelector('[data-runner]');
  if (!runner) return;

  // Practice pages give a missed question a second try before showing the answer (the
  // template sets this). A test does not, because a second try there would inflate the
  // score, so the flag is the page's decision rather than this file's.
  const secondTry = 'secondTry' in runner.dataset;

  const questions = Array.from(runner.querySelectorAll('[data-question]'));
  if (!questions.length) return;

  const total = questions.length;
  const scoreable = questions.filter((question) => question.dataset.kind !== 'none').length;

  const progress = runner.querySelector('[data-runner-progress]');
  const bar = runner.querySelector('[data-runner-bar]');
  const fill = runner.querySelector('[data-runner-fill]');
  const results = runner.querySelector('[data-runner-results]');

  const state = questions.map(() => ({ submitted: false, outcome: null, attempts: 0 }));
  let index = 0;

  /* ------------------------------------------------------------ submission ---- */

  // Where the answers go, and the token the POST needs. One exercise's page puts a
  // single URL on the runner; a session gathers questions from several exercises at
  // once, so each question carries its own and that one wins. Either way the server
  // grades the answer against the exercise the question really belongs to.
  const runnerSubmitUrl = runner.dataset.submitUrl || '';
  const csrfToken = document.querySelector('meta[name="csrf-token"]');

  function submitUrlFor(question) {
    return question.dataset.submitUrl || runnerSubmitUrl;
  }

  // When the current question came on screen. The learner's response time is measured
  // from here to the moment they submit — a rough number for learning analytics, which
  // is all the `response_time` field claims to be.
  let questionShownAt = performance.now();

  /** Seconds since a `performance.now()` reading, to one decimal place. */
  function secondsSince(start) {
    return Math.round((performance.now() - start) / 100) / 10;
  }

  /* -------------------------------------------------------------- render ---- */

  function syncProgress() {
    const percent = Math.round(((index + 1) / total) * 100);
    if (bar) bar.setAttribute('aria-valuenow', String(index + 1));
    if (fill) fill.style.width = `${percent}%`;
  }

  function syncActions(question) {
    const position = questions.indexOf(question);
    const current = state[position];
    const kind = question.dataset.kind;

    const actions = question.querySelector('[data-runner-actions]');
    if (actions) actions.hidden = false;

    const previous = question.querySelector('[data-runner-prev]');
    if (previous) previous.hidden = position === 0;

    const check = question.querySelector('[data-runner-check]');
    if (check) check.hidden = current.submitted || kind === 'none';

    const next = question.querySelector('[data-runner-next]');
    if (next) next.hidden = kind === 'none' ? false : !current.submitted;
  }

  function apply(nextIndex, options) {
    const settings = options || {};
    index = Math.max(0, Math.min(total - 1, nextIndex));
    if (results) results.hidden = true;
    if (progress) progress.hidden = total < 2;

    questions.forEach((question, position) => {
      question.classList.toggle('is-active', position === index);
    });

    const current = questions[index];
    // The clock starts when the question is actually on screen, so a learner who goes
    // back and forth does not accumulate time on it.
    questionShownAt = performance.now();
    syncProgress();
    syncActions(current);

    if (settings.focus) {
      const heading = current.querySelector('.runner-q__prompt');
      if (heading) heading.focus();
    }
  }

  function showHint(question, message) {
    const hint = question.querySelector('[data-runner-hint]');
    if (!hint) return;
    if (message) hint.textContent = message;
    hint.hidden = false;
  }

  function hideHint(question) {
    const hint = question.querySelector('[data-runner-hint]');
    if (hint) hint.hidden = true;
  }

  /* ---------------------------------------------------------------- hint ---- */

  // Where a hint is fetched from. The text is not in the page — the server decides
  // whether the learner has missed this question enough times to be owed one. Like the
  // submit URL, the question's own wins over the runner's, so a session can ask the
  // right exercise for a hint.
  const runnerHintUrl = runner.dataset.hintUrl || '';

  function hintUrlFor(question) {
    return question.dataset.hintUrl || runnerHintUrl;
  }

  function revealHelp(question) {
    const block = question.querySelector('[data-runner-help-block]');
    if (block) block.hidden = false;
  }

  function showHelpText(question, message) {
    const text = question.querySelector('[data-runner-help]');
    if (!text) return;
    text.textContent = message;
    text.hidden = false;
  }

  function requestHint(question) {
    const hintUrl = hintUrlFor(question);
    if (!hintUrl) return;

    const button = question.querySelector('[data-runner-hint-request]');
    if (button) button.disabled = true;

    fetch(`${hintUrl}?question=${Number(question.dataset.question)}`, { headers: { Accept: 'application/json' } })
      .then((response) => (response.ok ? response.json() : null))
      .then((data) => {
        if (button) button.disabled = false;
        if (data && data.hint) showHelpText(question, data.hint);
      })
      .catch(() => {
        if (button) button.disabled = false;
      });
  }

  // Never colour alone: each revealed option also gains a text flag.
  function flagOption(label, name) {
    if (!label) return;
    const element = label.querySelector(`[data-flag="${name}"]`);
    if (element) element.hidden = false;
    label.classList.add(name === 'correct' ? 'is-correct' : 'is-wrong');
  }

  function optionLabel(question, answerId) {
    const input = question.querySelector(`input[type="radio"][value="${answerId}"]`);
    return input ? input.closest('.runner-option') : null;
  }

  function markOptions(question, chosenId, verdict) {
    question.querySelectorAll('input[type="radio"]').forEach((input) => {
      input.disabled = true;
    });

    if (verdict.correct) {
      flagOption(optionLabel(question, chosenId), 'correct');
      return;
    }

    flagOption(optionLabel(question, chosenId), 'wrong');
    // The right option is named by the response; this page never held that knowledge.
    flagOption(optionLabel(question, verdict.correct_answer), 'correct');
  }

  function markTyped(question, correct) {
    const input = question.querySelector('.runner-answer__input');
    if (!input) return;
    input.readOnly = true;
    // Clear first: a first miss left the field marked wrong, and a second try that is
    // right must not keep both marks.
    input.classList.remove('is-correct', 'is-wrong');
    input.classList.add(correct ? 'is-correct' : 'is-wrong');
    disableSatzbau(question);
  }

  function showFeedback(question, verdict) {
    const feedback = question.querySelector('[data-runner-feedback]');
    if (!feedback) return;

    const result = feedback.querySelector(`[data-result="${verdict.correct ? 'correct' : 'wrong'}"]`);
    if (result) result.hidden = false;

    // Only reveal the answer when it was missed; a correct answer needs no correction.
    if (!verdict.correct) {
      const expected = feedback.querySelector('[data-expected]');
      const value = feedback.querySelector('[data-expected-value]');
      if (value) value.textContent = verdict.expected.join(' · ');
      if (expected) expected.hidden = false;
    }

    const explanation = feedback.querySelector('[data-explanation]');
    if (explanation && verdict.explanation) {
      explanation.textContent = verdict.explanation;
      explanation.hidden = false;
    }

    if (!verdict.correct && verdict.tested_word) {
      showWordCard(feedback, verdict.tested_word);
    }
  }

  /*
   * The word a missed question tested, said properly: the article, the plural, how it
   * sounds, what it means. This is the teaching moment a miss otherwise lacks — most
   * questions carry no authored explanation, but almost every one tests a real word, so
   * the facts come from the word itself. The response already carried them, because the
   * word is public lesson content; this only draws them.
   */
  function showWordCard(feedback, word) {
    const card = feedback.querySelector('[data-runner-word-card]');
    if (!card) return;

    card.textContent = '';

    const head = document.createElement('p');
    head.className = 'runner-word-card__head';

    const term = document.createElement('span');
    term.className = 'runner-word-card__term';
    term.lang = 'de';
    term.dir = 'ltr';
    if (word.article) term.textContent = word.article + ' ' + word.word;
    else term.textContent = word.word;
    head.appendChild(term);

    if (word.word_type) {
      const type = document.createElement('span');
      type.className = 'runner-word-card__type';
      type.textContent = word.word_type;
      head.appendChild(type);
    }

    card.appendChild(head);

    const meaning = document.createElement('p');
    meaning.className = 'runner-word-card__meaning';
    meaning.textContent = word.meaning_fa;
    card.appendChild(meaning);

    if (word.pronunciation) {
      const sound = document.createElement('p');
      sound.className = 'runner-word-card__sound';
      sound.lang = 'de';
      sound.dir = 'ltr';
      sound.textContent = word.pronunciation;
      card.appendChild(sound);
    }

    if (word.plural) {
      const plural = document.createElement('p');
      plural.className = 'runner-word-card__plural';
      plural.textContent = 'جمع: ';

      const value = document.createElement('span');
      value.lang = 'de';
      value.dir = 'ltr';
      value.textContent = word.plural;
      plural.appendChild(value);
      card.appendChild(plural);
    }

    const link = document.createElement('a');
    link.className = 'runner-word-card__link';
    link.href = word.url;
    link.textContent = 'واژه را کامل ببین ←';
    card.appendChild(link);

    card.hidden = false;
  }

  /*
   * The points this answer earned, straight from the response (accounts/xp.py).
   * Nothing is added up here on purpose: the server decides XP, so the page can only
   * ever echo it. A visitor has no totals to show, and the response says so with null.
   */
  function showXp(question, verdict) {
    const feedback = question.querySelector('[data-runner-feedback]');
    if (!feedback) return;
    if (!verdict.xp || !verdict.xp_gained) return;

    const previous = feedback.querySelector('[data-runner-xp]');
    if (previous) previous.remove();

    const note = document.createElement('p');
    note.setAttribute('data-runner-xp', '');
    note.className = 'runner-xp';
    note.textContent = `+${verdict.xp_gained} امتیاز · سطح ${verdict.xp.level}`;
    feedback.appendChild(note);
  }

  /* ------------------------------------------------------------- actions ---- */

  /** What the learner answered: an option id, or the text they typed. */
  function collectAnswer(question) {
    if (question.dataset.kind === 'choice') {
      const chosen = question.querySelector('input[type="radio"]:checked');
      return chosen ? { answer: Number(chosen.value), response_text: '' } : null;
    }

    const input = question.querySelector('.runner-answer__input');
    const typed = input ? input.value.trim() : '';
    return typed ? { answer: null, response_text: typed } : null;
  }

  function sendSubmission(question, submission, retry) {
    return fetch(submitUrlFor(question), {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrfToken ? csrfToken.content : '',
      },
      body: JSON.stringify({
        question: Number(question.dataset.question),
        answer: submission.answer,
        response_text: submission.response_text,
        response_time: secondsSince(questionShownAt),
        // A second try at the same question. The server still grades and records it, but
        // the points were already decided by the first attempt, so none are awarded now.
        retry: retry,
      }),
    })
      .then((response) => (response.ok ? response.json() : null))
      .catch(() => null);
  }

  /** While a submission is in flight the check button must not fire a second time. */
  function setChecking(question, busy) {
    const check = question.querySelector('[data-runner-check]');
    if (!check) return;
    check.disabled = busy;
    check.textContent = busy ? 'در حال بررسی…' : 'بررسی پاسخ';
  }

  function submit(question) {
    const position = questions.indexOf(question);
    const current = state[position];
    if (current.submitted || question.dataset.kind === 'none') return;

    const submission = collectAnswer(question);
    if (!submission) {
      showHint(question);
      return;
    }

    // How many tries this question has had. The first miss is answered again rather than
    // handed the answer, and a retry is sent as such so the server knows the points were
    // already decided by the first attempt.
    const attempt = current.attempts + 1;

    hideHint(question);
    setChecking(question, true);

    sendSubmission(question, submission, attempt > 1).then((verdict) => {
      setChecking(question, false);

      if (!verdict) {
        showHint(question, 'ارتباط با سرور برقرار نشد؛ دوباره تلاش کن.');
        return;
      }

      // Held back once on a practice page: the learner is told their answer was wrong —
      // the useful half — but not which one is right, so the second try is real work
      // instead of copying the answer. The question stays open and the check button
      // stays visible, because nothing has been settled yet.
      if (!verdict.correct && secondTry && attempt === 1) {
        current.attempts = attempt;
        offerSecondTry(question, submission);
        return;
      }

      // Keep what the learner actually answered alongside the verdict, so the results
      // screen can show their own answer next to the right one (see showResults) instead
      // of only naming the question. A choice answer is read from the option's text — the
      // page still never holds which option is correct, only what was picked.
      let answerText = '';
      if (question.dataset.kind === 'choice') {
        const label = optionLabel(question, submission.answer);
        const text = label ? label.querySelector('.runner-option__text') : null;
        answerText = text ? text.textContent.trim() : '';
      } else {
        const input = question.querySelector('.runner-answer__input');
        answerText = input ? input.value.trim() : '';
      }

      const secondTryNote = question.querySelector('[data-runner-second-try]');
      if (secondTryNote) secondTryNote.hidden = true;

      state[position] = {
        submitted: true,
        outcome: verdict.correct ? 'correct' : 'wrong',
        attempts: attempt,
        answerText: answerText,
        verdict: verdict,
        // The word this question tested, with the learner's counters, or null. It comes
        // only with a missed answer from a signed-in learner; the results screen uses it
        // to list the weak words (see showWeakWords).
        word: verdict.tested_word || null,
      };
      if (question.dataset.kind === 'choice') markOptions(question, submission.answer, verdict);
      else markTyped(question, verdict.correct);
      showFeedback(question, verdict);
      showXp(question, verdict);
      // A repeated mistake now owes a hint, so the button appears without a reload.
      if (Number(verdict.hint_strength) > 0) revealHelp(question);
      syncActions(question);

      const next = question.querySelector('[data-runner-next]');
      if (next) next.focus();
    });
  }

  /*
   * One more go at a missed question, before the right answer is shown. What the learner
   * picked is marked wrong and taken out of the running, but the other options stay live
   * and a typed answer is cleared and left editable, so the second try is a real attempt
   * rather than a copy. The answer and the word card wait for a second miss.
   */
  function offerSecondTry(question, submission) {
    if (question.dataset.kind === 'choice') {
      flagOption(optionLabel(question, submission.answer), 'wrong');
      const chosen = question.querySelector('input[type="radio"]:checked');
      if (chosen) chosen.disabled = true;
    } else {
      const input = question.querySelector('.runner-answer__input');
      if (input) {
        input.classList.add('is-wrong');
        input.value = '';
        input.focus();
      }
      resetSatzbau(question);
    }

    const note = question.querySelector('[data-runner-second-try]');
    if (note) note.hidden = false;
  }

  function advance(question) {
    const position = questions.indexOf(question);
    if (position === total - 1) {
      showResults();
      return;
    }
    apply(position + 1, { focus: true });
  }

  function setText(scope, selector, value) {
    const element = scope.querySelector(selector);
    if (element) element.textContent = String(value);
  }

  function showResults() {
    if (!results) return;

    const correct = state.filter((entry) => entry.outcome === 'correct').length;
    setText(results, '[data-results-correct]', correct);
    setText(results, '[data-results-total]', scoreable);

    const accuracyLine = results.querySelector('[data-results-accuracy-line]');
    if (accuracyLine) {
      accuracyLine.hidden = scoreable === 0;
      if (scoreable > 0) {
        setText(results, '[data-results-accuracy]', Math.round((correct / scoreable) * 100));
      }
    }

    const perfect = results.querySelector('[data-results-perfect]');
    if (perfect) perfect.hidden = !(scoreable > 0 && correct === scoreable);

    const missed = questions
      .map((question, position) => ({ question, position }))
      .filter((entry) => state[entry.position].outcome === 'wrong');

    const review = results.querySelector('[data-results-review]');
    const list = results.querySelector('[data-results-list]');
    if (review && list) {
      list.textContent = '';
      missed.forEach(({ question, position }) => {
        const item = document.createElement('li');
        const button = document.createElement('button');
        button.type = 'button';
        button.className = 'runner-review__link';
        button.dataset.reviewIndex = String(position);
        const eyebrow = question.querySelector('.runner-q__eyebrow');
        const prompt = question.querySelector('.runner-q__prompt');
        button.textContent = `${eyebrow ? eyebrow.textContent.trim() : ''} — ${prompt ? prompt.textContent.trim() : ''}`;
        item.appendChild(button);

        // What the learner answered, the answer they should have given, and the stored
        // explanation: the three things a review list exists for, all from the
        // submission's own response and kept per question as it was answered. The right
        // answer is not on this page, so a reload could not reconstruct it.
        const entry = state[position];
        if (entry.answerText) item.appendChild(reviewLine('پاسخ تو:', entry.answerText));
        if (entry.verdict && entry.verdict.expected.length > 0) {
          item.appendChild(reviewLine('پاسخ درست:', entry.verdict.expected.join(' · ')));
        }
        if (entry.verdict && entry.verdict.explanation) {
          const why = document.createElement('p');
          why.className = 'runner-review__why';
          why.textContent = entry.verdict.explanation;
          item.appendChild(why);
        }

        list.appendChild(item);
      });
      review.hidden = missed.length === 0;
    }

    showWeakWords(results);

    questions.forEach((question) => question.classList.remove('is-active'));
    if (progress) progress.hidden = true;
    results.hidden = false;
    results.focus();
  }

  /*
   * The words behind the missed questions, each named once even when two questions tested
   * the same word. A word the learner has now missed enough times to count as repeatedly
   * wrong is flagged with the same wording the lesson rows use (the server decides that,
   * so the threshold is never stated here). The block stays absent when the missed
   * questions tested no word (a reading or grammar question), which is a normal exercise.
   */
  function showWeakWords(results) {
    const block = results.querySelector('[data-results-weak]');
    const list = results.querySelector('[data-results-weak-list]');
    if (!block || !list) return;

    list.textContent = '';

    const seen = [];
    const words = [];
    questions.forEach((question, position) => {
      const entry = state[position];
      if (entry.outcome !== 'wrong' || !entry.word) return;
      if (seen.indexOf(entry.word.id) !== -1) return;
      seen.push(entry.word.id);
      words.push(entry.word);
    });

    words.forEach((word) => {
      const item = document.createElement('li');
      item.className = 'runner-weak__row';

      const link = document.createElement('a');
      link.className = 'runner-weak__term';
      link.href = word.url;
      link.lang = 'de';
      link.dir = 'ltr';
      link.textContent = word.article ? `${word.article} ${word.word}` : word.word;
      item.appendChild(link);

      const meaning = document.createElement('span');
      meaning.className = 'runner-weak__meaning';
      meaning.textContent = word.meaning_fa;
      item.appendChild(meaning);

      if (word.repeated) {
        const flag = document.createElement('span');
        flag.className = 'runner-weak__flag';
        flag.textContent = 'اشتباه پرتکرار';
        item.appendChild(flag);
      } else {
        const count = document.createElement('span');
        count.className = 'runner-weak__count';
        count.textContent = `غلط: ${word.wrong_count}`;
        item.appendChild(count);
      }

      list.appendChild(item);
    });

    block.hidden = words.length === 0;
  }

  /** One "label: value" line in the review list, with the German value kept LTR. */
  function reviewLine(label, value) {
    const line = document.createElement('p');
    line.className = 'runner-review__line';
    line.textContent = `${label} `;

    const strong = document.createElement('span');
    strong.className = 'runner-review__value';
    strong.lang = 'de';
    strong.dir = 'ltr';
    strong.textContent = value;
    line.appendChild(strong);

    return line;
  }

  /* ----------------------------------------------------------- satzbau lab ---- */

  function updateSatzbauZone(question) {
    const playground = question.querySelector('[data-satzbau-playground]');
    if (!playground) return;

    const zone = playground.querySelector('[data-satzbau-zone]');
    const placeholder = playground.querySelector('[data-satzbau-placeholder]');
    const input = question.querySelector('.runner-answer__input');
    if (!zone || !input) return;

    const chips = zone.querySelectorAll('.satzbau-chip');
    if (placeholder) {
      placeholder.hidden = chips.length > 0;
    }

    const words = [];
    chips.forEach((chip, pos) => {
      words.push(chip.dataset.satzbauToken || chip.textContent.trim());
      if (pos === 1) {
        chip.classList.add('is-verb-pos');
      } else {
        chip.classList.remove('is-verb-pos');
      }
    });

    input.value = words.join(' ');
  }

  function resetSatzbau(question) {
    const playground = question.querySelector('[data-satzbau-playground]');
    if (!playground) return;

    const zone = playground.querySelector('[data-satzbau-zone]');
    const bank = playground.querySelector('[data-satzbau-bank]');
    const placeholder = playground.querySelector('[data-satzbau-placeholder]');
    const resetBtn = playground.querySelector('[data-satzbau-reset]');

    if (zone) {
      zone.querySelectorAll('.satzbau-chip').forEach((chip) => chip.remove());
    }
    if (placeholder) {
      placeholder.hidden = false;
    }
    if (bank) {
      bank.querySelectorAll('[data-satzbau-token]').forEach((chip) => {
        chip.disabled = false;
        chip.classList.remove('is-used');
      });
    }
    if (resetBtn) {
      resetBtn.disabled = false;
    }

    const input = question.querySelector('.runner-answer__input');
    if (input && !input.readOnly) {
      input.value = '';
    }
  }

  function disableSatzbau(question) {
    const playground = question.querySelector('[data-satzbau-playground]');
    if (!playground) return;

    playground.querySelectorAll('button').forEach((btn) => {
      btn.disabled = true;
    });
  }

  function initSatzbau(question) {
    const playground = question.querySelector('[data-satzbau-playground]');
    if (!playground || playground.dataset.satzbauReady) return;
    playground.dataset.satzbauReady = 'true';

    const zone = playground.querySelector('[data-satzbau-zone]');
    const bank = playground.querySelector('[data-satzbau-bank]');
    const resetBtn = playground.querySelector('[data-satzbau-reset]');
    const input = question.querySelector('.runner-answer__input');

    if (!zone || !bank) return;

    bank.addEventListener('click', (event) => {
      const chip = event.target.closest('[data-satzbau-token]');
      if (!chip || chip.disabled) return;
      if (input && input.readOnly) return;

      const token = chip.dataset.satzbauToken || chip.textContent.trim();
      chip.disabled = true;
      chip.classList.add('is-used');

      const zoneChip = document.createElement('button');
      zoneChip.type = 'button';
      zoneChip.className = 'satzbau-chip satzbau-chip--placed';
      zoneChip.dataset.satzbauToken = token;
      zoneChip.textContent = token;

      zoneChip.addEventListener('click', () => {
        if (input && input.readOnly) return;
        zoneChip.remove();
        chip.disabled = false;
        chip.classList.remove('is-used');
        updateSatzbauZone(question);
      });

      zone.appendChild(zoneChip);
      updateSatzbauZone(question);
    });

    if (resetBtn) {
      resetBtn.addEventListener('click', () => {
        if (input && input.readOnly) return;
        resetSatzbau(question);
      });
    }
  }

  function reset() {
    state.forEach((entry, position) => {
      state[position] = { submitted: false, outcome: null, attempts: 0 };
    });

    questions.forEach((question) => {
      question.querySelectorAll('input[type="radio"]').forEach((input) => {
        input.disabled = false;
        input.checked = false;
      });
      question.querySelectorAll('.runner-option').forEach((label) => {
        label.classList.remove('is-correct', 'is-wrong', 'is-selected');
      });
      question.querySelectorAll('[data-flag]').forEach((flag) => {
        flag.hidden = true;
      });
      question.querySelectorAll('[data-result], [data-expected], [data-explanation], [data-runner-word-card], [data-runner-second-try]').forEach((element) => {
        element.hidden = true;
      });

      const wordCard = question.querySelector('[data-runner-word-card]');
      if (wordCard) wordCard.textContent = '';

      const input = question.querySelector('.runner-answer__input');
      if (input) {
        input.value = '';
        input.readOnly = false;
        input.classList.remove('is-correct', 'is-wrong');
      }
      hideHint(question);

      const helpText = question.querySelector('[data-runner-help]');
      if (helpText) {
        helpText.textContent = '';
        helpText.hidden = true;
      }
      resetSatzbau(question);
    });

    const weak = results ? results.querySelector('[data-results-weak]') : null;
    if (weak) weak.hidden = true;

    apply(0, { focus: true });
  }

  /* --------------------------------------------------------------- events ---- */

  runner.addEventListener('click', (event) => {
    const check = event.target.closest('[data-runner-check]');
    if (check) {
      submit(check.closest('[data-question]'));
      return;
    }

    const next = event.target.closest('[data-runner-next]');
    if (next) {
      advance(next.closest('[data-question]'));
      return;
    }

    const previous = event.target.closest('[data-runner-prev]');
    if (previous) {
      apply(questions.indexOf(previous.closest('[data-question]')) - 1, { focus: true });
      return;
    }

    const hintButton = event.target.closest('[data-runner-hint-request]');
    if (hintButton) {
      requestHint(hintButton.closest('[data-question]'));
      return;
    }

    const review = event.target.closest('[data-review-index]');
    if (review) {
      apply(Number(review.dataset.reviewIndex), { focus: true });
      return;
    }

    if (event.target.closest('[data-runner-retry]')) reset();
  });

  // The selected state is drawn from `:has(input:checked)` in CSS and from this class,
  // so it survives a browser that does not support `:has`.
  runner.addEventListener('change', (event) => {
    const input = event.target.closest('input[type="radio"]');
    if (!input) return;
    const question = input.closest('[data-question]');
    question.querySelectorAll('.runner-option').forEach((label) => {
      const radio = label.querySelector('input[type="radio"]');
      label.classList.toggle('is-selected', Boolean(radio && radio.checked));
    });
  });

  /* The keyboard: Enter submits, and 1–9 pick an option.
   *
   * Enter after typing is what a learner already expects. The digits are the faster half
   * of a multiple-choice question: the option's own number is the key, so a learner who is
   * reading with the keyboard never has to reach for the mouse — and Enter right after a
   * digit sends the answer, which makes "2, Enter" the whole interaction.
   *
   * Both are listened for on the document, because neither is useful if it only works while
   * the focus happens to be inside the widget — the page is a lesson page and the exercise
   * sits in the middle of it. Nothing else on the page may lose its keyboard to this:
   *   * a learner typing an answer keeps their digits (the text input is left alone);
   *   * if another control on the page holds the focus, the keys are not ours, with the one
   *     exception of the page body, which is what is focused before the learner touches
   *     anything — the case where the shortcuts have to work.
   */
  document.addEventListener('keydown', (event) => {
    const typing = event.target.closest ? event.target.closest('.runner-answer__input') : null;

    if (/^[1-9]$/.test(event.key)) {
      if (typing) return;

      const focused = document.activeElement;
      if (focused && focused !== document.body && !runner.contains(focused)) return;

      const question = questions[index];
      if (!question) return;

      const options = question.querySelectorAll('.runner-option input[type="radio"]');
      const chosen = options[Number(event.key) - 1];
      if (!chosen || chosen.disabled) return;

      event.preventDefault();
      chosen.checked = true;
      // The `change` event is what draws the selected state (the same listener the mouse
      // goes through), so the keyboard and the mouse cannot end up looking different.
      chosen.dispatchEvent(new Event('change', { bubbles: true }));
      return;
    }

    if (event.key !== 'Enter') return;

    const question = typing ? typing.closest('[data-question]') : questions[index];
    if (!question) return;

    event.preventDefault();
    submit(question);
  });

  // A question that already owes a hint shows its button from the start; the button was
  // rendered for every question, because a mistake in this sitting can earn one later.
  questions.forEach((question) => {
    if (Number(question.dataset.hintStrength) > 0) revealHelp(question);
    initSatzbau(question);
  });

  apply(0, { focus: false });
})();
