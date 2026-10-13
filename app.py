"""Dashboard en tiempo real de Helldivers 2 (Tkinter + Matplotlib).

Ejecutar:  python app.py
"""

from __future__ import annotations

import csv
import queue
import threading
import tkinter as tk
from datetime import datetime, timezone
from pathlib import Path
from tkinter import ttk

import matplotlib

matplotlib.use("TkAgg")
import matplotlib.dates as mdates  # noqa: E402
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg  # noqa: E402
from matplotlib.figure import Figure  # noqa: E402
from matplotlib.ticker import FuncFormatter  # noqa: E402

from hd2_api import Snapshot, fetch_snapshot  # noqa: E402

HISTORY_FILE = Path(__file__).with_name("history.csv")
FACTIONS = ["Terminids", "Automaton", "Illuminate"]

# --- Tema (oscuro, acento amarillo Super Tierra) ---------------------------
BG = "#121211"
SURFACE = "#1a1a19"
GRID = "#2c2c2a"
TEXT = "#f0efec"
TEXT_2 = "#c3c2b7"
MUTED = "#8a8980"
ACCENT = "#f2c200"           # sólo para cromo de UI
SERIES_TOTAL = "#c98500"     # serie única: jugadores totales
# Colores categóricos validados (CVD) para fondo oscuro, orden fijo.
FACTION_COLOR = {
    "Illuminate": "#3987e5",
    "Automaton": "#d95926",
    "Terminids": "#199e70",
    "Humans": MUTED,
}
FACTION_ES = {"Terminids": "Terminidos", "Automaton": "Autómatas", "Illuminate": "Iluminados", "Humans": "Humanos"}

INTERVALS = {"30 s": 30, "1 min": 60, "2 min": 120, "5 min": 300}


def fmt_int(n: float) -> str:
    return f"{int(n):,}".replace(",", ".")


def fmt_compact(n: float, _pos=None) -> str:
    for div, suf in ((1e12, "T"), (1e9, "B"), (1e6, "M"), (1e3, "k")):
        if abs(n) >= div:
            return f"{n / div:.1f}{suf}".replace(".0", "")
    return f"{int(n)}"


# --- Historial persistente ---------------------------------------------------
class History:
    COLS = ["timestamp", "players", *FACTIONS]

    def __init__(self, path: Path):
        self.path = path
        self.rows: list[dict] = []
        if path.exists():
            with path.open() as f:
                for r in csv.DictReader(f):
                    try:
                        self.rows.append({
                            "timestamp": datetime.fromisoformat(r["timestamp"]),
                            "players": int(r["players"]),
                            **{k: int(r[k]) for k in FACTIONS},
                        })
                    except (KeyError, ValueError):
                        continue

    def add(self, snap: Snapshot) -> None:
        by_faction = {k: 0 for k in FACTIONS}
        for c in snap.campaigns:
            if c.faction in by_faction:
                by_faction[c.faction] += c.players
        row = {"timestamp": snap.fetched_at, "players": snap.players, **by_faction}
        self.rows.append(row)
        new_file = not self.path.exists()
        with self.path.open("a", newline="") as f:
            w = csv.DictWriter(f, fieldnames=self.COLS)
            if new_file:
                w.writeheader()
            w.writerow({**row, "timestamp": row["timestamp"].isoformat()})

    def series(self, key: str, since: datetime | None):
        rows = [r for r in self.rows if since is None or r["timestamp"] >= since]
        return [r["timestamp"] for r in rows], [r[key] for r in rows]


# --- Aplicación --------------------------------------------------------------
class Dashboard(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Helldivers 2 · Galactic War Dashboard")
        self.geometry("1500x940")
        self.minsize(1100, 720)
        self.configure(bg=BG)

        self.history = History(HISTORY_FILE)
        self.snapshot: Snapshot | None = None
        self.results: queue.Queue = queue.Queue()
        self.fetching = False
        self.next_refresh = 0
        self.interval = tk.StringVar(value="1 min")
        self.window = tk.StringVar(value="Todo")
        self._hover_artists: list = []

        self._style()
        self._build_header()
        self._build_kpis()
        self._build_body()

        self.after(200, self._poll_results)
        self.after(1000, self._tick)
        self.refresh()

    # ---- estilo ----
    def _style(self):
        st = ttk.Style(self)
        st.theme_use("clam")
        st.configure(".", background=BG, foreground=TEXT, fieldbackground=SURFACE, font=("Segoe UI", 10))
        st.configure("TFrame", background=BG)
        st.configure("Card.TFrame", background=SURFACE)
        st.configure("TLabel", background=BG, foreground=TEXT)
        st.configure("Card.TLabel", background=SURFACE, foreground=TEXT_2, font=("Segoe UI", 10))
        st.configure("KpiValue.TLabel", background=SURFACE, foreground=TEXT, font=("Segoe UI", 22, "bold"))
        st.configure("Title.TLabel", font=("Segoe UI", 18, "bold"), foreground=ACCENT)
        st.configure("Muted.TLabel", foreground=MUTED)
        st.configure("Section.TLabel", background=SURFACE, foreground=ACCENT, font=("Segoe UI", 11, "bold"))
        st.configure("TButton", background=ACCENT, foreground="#111", borderwidth=0, padding=(12, 6),
                     font=("Segoe UI", 10, "bold"))
        st.map("TButton", background=[("active", "#ffd83d"), ("disabled", GRID)])
        st.configure("TCombobox", fieldbackground=SURFACE, background=SURFACE, foreground=TEXT, arrowcolor=TEXT)
        st.map("TCombobox", fieldbackground=[("readonly", SURFACE)], foreground=[("readonly", TEXT)],
               selectbackground=[("readonly", SURFACE)], selectforeground=[("readonly", TEXT)])
        self.option_add("*TCombobox*Listbox.background", SURFACE)
        self.option_add("*TCombobox*Listbox.foreground", TEXT)
        st.configure("Treeview", background=SURFACE, fieldbackground=SURFACE, foreground=TEXT, rowheight=24,
                     borderwidth=0)
        st.configure("Treeview.Heading", background=GRID, foreground=TEXT_2, relief="flat",
                     font=("Segoe UI", 9, "bold"))
        st.map("Treeview", background=[("selected", "#3a3520")])
        st.configure("Vertical.TScrollbar", background=GRID, troughcolor=SURFACE, arrowcolor=TEXT_2)

    def _build_header(self):
        bar = ttk.Frame(self, padding=(16, 12, 16, 4))
        bar.pack(fill="x")
        ttk.Label(bar, text="⚔ HELLDIVERS 2 — GUERRA GALÁCTICA", style="Title.TLabel").pack(side="left")

        right = ttk.Frame(bar)
        right.pack(side="right")
        self.status = ttk.Label(right, text="Conectando…", style="Muted.TLabel")
        self.status.pack(side="left", padx=(0, 16))
        ttk.Label(right, text="Ventana").pack(side="left", padx=(0, 4))
        cb_w = ttk.Combobox(right, textvariable=self.window, values=["1 h", "6 h", "24 h", "7 d", "Todo"],
                            width=6, state="readonly")
        cb_w.pack(side="left", padx=(0, 12))
        cb_w.bind("<<ComboboxSelected>>", lambda e: self._redraw())
        ttk.Label(right, text="Actualizar cada").pack(side="left", padx=(0, 4))
        cb = ttk.Combobox(right, textvariable=self.interval, values=list(INTERVALS), width=6, state="readonly")
        cb.pack(side="left", padx=(0, 12))
        cb.bind("<<ComboboxSelected>>", lambda e: self._schedule())
        self.btn = ttk.Button(right, text="Actualizar ahora", command=self.refresh)
        self.btn.pack(side="left")

    def _build_kpis(self):
        row = ttk.Frame(self, padding=(16, 4))
        row.pack(fill="x")
        self.kpi = {}
        for i, (key, label) in enumerate([
            ("players", "Helldivers en línea"),
            ("campaigns", "Campañas activas"),
            ("success", "Tasa de éxito de misiones"),
            ("missions", "Misiones ganadas"),
            ("deaths", "Muertes totales"),
        ]):
            card = ttk.Frame(row, style="Card.TFrame", padding=(14, 10))
            card.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 8, 0))
            row.columnconfigure(i, weight=1)
            ttk.Label(card, text=label, style="Card.TLabel").pack(anchor="w")
            val = ttk.Label(card, text="—", style="KpiValue.TLabel")
            val.pack(anchor="w")
            delta = ttk.Label(card, text="", style="Card.TLabel")
            delta.pack(anchor="w")
            self.kpi[key] = (val, delta)

    def _build_body(self):
        body = ttk.Frame(self, padding=(16, 8, 16, 16))
        body.pack(fill="both", expand=True)
        body.columnconfigure(0, weight=3)
        body.columnconfigure(1, weight=1)
        body.rowconfigure(0, weight=1)

        # Gráficas
        chart_card = ttk.Frame(body, style="Card.TFrame", padding=4)
        chart_card.grid(row=0, column=0, sticky="nsew")
        self.fig = Figure(facecolor=SURFACE, dpi=100)
        gs = self.fig.add_gridspec(2, 2, hspace=0.55, wspace=0.42, left=0.13, right=0.89, top=0.92, bottom=0.07)
        self.ax_total = self.fig.add_subplot(gs[0, 0])
        self.ax_front = self.fig.add_subplot(gs[0, 1])
        self.ax_top = self.fig.add_subplot(gs[1, 0])
        self.ax_lib = self.fig.add_subplot(gs[1, 1])
        self.canvas = FigureCanvasTkAgg(self.fig, master=chart_card)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)
        self.canvas.mpl_connect("motion_notify_event", self._on_hover)

        # Panel lateral: orden mayor + tabla de campañas
        side = ttk.Frame(body)
        side.grid(row=0, column=1, sticky="nsew", padx=(12, 0))
        side.rowconfigure(1, weight=1)
        side.columnconfigure(0, weight=1)

        mo = ttk.Frame(side, style="Card.TFrame", padding=12)
        mo.grid(row=0, column=0, sticky="ew")
        ttk.Label(mo, text="ORDEN MAYOR", style="Section.TLabel").pack(anchor="w")
        self.mo_text = tk.Text(mo, height=9, wrap="word", bg=SURFACE, fg=TEXT, relief="flat",
                               font=("Segoe UI", 10), highlightthickness=0, borderwidth=0)
        self.mo_text.pack(fill="x", pady=(6, 0))
        self.mo_text.configure(state="disabled")

        tbl = ttk.Frame(side, style="Card.TFrame", padding=12)
        tbl.grid(row=1, column=0, sticky="nsew", pady=(12, 0))
        ttk.Label(tbl, text="CAMPAÑAS", style="Section.TLabel").pack(anchor="w", pady=(0, 6))
        cols = ("planet", "faction", "players", "lib")
        self.tree = ttk.Treeview(tbl, columns=cols, show="headings", selectmode="browse")
        for c, txt, w, anchor in [("planet", "Planeta", 130, "w"), ("faction", "Enemigo", 90, "w"),
                                  ("players", "Jugadores", 80, "e"), ("lib", "Liberación", 80, "e")]:
            self.tree.heading(c, text=txt, command=lambda c=c: self._sort_tree(c))
            self.tree.column(c, width=w, anchor=anchor, stretch=c == "planet")
        self.tree.tag_configure("defense", background="#2a2218")
        sb = ttk.Scrollbar(tbl, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.tree.pack(fill="both", expand=True)
        self._sort_state = ("players", True)

    # ---- ciclo de refresco ----
    def refresh(self):
        if self.fetching:
            return
        self.fetching = True
        self.btn.state(["disabled"])
        self.status.configure(text="Descargando datos…")

        def worker():
            try:
                self.results.put(("ok", fetch_snapshot()))
            except Exception as exc:  # red, rate limit, JSON…
                self.results.put(("err", exc))

        threading.Thread(target=worker, daemon=True).start()

    def _poll_results(self):
        try:
            kind, payload = self.results.get_nowait()
        except queue.Empty:
            pass
        else:
            self.fetching = False
            self.btn.state(["!disabled"])
            if kind == "ok":
                prev = self.snapshot
                self.snapshot = payload
                self.history.add(payload)
                self._update_kpis(prev)
                self._update_major_order()
                self._update_tree()
                self._redraw()
            else:
                self.status.configure(text=f"Error: {payload}")
            self._schedule()
        self.after(200, self._poll_results)

    def _schedule(self):
        self.next_refresh = INTERVALS[self.interval.get()]

    def _tick(self):
        if not self.fetching and self.next_refresh > 0:
            self.next_refresh -= 1
            if self.snapshot:
                t = self.snapshot.fetched_at.astimezone().strftime("%H:%M:%S")
                self.status.configure(text=f"Última actualización {t} · próxima en {self.next_refresh}s")
            if self.next_refresh == 0:
                self.refresh()
        self.after(1000, self._tick)

    # ---- KPIs / paneles ----
    def _update_kpis(self, prev: Snapshot | None):
        s = self.snapshot
        values = {
            "players": (fmt_int(s.players), s.players - prev.players if prev else None),
            "campaigns": (str(len(s.campaigns)),
                          f"{sum(c.is_defense for c in s.campaigns)} en defensa"),
            "success": (f"{s.success_rate}%", f"{fmt_compact(s.missions_lost)} misiones perdidas"),
            "missions": (fmt_compact(s.missions_won), s.missions_won - prev.missions_won if prev else None),
            "deaths": (fmt_compact(s.deaths), s.deaths - prev.deaths if prev else None),
        }
        for key, (val, delta) in values.items():
            lbl, dlbl = self.kpi[key]
            lbl.configure(text=val)
            if isinstance(delta, int):
                arrow = "▲" if delta > 0 else "▼" if delta < 0 else "■"
                dlbl.configure(text=f"{arrow} {fmt_int(abs(delta))} desde la última lectura")
            else:
                dlbl.configure(text=delta or "")

    def _update_major_order(self):
        orders = self.snapshot.major_orders
        if not orders:
            text = "No hay ninguna Orden Mayor activa en este momento."
        else:
            parts = []
            for o in orders:
                title = o.get("title") or "Orden Mayor"
                brief = o.get("briefing") or o.get("description") or ""
                exp = o.get("expiration")
                line = f"{title}\n{brief}"
                if exp:
                    end = datetime.fromisoformat(exp.replace("Z", "+00:00"))
                    left = end - datetime.now(timezone.utc)
                    h = int(left.total_seconds() // 3600)
                    line += f"\n⏱ Expira en {h // 24}d {h % 24}h"
                parts.append(line)
            text = "\n\n".join(parts)
        self.mo_text.configure(state="normal")
        self.mo_text.delete("1.0", "end")
        self.mo_text.insert("1.0", text)
        self.mo_text.configure(state="disabled")

    def _update_tree(self):
        self.tree.delete(*self.tree.get_children())
        for i, c in enumerate(self.snapshot.campaigns):
            name = ("🛡 " if c.is_defense else "") + c.planet
            tags = (c.faction, "defense") if c.is_defense else (c.faction,)
            self.tree.insert("", "end", iid=str(i), tags=tags, values=(
                name, FACTION_ES.get(c.faction, c.faction), fmt_int(c.players), f"{c.liberation:.1f}%"))
        col, desc = self._sort_state
        self._sort_tree(col, keep=desc)

    def _sort_tree(self, col, keep=None):
        desc = keep if keep is not None else not (self._sort_state[0] == col and self._sort_state[1])
        self._sort_state = (col, desc)

        def key(iid):
            v = self.tree.set(iid, col)
            if col in ("players", "lib"):
                return float(v.replace(".", "").replace("%", "")) if col == "players" else float(v[:-1])
            return v.lower()

        for idx, iid in enumerate(sorted(self.tree.get_children(), key=key, reverse=desc)):
            self.tree.move(iid, "", idx)

    # ---- gráficas ----
    def _since(self):
        span = {"1 h": 1, "6 h": 6, "24 h": 24, "7 d": 168}.get(self.window.get())
        if span is None:
            return None
        from datetime import timedelta
        return datetime.now(timezone.utc) - timedelta(hours=span)

    def _style_ax(self, ax, title, subtitle=""):
        ax.set_facecolor(SURFACE)
        for side in ("top", "right", "left"):
            ax.spines[side].set_visible(False)
        ax.spines["bottom"].set_color(GRID)
        ax.tick_params(colors=MUTED, labelsize=8, length=0)
        ax.grid(True, axis="y", color=GRID, linewidth=0.8)
        ax.set_axisbelow(True)
        ax.set_title(title, loc="left", color=TEXT, fontsize=11, fontweight="bold", pad=18)
        if subtitle:
            ax.text(0, 1.03, subtitle, transform=ax.transAxes, color=MUTED, fontsize=8)

    def _redraw(self):
        if not self.snapshot:
            return
        s = self.snapshot
        since = self._since()
        for ax in (self.ax_total, self.ax_front, self.ax_top, self.ax_lib):
            ax.clear()
        self._hover_artists = []

        # 1) Jugadores totales en el tiempo
        ax = self.ax_total
        self._style_ax(ax, "Helldivers en línea", "Serie temporal capturada por esta app")
        xs, ys = self.history.series("players", since)
        xs = [x.astimezone() for x in xs]
        ax.plot(xs, ys, color=SERIES_TOTAL, linewidth=2, marker="o" if len(xs) < 30 else None, markersize=4)
        if len(xs) > 1:
            ax.fill_between(xs, ys, min(ys) * 0.98, color=SERIES_TOTAL, alpha=0.12, linewidth=0)
        if xs:
            ax.annotate(fmt_int(ys[-1]), (xs[-1], ys[-1]), xytext=(6, 0), textcoords="offset points",
                        color=TEXT, fontsize=9, va="center", fontweight="bold")
        self._time_axis(ax)
        ax._hover = ("line", [("Total", SERIES_TOTAL, xs, ys)])

        # 2) Jugadores por frente (facción) en el tiempo
        ax = self.ax_front
        self._style_ax(ax, "Jugadores por frente", "Suma de jugadores en campañas contra cada facción")
        series = []
        for f in FACTIONS:
            fx, fy = self.history.series(f, since)
            fx = [x.astimezone() for x in fx]
            ax.plot(fx, fy, color=FACTION_COLOR[f], linewidth=2, label=FACTION_ES[f],
                    marker="o" if len(fx) < 30 else None, markersize=4)
            if fx:
                ax.annotate(FACTION_ES[f], (fx[-1], fy[-1]), xytext=(6, 0), textcoords="offset points",
                            color=TEXT_2, fontsize=8, va="center")
            series.append((FACTION_ES[f], FACTION_COLOR[f], fx, fy))
        leg = ax.legend(loc="upper center", fontsize=8, frameon=False, ncol=3, bbox_to_anchor=(0.5, -0.1))
        for t in leg.get_texts():
            t.set_color(TEXT_2)
        self._time_axis(ax)
        ax._hover = ("line", series)

        # 3) Top 10 planetas por jugadores
        ax = self.ax_top
        self._style_ax(ax, "Top 10 planetas por jugadores", "Color = facción enemiga · ◆ = defensa")
        ax.grid(True, axis="x", color=GRID, linewidth=0.8)
        ax.grid(False, axis="y")
        top = s.campaigns[:10][::-1]
        names = [("◆ " if c.is_defense else "") + c.planet for c in top]
        bars = ax.barh(names, [c.players for c in top], color=[FACTION_COLOR.get(c.faction, MUTED) for c in top],
                       height=0.7, edgecolor=SURFACE, linewidth=2)
        for b, c in zip(bars, top):
            ax.text(b.get_width(), b.get_y() + b.get_height() / 2, f"  {fmt_compact(c.players)}",
                    va="center", color=TEXT_2, fontsize=8)
        ax.xaxis.set_major_formatter(FuncFormatter(fmt_compact))
        ax.tick_params(axis="y", labelcolor=TEXT_2, labelsize=8)
        ax.margins(x=0.12)
        ax._hover = ("bar", list(zip(bars, top)))

        # 4) Progreso de liberación/defensa de planetas en disputa
        ax = self.ax_lib
        self._style_ax(ax, "Progreso de liberación", "Planetas con avance > 0 % (◆ = defensa)")
        ax.grid(True, axis="x", color=GRID, linewidth=0.8)
        ax.grid(False, axis="y")
        contested = sorted([c for c in s.campaigns if c.liberation > 0.05], key=lambda c: c.liberation)[-10:]
        if contested:
            names = [("◆ " if c.is_defense else "") + c.planet for c in contested]
            ax.barh(names, [100] * len(contested), color=GRID, height=0.7)
            bars = ax.barh(names, [c.liberation for c in contested],
                           color=[FACTION_COLOR.get(c.faction, MUTED) for c in contested], height=0.7)
            for b, c in zip(bars, contested):
                ax.text(101, b.get_y() + b.get_height() / 2, f"{c.liberation:.1f}%", va="center",
                        color=TEXT_2, fontsize=8)
            ax._hover = ("bar", list(zip(bars, contested)))
        else:
            ax.text(0.5, 0.5, "Sin planetas en disputa", transform=ax.transAxes, ha="center", color=MUTED)
            ax._hover = None
        ax.set_xlim(0, 100)
        ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{int(v)}%"))
        ax.tick_params(axis="y", labelcolor=TEXT_2, labelsize=8)

        self.canvas.draw_idle()

    def _time_axis(self, ax):
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M", tz=datetime.now().astimezone().tzinfo))
        ax.xaxis.set_major_locator(mdates.AutoDateLocator(maxticks=6))
        ax.yaxis.set_major_formatter(FuncFormatter(fmt_compact))
        ax.margins(x=0.08)
        lines = [l for l in ax.get_lines() if len(l.get_xdata())]
        if lines and len(lines[0].get_xdata()) == 1:
            # Con un solo punto, abre una ventana de ±10 min para que el eje sea legible.
            x0 = mdates.date2num(lines[0].get_xdata()[0])
            ax.set_xlim(x0 - 10 / 1440, x0 + 10 / 1440)

    # ---- tooltips ----
    def _on_hover(self, event):
        for a in self._hover_artists:
            a.remove()
        self._hover_artists = []
        ax = event.inaxes
        info = getattr(ax, "_hover", None) if ax else None
        if not info or event.xdata is None:
            self.canvas.draw_idle()
            return
        kind, data = info
        if kind == "line":
            ref = next((d for d in data if d[2]), None)
            if ref:
                xnums = mdates.date2num(ref[2])
                i = min(range(len(xnums)), key=lambda k: abs(xnums[k] - event.xdata))
                x = ref[2][i]
                self._hover_artists.append(ax.axvline(x, color=MUTED, linewidth=1, linestyle="--"))
                lines = [x.strftime("%d/%m %H:%M:%S")]
                for name, color, xs, ys in data:
                    if i < len(ys):
                        self._hover_artists.append(ax.plot([xs[i]], [ys[i]], "o", color=color, markersize=8,
                                                           markeredgecolor=SURFACE, markeredgewidth=2)[0])
                        lines.append(f"{name}: {fmt_int(ys[i])}")
                self._tooltip(ax, event, "\n".join(lines))
        elif kind == "bar":
            for bar, c in data:
                if bar.contains(event)[0]:
                    tipo = "Defensa" if c.is_defense else "Liberación"
                    txt = (f"{c.planet} ({c.sector})\n{FACTION_ES.get(c.faction, c.faction)} · {c.biome}\n"
                           f"Jugadores: {fmt_int(c.players)}\n{tipo}: {c.liberation:.2f}%")
                    if c.ends:
                        left = c.ends - datetime.now(timezone.utc)
                        txt += f"\nTermina en {int(left.total_seconds() // 3600)}h"
                    self._tooltip(ax, event, txt)
                    break
        self.canvas.draw_idle()

    def _tooltip(self, ax, event, text):
        # Coloca el tooltip hacia el interior del eje para que no se salga.
        bbox = ax.get_window_extent()
        dx = -12 if event.x > bbox.x0 + bbox.width * 0.6 else 12
        ha = "right" if dx < 0 else "left"
        ann = ax.annotate(text, (event.xdata, event.ydata), xytext=(dx, 10), textcoords="offset points",
                          ha=ha, va="bottom", fontsize=8, color=TEXT, zorder=10,
                          bbox=dict(boxstyle="round,pad=0.5", fc="#26261f", ec=GRID))
        self._hover_artists.append(ann)


if __name__ == "__main__":
    Dashboard().mainloop()
