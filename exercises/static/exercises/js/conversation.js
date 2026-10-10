/*
 * conversation.js — the lesson's own dialogue, played one line at a time.
 *
 * The server rendered every turn of the lesson's dialogue (exercises/conversation.py); this
 * file reveals them in order. The partner's lines arrive on their own, with a short beat
 * between them so a scene reads as a conversation rather than a wall of text. The learner's
 * own lines wait for them: they write their answer in their own words, then the line the
 * lesson actually uses is revealed and they say whether they were close.
 *
 * There is no request in this file. A spoken turn cannot be graded and the lesson's line is
 * already public lesson content, so nothing is sent, recorded or stored — the same limit
 * the speaking node keeps. What the learner picks at the end is a tally for the summary on
 * this page and nothing else.
 */
(() => {
  'use strict';

  const chat = document.querySelector('[data-chat]');
  if (!chat) return;

  const turns = Array.from(chat.querySelectorAll('[data-turn]'));
  if (!turns.length) return;

  const summary = chat.querySelector('[data-chat-summary]');
  const okOut = chat.querySelector('[data-chat-ok]');
  const noOut = chat.querySelector('[data-chat-no]');

  // How many of the learner's own lines they judged close or not, for the closing summary.
  let ok = 0;
  let no = 0;
  let cursor = 0;

  function finish() {
    if (!summary) return;

    if (okOut) okOut.textContent = String(ok);
    if (noOut) noOut.textContent = String(no);

    summary.hidden = false;
    summary.scrollIntoView({ block: 'center' });
    summary.focus();
  }

  function next() {
    if (cursor >= turns.length) {
      finish();
      return;
    }

    const turn = turns[cursor];
    cursor += 1;
    turn.classList.add('is-shown');
    turn.scrollIntoView({ block: 'center' });

    if (turn.hasAttribute('data-mine')) {
      const input = turn.querySelector('[data-answer]');
      if (input) input.focus();
      return;
    }

    // The partner keeps talking, one line at a time.
    window.setTimeout(next, 600);
  }

  // The learner's answer becomes their own bubble, and the lesson's line is shown beside it
  // so they can judge the difference themselves.
  function send(turn) {
    const input = turn.querySelector('[data-answer]');
    const typed = turn.querySelector('[data-typed]');
    const compose = turn.querySelector('[data-compose]');
    const model = turn.querySelector('[data-model]');
    if (!input || !typed || !compose || !model) return;

    const text = input.value.trim();
    if (!text) {
      input.focus();
      return;
    }

    const branches = turn.querySelector('[data-branches]');
    if (branches) branches.hidden = true;

    typed.textContent = text;
    typed.hidden = false;
    compose.hidden = true;
    model.hidden = false;

    const first = model.querySelector('[data-check]');
    if (first) first.focus();
  }

  function pickBranch(turn, button) {
    const typed = turn.querySelector('[data-typed]');
    const compose = turn.querySelector('[data-compose]');
    const branches = turn.querySelector('[data-branches]');
    const model = turn.querySelector('[data-model]');
    const toast = turn.querySelector('[data-etiquette-toast]');
    const toastMsg = turn.querySelector('[data-etiquette-msg]');

    const text = button.dataset.branchText || button.textContent.trim();
    const note = button.dataset.branchNote;

    if (typed) {
      typed.textContent = text;
      typed.hidden = false;
    }
    if (compose) compose.hidden = true;
    if (branches) branches.hidden = true;

    if (toast && toastMsg && note) {
      toastMsg.textContent = note;
      toast.hidden = false;
    }

    if (model) {
      model.hidden = false;
      const first = model.querySelector('[data-check]');
      if (first) first.focus();
    }
  }

  function check(turn, verdict) {
    if (verdict === 'ok') ok += 1;
    else no += 1;

    const buttons = turn.querySelector('.chat-model__check');
    if (buttons) buttons.hidden = true;

    next();
  }

  chat.addEventListener('click', (event) => {
    const branchButton = event.target.closest('[data-branch-btn]');
    if (branchButton) {
      pickBranch(branchButton.closest('[data-turn]'), branchButton);
      return;
    }

    const sendButton = event.target.closest('[data-send]');
    if (sendButton) {
      send(sendButton.closest('[data-turn]'));
      return;
    }

    const checkButton = event.target.closest('[data-check]');
    if (checkButton) {
      check(checkButton.closest('[data-turn]'), checkButton.dataset.check);
    }
  });

  chat.addEventListener('keydown', (event) => {
    if (event.key !== 'Enter') return;

    const input = event.target.closest('[data-answer]');
    if (!input) return;

    event.preventDefault();
    send(input.closest('[data-turn]'));
  });

  next();
})();
