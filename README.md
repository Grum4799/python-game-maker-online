# pysite

A static site that runs Python in the visitor's browser — a general-purpose
code sandbox, an in-browser game maker, and a hub for real pygame games
compiled to WebAssembly. Three ways to use it, in order of how much local
setup they need:

| | runs in-browser | builds in-browser | real pygame |
|---|---|---|---|
| **Sandbox** | yes | yes | n/a |
| **Make** (`webgame` engine) | yes | yes | no — a pygame-style subset |
| **Games** (pygbag) | yes (to play) | no — needs local build | yes |

No backend, no server-side Python anywhere — GitHub Pages only serves
static files, so all execution happens client-side.

## Structure

```
index.html              landing page (runs a live Pyodide snippet on load)
sandbox/index.html       general code editor — numpy/matplotlib preloaded,
                          anything else installable on the fly
make/index.html           in-browser game editor + live canvas + Run/Stop,
                           code autosaved to the browser (localStorage)
assets/webgame.py         the pygame-style engine that powers Make — Rect,
                           Surface, draw, event, key, an async frame clock
games/index.html          hub linking to both the in-browser and compiled games
games/dodger/main.py       example real pygame game (async-loop pattern pygbag needs)
assets/style.css          shared styling
.github/workflows/deploy.yml   builds every game with pygbag, deploys to Pages
```

## Getting it live

1. Create a new GitHub repo and push this folder as its contents.
2. In the repo, go to **Settings → Pages** and set **Source** to
   **GitHub Actions** (not "Deploy from a branch" — the workflow here
   handles the build itself).
3. Push to `main`. The workflow builds every game under `games/*/main.py`
   with pygbag and deploys the whole site. First run takes a few minutes;
   check the **Actions** tab for progress.
4. Your site will be live at `https://<username>.github.io/<repo>/`.

## Working on it locally

The sandbox and landing page need nothing special — Pyodide loads from a
CDN, so you can just open `index.html` in a browser, or serve the folder
locally to avoid any file:// restrictions:

```bash
python -m http.server 8000
# visit http://localhost:8000
```

Games need pygbag to build a browser version:

```bash
pip install pygbag
pygbag games/dodger        # serves a local preview at http://localhost:8000
pygbag --build games/dodger  # writes games/dodger/build/web/ for real
```

You can also just run a game natively while developing it, since the async
pattern works fine outside the browser too:

```bash
pip install pygame-ce
python games/dodger/main.py
```

## Making a game with no local setup at all

Open `make/index.html`. It's an editor and a live `<canvas>` side by side:
write code, hit Run, it plays immediately — nothing is built, uploaded, or
saved anywhere but that browser's local storage. Games there `import
webgame`, the small pygame-style module in `assets/webgame.py`. It covers
`Rect`, `Surface`, `draw.rect/circle/line`, `event.get()`,
`key.get_pressed()`, and `font.SysFont` with pygame-matching semantics.

The one real difference from real pygame: nothing in a browser tab may
block the main thread, so the frame clock is awaited —
`dt_ms = await clock.tick(60)` instead of pygame's synchronous
`clock.tick(60)`. Everything else reads like ordinary pygame code.

`webgame` is a subset, not a full port — no sprite groups, sound, or image
loading yet. Outgrow it and want the real thing? The same async-loop style
carries over almost directly to a pygbag project (see below); it's a small
rewrite, not a restart.

## Adding a library to the sandbox

Anything in [Pyodide's built-in package list](https://pyodide.org/en/stable/usage/packages-in-pyodide.html)
(numpy, pandas, sympy, scikit-learn, matplotlib, and more) can be loaded
from the "Load another package" box on the sandbox page, or added by
default by editing the `pyodide.loadPackage([...])` call in
`sandbox/index.html`. Pure-Python packages not on that list can usually be
installed at runtime via `micropip` — the sandbox already falls back to
that automatically.

## Adding a game

1. Make a new folder under `games/`, e.g. `games/my-game/`.
2. Write `main.py` as a normal pygame script, but structure the main loop
   like `games/dodger/main.py`: wrap it in `async def main()`, call
   `await asyncio.sleep(0)` once per frame, and kick it off with
   `asyncio.run(main())`. This is what lets pygbag hand control back to the
   browser between frames instead of freezing the tab.
3. Add a card to `games/index.html` linking to
   `games/my-game/build/web/index.html`.
4. Push — the workflow builds it automatically.

## Why not tkinter?

tkinter binds to a native desktop windowing system; there's no browser
equivalent, so it can't run on a page at all, on GitHub Pages or anywhere
else client-side. Pyodide covers general-purpose libraries (including the
math side of what tkinter apps usually need), and pygbag covers the
GUI/game side by targeting a `<canvas>` instead of a window.
