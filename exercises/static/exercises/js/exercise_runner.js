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

  const questions = Array.from(runner.querySelectorAll('[data-question]'));
  if (!questions.length) return;

  const total = questions.length;
  const scoreable = questions.filter((question) => question.dataset.kind !== 'none').length;

  const progress = runner.querySelector('[data-runner-progress]');
  const bar = runner.querySelector('[data-runner-bar]');
  const fill = runner.querySelector('[data-runner-fill]');
  const results = runner.querySelector('[data-runner-results]');

  const state = questions.map(() => ({ submitted: false, outcome: null }));
  let index = 0;

  /* ------------------------------------------------------------ submission ---- */

  // Where the answers go, and the token the POST needs.
  const submitUrl = runner.dataset.submitUrl || '';
  const csrfToken = document.querySelector('meta[name="csrf-token"]');

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
    input.classList.add(correct ? 'is-correct' : 'is-wrong');
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

  function sendSubmission(question, submission) {
    return fetch(submitUrl, {
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

    hideHint(question);
    setChecking(question, true);

    sendSubmission(question, submission).then((verdict) => {
      setChecking(question, false);

      if (!verdict) {
        showHint(question, 'ارتباط با سرور برقرار نشد؛ دوباره تلاش کن.');
        return;
      }

      state[position] = { submitted: true, outcome: verdict.correct ? 'correct' : 'wrong' };
      if (question.dataset.kind === 'choice') markOptions(question, submission.answer, verdict);
      else markTyped(question, verdict.correct);
      showFeedback(question, verdict);
      syncActions(question);

      const next = question.querySelector('[data-runner-next]');
      if (next) next.focus();
    });
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
        list.appendChild(item);
      });
      review.hidden = missed.length === 0;
    }

    questions.forEach((question) => question.classList.remove('is-active'));
    if (progress) progress.hidden = true;
    results.hidden = false;
    results.focus();
  }

  function reset() {
    state.forEach((entry, position) => {
      state[position] = { submitted: false, outcome: null };
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
      question.querySelectorAll('[data-result], [data-expected], [data-explanation]').forEach((element) => {
        element.hidden = true;
      });

      const input = question.querySelector('.runner-answer__input');
      if (input) {
        input.value = '';
        input.readOnly = false;
        input.classList.remove('is-correct', 'is-wrong');
      }
      hideHint(question);
    });

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

  // Enter is what a learner expects to do after typing an answer.
  runner.addEventListener('keydown', (event) => {
    if (event.key !== 'Enter') return;
    const input = event.target.closest('.runner-answer__input');
    if (!input) return;
    const question = input.closest('[data-question]');
    if (!question) return;
    event.preventDefault();
    submit(question);
  });

  apply(0, { focus: false });
})();
