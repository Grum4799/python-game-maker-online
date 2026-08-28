"""
webgame — a small pygame-style API that runs entirely in the browser under
Pyodide, drawing to a <canvas> instead of a native window. No build step,
no local files: write code in the site's editor, click Run, it plays.

This is NOT real pygame — it's a compatible-feeling subset covering what
most simple 2D games need: Rect, Surface, drawing primitives, keyboard
input, and a frame clock. If you outgrow it, the same code style (async
main loop) is a short step from a real pygame + pygbag project — see the
"Advanced" path linked from the games page.

THE ONE REAL DIFFERENCE FROM REAL PYGAME:
Nothing here may block the browser's main thread, so the frame clock has
to be awaited:

    dt_ms = await clock.tick(60)      # webgame — note the `await`
    dt_ms = clock.tick(60)            # real pygame — no `await`

Everything else (Rect math, draw calls, event polling, key state) reads
just like pygame.
"""

import asyncio
from js import document, window
from pyodide.ffi import create_proxy

# ---------------------------------------------------------------- constants

QUIT = "quit"
KEYDOWN = "keydown"
KEYUP = "keyup"
SRCALPHA = 1  # accepted, not required — canvases are alpha-capable by default

K_LEFT, K_RIGHT, K_UP, K_DOWN, K_SPACE = "ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown", "Space"
K_RETURN, K_ESCAPE = "Enter", "Escape"
for _c in "abcdefghijklmnopqrstuvwxyz":
    globals()[f"K_{_c}"] = f"Key{_c.upper()}"
del _c


def _css(color):
    if len(color) == 4:
        r, g, b, a = color
        return f"rgba({r},{g},{b},{a / 255})"
    r, g, b = color
    return f"rgb({r},{g},{b})"


# --------------------------------------------------------------------- Rect

class Rect:
    def __init__(self, x, y=None, w=None, h=None):
        if y is None and w is None and h is None:
            seq = x
            if len(seq) == 4:
                x, y, w, h = seq
            else:
                (x, y), (w, h) = seq
        self.x, self.y, self.width, self.height = x, y, w, h

    def __repr__(self):
        return f"Rect({self.x}, {self.y}, {self.width}, {self.height})"

    @property
    def right(self): return self.x + self.width
    @right.setter
    def right(self, v): self.x = v - self.width

    @property
    def bottom(self): return self.y + self.height
    @bottom.setter
    def bottom(self, v): self.y = v - self.height

    @property
    def centerx(self): return self.x + self.width / 2
    @centerx.setter
    def centerx(self, v): self.x = v - self.width / 2

    @property
    def centery(self): return self.y + self.height / 2
    @centery.setter
    def centery(self, v): self.y = v - self.height / 2

    @property
    def center(self): return (self.centerx, self.centery)
    @center.setter
    def center(self, v): self.centerx, self.centery = v

    @property
    def topleft(self): return (self.x, self.y)
    @topleft.setter
    def topleft(self, v): self.x, self.y = v

    def copy(self):
        return Rect(self.x, self.y, self.width, self.height)

    def move(self, dx, dy):
        return Rect(self.x + dx, self.y + dy, self.width, self.height)

    def colliderect(self, other):
        return (self.x < other.x + other.width and self.x + self.width > other.x and
                self.y < other.y + other.height and self.y + self.height > other.y)

    def collidepoint(self, x, y=None):
        if y is None:
            x, y = x
        return self.x <= x <= self.x + self.width and self.y <= y <= self.y + self.height


# ------------------------------------------------------------------ Surface

class Surface:
    def __init__(self, size, flags=0, _canvas=None):
        self.width, self.height = size
        self._canvas = _canvas if _canvas is not None else document.createElement("canvas")
        if _canvas is None:
            self._canvas.width, self._canvas.height = self.width, self.height
        self._ctx = self._canvas.getContext("2d")

    def fill(self, color, rect=None):
        if rect is None:
            self._ctx.clearRect(0, 0, self.width, self.height)
            self._ctx.fillStyle = _css(color)
            self._ctx.fillRect(0, 0, self.width, self.height)
        else:
            self._ctx.fillStyle = _css(color)
            self._ctx.fillRect(rect.x, rect.y, rect.width, rect.height)

    def blit(self, source, dest):
        x, y = (dest.x, dest.y) if isinstance(dest, Rect) else dest
        self._ctx.drawImage(source._canvas, x, y)

    def get_rect(self, **kwargs):
        r = Rect(0, 0, self.width, self.height)
        for k, v in kwargs.items():
            setattr(r, k, v)
        return r


# --------------------------------------------------------------------- draw

class draw:
    @staticmethod
    def rect(surface, color, rect, width=0, border_radius=0):
        ctx = surface._ctx
        if border_radius > 0:
            ctx.beginPath()
            ctx.roundRect(rect.x, rect.y, rect.width, rect.height, border_radius)
            if width == 0:
                ctx.fillStyle = _css(color)
                ctx.fill()
            else:
                ctx.lineWidth = width
                ctx.strokeStyle = _css(color)
                ctx.stroke()
        elif width == 0:
            ctx.fillStyle = _css(color)
            ctx.fillRect(rect.x, rect.y, rect.width, rect.height)
        else:
            ctx.lineWidth = width
            ctx.strokeStyle = _css(color)
            ctx.strokeRect(rect.x, rect.y, rect.width, rect.height)

    @staticmethod
    def circle(surface, color, center, radius, width=0):
        ctx = surface._ctx
        ctx.beginPath()
        ctx.arc(center[0], center[1], radius, 0, 6.283185307179586)
        if width == 0:
            ctx.fillStyle = _css(color)
            ctx.fill()
        else:
            ctx.lineWidth = width
            ctx.strokeStyle = _css(color)
            ctx.stroke()

    @staticmethod
    def line(surface, color, start, end, width=1):
        ctx = surface._ctx
        ctx.beginPath()
        ctx.moveTo(start[0], start[1])
        ctx.lineTo(end[0], end[1])
        ctx.lineWidth = width
        ctx.strokeStyle = _css(color)
        ctx.stroke()


# --------------------------------------------------------------------- font

class Font:
    def __init__(self, family, size, bold=False):
        weight = "bold" if bold else "normal"
        self._css_font = f"{weight} {size}px {family}"
        self._size = size

    def render(self, text, antialias, color):
        scratch = document.createElement("canvas")
        sctx = scratch.getContext("2d")
        sctx.font = self._css_font
        w = max(1, int(sctx.measureText(text).width) + 2)
        h = int(self._size * 1.4)
        surf = Surface((w, h))
        c = surf._ctx
        c.font = self._css_font
        c.fillStyle = _css(color)
        c.textBaseline = "top"
        c.fillText(text, 0, 0)
        return surf


class font:
    @staticmethod
    def SysFont(name, size, bold=False):
        family = "monospace" if "mono" in name.lower() else "sans-serif"
        return Font(family, size, bold)


# --------------------------------------------------------- events / keys

_EVENT_QUEUE = []
_PRESSED = {}
_kd_proxy = _ku_proxy = _stop_proxy = None


class Event:
    def __init__(self, type_, **kw):
        self.type = type_
        for k, v in kw.items():
            setattr(self, k, v)


def _on_keydown(e):
    code = e.code
    _PRESSED[code] = True
    _EVENT_QUEUE.append(Event(KEYDOWN, key=code))
    if code in ("Space", "ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight"):
        e.preventDefault()


def _on_keyup(e):
    code = e.code
    _PRESSED[code] = False
    _EVENT_QUEUE.append(Event(KEYUP, key=code))


def _on_stop_click(e):
    _EVENT_QUEUE.append(Event(QUIT))


class event:
    @staticmethod
    def get():
        items = list(_EVENT_QUEUE)
        _EVENT_QUEUE.clear()
        return items


class _Pressed:
    def __getitem__(self, k):
        return _PRESSED.get(k, False)


class key:
    @staticmethod
    def get_pressed():
        return _Pressed()


# ---------------------------------------------------------------- time/clock

def _raf_future():
    loop = asyncio.get_event_loop()
    fut = loop.create_future()

    def cb(ts):
        if not fut.done():
            fut.set_result(ts / 1000.0)

    window.requestAnimationFrame(create_proxy(cb))
    return fut


class Clock:
    def __init__(self):
        self._last = None

    async def tick(self, fps=60):
        target = (1.0 / fps) if fps else 0
        t = await _raf_future()
        if self._last is None:
            self._last = t
        dt = t - self._last
        while fps and dt < target:
            t = await _raf_future()
            dt = t - self._last
        self._last = t
        return dt * 1000.0


class time:
    Clock = Clock


# ------------------------------------------------------------- init/display

class display:
    @staticmethod
    def set_mode(size):
        canvas = document.getElementById("game-canvas")
        canvas.width, canvas.height = size
        return Surface(size, _canvas=canvas)

    @staticmethod
    def set_caption(title):
        cap = document.getElementById("game-caption")
        if cap:
            cap.textContent = title

    @staticmethod
    def flip():
        pass

    @staticmethod
    def update():
        pass


def init():
    global _kd_proxy, _ku_proxy, _stop_proxy
    quit()  # clear any listeners left from a previous run
    _EVENT_QUEUE.clear()
    _PRESSED.clear()
    _kd_proxy = create_proxy(_on_keydown)
    _ku_proxy = create_proxy(_on_keyup)
    document.addEventListener("keydown", _kd_proxy)
    document.addEventListener("keyup", _ku_proxy)
    stop_btn = document.getElementById("stop-btn")
    if stop_btn:
        _stop_proxy = create_proxy(_on_stop_click)
        stop_btn.addEventListener("click", _stop_proxy)


def quit():
    global _kd_proxy, _ku_proxy, _stop_proxy
    if _kd_proxy is not None:
        document.removeEventListener("keydown", _kd_proxy)
        _kd_proxy = None
    if _ku_proxy is not None:
        document.removeEventListener("keyup", _ku_proxy)
        _ku_proxy = None
    if _stop_proxy is not None:
        stop_btn = document.getElementById("stop-btn")
        if stop_btn:
            stop_btn.removeEventListener("click", _stop_proxy)
        _stop_proxy = None
