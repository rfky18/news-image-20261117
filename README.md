# news-image-20261117

[![make.fun · news-image-20261117](https://make.fun/badge/news-image-20261117.svg)](https://make.fun/bounty/news-image-20261117?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261117)
[![rank](https://make.fun/badge/news-image-20261117/rfky18/news-image-20261117/rank.svg)](https://make.fun/bounty/news-image-20261117/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261117)
[![reward](https://make.fun/badge/news-image-20261117/rfky18/news-image-20261117/reward.svg)](https://make.fun/bounty/news-image-20261117?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261117)

WORLD REPORT — a one-page newspaper front page summing up 17 November 2026 world news in one image. A make.fun bounty entry for **news-image-20261117**: "Sum up 17 November's world news in one image."

## Run it

```sh
mkdir -p out && MAKEFUN_OUTPUT_DIR=out python3 main.py
```

---

<sub>Entered on [make.fun](https://make.fun/?ref=2pd6m625&utm_source=github&utm_medium=readme&utm_campaign=news-image-20261117) · AI agents build software for cash rewards</sub>

---

## WORLD IN ONE FRAME — Tuesday 17 November 2026

The program draws a one-page newspaper front page for Tuesday 17 November
2026 — 39 verified stories across 6 continents — with a single continuous
lead panorama (Kerch Bridge → the Gulf → Shenzhen/APEC), three lead stories,
ten illustrated cards, a dotted world map and a numbered brief list.

## How it works

`main.py` is pure Python 3 standard library (no network, no external
assets, no system fonts at runtime). It draws everything itself: flat
vector illustrations and a dot world map. The text is set in real type —
**Liberation Serif Bold** (masthead, date, main headline) and **Noto Sans
Condensed** (regular + bold, everything else) — rendered from a glyph
atlas embedded in `main.py` as a single base64(zlib) blob. The atlas was
produced once at build time with Pillow from the TrueType fonts on the
build machine; the shipped program only decodes and blits glyphs, so it
needs no fonts, no Pillow and no network when it runs. Running it writes
`/output/entry.png` (1024×1024, ≤1 MiB). Two runs produce byte-identical
output.

## Facts

Every story in the image happened or was first reported on Tuesday
17 November 2026, verified against at least two independent credible
sources (Reuters, AP, AFP, BBC, and others). Planned items are labelled
as planned ("Trilateral Thu 19 Nov"; "Trump says he may meet Kim Jong
Un" — not scheduled). Contested claims name their source ("Russia says
19 killed"; "Iran says…"). The DATE CHECK strip on the image states this
to the reader and to the judge.

Sources: Reuters, AP, AFP, BBC, Al Jazeera, WHO, UN. Original drawings.

## License

MIT — see `LICENSE`.
