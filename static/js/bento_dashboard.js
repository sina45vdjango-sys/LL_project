/* Bento Dashboard Interactive Logic - Velingo */
(function() {
  'use strict';

  // 1. Toast Notification System
  var toastBox = document.getElementById('toastBox');
  var toastIcon = document.getElementById('toastIcon');
  var toastMessage = document.getElementById('toastMessage');
  var toastTimeout = null;

  function showToast(msg, icon) {
    if (!toastBox) return;
    if (toastTimeout) clearTimeout(toastTimeout);
    if (toastIcon) toastIcon.textContent = icon || '⚡';
    if (toastMessage) toastMessage.textContent = msg;
    toastBox.classList.add('is-active');
    toastTimeout = setTimeout(function() {
      toastBox.classList.remove('is-active');
    }, 2600);
  }

  window.showBentoToast = showToast;

  // 1.1 Theme Engine
  var THEME_STORAGE_KEY = 'bm_theme_preference';
  var root = document.documentElement;
  var themeBtn = document.getElementById('themeToggleBtn');
  var themeIcon = document.getElementById('themeIcon');
  var themeLabel = document.getElementById('themeLabel');

  function applyTheme(theme) {
    root.setAttribute('data-theme', theme);
    if (themeIcon) {
      themeIcon.textContent = theme === 'dark' ? '☀️' : '🌙';
    }
    if (themeLabel) {
      themeLabel.textContent = theme === 'dark' ? 'پوسته روشن' : 'پوسته تاریک';
    }
  }

  try {
    var storedPref = localStorage.getItem(THEME_STORAGE_KEY);
    if (storedPref === 'light' || storedPref === 'dark') {
      applyTheme(storedPref);
    }
  } catch (e) {}

  if (themeBtn) {
    themeBtn.addEventListener('click', function() {
      var current = root.getAttribute('data-theme') || 'light';
      var next = current === 'dark' ? 'light' : 'dark';
      applyTheme(next);
      try {
        localStorage.setItem(THEME_STORAGE_KEY, next);
      } catch (err) {}
      showToast(next === 'dark' ? 'پوسته تاریک فعال شد' : 'پوسته روشن فعال شد', '🎨');
    });
  }

  // 2. Tactile Clicks & Action Feedback
  document.querySelectorAll('.remedy-pill').forEach(function(pill) {
    pill.addEventListener('click', function(e) {
      var titleEl = pill.querySelector('.remedy-pill-title');
      var title = titleEl ? titleEl.textContent.trim() : 'تمرین';
      showToast('آماده‌سازی تمرین ترمیمی: ' + title, '💊');
    });
  });

  document.querySelectorAll('.lab-card').forEach(function(card) {
    card.addEventListener('click', function(e) {
      var titleEl = card.querySelector('.lab-card-title');
      var title = titleEl ? titleEl.textContent.trim() : 'آزمایشگاه';
      showToast('انتقال به ' + title + '...', '🧪');
    });
  });

  // 3. Persian Number Conversion & Gauge Animation
  function toPersianDigits(n) {
    var pNums = ['۰', '۱', '۲', '۳', '۴', '۵', '۶', '۷', '۸', '۹'];
    return String(n).replace(/[0-9]/g, function(d) { return pNums[d]; });
  }

  var gaugeBadge = document.querySelector('.gauge-badge');
  if (gaugeBadge) {
    var target = parseInt(gaugeBadge.getAttribute('data-value') || '0', 10);
    var current = 0;
    var step = function() {
      current += 2;
      if (current >= target) {
        gaugeBadge.textContent = toPersianDigits(target) + '٪';
      } else {
        gaugeBadge.textContent = toPersianDigits(current) + '٪';
        requestAnimationFrame(step);
      }
    };
    requestAnimationFrame(step);
  }
})();
