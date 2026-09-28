/* Lesson status classification — the one place that decides "where am I?".
 *
 * Pure logic, no DOM and no copy: given the lesson list the server rendered and
 * the localStorage state from `progress.js`, it says what each lesson is. Both
 * the dashboard and the learning path read from here, so they can never disagree
 * about which lesson is next.
 *
 * Statuses:
 *   completed  the learner finished it
 *   current    the lesson they last opened, or (if that one is finished) the
 *              first lesson they have not finished yet — the next step
 *   started    opened before, but not the current step
 *   upcoming   not opened, and further along the path than the current lesson
 *   available  not opened, but no further along than the current lesson
 *
 * Public API (window.GamStatus): the status names above plus
 *   resolve(lessons, state) -> { of(id), currentId, total, completed, started,
 *                                finished, percent }
 *
 * `currentId` is null only when the course is finished (or empty).
 */
(() => {
  'use strict';

  const COMPLETED = 'completed';
  const CURRENT = 'current';
  const STARTED = 'started';
  const UPCOMING = 'upcoming';
  const AVAILABLE = 'available';

  function resolve(lessons, state) {
    const list = Array.isArray(lessons) ? lessons : [];
    const source = state && typeof state === 'object' ? state : {};
    const entries = source.lessons && typeof source.lessons === 'object' ? source.lessons : {};
    const lastLessonId = source.lastLessonId;

    const done = (id) => !!entries[id] && entries[id].status === COMPLETED;
    const opened = (id) => !!entries[id];

    // The current step: the last lesson opened if it is unfinished, otherwise the
    // first lesson that has not been finished yet.
    const last = list.find((lesson) => lesson.id === lastLessonId);
    let currentId = null;
    if (last && !done(last.id)) {
      currentId = last.id;
    } else {
      const next = list.find((lesson) => !done(lesson.id));
      currentId = next ? next.id : null;
    }
    const currentIndex = currentId === null ? -1 : list.findIndex((lesson) => lesson.id === currentId);

    const of = (id) => {
      if (done(id)) return COMPLETED;
      if (currentId !== null && Number(id) === currentId) return CURRENT;
      if (opened(id)) return STARTED;
      const index = list.findIndex((lesson) => lesson.id === Number(id));
      return currentIndex >= 0 && index > currentIndex ? UPCOMING : AVAILABLE;
    };

    const total = list.length;
    const completed = list.filter((lesson) => done(lesson.id)).length;
    const started = list.filter((lesson) => opened(lesson.id)).length;

    return {
      of,
      currentId,
      total,
      completed,
      started,
      finished: total > 0 && completed === total,
      percent: total ? Math.round((completed / total) * 100) : 0,
    };
  }

  window.GamStatus = { COMPLETED, CURRENT, STARTED, UPCOMING, AVAILABLE, resolve };
})();
