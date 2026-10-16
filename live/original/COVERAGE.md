# Original challenge-site coverage

Each pre-2026 NZCSC competition was **one website** with a navbar tab per
challenge (a `home` tab + `challengeN` tabs). This directory stages each one as
clean static content, ready to host at a dedicated subdomain:

```
challenges.r<round>.<year>.nzcsc.xyz      e.g. challenges.r0.2024.nzcsc.xyz
```

Navbar links are **absolute** (`/home/`, `/challengeN/`) so they resolve at the
subdomain root. Chrome assets live under each tab's own `files/` (per the 2024
convention). Pages and assets were recovered from the Internet Archive Wayback
Machine using the `id_` modifier (raw original bytes, no toolbar / no URL
rewriting); gzip'd captures were decompressed; no Wayback banner HTML is present.

## Summary

| Year | Round | Subdomain | `home` | Challenge tabs with real pages | Source |
|------|-------|-----------|:------:|--------------------------------|--------|
| 2015–2020 | — | — | — | *(none — see "No tabbed challenge site" below)* | — |
| 2021 | r0 | `challenges.r0.2021.nzcsc.xyz` | yes | **8** | Wayback `r0.nzcsc.org.nz` |
| 2022 | r0 | `challenges.r0.2022.nzcsc.xyz` | no | *(none captured)* | Wayback (only 404s) |
| 2023 | r0 | `challenges.r0.2023.nzcsc.xyz` | yes | **2, 3, 16** | Wayback `r0.nzcsc.org.nz` |
| 2024 | r0 | `challenges.r0.2024.nzcsc.xyz` | yes | **1, 3, 5, 6, 8, 13** | pre-staged (`mirrors/mirror2024`) |
| 2025 | r0 | `challenges.r0.2025.nzcsc.xyz` | yes* | **2, 15, 16** | repo recreations + Wayback `ctf.nzcsc.org.nz` |

\* The 2025 `home` landing is a faithful **recreation** (authentic chrome +
navbar), because no `/` or `/home/` capture of `ctf.nzcsc.org.nz` exists in
Wayback. All other pages are authentic captures or the pre-existing recreations.

Total staged in `live/original/`: ~33 MB (2021 ≈ 0.2 MB, 2023 ≈ 7.5 MB,
2024 ≈ 21 MB, 2025 ≈ 5 MB).

## Challenge number → original-site tab URL

These drive later CTFd "connection_info" linking.

### 2021 — `challenges.r0.2021.nzcsc.xyz`
| # | Title / prompt | Tab URL |
|---|----------------|---------|
| 8 | *"We intercepted this coded message"* (encoded blob to decode) | `https://challenges.r0.2021.nzcsc.xyz/challenge8/` |

### 2023 — `challenges.r0.2023.nzcsc.xyz`
| # | Title / prompt | Tab URL |
|---|----------------|---------|
| 2 | Simple AI — links `simple.png` (download) | `https://challenges.r0.2023.nzcsc.xyz/challenge2/` |
| 3 | Confectionary AI — login form POSTing to `/challenge3/index.php` | `https://challenges.r0.2023.nzcsc.xyz/challenge3/` |
| 16 | Time Machines — links `challenge16.zip` ("The Mystery File") | `https://challenges.r0.2023.nzcsc.xyz/challenge16/` |

### 2024 — `challenges.r0.2024.nzcsc.xyz` (pre-staged)
| # | Tab URL |
|---|---------|
| 1 | `https://challenges.r0.2024.nzcsc.xyz/challenge1/` |
| 3 | `https://challenges.r0.2024.nzcsc.xyz/challenge3/` |
| 5 | `https://challenges.r0.2024.nzcsc.xyz/challenge5/` |
| 6 | `https://challenges.r0.2024.nzcsc.xyz/challenge6/` |
| 8 | `https://challenges.r0.2024.nzcsc.xyz/challenge8/` |
| 13 | `https://challenges.r0.2024.nzcsc.xyz/challenge13/` |

### 2025 — `challenges.r0.2025.nzcsc.xyz`
| # | Title / prompt | Tab URL |
|---|----------------|---------|
| 2 | Explore Fun Facts — flag hidden in HTML comments + `js/backup/flag.js` | `https://challenges.r0.2025.nzcsc.xyz/challenge2/` |
| 15 | Login for flag — creds leaked in page JS (`securelogin.php`) | `https://challenges.r0.2025.nzcsc.xyz/challenge15/` |
| 16 | Cyber Space — robots.txt → `report.html` (`FLAG[...]`) | `https://challenges.r0.2025.nzcsc.xyz/challenge16/` |

## Gaps / notes

- **Navbar tabs without pages.** Every site's navbar lists the full challenge
  set (C-1 … C-16, or CH1 … CH10 in 2021). Only the challenges above have real
  pages staged; the other tab links will 404. This is inherent to the archived
  design and matches the pre-staged 2024 site.
- **2021** uses the *old-style* chrome (`files/assets`, `files/css/{web,phone,font}.css`,
  `files/scripts/javaScript.js`); `home` references it via `../home/files/…`,
  `challenge8` via `files/…`. The 1.8 MB `crop.gif` CSS background
  (`web.css url(../assets/crop.gif)`) was **dropped** to keep the year small; the
  page still renders. `font.css` pulls Roboto from Google Fonts (external).
- **2022** — Wayback has only 404 captures of `/challenge4/` on
  `nzcsc.org.nz` / `r0.nzcsc.org.nz`; no challenge content exists. Not staged.
- **2023** — `challenge2`'s `simple.png` download target was **never captured**
  by Wayback (link kept, file absent). `challenge3`'s `/challenge3/index.php`
  was server-side (not captured); the login form is kept as static HTML.
  `challenge16.zip` (≈306 KB, authentic) **is** included.
  A round-2 host (`r2.nzcsc.org.nz`) exists in Wayback but only as a `301` on
  `/home` — no usable 200 page, so no `2023-r2` site was built.
- **2024, 2025 chrome** references `files/font/OpenSans-Regular.ttf` and
  `files/img/bg_dark.png` in `web.css`; these were never archived (they also 404
  in the authentic 2024 mirror), so the refs are left to fall back gracefully —
  consistent across all new-style years.
- **No tabbed challenge site (2014–2020).** The old event domain
  `cybersecuritychallenge.org.nz` is well-archived (2014–2019) but it is the
  *conference/competition info site* (about, accommodation, FAQ, sponsors, per-year
  `/2014/ … /2019/` subdirs), **not** the `home` + `challengeN` tabbed challenge
  model. `nzcsc.org.nz/competition/` (2019+) is an Angular SPA shell with no
  static challenge content. These are preserved in `mirrors/mirror_other/` but
  were not reshaped into tabbed sites, since no per-challenge pages were captured.
- **2026** — intentionally skipped.
