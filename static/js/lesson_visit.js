/* Records that this lesson was opened.
 *
 * One line of real behaviour on top of the progress.js abstraction, so the
 * dashboard has genuine data to build "continue where you left off" from.
 * The lesson id comes from the markup (an open lesson, a locked item, or a
 * guarded step) and nothing is sent to the server: this is the temporary
 * localStorage layer that a LessonProgress model will replace.
 */
(() => {
  'use strict';

  const lesson = document.querySelector('[data-lesson-id]');
  if (!lesson || !window.GamProgress) return;

  window.GamProgress.markVisited(lesson.dataset.lessonId);
})();
