/* Tactile Exercise Runner Interactive Engine - Velingo */
(function() {
  'use strict';

  // 1. Theme Synchronization
  var THEME_STORAGE_KEY = 'bm_theme_preference';
  var root = document.documentElement;
  var themeMiniBtn = document.getElementById('themeMiniBtn');

  function getPreferredTheme() {
    try {
      var stored = localStorage.getItem(THEME_STORAGE_KEY);
      if (stored === 'light' || stored === 'dark') {
        return stored;
      }
    } catch (e) {}
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  }

  function applyTheme(theme) {
    root.setAttribute('data-theme', theme);
    if (themeMiniBtn) {
      themeMiniBtn.textContent = (theme === 'dark') ? '☀️' : '🌙';
    }
  }

  applyTheme(getPreferredTheme());

  if (themeMiniBtn) {
    themeMiniBtn.addEventListener('click', function() {
      var current = root.getAttribute('data-theme') || 'light';
      var next = (current === 'dark') ? 'light' : 'dark';
      applyTheme(next);
      try {
        localStorage.setItem(THEME_STORAGE_KEY, next);
      } catch (e) {}
    });
  }

  // 2. DOM Elements
  var assemblyZone = document.getElementById('assemblyZone');
  var placeholder = document.getElementById('assemblyPlaceholder');
  var wordBank = document.getElementById('wordBank');
  var submitBtn = document.getElementById('submitActionBtn');
  var clearBtn = document.getElementById('clearAssemblyBtn');
  var questionCard = document.getElementById('questionCard');
  var feedbackDrawer = document.getElementById('feedbackDrawer');
  var feedbackIcon = document.getElementById('feedbackIcon');
  var feedbackHeading = document.getElementById('feedbackHeading');
  var feedbackExplanation = document.getElementById('feedbackExplanation');
  var progressFill = document.getElementById('springProgressFill');
  var runnerStats = document.getElementById('runnerStats');

  if (!assemblyZone || !wordBank || !submitBtn) {
    return;
  }

  var assembledWords = [];
  var isAnswered = false;

  // Read target valid sequences from data attribute or fallback
  var correctSequences = [
    ['Ich', 'kaufe', 'heute', 'im Supermarkt', 'ein'],
    ['Heute', 'kaufe', 'ich', 'im Supermarkt', 'ein']
  ];

  if (questionCard && questionCard.getAttribute('data-correct-sequences')) {
    try {
      correctSequences = JSON.parse(questionCard.getAttribute('data-correct-sequences'));
    } catch (err) {}
  }

  function updateUIState() {
    if (assembledWords.length > 0) {
      assemblyZone.classList.add('has-items');
      if (placeholder) placeholder.style.display = 'none';
      if (!isAnswered) submitBtn.disabled = false;
    } else {
      assemblyZone.classList.remove('has-items');
      if (placeholder) placeholder.style.display = 'block';
      submitBtn.disabled = true;
    }
  }

  function renderAssembledChips() {
    var existingChips = assemblyZone.querySelectorAll('.assembled-chip');
    existingChips.forEach(function(c) { c.remove(); });

    assembledWords.forEach(function(item, index) {
      var chipEl = document.createElement('button');
      chipEl.type = 'button';
      chipEl.className = 'assembled-chip';
      chipEl.setAttribute('aria-label', 'حذف کلمه ' + item.word);
      chipEl.innerHTML = '<span class="de" dir="ltr" lang="de">' + item.word + '</span> <span style="font-size:11px;opacity:0.7" aria-hidden="true">✕</span>';

      chipEl.addEventListener('click', function() {
        if (isAnswered) return;
        item.bankBtn.classList.remove('is-used');
        assembledWords.splice(index, 1);
        renderAssembledChips();
        updateUIState();
      });

      assemblyZone.appendChild(chipEl);
    });

    updateUIState();
  }

  // Word bank button clicks
  wordBank.querySelectorAll('.tactile-chip').forEach(function(btn) {
    btn.addEventListener('click', function() {
      if (isAnswered || btn.classList.contains('is-used')) return;
      var word = btn.getAttribute('data-word');
      btn.classList.add('is-used');
      assembledWords.push({ word: word, bankBtn: btn });
      renderAssembledChips();
    });
  });

  // Clear button
  if (clearBtn) {
    clearBtn.addEventListener('click', function() {
      if (isAnswered) return;
      assembledWords.forEach(function(item) {
        item.bankBtn.classList.remove('is-used');
      });
      assembledWords = [];
      renderAssembledChips();
      resetFeedback();
    });
  }

  function resetFeedback() {
    if (feedbackDrawer) {
      feedbackDrawer.style.display = 'none';
      feedbackDrawer.className = 'feedback-drawer';
    }
    if (questionCard) {
      questionCard.classList.remove('is-correct-pulse', 'is-wrong-shake');
    }
  }

  // 3. Validation & Answer Evaluation
  submitBtn.addEventListener('click', function() {
    var mode = submitBtn.getAttribute('data-mode');
    if (mode === 'next') {
      isAnswered = false;
      submitBtn.removeAttribute('data-mode');
      submitBtn.innerHTML = '<span>بررسی پاسخ</span> <span>⚡</span>';
      resetFeedback();
      assembledWords.forEach(function(item) { item.bankBtn.classList.remove('is-used'); });
      assembledWords = [];
      renderAssembledChips();
      return;
    }

    if (mode === 'retry') {
      isAnswered = false;
      submitBtn.removeAttribute('data-mode');
      submitBtn.innerHTML = '<span>بررسی پاسخ</span> <span>⚡</span>';
      resetFeedback();
      return;
    }

    if (assembledWords.length === 0) return;

    var currentSeq = assembledWords.map(function(item) { return item.word.trim(); });
    var isCorrect = correctSequences.some(function(seq) {
      if (seq.length !== currentSeq.length) return false;
      return seq.every(function(val, idx) {
        return val.toLowerCase() === currentSeq[idx].toLowerCase();
      });
    });

    resetFeedback();

    if (isCorrect) {
      isAnswered = true;
      if (questionCard) questionCard.classList.add('is-correct-pulse');
      if (feedbackDrawer) {
        feedbackDrawer.className = 'feedback-drawer is-correct';
        feedbackDrawer.style.display = 'flex';
      }
      if (feedbackIcon) feedbackIcon.textContent = '✅';
      if (feedbackHeading) feedbackHeading.textContent = 'کاملاً درست و دقیق!';
      if (feedbackExplanation) {
        feedbackExplanation.innerHTML = 'عالی بود! در جمله خبری حال ساده، بخش صرف‌شده فعل در جایگاه دوم (<span class="de" dir="ltr" lang="de">kaufe</span>) و پیشوند جداشدنی (<span class="de" dir="ltr" lang="de">ein</span>) در انتهای جمله قرار می‌گیرد.';
      }

      // Update spring progress bar
      if (progressFill) progressFill.style.width = '40%';
      if (runnerStats) {
        runnerStats.innerHTML = '<span class="prompt-badge">🔥 ۴ استریک</span> <span>سوال ۴ از ۱۰</span> <span>·</span> <span>۴۰٪</span>';
      }

      submitBtn.setAttribute('data-mode', 'next');
      submitBtn.innerHTML = '<span>سوال بعدی</span> <span aria-hidden="true">→</span>';
      submitBtn.disabled = false;
    } else {
      if (questionCard) questionCard.classList.add('is-wrong-shake');
      if (feedbackDrawer) {
        feedbackDrawer.className = 'feedback-drawer is-wrong';
        feedbackDrawer.style.display = 'flex';
      }
      if (feedbackIcon) feedbackIcon.textContent = '❌';
      if (feedbackHeading) feedbackHeading.textContent = 'جایگاه قطعات نیاز به اصلاح دارد';
      if (feedbackExplanation) {
        feedbackExplanation.innerHTML = 'توجه کنید: در زبان آلمانی جایگاه دوم همیشه متعلق به فعل صرف‌شده (<span class="de" dir="ltr" lang="de">kaufe</span>) است و پیشوند جداشدنی (<span class="de" dir="ltr" lang="de">ein</span>) باید دقیقاً در آخرین جایگاه جمله قرار گیرد. کلمه <span class="de" dir="ltr" lang="de">kaufen</span> شکل مصدر است و اینجا صرف نمی‌شود.';
      }

      submitBtn.setAttribute('data-mode', 'retry');
      submitBtn.innerHTML = '<span>تلاش مجدد</span> <span>🔄</span>';
      submitBtn.disabled = false;
    }
  });
})();
