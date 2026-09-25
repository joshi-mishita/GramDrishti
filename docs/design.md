# Design system

Source: Frontend Guide section 2 (direction), section 4 (tokens) and section 8 (components).
Code: `frontend/src/styles/tokens.css`, `base.css`, `shell.css`, `components.css`, `pages.css`, `print.css`.

## Tokens

The palette, radius, gaps and font stack are exactly Guide 2.3 and section 4. The tokens below
are additions. Each one derives from a guide colour or rule, and `src/styles/tokens.test.ts`
checks text contrast of at least 4.5:1 (Guide 11.1).

| Token | Value | Why |
|---|---|---|
| `--brand-strong` | `#1B4538` | Darker brand for top bar borders, pressed and hover states |
| `--brand-tint` | `#E3EDE9` | Selected navigation row and selected list option on white |
| `--brand-ink-soft` | `#CFE0D9` | Dividers and secondary text on the brand top bar (5.8:1) |
| `--surface-hover` | `#F5F7F6` | Row and button hover |
| `--skeleton` | `#E3E8E6` | Loading blocks; the "no value" grey from Guide 8.1 |
| `--ribbon-bg` / `--ribbon-line` | `#FBF1CF` / `#E8B923` | Mock ribbon: a pale tint of `--sev-mod`, text stays `--ink` |
| `--fs-1` to `--fs-5` | 12/14/16/20/28 px | Guide 2.4 scale |
| `--fs-farmer-body`, `--fs-farmer-action` | 17 px, 24 px | Guide 2.4 farmer app |
| `--lh-latin`, `--lh-indic` | 1.45, 1.65 | Devanagari and Gurmukhi get about 15 percent more line height |
| `--topbar-h`, `--ribbon-h`, `--nav-w`, `--panel-w`, `--row-h`, `--touch` | 52, 28, 184, 320, 36, 48 px | Layout rules of Guide 2.5 and 5 |

Measured contrast: `--muted` on `--canvas` is 4.9:1 and on white 5.6:1; white on `--brand` 8.1:1.

## Shell

- Top bar on `--brand`: product name, district, issue date (with the reason for each demo date
  from `/meta.issue_date_info`), role switch, language switch. Each language name is in its own
  script with a `lang` attribute.
- Mock ribbon, 28 px, directly under the top bar, not dismissible, shown only when
  `meta.data_mode === "mock"`. It also prints (print.css draws it with a plain border).
- Officer: left navigation with icon and label; below 768 px it becomes a sticky bottom bar.
- Farmer: a phone-width column (max 480 px) with a three-item bottom navigation, also on desktop.

## Components so far

`SegmentedControl` (native radios in three variants: `bar`, `list`, `wrap`), `Ribbon`,
`QueryBoundary` with `Skeleton`, `EmptyState` and `ErrorState`, `RiskChip` (colour swatch plus
word), `ProvenanceNote`, `PageHeader`, `ErrorBoundary`, `LangSwitch`, `RoleSwitch`,
`IssueDateSelect`, `SideNav`, `FarmerNav`. Map, legend, fan chart and the other components of
Guide 8 arrive with their screens.

## Rules kept

No gradients, emoji, purple or indigo (a token test checks hue), no all-caps labels (an i18n test
checks English strings), no entrance animation (loading blocks are static), no KPI card row,
sentence case, left-aligned text, radius 3 px for controls and 2 px for panels, borders instead of
shadows.
