/* Learning progress: one interface, two places it can come from.
 *
 * A signed-in learner has real LessonProgress rows, so the server is the source of
 * truth and the page ships them as a "progress-state" JSON script. Everyone else
 * only has this browser, so localStorage works exactly as before. The rest of the
 * product cannot tell the difference: the dashboard, the learning path and the
 * lesson page all read the same read() and summary() from here.
 *
 * Storage key (browser-only mode): gam.progress.v1
 * Shape: { version: 1, lastLessonId: number|null,
 *          lessons: { "<id>": { status, updatedAt } },
 *          positions: { "<id>": stepIndex } }
 *   status: "started" (lesson opened) | "completed"
 * `positions` remembers which step of a lesson the learner was on; it is optional in
 * stored data and defaults to {}. Server-backed state has no `positions` — the lesson
 * page asks the server where to resume instead (see data-resume-step).
 *
 * Public API (window.GamProgress):
 *   available            -> false when localStorage is blocked (private mode)
 *   serverBacked         -> true when the page shipped the learner's real progress
 *   read()               -> full state, always a valid object
 *   guestRead()          -> what this browser remembers, even when read() is server-backed
 *                           (the sign-up import asks for exactly this — see
 *                           static/js/progress_import.js)
 *   markVisited(id)      -> record "started"
 *   markCompleted(id)    -> record "completed" (never downgraded back to started)
 *   setLessonPosition(id, index) / lessonPosition(id) -> step within a lesson
 *   summary()            -> { started, completed, lastLessonId, lastVisitedAt }
 *   clear()              -> forget everything on this device
 *
 * Writes go to localStorage in browser-only mode. In server-backed mode they only
 * update the copy in memory, because saving belongs to the lesson page, which posts
 * each step to lessons:lesson-progress (lessons/static/lessons/js/lesson_steps.js).
 * One writer per fact, so the two can never disagree.
 */
(() => {
  'use strict';

  const KEY = 'gam.progress.v1';
  const VERSION = 1;
  const STARTED = 'started';
  const COMPLETED = 'completed';

  const empty = () => ({ version: VERSION, lastLessonId: null, lessons: {}, positions: {} });

  // Probe once: private mode and some embedded browsers throw on access.
  const available = (() => {
    try {
      const probe = '__gam_probe__';
      window.localStorage.setItem(probe, '1');
      window.localStorage.removeItem(probe);
      return true;
    } catch (_) {
      return false;
    }
  })();

  /* ------------------------------------------- where the state comes from ----
   * The server's answer, when the page provides one. Only a signed-in learner gets
   * it. The `source` marker is checked on purpose: a page that shipped `null` by
   * accident must not be taken for an empty history, because that would silently
   * hide everything already in localStorage.
   */
  function readServerState() {
    const element = document.getElementById('progress-state');
    if (!element) return null;

    try {
      const parsed = JSON.parse(element.textContent);
      if (!parsed || parsed.source !== 'server') return null;
      return {
        version: VERSION,
        lastLessonId: Number.isInteger(parsed.lastLessonId) ? parsed.lastLessonId : null,
        lessons: parsed.lessons && typeof parsed.lessons === 'object' ? parsed.lessons : {},
        positions: {},
      };
    } catch (_) {
      return null;
    }
  }

  const serverState = readServerState();

  /* What this browser itself remembers, read the same way whether or not the page is
   * server-backed. read() prefers the server's answer; the sign-up import needs the
   * browser's own memory *while* the server is the source of truth, which is the only
   * moment the two can be compared — so the read is split rather than rewritten. */
  function readLocal() {
    if (!available) return empty();
    try {
      const raw = window.localStorage.getItem(KEY);
      if (!raw) return empty();
      const parsed = JSON.parse(raw);
      if (!parsed || typeof parsed !== 'object' || parsed.version !== VERSION) return empty();
      const lessons = parsed.lessons && typeof parsed.lessons === 'object' ? parsed.lessons : {};
      const positions = parsed.positions && typeof parsed.positions === 'object' ? parsed.positions : {};
      const lastLessonId = Number.isInteger(parsed.lastLessonId) ? parsed.lastLessonId : null;
      return { version: VERSION, lastLessonId, lessons, positions };
    } catch (_) {
      return empty();
    }
  }

  function read() {
    if (serverState) return serverState;
    return readLocal();
  }

  function write(state) {
    if (!available) return false;
    try {
      window.localStorage.setItem(KEY, JSON.stringify(state));
      return true;
    } catch (_) {
      return false;
    }
  }

  function mark(id, status) {
    const lessonId = Number(id);
    if (!Number.isInteger(lessonId) || lessonId <= 0) return read();

    const state = read();
    const previous = state.lessons[lessonId];
    // Opening a finished lesson again must not undo its completion.
    const nextStatus = previous && previous.status === COMPLETED ? COMPLETED : status;

    state.lessons[lessonId] = { status: nextStatus, updatedAt: new Date().toISOString() };
    state.lastLessonId = lessonId;
    if (!serverState) write(state);
    return state;
  }

  window.GamProgress = {
    available,
    serverBacked: serverState !== null,
    STARTED,
    COMPLETED,
    read,
    guestRead: readLocal,
    markVisited: (id) => mark(id, STARTED),
    markCompleted: (id) => mark(id, COMPLETED),
    /** Remember which step of a lesson the learner was on. */
    setLessonPosition(id, index) {
      const lessonId = Number(id);
      const step = Number(index);
      if (!Number.isInteger(lessonId) || lessonId <= 0) return read();
      if (!Number.isInteger(step) || step < 0) return read();
      // Server-backed: the lesson page has already told the server. Nothing to keep.
      if (serverState) return read();
      const state = read();
      state.positions[lessonId] = step;
      write(state);
      return state;
    },
    /** The remembered step for a lesson, or null when there is none. */
    lessonPosition(id) {
      const step = read().positions[Number(id)];
      return Number.isInteger(step) ? step : null;
    },
    summary() {
      const state = read();
      const entries = Object.entries(state.lessons);
      const last = state.lastLessonId != null ? state.lessons[state.lastLessonId] : null;
      return {
        started: entries.length,
        completed: entries.filter(([, value]) => value && value.status === COMPLETED).length,
        lastLessonId: state.lastLessonId,
        lastVisitedAt: last ? last.updatedAt : null,
      };
    },
    clear() {
      if (!available) return;
      try {
        window.localStorage.removeItem(KEY);
      } catch (_) {
        /* nothing else to do */
      }
    },
  };
})();
