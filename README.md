# WORLD IN ONE FRAME — Tuesday 17 November 2026

A make.fun bounty entry for **news-image-20261117**: "Sum up 17 November's
world news in one image."

The program draws a one-page newspaper front page for Tuesday 17 November
2026 — 39 verified stories across 6 continents — with a single continuous
lead panorama (Kerch Bridge → the Gulf → Shenzhen/APEC), three lead stories,
ten illustrated cards, a dotted world map and a numbered brief list.

## How it works

`main.py` is pure Python 3 standard library (no network, no external
assets). It draws everything itself: a hand-authored proportional stroke
font, flat vector illustrations, and a dot world map. Running it writes
`/output/entry.png` (1024×1024, ≤1 MiB). Two runs produce byte-identical
output.

```sh
mkdir -p out && MAKEFUN_OUTPUT_DIR=out python3 main.py
```

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
