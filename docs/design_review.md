# Design and accessibility review (S15)

Session S15, 2026-09-28. Method: `npm run shots` for every screen in English, Hindi and Punjabi at
1366x768, 1920x1080 and 360x740 (126 full-page screenshots before, 126 after, all on the demo
files). I read them at full size and checked each screen against the "generated-looking habits"
table in Frontend Guide 2.6, the voice rules in 2.7, the accessibility list in 11.1 and the final
polish checklist in section 12. Accessibility was checked with axe-core and a keyboard-only
walkthrough (`npm run a11y`), performance with Lighthouse.

Curated before and after pairs: `docs/screens/before/readme-*.png` and
`docs/screens/after/readme-*.png` (see `docs/screens/README.md`). The full sets are regenerated with
`SHOTS_SET=before|after npm run shots` and are not committed (27 MB each).

Everything on screen is synthetic demo data; nothing here is a claim about real weather or
real accuracy.

## Guide 2.6 checklist, whole app

| Habit to avoid | Finding | Status |
|---|---|---|
| Gradient hero, big number with a coloured badge | None. The map opens first; numbers sit next to their legend or in tables. | ok |
| Rows of identical rounded cards with soft shadows | None. Tables, divided lists and one panel per topic; shadows only on the map tooltip. | ok |
| Emoji as icons | None. Lucide line icons plus text everywhere. | ok |
| Purple/indigo, cream + terracotta, black + neon | None; the token test checks hues. | ok |
| ALL-CAPS tiny labels above headings | None; the i18n test checks English strings. | ok |
| Fade-and-slide on every section | None. No CSS transitions; every Recharts series has animation off; MapLibre skips easing under reduced motion. | ok |
| Lorem ipsum, fake names | None. Synthetic Panchayat MP0307, real crops, dates and units. "Demo farmer N" is labelled as a demo. | ok |
| Vague copy ("Insights", "Smart") | None found in 630 English strings (scripted scan for vague words, "please", "click", "!", "Oops", "Nothing here"). | ok |
| Everything centred | Text is left-aligned, numbers right-aligned in tables. | ok |
| Internal job names on screen (added to the list) | Verification and impact notes showed `temporal_holdout`, `rain_intensity heavy_ge_35mm`, `wasted_wait`, "Does NOT", "95% CI". | fixed |

## Per screen

### Map explorer (`/map`)

Before:
- **Cramped:** at 1366x768 the controls column overflowed: the risk layer and Panchayat picker
  were below the fold, and the page itself scrolled 63 px because a visually hidden table caption
  in the detail panel was positioned against the page instead of its scrolling column.
- **Inconsistent:** the five lead days wrapped as 2 + 2 + 1 pills with the last one full width;
  the detail panel's five variable buttons as a heavy 3 + 2 grid of equal-width buttons.
- **Unclear:** the map title read "Rain, Tue 10 Sep 2024: Panchayat". "Panchayat" alone did not
  say it was the view mode.
- **Wrong:** the fan chart's y axis for a dry week read 0, 0.2, 0.3, 0.5 mm (uneven steps chosen
  by Recharts inside a 0 to 0.5 domain).
- **Generic:** the variable list spent two lines per row on "Rain / mm".

After:
- Day strip: one row of five equal cells, weekday over date, the full date read to screen readers.
- Variable list: unit on the same line, right-aligned, 36 px rows. All controls fit in 768 px
  and the page no longer scrolls.
- Title: "Rain on Tue 10 Sep 2024, Panchayat forecast" (and "block forecast", "Panchayat minus
  block"). Hindi and Punjabi drafted, need native review.
- Fan chart: explicit ticks on the same round steps as the axis ends (a dry week is 0 to 4 mm in
  steps of 1).
- Panel variable switch: natural-width pills, 30 px high, wrapping left-aligned.

Still open: the headline reads "0 mm" and then "likely about 0 mm" on a dry day (redundant, but
correct); the Panchayat picker truncates "Synthetic Panchayat MP010…" in the 232 px column.

### Priority (`/priority`)

Before: on phones the Panchayat link wrapped over three lines ("Synthetic / Panchayat / MP0301")
and the reason column wrapped to three lines, so each row was about 70 px; the table scrolled in a
box inside the scrolling page.
After: names stay on one line, the reason column is wide enough for one line (the table scrolls
sideways), rows are 36 px again, and on phones the page scrolls instead of an inner box.
Still open: the "Why" text repeats "Heavy rain likely on 10 September" in every row of a
heavy-rain day. That is honest output of the rules engine, but a grouped view would scan faster.

### Review (`/review`)

Checked: one word per action. Approve / Approved / approved, Reject / Rejected / rejected,
"Save edit and approve" / "Edited and approved" across button, toast, status chip and history.
Evidence rows are labelled as English (officer view). Disabled buttons on the demo files are pale
by design and say why underneath.
Still open: the queue scrolls the selected advisory into view, so the first visible item can be
cut at the top edge; the "Spray day ratings" evidence row is one long line of five ratings.

### Verification (`/verification`)

Before:
- **Unclear:** "Where the model does not help" was one bullet per comparison, up to eight lines
  of job output each: `Does NOT beat B1 on rain MAE (temporal_holdout): overall: tie (...);
  lead_day 1: ...; rain_intensity light_1_10mm: loss (...)`. The losses were in there but hard to
  find.
- **Inconsistent:** the three check tabs stretched to about 400 px each on a desktop.

After:
- Each comparison is a headline ("Does not beat B1 on rain mean absolute error (held-out period)")
  with one line per stratum ("light rain days (1 to 10 mm): loss (-6.4%, 95% interval -12.5% to
  -3.0%)"). Real losses (interval below 0) are bold; ties and "too few days" are regular.
  Every number is unchanged; only the job's names are replaced (`lib/verify.ts` `readableNote`,
  with tests). "About these numbers" and the section notes use the same wording.
- Tabs keep their natural width.

Still open: the page is about 7,300 px tall at 1366 px (every block and station row). It is
complete rather than generic, but a "show all 30 stations" toggle would help a projector demo.

### Impact (`/impact`)

After: notes in plain words ("Wasted wait = acted ... but the event did not come"). The outcome
bars and table already paired colour with words.
Still open: the rule sentences ("Advise spraying tomorrow when...") and notes are English on the
Hindi and Punjabi screens because the API sends them in English only. They carry `lang="en"`.

### Farmer app (`/farmer`, `/farmer/forecast`, `/farmer/farm`)

Before: on a desktop the green top bar was phone-width but the yellow ribbon ran the full window
width, so the two bars did not line up.
After: the ribbon sits inside the phone column under the farmer top bar.
Checked at 360 px in three languages: one action first, 17 px body, 24 px action headline, icons
with words, 48 px targets, bottom navigation with three items. Hindi and Punjabi fit without
overflow.

### Bulletin (`/bulletin/:pid`)

No layout change needed; the farmer e2e test still measures that a normal bulletin prints on one
A4 page. The officer top bar shows on screen (hidden in print).

### Not found

"Page not found. There is no screen at /nowhere." with a link to the map. Real product wording.

## Copy audit

- Sentence case everywhere (test enforced).
- One word per action across button, toast and log (see Review).
- Units on every number; dates as "Tue 10 Sep" or "Tue 10 Sep 2024".
- No vague marketing words; errors say what failed and what to do ("Could not load the forecast
  for MP0103. Check the server is running, then try again.").
- Hindi and Punjabi files have no string that is English-only (scripted check). The new map
  title strings are drafts that need native review (`docs/translation_notes.md`).
- Known: text that comes from the API in English only: demo date reasons in the issue date menu
  ("Heavy monsoon rain"), impact rule sentences, verification and impact notes, review evidence.

## Accessibility

**axe-core** (`@axe-core/playwright` 4.13, tags wcag2a, wcag2aa, wcag21a, wcag21aa, best-practice),
14 screens and states x en/hi/pa x 1366 and 360 px = 84 runs.

| | serious / critical | moderate | minor |
|---|---|---|---|
| Before | 24 runs failed: `scrollable-region-focusable` (29 nodes: tables in the map, verification and impact), `aria-hidden-focus` (18 nodes: Recharts SVGs focusable inside `aria-hidden` figures) | `region` on all 84 runs (ribbon outside landmarks) | 0 |
| After | **0** | **0** | **0** |

Fixes: `TableScroll` (a focusable, named region around the seven wide tables), Recharts'
accessibility layer off inside hidden charts (each chart has a table alternative), the ribbon as a
named region, one named landmark per table on Impact, and the map's hidden `h1` no longer given
`overflow-y: auto`.

**Keyboard only** (`e2e/keyboard.spec.ts`, part of `npm run a11y`): skip link to main; day strip
with arrow keys; variable list; "Show as table"; open a Panchayat from the table; priority row
link to the map; review queue with arrow keys and Enter; farmer language switch with arrows,
"Why, and what if" with Enter, bottom navigation, and the rain question. After every Tab the test
checks that a focus ring (outline or box shadow) is visible. It found three real bugs:

1. After choosing a farmer bottom-nav tab, focus stayed on the navigation, the last thing on the
   page; the next Tab left the page. Now focus moves to `<main>` on every screen change.
2. Pressing Yes on "Did it rain today?" removed the focused button and dropped focus to the page
   body. Each step now moves focus to its first control, then to the result message.
3. Two quick changes to a map control (ArrowRight then ArrowLeft on the day strip) could leave the
   first value in the URL and put it back: React Router commits location in a transition, and the
   URL sync compared against the stale location (3 of 12 runs before the fix, 0 of 33 after).

**Contrast:** `tokens.test.ts` checks every text token pair at 4.5:1 or more (`--muted` is 5.6:1 on
white, 4.9:1 on `--canvas`); axe's `color-contrast` passes on every screen in every language.
Disabled buttons are exempt by WCAG and say in text why they are disabled.

**Reduced motion:** no CSS transitions or entrance animations exist; `prefers-reduced-motion`
also switches off any animation in `base.css`; chart animation is off; MapLibre skips easing.

**Charts and map:** the fan chart, reliability plot and coverage chart are `aria-hidden` with a
table of the same numbers; the map has "Show as table" and each Panchayat is a named button there.

**200 % zoom** (683x384 CSS px): no horizontal page scroll on any screen in English or Hindi; wide
tables scroll inside their focusable boxes.

## Performance

Lighthouse 12.8.2, `/farmer?date=2024-09-09`, production build on `vite preview` and the demo
files, mobile form factor, simulated throttling (150 ms RTT, 1.6 Mbps down, 4x CPU slowdown; the
same as DevTools' "Fast 3G"). Median of three runs each:

| | Performance | Accessibility | Best practices | SEO | FCP | LCP | TBT | CLS | Bytes |
|---|---|---|---|---|---|---|---|---|---|
| Before (1e11203) | 91 (91, 91, 88) | 100 | 100 | 91 | 2.28 s | 3.17 s | 0 ms | 0 | 298 KiB |
| After | 93 (93, 93, 90) | 100 | 100 | 100 | 1.36 s | 3.17 s | 0 ms | 0 | 298 KiB |

- FCP: `index.html` now contains a static brand bar that paints as soon as the stylesheet
  arrives, before the 132 kB (gzip) script has run.
- SEO: `public/robots.txt` (the preview answered `/robots.txt` with the app's HTML).
- LCP is unchanged: it is the first advice text, which waits for the script, the route chunk and
  the data (`/mock/index.json`, then the farmer, then the advice). Against the API the index step
  goes away.
- Considered and not done: loading Hindi and Punjabi strings on demand. It would save about
  40 kB (gzip) for English users but add a serial request before the first render for Hindi and
  Punjabi users, who are the main farmer audience (D142).
- Route code splitting was already in place (the farmer route loads no map, chart or officer
  code). Fonts: only the subsets a screen uses are fetched; an English farmer screen still loads
  Devanagari and Gurmukhi 500 for the language switch labels (66 kB), which must be in their own
  scripts.

## Not verified

- A screen reader pass with NVDA or VoiceOver (axe and the keyboard test are not a substitute).
- A real low-end Android phone and a real projector.
- The question for someone outside the team, "Does this look like a real government or agri
  tool?", has not been asked yet. Please write their reactions below.

## Outside reactions

(To be filled in by the team.)
