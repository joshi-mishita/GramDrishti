# UI strings

`en.json`, `hi.json` and `pa.json` hold interface strings only. Advisory text comes translated
from the API and is never translated here.

**Status: `hi.json` and `pa.json` are drafts by Claude Code and need native review** (CLAUDE.md
rule 3). The same applies to the Hindi and Punjabi day and month names in `src/lib/format.ts`.
Record the reviewer and date in `docs/PROGRESS.md` when done.

Rules:

- Keys are grouped by screen. `src/i18n/i18n.test.ts` fails if a key exists in `en.json` but not
  in `hi.json` or `pa.json` (or the reverse), if a translation is empty, or if `{{placeholders}}`
  differ.
- Plurals use i18next suffixes `_one` / `_other` (Hindi and Punjabi also use one/other).
- Sentence case. Say what it is ("Waiting for review"), no vague copy.
- Leave 30 to 40 percent extra width for Hindi and Punjabi labels.

Words the reviewer should check first: "सत्यापन"/"ਤਸਦੀਕ" for verification, "ਭਵਿੱਖਬਾਣੀ" for
forecast, "उच्च"/"ਉੱਚਾ" for the high risk level, and the placeholder and provisional notices.
