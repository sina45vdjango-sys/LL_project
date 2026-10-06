# RESCORE.md — the audit's own scorecard, scored again

The same 22 categories and the same 10-point scale as `CONTENT-AND-PRODUCT-AUDIT.md`
("# Scorecard"), so the two tables can be read side by side. A score moves only where this
run changed the specific thing the audit gave as the reason for the old one; the reason
column names that thing. **Nothing was raised because it was worked on** — only because the
named cause is gone, and only where I could check it.

Where a number moved, the evidence is in `REPORT.md`; where it did not, the item is in
`DEFERRED.md` or `OWNER-DECISIONS.md` and is still open.

| Category | Was | Now | The audit's stated reason, and what is true of it now |
|---|---|---|---|
| Product | 5.5 | **6.5** | "A real product exists and works, but its front door and its exam are wrong." Both are addressed: `/` explains itself with the course's own numbers, and the exam is a curated 135-item set in the official shape instead of every drill. Still one course that stops at A1. |
| Business | 2.5 | **2.5** | Untouched. Nothing is sold, measured or contactable. |
| UX | 6.5 | **8.0** | "Login lands on the wrong page; 405 is a blank screen." Both gone, and two more dead ends with them: a visitor's progress now follows them onto their account, and the last lesson is no longer a stop. |
| UI | 7.0 | **7.5** | "Hurt by 9px text and 17px touch rows." The type floor is 12px everywhere and the lesson rows are 44px. The rest of the audit's UI judgement was positive, so this is a repair, not a redesign. |
| First Impression | 3.5 | **7.0** | "A stranger cannot learn what this is or who it is for." A stranger now reads what it is, who it is for, what is inside (1,018 words / 745 exercises / 24 lessons, counted from the database) and one action. Not higher: there is no proof, no sample, no face and no illustration. |
| Learning Experience | 7.0 | **7.5** | "Drills do not match each lesson's own grammar." Half of that is fixed — a lesson is now drilled only on the rules it teaches, and the two review lessons review what the course has reached. The other half, *drills for each lesson's own grammar topics*, does not exist yet. **This is why it is not 9.** |
| Teacher Perspective | 6.5 | **7.0** | "The exam is not a valid assessment; writing is one word at a time." The exam now tests sentences and passages in section shape, with a guard test that locks its composition. Writing is still one word at a time in practice (the exam's SCHREIBEN asks for real sentences). |
| Content | 7.5 | **8.0** | "Exam pool and 2,208 untaught words pull it down." The exam pool is solved; the untaught rows are still there (they are informational — the course is deliberately wider than the exam). Added: the "why" after an answer went from 157 to 3,173 questions. |
| Sales | 1.5 | **1.5** | Untouched. |
| Conversion | 2.0 | **2.0** | Untouched. |
| Retention | 7.0 | **7.5** | "The loop is genuinely habit-forming; no email/nudge outside the app." The loop is intact, a visitor's work survives signup, and the course's end now offers the three real next steps. The nudge outside the app is still absent (it needs the email backend). |
| Technical Architecture | 8.0 | **8.5** | "Clean seams; only the exam-pool coupling hurts." That coupling is gone: which exam section a question belongs to is a property of the row, read from a versioned data file, so the exam can no longer be changed by adding a drill. |
| Code Quality | 8.0 | **8.0** | 1,036 tests green, no new dependency, the project's own style kept. No refactor happened, so no point is claimed. |
| Performance | 6.0 | **7.5** | "Fast everywhere except one public page that is O(all content)." `/exam/` went from 585 ms to 81 ms. The lesson page is still ~138–163 KB, which is why this is not higher. |
| Mobile | 7.5 | **8.0** | "Solid layout; small tap targets in lists." The lesson-list rows and the exercise buttons are 44px, checked at 390px. |
| SEO | 2.0 | **2.0** | Untouched. |
| Accessibility | 8.0 | **8.5** | "No live regions, small targets." The live regions were already there (the audit's finding did not reproduce) and the small targets are fixed; 1–9/Enter answer a multiple-choice question without a mouse. Not verified beyond measured styles and geometry — no screen reader, no axe. |
| Security | 7.0 | **7.0** | Every security finding is deferred by instruction. |
| Trust | 3.0 | **3.0** | Untouched: still no contact page, no policies, no proof, no named owner. |
| Gamification | 7.0 | **7.0** | Untouched. |
| Analytics | 1.0 | **1.0** | Untouched. |
| Scalability | 5.0 | **5.5** | The O(content) public page is gone. There is still no cache, no CDN and no real server. |

**Unweighted average: 119 / 22 = 5.4 → 131 / 22 = 6.0.**
**Weighted for "is this a good learning product?" (learning, content, code, UX, a11y, mobile,
retention): ≈ 6.5 → ≈ 7.3** — the seven dimensions now read 7.5, 8.0, 8.0, 8.0, 8.5, 8.0, 7.5.
**Weighted for "is this a business?": ≈ 2.2 → ≈ 2.2.** Nothing business-shaped was done, and
no amount of front-end work was going to move it.

## What a 9/10 still needs, and which parts I cannot verify myself

Grouped by who has to do it, because that is the honest answer to "is it finished?".

### Content a teacher has to check (the largest gap)
1. **Drills for each lesson's own grammar** (P-19, first half). Imperative, `nicht/kein`,
   separable verbs, the modal bracket, dative prepositions, the comparative, `seit + Dativ`.
   The gating half is done, so today most lessons drill their words and not their rules.
   Every German item would have to be checked word by word against the course's own
   vocabulary and the official A1 list, and the rule is that nothing uncertain is published.
2. **The exam in the official Goethe shapes** (owner decision 7): a short announcement and an
   email for LESEN, a message and a form for SCHREIBEN. The structure, the data file and the
   guard test are ready; the items are not written.
3. **A native speaker's ear on the audio and the German**, and a Persian proofread of the
   explanations. I can check spelling, articles and word order against the data, which I did;
   I cannot hear a clip or judge how a sentence sounds.
4. **The writing task** (P-25 half): a short message needs human or machine feedback. Owner's
   decision.

### Engineering that is written down but not done
5. **Server-side step pagination for the lesson page** (P-17) — the audit's "paginate or
   lazy-render". It changes the design the no-JavaScript path depends on, so it is a
   deliberate change with its own tests, not a tweak.

### Things a browser here cannot answer
6. **Safari, Firefox and iOS Safari.** Only Chromium ran. iOS Safari is the one that most
   often disagrees with the mobile layout, and it is the one I could not open.
7. **A screen reader and axe.** The accessible names, live regions and focus handling are
   built as if they work; only a real screen reader proves it.
8. **Lighthouse and Core Web Vitals**, and any performance number on a real network and a real
   server. Every timing in `REPORT.md` is a local `runserver` and is only comparable to itself.
9. **The microphone path** (P-25): headless Chromium over plain HTTP cannot grant it, so
   record-and-compare is verified as markup and honest degradation, not as a recording.

### Owner decisions, not engineering
10. **Business and trust** (pricing, contact, privacy, terms, analytics, error monitoring) —
    `OWNER-DECISIONS.md` 1–5. Until these exist, Business, Sales, Conversion, Trust and
    Analytics stay where they are, and the "is this a business?" score cannot move.
11. **A2**, or accepting A1 as the whole product. The course now *says* it ends; whether there
    is a second course is a content project of the same size again.
12. **Email**, without which there is no password recovery and no nudge — `OWNER-DECISIONS.md` 2.

## What I did not do to these numbers

- I did not raise a score for work that was verified only by a test I wrote myself.
- I did not raise Security, Trust, SEO, Sales, Conversion, Analytics or Business, because
  nothing in them changed, however much the front end improved.
- I did not raise Learning Experience above 7.5, because the audit's own reason for it — the
  drills not matching the teaching — is only half answered.
- I did not raise Performance above 7.5, because the lesson page is still one large payload.
- Where a finding did not reproduce (the exercise verdict's live region, `prefers-reduced-motion`),
  I said so instead of claiming a fix.
