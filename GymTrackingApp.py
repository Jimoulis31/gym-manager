import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog
import json
import os
import csv
from datetime import date, datetime
import calendar

try:
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    from matplotlib.figure import Figure
    import matplotlib.dates as mdates
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False

# ─── DATA FILES ───────────────────────────────────────────────────────────────
DATA_FILE      = "workouts.json"
TEMPLATES_FILE = "templates.json"
BODYWEIGHT_FILE= "bodyweight.json"

def load_json(path, default):
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    return default

def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

# ─── COLORS & FONTS ───────────────────────────────────────────────────────────
BG      = "#0f0f0f"
CARD    = "#1a1a1a"
CARD2   = "#222222"
ACCENT  = "#e8ff47"
ACCENT2 = "#ff6b35"
ACCENT3 = "#47c8ff"
GREEN   = "#4fffb0"
RED     = "#ff4f4f"
TEXT    = "#f0f0f0"
SUBTEXT = "#888888"
BORDER  = "#2a2a2a"

FONT_TITLE = ("Courier New", 22, "bold")
FONT_HEAD  = ("Courier New", 13, "bold")
FONT_BODY  = ("Courier New", 11)
FONT_SMALL = ("Courier New", 9)
FONT_BTN   = ("Courier New", 11, "bold")
FONT_TINY  = ("Courier New", 8)
FONT_TIMER = ("Courier New", 48, "bold")

# ─── HELPERS ──────────────────────────────────────────────────────────────────
def parse_date(s):
    try:
        return datetime.strptime(s, "%d/%m/%Y")
    except Exception:
        return None

def make_btn(parent, text, command, bg=CARD, fg=TEXT, padx=12, pady=6):
    return tk.Button(
        parent, text=text, command=command,
        bg=bg, fg=fg, font=FONT_BTN,
        relief="flat", bd=0, padx=padx, pady=pady,
        activebackground=ACCENT, activeforeground=BG,
        cursor="hand2"
    )

# ─── MAIN APP ─────────────────────────────────────────────────────────────────
class GymManagerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("GYM MANAGER")
        self.root.configure(bg=BG)
        self.root.geometry("1200x740")
        self.root.minsize(1000, 640)

        self.workouts    = load_json(DATA_FILE, [])
        self.templates   = load_json(TEMPLATES_FILE, [])
        self.bodyweights = load_json(BODYWEIGHT_FILE, [])

        self.selected_workout_index = None
        self.chart_canvas_widget    = None
        self.bw_chart_widget        = None

        self._apply_styles()
        self._build_ui()
        self._refresh_workout_list()

    # ── STYLES ────────────────────────────────────────────────────────────────
    def _apply_styles(self):
        s = ttk.Style()
        s.theme_use("clam")
        s.configure("TNotebook", background=BG, borderwidth=0)
        s.configure("TNotebook.Tab", background=CARD, foreground=SUBTEXT,
                    font=FONT_BTN, padding=[16, 8], borderwidth=0)
        s.map("TNotebook.Tab",
              background=[("selected", BG)],
              foreground=[("selected", ACCENT)])
        s.configure("Inner.TNotebook", background=BG, borderwidth=0)
        s.configure("Inner.TNotebook.Tab", background=CARD2, foreground=SUBTEXT,
                    font=FONT_SMALL, padding=[10, 5])
        s.map("Inner.TNotebook.Tab",
              background=[("selected", CARD)],
              foreground=[("selected", ACCENT3)])
        s.configure("Treeview",
                    background=CARD, foreground=TEXT,
                    fieldbackground=CARD, rowheight=30,
                    font=FONT_BODY, borderwidth=0)
        s.configure("Treeview.Heading",
                    background=BG, foreground=ACCENT,
                    font=FONT_SMALL, relief="flat", borderwidth=0)
        s.map("Treeview",
              background=[("selected", ACCENT)],
              foreground=[("selected", BG)])

    # ── UI ────────────────────────────────────────────────────────────────────
    def _build_ui(self):
        header = tk.Frame(self.root, bg=BG, pady=14)
        header.pack(fill="x", padx=24)
        tk.Label(header, text="GYM MANAGER", font=FONT_TITLE,
                 bg=BG, fg=ACCENT).pack(side="left")
        tk.Label(header, text=f"TODAY: {date.today().strftime('%d %b %Y').upper()}",
                 font=FONT_SMALL, bg=BG, fg=SUBTEXT).pack(side="right", pady=6)
        tk.Frame(self.root, bg=BORDER, height=1).pack(fill="x", padx=24)

        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=24, pady=12)

        self.tab_workouts  = tk.Frame(self.notebook, bg=BG)
        self.tab_progress  = tk.Frame(self.notebook, bg=BG)
        self.tab_prs       = tk.Frame(self.notebook, bg=BG)
        self.tab_calendar  = tk.Frame(self.notebook, bg=BG)
        self.tab_templates = tk.Frame(self.notebook, bg=BG)
        self.tab_bodyweight= tk.Frame(self.notebook, bg=BG)
        self.tab_timer     = tk.Frame(self.notebook, bg=BG)

        self.notebook.add(self.tab_workouts,   text="  WORKOUTS  ")
        self.notebook.add(self.tab_progress,   text="  PROGRESS  ")
        self.notebook.add(self.tab_prs,        text="  RECORDS   ")
        self.notebook.add(self.tab_calendar,   text="  CALENDAR  ")
        self.notebook.add(self.tab_templates,  text="  TEMPLATES ")
        self.notebook.add(self.tab_bodyweight, text="  BODY WEIGHT ")
        self.notebook.add(self.tab_timer,      text="  REST TIMER ")

        self.notebook.bind("<<NotebookTabChanged>>", self._on_tab_change)

        self._build_workouts_tab()
        self._build_progress_tab()
        self._build_prs_tab()
        self._build_calendar_tab()
        self._build_templates_tab()
        self._build_bodyweight_tab()
        self._build_timer_tab()

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 1 — WORKOUTS
    # ══════════════════════════════════════════════════════════════════════════
    def _build_workouts_tab(self):
        main = tk.Frame(self.tab_workouts, bg=BG)
        main.pack(fill="both", expand=True)
        self._build_left_panel(main)
        self._build_right_panel(main)

    def _build_left_panel(self, parent):
        left = tk.Frame(parent, bg=BG, width=270)
        left.pack(side="left", fill="y", padx=(0, 16))
        left.pack_propagate(False)

        tk.Label(left, text="WORKOUTS", font=FONT_HEAD,
                 bg=BG, fg=ACCENT).pack(anchor="w", pady=(4, 10))

        lf = tk.Frame(left, bg=BORDER, bd=1)
        lf.pack(fill="both", expand=True)
        sb = tk.Scrollbar(lf, bg=CARD, troughcolor=CARD, activebackground=ACCENT)
        sb.pack(side="right", fill="y")
        self.workout_listbox = tk.Listbox(
            lf, yscrollcommand=sb.set, bg=CARD, fg=TEXT,
            selectbackground=ACCENT, selectforeground=BG,
            font=FONT_BODY, borderwidth=0, highlightthickness=0,
            activestyle="none", cursor="hand2"
        )
        self.workout_listbox.pack(fill="both", expand=True)
        sb.config(command=self.workout_listbox.yview)
        self.workout_listbox.bind("<<ListboxSelect>>", self._on_workout_select)

        btn_row = tk.Frame(left, bg=BG)
        btn_row.pack(fill="x", pady=(10, 0))
        make_btn(btn_row, "+ NEW", self._add_workout,
                 bg=ACCENT, fg=BG).pack(side="left", fill="x", expand=True, padx=(0, 4))
        make_btn(btn_row, "TEMPLATE", self._new_from_template,
                 bg=ACCENT3, fg=BG).pack(side="left", padx=(0, 4))
        make_btn(btn_row, "DEL", self._delete_workout,
                 bg=CARD, fg=ACCENT2).pack(side="left")

        # Export button
        make_btn(left, "EXPORT ALL TO CSV", self._export_csv,
                 bg=CARD, fg=GREEN).pack(fill="x", pady=(8, 0))

    def _build_right_panel(self, parent):
        right = tk.Frame(parent, bg=BG)
        right.pack(side="left", fill="both", expand=True)

        title_row = tk.Frame(right, bg=BG)
        title_row.pack(fill="x", pady=(0, 8))
        self.workout_title_var = tk.StringVar(value="<- Select or create a workout")
        tk.Label(title_row, textvariable=self.workout_title_var,
                 font=FONT_HEAD, bg=BG, fg=TEXT).pack(side="left")
        make_btn(title_row, "SAVE AS TEMPLATE", self._save_as_template,
                 bg=CARD, fg=ACCENT).pack(side="right", padx=(6, 0))
        make_btn(title_row, "RENAME", self._rename_workout,
                 bg=CARD, fg=SUBTEXT).pack(side="right")

        self.inner_nb = ttk.Notebook(right, style="Inner.TNotebook")
        self.inner_nb.pack(fill="both", expand=True)

        self.exercises_frame = tk.Frame(self.inner_nb, bg=BG)
        self.notes_frame     = tk.Frame(self.inner_nb, bg=BG)
        self.inner_nb.add(self.exercises_frame, text="  EXERCISES  ")
        self.inner_nb.add(self.notes_frame,     text="  NOTES  ")

        self._build_exercises_panel()
        self._build_notes_panel()

    def _build_exercises_panel(self):
        hdr = tk.Frame(self.exercises_frame, bg=BG)
        hdr.pack(fill="x", pady=(6, 6))
        tk.Label(hdr, text="EXERCISES", font=FONT_SMALL,
                 bg=BG, fg=SUBTEXT).pack(side="left")
        make_btn(hdr, "+ ADD", self._add_exercise,
                 bg=CARD, fg=ACCENT).pack(side="right")

        tf = tk.Frame(self.exercises_frame, bg=BORDER, bd=1)
        tf.pack(fill="both", expand=True)

        cols = ("exercise", "sets", "reps", "kg", "pr")
        self.exercise_tree = ttk.Treeview(tf, columns=cols, show="headings", height=14)
        for col, label, width, anchor in [
            ("exercise", "EXERCISE", 220, "w"),
            ("sets",     "SETS",      70, "center"),
            ("reps",     "REPS",      70, "center"),
            ("kg",       "KG",        90, "center"),
            ("pr",       "PR",        80, "center"),
        ]:
            self.exercise_tree.heading(col, text=label)
            self.exercise_tree.column(col, width=width, anchor=anchor)

        self.exercise_tree.tag_configure("pr_row", foreground=ACCENT)
        sb2 = tk.Scrollbar(tf, command=self.exercise_tree.yview)
        sb2.pack(side="right", fill="y")
        self.exercise_tree.configure(yscrollcommand=sb2.set)
        self.exercise_tree.pack(fill="both", expand=True)
        self.exercise_tree.bind("<Double-1>", self._edit_exercise)
        self.exercise_tree.bind("<Delete>",   self._delete_exercise)

        tk.Label(self.exercises_frame,
                 text="Double-click to edit  |  Delete key to remove",
                 font=FONT_TINY, bg=BG, fg=SUBTEXT).pack(anchor="e", pady=(4, 0))

    def _build_notes_panel(self):
        tk.Label(self.notes_frame, text="WORKOUT NOTES", font=FONT_SMALL,
                 bg=BG, fg=SUBTEXT).pack(anchor="w", pady=(6, 4))
        tf = tk.Frame(self.notes_frame, bg=BORDER, bd=1)
        tf.pack(fill="both", expand=True)
        sb = tk.Scrollbar(tf)
        sb.pack(side="right", fill="y")
        self.notes_text = tk.Text(
            tf, bg=CARD, fg=TEXT, font=FONT_BODY,
            relief="flat", bd=6, wrap="word",
            insertbackground=ACCENT, yscrollcommand=sb.set
        )
        self.notes_text.pack(fill="both", expand=True)
        sb.config(command=self.notes_text.yview)
        self.notes_text.bind("<KeyRelease>", self._auto_save_notes)
        tk.Label(self.notes_frame, text="Notes are saved automatically.",
                 font=FONT_TINY, bg=BG, fg=SUBTEXT).pack(anchor="e", pady=(4, 0))

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 2 — PROGRESS
    # ══════════════════════════════════════════════════════════════════════════
    def _build_progress_tab(self):
        top = tk.Frame(self.tab_progress, bg=BG)
        top.pack(fill="x", pady=(4, 10))
        tk.Label(top, text="EXERCISE", font=FONT_SMALL,
                 bg=BG, fg=SUBTEXT).pack(side="left", padx=(0, 8))
        self.progress_exercise_var = tk.StringVar()
        self.progress_combo = ttk.Combobox(
            top, textvariable=self.progress_exercise_var,
            state="readonly", font=FONT_BODY, width=28
        )
        self.progress_combo.pack(side="left")
        self.progress_combo.bind("<<ComboboxSelected>>", self._refresh_progress)
        make_btn(top, "SHOW", self._refresh_progress,
                 bg=CARD, fg=ACCENT).pack(side="left", padx=10)

        paned = tk.PanedWindow(self.tab_progress, orient="vertical",
                               bg=BORDER, sashwidth=4)
        paned.pack(fill="both", expand=True)
        self.chart_frame = tk.Frame(paned, bg=BG)
        paned.add(self.chart_frame, minsize=240)
        list_outer = tk.Frame(paned, bg=BG)
        paned.add(list_outer, minsize=130)

        tk.Label(list_outer, text="ALL LOGGED ENTRIES", font=FONT_SMALL,
                 bg=BG, fg=SUBTEXT).pack(anchor="w", pady=(6, 4))
        tf = tk.Frame(list_outer, bg=BORDER, bd=1)
        tf.pack(fill="both", expand=True)
        cols = ("date", "workout", "sets", "reps", "kg")
        self.progress_tree = ttk.Treeview(tf, columns=cols, show="headings", height=5)
        for col, label, width in [
            ("date",    "DATE",    110), ("workout", "WORKOUT", 160),
            ("sets",    "SETS",     70), ("reps",    "REPS",     70),
            ("kg",      "KG",      100),
        ]:
            self.progress_tree.heading(col, text=label)
            self.progress_tree.column(col, width=width,
                                      anchor="w" if col == "workout" else "center")
        sb = tk.Scrollbar(tf, command=self.progress_tree.yview)
        sb.pack(side="right", fill="y")
        self.progress_tree.configure(yscrollcommand=sb.set)
        self.progress_tree.pack(fill="both", expand=True)

    def _gather_exercise_names(self):
        names = set()
        for w in self.workouts:
            for ex in w.get("exercises", []):
                names.add(ex["name"])
        return sorted(names)

    def _refresh_progress(self, event=None):
        self.progress_combo["values"] = self._gather_exercise_names()
        name = self.progress_exercise_var.get()
        if not name:
            return
        points = []
        for w in self.workouts:
            d = parse_date(w.get("date", ""))
            for ex in w.get("exercises", []):
                if ex["name"] == name and ex["kg"] != "":
                    try:
                        points.append((d, w["name"], ex["sets"], ex["reps"], float(ex["kg"])))
                    except ValueError:
                        pass
        points.sort(key=lambda x: x[0] or datetime.min)

        self.progress_tree.delete(*self.progress_tree.get_children())
        for d, wname, sets, reps, kg in points:
            self.progress_tree.insert("", "end", values=(
                d.strftime("%d/%m/%Y") if d else "?", wname, sets, reps, f"{kg} kg"
            ))

        if self.chart_canvas_widget:
            self.chart_canvas_widget.get_tk_widget().destroy()
            self.chart_canvas_widget = None
        for w in self.chart_frame.winfo_children():
            w.destroy()

        if not MATPLOTLIB_AVAILABLE:
            tk.Label(self.chart_frame,
                     text="Install matplotlib:\n  pip install matplotlib",
                     font=FONT_BODY, bg=BG, fg=ACCENT2, justify="center").pack(expand=True)
            return
        if not points:
            tk.Label(self.chart_frame, text="No weight data found.",
                     font=FONT_BODY, bg=BG, fg=SUBTEXT).pack(expand=True)
            return

        dates = [p[0] for p in points if p[0]]
        kgs   = [p[4] for p in points if p[0]]

        fig = Figure(figsize=(8, 3.0), dpi=96, facecolor=BG)
        ax  = fig.add_subplot(111)
        ax.set_facecolor(CARD)
        fig.subplots_adjust(left=0.08, right=0.97, top=0.88, bottom=0.22)
        ax.plot(dates, kgs, color=ACCENT, linewidth=2,
                marker="o", markersize=6, markerfacecolor=ACCENT2)
        if kgs:
            max_kg = max(kgs)
            max_i  = kgs.index(max_kg)
            ax.annotate(f"  ** PR: {max_kg} kg **",
                        xy=(dates[max_i], max_kg), xytext=(8, 6),
                        textcoords="offset points", color=ACCENT,
                        fontsize=8, fontfamily="Courier New")
        ax.set_title(f"{name.upper()} -- KG OVER TIME",
                     color=ACCENT, fontsize=10, fontfamily="Courier New")
        ax.tick_params(colors=SUBTEXT, labelsize=8)
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%d/%m/%y"))
        fig.autofmt_xdate(rotation=30)
        for spine in ax.spines.values():
            spine.set_edgecolor(BORDER)
        ax.grid(True, color=BORDER, linestyle="--", linewidth=0.5)

        canvas = FigureCanvasTkAgg(fig, master=self.chart_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)
        self.chart_canvas_widget = canvas

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 3 — PERSONAL RECORDS
    # ══════════════════════════════════════════════════════════════════════════
    def _build_prs_tab(self):
        hdr = tk.Frame(self.tab_prs, bg=BG)
        hdr.pack(fill="x", pady=(4, 10))
        tk.Label(hdr, text="PERSONAL RECORDS", font=FONT_HEAD,
                 bg=BG, fg=ACCENT).pack(side="left")
        make_btn(hdr, "REFRESH", self._refresh_prs,
                 bg=CARD, fg=ACCENT).pack(side="right")

        tf = tk.Frame(self.tab_prs, bg=BORDER, bd=1)
        tf.pack(fill="both", expand=True)
        cols = ("exercise", "max_kg", "sets", "reps", "date", "workout")
        self.prs_tree = ttk.Treeview(tf, columns=cols, show="headings")
        for col, label, width, anchor in [
            ("exercise", "EXERCISE", 200, "w"),
            ("max_kg",   "BEST KG",  100, "center"),
            ("sets",     "SETS",      70, "center"),
            ("reps",     "REPS",      70, "center"),
            ("date",     "DATE",     110, "center"),
            ("workout",  "WORKOUT",  160, "w"),
        ]:
            self.prs_tree.heading(col, text=label)
            self.prs_tree.column(col, width=width, anchor=anchor)
        self.prs_tree.tag_configure("pr", foreground=ACCENT)
        sb = tk.Scrollbar(tf, command=self.prs_tree.yview)
        sb.pack(side="right", fill="y")
        self.prs_tree.configure(yscrollcommand=sb.set)
        self.prs_tree.pack(fill="both", expand=True)
        tk.Label(self.tab_prs,
                 text="Your all-time heaviest lift per exercise.",
                 font=FONT_TINY, bg=BG, fg=SUBTEXT).pack(anchor="w", pady=(6, 0))

    def _refresh_prs(self):
        self.prs_tree.delete(*self.prs_tree.get_children())
        pr_map = {}
        for w in self.workouts:
            for ex in w.get("exercises", []):
                if ex["kg"] == "":
                    continue
                try:
                    kg = float(ex["kg"])
                except ValueError:
                    continue
                name = ex["name"]
                if name not in pr_map or kg > pr_map[name]["kg"]:
                    pr_map[name] = {"kg": kg, "sets": ex["sets"], "reps": ex["reps"],
                                    "date": w.get("date", "?"), "workout": w.get("name", "?")}
        for name, pr in sorted(pr_map.items()):
            self.prs_tree.insert("", "end", tags=("pr",), values=(
                name, f"{pr['kg']} kg", pr["sets"], pr["reps"], pr["date"], pr["workout"]
            ))

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 4 — CALENDAR
    # ══════════════════════════════════════════════════════════════════════════
    def _build_calendar_tab(self):
        hdr = tk.Frame(self.tab_calendar, bg=BG)
        hdr.pack(fill="x", pady=(4, 10))
        self.cal_year  = date.today().year
        self.cal_month = date.today().month
        make_btn(hdr, "<", self._cal_prev, bg=CARD, fg=TEXT).pack(side="left")
        self.cal_title_var = tk.StringVar()
        tk.Label(hdr, textvariable=self.cal_title_var, font=FONT_HEAD,
                 bg=BG, fg=ACCENT, width=22).pack(side="left", padx=10)
        make_btn(hdr, ">", self._cal_next,  bg=CARD, fg=TEXT).pack(side="left")
        make_btn(hdr, "TODAY", self._cal_today, bg=CARD, fg=ACCENT3).pack(side="left", padx=8)
        self.cal_grid = tk.Frame(self.tab_calendar, bg=BG)
        self.cal_grid.pack(fill="both", expand=True)
        tk.Frame(self.tab_calendar, bg=BORDER, height=1).pack(fill="x", pady=8)
        self.cal_detail_var = tk.StringVar(value="Click a day to see workouts.")
        tk.Label(self.tab_calendar, textvariable=self.cal_detail_var,
                 font=FONT_BODY, bg=BG, fg=TEXT, justify="left",
                 wraplength=900).pack(anchor="w", padx=4)
        self._render_calendar()

    def _render_calendar(self):
        for w in self.cal_grid.winfo_children():
            w.destroy()
        self.cal_title_var.set(
            f"{calendar.month_name[self.cal_month].upper()}  {self.cal_year}"
        )
        workout_dates = {}
        for w in self.workouts:
            d = parse_date(w.get("date", ""))
            if d:
                workout_dates.setdefault((d.year, d.month, d.day), []).append(w["name"])
        for col, day in enumerate(["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]):
            tk.Label(self.cal_grid, text=day, font=FONT_SMALL,
                     bg=BG, fg=SUBTEXT, width=11).grid(row=0, column=col, padx=2, pady=(0, 4))
        today = date.today()
        for row_i, week in enumerate(calendar.monthcalendar(self.cal_year, self.cal_month)):
            for col_i, day_num in enumerate(week):
                if day_num == 0:
                    tk.Label(self.cal_grid, text="", bg=BG,
                             width=11, height=3).grid(row=row_i+1, column=col_i, padx=2, pady=2)
                    continue
                key = (self.cal_year, self.cal_month, day_num)
                has_w    = key in workout_dates
                is_today = (self.cal_year == today.year and
                            self.cal_month == today.month and day_num == today.day)
                cell_bg = ACCENT if is_today else CARD2 if has_w else CARD
                cell_fg = BG     if is_today else GREEN if has_w else SUBTEXT
                tk.Button(
                    self.cal_grid, text=f"{day_num}\n{'*' if has_w else ''}",
                    bg=cell_bg, fg=cell_fg, font=FONT_SMALL, relief="flat", bd=0,
                    width=10, height=3,
                    cursor="hand2" if has_w or is_today else "arrow",
                    command=lambda k=key: self._cal_day_click(k)
                ).grid(row=row_i+1, column=col_i, padx=2, pady=2)

    def _cal_day_click(self, key):
        year, month, day = key
        workout_dates = {}
        for w in self.workouts:
            d = parse_date(w.get("date", ""))
            if d:
                workout_dates.setdefault((d.year, d.month, d.day), []).append(w["name"])
        names = workout_dates.get(key, [])
        detail = (f"{day:02d}/{month:02d}/{year}  --  " + "  |  ".join(names)
                  if names else f"{day:02d}/{month:02d}/{year}  --  No workouts logged.")
        self.cal_detail_var.set(detail)

    def _cal_prev(self):
        self.cal_month, self.cal_year = (12, self.cal_year - 1) if self.cal_month == 1 \
                                        else (self.cal_month - 1, self.cal_year)
        self._render_calendar()

    def _cal_next(self):
        self.cal_month, self.cal_year = (1, self.cal_year + 1) if self.cal_month == 12 \
                                        else (self.cal_month + 1, self.cal_year)
        self._render_calendar()

    def _cal_today(self):
        self.cal_year, self.cal_month = date.today().year, date.today().month
        self._render_calendar()

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 5 — TEMPLATES
    # ══════════════════════════════════════════════════════════════════════════
    def _build_templates_tab(self):
        hdr = tk.Frame(self.tab_templates, bg=BG)
        hdr.pack(fill="x", pady=(4, 10))
        tk.Label(hdr, text="WORKOUT TEMPLATES", font=FONT_HEAD,
                 bg=BG, fg=ACCENT).pack(side="left")
        make_btn(hdr, "DELETE TEMPLATE", self._delete_template,
                 bg=CARD, fg=ACCENT2).pack(side="right")

        main = tk.Frame(self.tab_templates, bg=BG)
        main.pack(fill="both", expand=True)

        # Left: template list
        left = tk.Frame(main, bg=BG, width=260)
        left.pack(side="left", fill="y", padx=(0, 16))
        left.pack_propagate(False)
        tk.Label(left, text="SAVED TEMPLATES", font=FONT_SMALL,
                 bg=BG, fg=SUBTEXT).pack(anchor="w", pady=(0, 6))
        lf = tk.Frame(left, bg=BORDER, bd=1)
        lf.pack(fill="both", expand=True)
        sb = tk.Scrollbar(lf, bg=CARD, troughcolor=CARD)
        sb.pack(side="right", fill="y")
        self.template_listbox = tk.Listbox(
            lf, yscrollcommand=sb.set, bg=CARD, fg=TEXT,
            selectbackground=ACCENT, selectforeground=BG,
            font=FONT_BODY, borderwidth=0, highlightthickness=0,
            activestyle="none", cursor="hand2"
        )
        self.template_listbox.pack(fill="both", expand=True)
        sb.config(command=self.template_listbox.yview)
        self.template_listbox.bind("<<ListboxSelect>>", self._on_template_select)

        make_btn(left, "USE THIS TEMPLATE", self._new_from_template,
                 bg=ACCENT, fg=BG).pack(fill="x", pady=(10, 0))

        # Right: template exercise preview
        right = tk.Frame(main, bg=BG)
        right.pack(side="left", fill="both", expand=True)
        self.template_name_var = tk.StringVar(value="<- Select a template to preview")
        tk.Label(right, textvariable=self.template_name_var,
                 font=FONT_HEAD, bg=BG, fg=TEXT).pack(anchor="w", pady=(0, 8))

        tf = tk.Frame(right, bg=BORDER, bd=1)
        tf.pack(fill="both", expand=True)
        cols = ("exercise", "sets", "reps", "kg")
        self.template_tree = ttk.Treeview(tf, columns=cols, show="headings")
        for col, label, width in [
            ("exercise", "EXERCISE", 220), ("sets", "SETS", 80),
            ("reps", "REPS", 80),          ("kg",   "KG",   90),
        ]:
            self.template_tree.heading(col, text=label)
            self.template_tree.column(col, width=width,
                                      anchor="w" if col == "exercise" else "center")
        sb2 = tk.Scrollbar(tf, command=self.template_tree.yview)
        sb2.pack(side="right", fill="y")
        self.template_tree.configure(yscrollcommand=sb2.set)
        self.template_tree.pack(fill="both", expand=True)

        self._refresh_template_list()

    def _refresh_template_list(self):
        self.template_listbox.delete(0, tk.END)
        for t in self.templates:
            self.template_listbox.insert(tk.END, f"  {t['name']}")

    def _on_template_select(self, event):
        sel = self.template_listbox.curselection()
        if not sel:
            return
        t = self.templates[sel[0]]
        self.template_name_var.set(f"TEMPLATE: {t['name'].upper()}")
        self.template_tree.delete(*self.template_tree.get_children())
        for ex in t.get("exercises", []):
            self.template_tree.insert("", "end", values=(
                ex["name"], ex["sets"], ex["reps"],
                f"{ex['kg']} kg" if ex["kg"] != "" else "-"
            ))

    def _save_as_template(self):
        if self.selected_workout_index is None:
            messagebox.showwarning("No Workout", "Select a workout first.")
            return
        workout = self.workouts[self.selected_workout_index]
        name = simpledialog.askstring(
            "Save Template", "Template name:",
            initialvalue=workout["name"], parent=self.root
        )
        if not name or not name.strip():
            return
        # Check for duplicate name
        for t in self.templates:
            if t["name"].lower() == name.strip().lower():
                if not messagebox.askyesno("Overwrite", f"Template '{name}' already exists. Overwrite?"):
                    return
                self.templates.remove(t)
                break
        self.templates.append({
            "name":      name.strip(),
            "exercises": [dict(ex) for ex in workout.get("exercises", [])]
        })
        save_json(TEMPLATES_FILE, self.templates)
        self._refresh_template_list()
        messagebox.showinfo("Saved", f"Template '{name.strip()}' saved!")

    def _new_from_template(self):
        if not self.templates:
            messagebox.showinfo("No Templates", "No templates saved yet.\nCreate a workout and use 'SAVE AS TEMPLATE'.")
            return
        sel = self.template_listbox.curselection()
        if not sel:
            # Try to pick from dropdown if not on templates tab
            names = [t["name"] for t in self.templates]
            chosen = simpledialog.askstring(
                "Load Template",
                "Template name:\n" + "\n".join(f"  {n}" for n in names),
                parent=self.root
            )
            if not chosen:
                return
            matches = [t for t in self.templates if t["name"].lower() == chosen.strip().lower()]
            if not matches:
                messagebox.showwarning("Not Found", f"No template named '{chosen}'.")
                return
            template = matches[0]
        else:
            template = self.templates[sel[0]]

        new_name = simpledialog.askstring(
            "New Workout from Template",
            f"Workout name (based on '{template['name']}'):",
            initialvalue=template["name"], parent=self.root
        )
        if not new_name or not new_name.strip():
            return

        self.workouts.append({
            "name":      new_name.strip(),
            "date":      date.today().strftime("%d/%m/%Y"),
            "exercises": [dict(ex) for ex in template.get("exercises", [])],
            "notes":     ""
        })
        save_json(DATA_FILE, self.workouts)
        self._refresh_workout_list()
        self.notebook.select(0)
        self.workout_listbox.select_set(tk.END)
        self.workout_listbox.event_generate("<<ListboxSelect>>")

    def _delete_template(self):
        sel = self.template_listbox.curselection()
        if not sel:
            messagebox.showwarning("No Selection", "Select a template first.")
            return
        name = self.templates[sel[0]]["name"]
        if messagebox.askyesno("Delete", f"Delete template '{name}'?"):
            self.templates.pop(sel[0])
            save_json(TEMPLATES_FILE, self.templates)
            self._refresh_template_list()
            self.template_tree.delete(*self.template_tree.get_children())
            self.template_name_var.set("<- Select a template to preview")

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 6 — BODY WEIGHT TRACKER
    # ══════════════════════════════════════════════════════════════════════════
    def _build_bodyweight_tab(self):
        hdr = tk.Frame(self.tab_bodyweight, bg=BG)
        hdr.pack(fill="x", pady=(4, 10))
        tk.Label(hdr, text="BODY WEIGHT TRACKER", font=FONT_HEAD,
                 bg=BG, fg=ACCENT).pack(side="left")

        # Input row
        input_row = tk.Frame(self.tab_bodyweight, bg=BG)
        input_row.pack(fill="x", pady=(0, 10))
        tk.Label(input_row, text="Weight (kg):", font=FONT_SMALL,
                 bg=BG, fg=SUBTEXT).pack(side="left", padx=(0, 8))
        self.bw_entry_var = tk.StringVar()
        tk.Entry(input_row, textvariable=self.bw_entry_var, bg=CARD, fg=TEXT,
                 font=FONT_BODY, relief="flat", insertbackground=ACCENT,
                 bd=4, width=10).pack(side="left", padx=(0, 8))
        tk.Label(input_row, text="Date (dd/mm/yyyy):", font=FONT_SMALL,
                 bg=BG, fg=SUBTEXT).pack(side="left", padx=(0, 8))
        self.bw_date_var = tk.StringVar(value=date.today().strftime("%d/%m/%Y"))
        tk.Entry(input_row, textvariable=self.bw_date_var, bg=CARD, fg=TEXT,
                 font=FONT_BODY, relief="flat", insertbackground=ACCENT,
                 bd=4, width=13).pack(side="left", padx=(0, 8))
        make_btn(input_row, "+ LOG WEIGHT", self._log_bodyweight,
                 bg=ACCENT, fg=BG).pack(side="left", padx=(0, 8))
        make_btn(input_row, "DELETE SELECTED", self._delete_bodyweight,
                 bg=CARD, fg=ACCENT2).pack(side="left")

        # Paned: chart top, list bottom
        paned = tk.PanedWindow(self.tab_bodyweight, orient="vertical",
                               bg=BORDER, sashwidth=4)
        paned.pack(fill="both", expand=True)

        self.bw_chart_frame = tk.Frame(paned, bg=BG)
        paned.add(self.bw_chart_frame, minsize=220)

        list_outer = tk.Frame(paned, bg=BG)
        paned.add(list_outer, minsize=120)

        tk.Label(list_outer, text="WEIGHT LOG", font=FONT_SMALL,
                 bg=BG, fg=SUBTEXT).pack(anchor="w", pady=(6, 4))
        tf = tk.Frame(list_outer, bg=BORDER, bd=1)
        tf.pack(fill="both", expand=True)
        cols = ("date", "kg")
        self.bw_tree = ttk.Treeview(tf, columns=cols, show="headings", height=5)
        self.bw_tree.heading("date", text="DATE")
        self.bw_tree.heading("kg",   text="WEIGHT (KG)")
        self.bw_tree.column("date", width=160, anchor="center")
        self.bw_tree.column("kg",   width=160, anchor="center")
        sb = tk.Scrollbar(tf, command=self.bw_tree.yview)
        sb.pack(side="right", fill="y")
        self.bw_tree.configure(yscrollcommand=sb.set)
        self.bw_tree.pack(fill="both", expand=True)

        self._refresh_bodyweight()

    def _log_bodyweight(self):
        kg_str = self.bw_entry_var.get().strip()
        d_str  = self.bw_date_var.get().strip()
        if not kg_str:
            messagebox.showwarning("Missing", "Enter a weight value.")
            return
        try:
            kg = float(kg_str)
        except ValueError:
            messagebox.showwarning("Invalid", "Weight must be a number.")
            return
        if not parse_date(d_str):
            messagebox.showwarning("Invalid", "Date must be in dd/mm/yyyy format.")
            return
        self.bodyweights.append({"date": d_str, "kg": kg})
        self.bodyweights.sort(key=lambda x: parse_date(x["date"]) or datetime.min)
        save_json(BODYWEIGHT_FILE, self.bodyweights)
        self.bw_entry_var.set("")
        self.bw_date_var.set(date.today().strftime("%d/%m/%Y"))
        self._refresh_bodyweight()

    def _delete_bodyweight(self):
        sel = self.bw_tree.focus()
        if not sel:
            messagebox.showwarning("No Selection", "Select a log entry first.")
            return
        idx = self.bw_tree.index(sel)
        if messagebox.askyesno("Delete", "Remove this weight entry?"):
            self.bodyweights.pop(idx)
            save_json(BODYWEIGHT_FILE, self.bodyweights)
            self._refresh_bodyweight()

    def _refresh_bodyweight(self):
        self.bw_tree.delete(*self.bw_tree.get_children())
        for entry in self.bodyweights:
            self.bw_tree.insert("", "end", values=(entry["date"], f"{entry['kg']} kg"))

        if self.bw_chart_widget:
            self.bw_chart_widget.get_tk_widget().destroy()
            self.bw_chart_widget = None
        for w in self.bw_chart_frame.winfo_children():
            w.destroy()

        if not MATPLOTLIB_AVAILABLE or not self.bodyweights:
            msg = ("Install matplotlib:\n  pip install matplotlib"
                   if not MATPLOTLIB_AVAILABLE else "No body weight entries yet.")
            tk.Label(self.bw_chart_frame, text=msg,
                     font=FONT_BODY, bg=BG, fg=SUBTEXT,
                     justify="center").pack(expand=True)
            return

        dates = [parse_date(e["date"]) for e in self.bodyweights if parse_date(e["date"])]
        kgs   = [e["kg"] for e in self.bodyweights if parse_date(e["date"])]

        fig = Figure(figsize=(8, 2.8), dpi=96, facecolor=BG)
        ax  = fig.add_subplot(111)
        ax.set_facecolor(CARD)
        fig.subplots_adjust(left=0.08, right=0.97, top=0.88, bottom=0.22)
        ax.plot(dates, kgs, color=ACCENT3, linewidth=2,
                marker="o", markersize=5, markerfacecolor=GREEN)
        ax.set_title("BODY WEIGHT OVER TIME",
                     color=ACCENT3, fontsize=10, fontfamily="Courier New")
        ax.tick_params(colors=SUBTEXT, labelsize=8)
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%d/%m/%y"))
        fig.autofmt_xdate(rotation=30)
        for spine in ax.spines.values():
            spine.set_edgecolor(BORDER)
        ax.grid(True, color=BORDER, linestyle="--", linewidth=0.5)

        canvas = FigureCanvasTkAgg(fig, master=self.bw_chart_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)
        self.bw_chart_widget = canvas

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 7 — REST TIMER
    # ══════════════════════════════════════════════════════════════════════════
    def _build_timer_tab(self):
        self.timer_seconds_left = 0
        self.timer_running      = False
        self.timer_job          = None
        self.timer_total        = 0

        outer = tk.Frame(self.tab_timer, bg=BG)
        outer.pack(expand=True)

        tk.Label(outer, text="REST TIMER", font=FONT_HEAD,
                 bg=BG, fg=ACCENT).pack(pady=(0, 16))

        # Countdown display
        self.timer_display_var = tk.StringVar(value="00:00")
        tk.Label(outer, textvariable=self.timer_display_var,
                 font=FONT_TIMER, bg=BG, fg=ACCENT).pack(pady=(0, 8))

        # Progress bar
        self.timer_progress = ttk.Progressbar(
            outer, orient="horizontal", length=400, mode="determinate"
        )
        style = ttk.Style()
        style.configure("green.Horizontal.TProgressbar",
                        troughcolor=CARD, background=ACCENT,
                        bordercolor=BORDER, lightcolor=ACCENT, darkcolor=ACCENT)
        self.timer_progress.configure(style="green.Horizontal.TProgressbar")
        self.timer_progress.pack(pady=(0, 20))

        # Preset buttons
        tk.Label(outer, text="QUICK PRESETS", font=FONT_SMALL,
                 bg=BG, fg=SUBTEXT).pack(pady=(0, 8))
        presets_row = tk.Frame(outer, bg=BG)
        presets_row.pack(pady=(0, 20))
        for label, secs in [("30s", 30), ("1 min", 60), ("90s", 90),
                             ("2 min", 120), ("3 min", 180)]:
            make_btn(presets_row, label,
                     lambda s=secs: self._timer_set(s),
                     bg=CARD2, fg=ACCENT).pack(side="left", padx=4)

        # Custom duration
        custom_row = tk.Frame(outer, bg=BG)
        custom_row.pack(pady=(0, 20))
        tk.Label(custom_row, text="Custom (seconds):", font=FONT_SMALL,
                 bg=BG, fg=SUBTEXT).pack(side="left", padx=(0, 8))
        self.timer_custom_var = tk.StringVar(value="60")
        tk.Entry(custom_row, textvariable=self.timer_custom_var,
                 bg=CARD, fg=TEXT, font=FONT_BODY, relief="flat",
                 insertbackground=ACCENT, bd=4, width=6).pack(side="left", padx=(0, 8))
        make_btn(custom_row, "SET", self._timer_set_custom,
                 bg=CARD, fg=ACCENT).pack(side="left")

        # Control buttons
        ctrl_row = tk.Frame(outer, bg=BG)
        ctrl_row.pack()
        self.timer_start_btn = make_btn(ctrl_row, "START",
                                        self._timer_start, bg=GREEN, fg=BG, padx=20, pady=10)
        self.timer_start_btn.pack(side="left", padx=6)
        make_btn(ctrl_row, "PAUSE", self._timer_pause,
                 bg=CARD, fg=TEXT, padx=20, pady=10).pack(side="left", padx=6)
        make_btn(ctrl_row, "RESET", self._timer_reset,
                 bg=CARD, fg=ACCENT2, padx=20, pady=10).pack(side="left", padx=6)

    def _timer_set(self, seconds):
        self._timer_reset()
        self.timer_seconds_left = seconds
        self.timer_total        = seconds
        self._timer_update_display()

    def _timer_set_custom(self):
        try:
            secs = int(self.timer_custom_var.get())
            if secs <= 0:
                raise ValueError
        except ValueError:
            messagebox.showwarning("Invalid", "Enter a positive whole number of seconds.")
            return
        self._timer_set(secs)

    def _timer_start(self):
        if self.timer_seconds_left <= 0:
            return
        self.timer_running = True
        self._timer_tick()

    def _timer_pause(self):
        self.timer_running = False
        if self.timer_job:
            self.root.after_cancel(self.timer_job)
            self.timer_job = None

    def _timer_reset(self):
        self._timer_pause()
        self.timer_seconds_left = self.timer_total
        self.timer_progress["value"] = 0
        self._timer_update_display()

    def _timer_tick(self):
        if not self.timer_running:
            return
        if self.timer_seconds_left <= 0:
            self.timer_running = False
            self.timer_display_var.set("DONE!")
            self.timer_progress["value"] = 100
            self.root.bell()
            return
        self.timer_seconds_left -= 1
        self._timer_update_display()
        pct = ((self.timer_total - self.timer_seconds_left) / self.timer_total * 100
               if self.timer_total > 0 else 0)
        self.timer_progress["value"] = pct
        self.timer_job = self.root.after(1000, self._timer_tick)

    def _timer_update_display(self):
        mins = self.timer_seconds_left // 60
        secs = self.timer_seconds_left % 60
        self.timer_display_var.set(f"{mins:02d}:{secs:02d}")

    # ══════════════════════════════════════════════════════════════════════════
    # EXPORT TO CSV
    # ══════════════════════════════════════════════════════════════════════════
    def _export_csv(self):
        if not self.workouts:
            messagebox.showinfo("Nothing to Export", "No workouts logged yet.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
            initialfile="gym_export.csv",
            title="Export Workouts to CSV"
        )
        if not path:
            return
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Workout", "Date", "Exercise", "Sets", "Reps", "KG", "Notes"])
            for w in self.workouts:
                notes = w.get("notes", "").replace("\n", " ")
                if w.get("exercises"):
                    for ex in w["exercises"]:
                        writer.writerow([
                            w["name"], w["date"],
                            ex["name"], ex["sets"], ex["reps"], ex["kg"],
                            notes
                        ])
                else:
                    writer.writerow([w["name"], w["date"], "", "", "", "", notes])
        messagebox.showinfo("Exported", f"Saved to:\n{path}")

    # ── TAB CHANGE ────────────────────────────────────────────────────────────
    def _on_tab_change(self, event):
        tab = self.notebook.index(self.notebook.select())
        if tab == 1:
            self.progress_combo["values"] = self._gather_exercise_names()
        elif tab == 2:
            self._refresh_prs()
        elif tab == 3:
            self._render_calendar()
        elif tab == 4:
            self._refresh_template_list()

    # ── REFRESH ───────────────────────────────────────────────────────────────
    def _refresh_workout_list(self):
        self.workout_listbox.delete(0, tk.END)
        for w in self.workouts:
            self.workout_listbox.insert(tk.END, f"  {w['name']}  ({w['date']})")

    def _refresh_exercise_table(self):
        self.exercise_tree.delete(*self.exercise_tree.get_children())
        if self.selected_workout_index is None:
            return
        workout = self.workouts[self.selected_workout_index]
        pr_map = {}
        for w in self.workouts:
            for ex in w.get("exercises", []):
                if ex["kg"] != "":
                    try:
                        pr_map[ex["name"]] = max(pr_map.get(ex["name"], 0), float(ex["kg"]))
                    except ValueError:
                        pass
        for ex in workout.get("exercises", []):
            kg_val = ex["kg"]
            is_pr  = False
            try:
                is_pr = kg_val != "" and float(kg_val) >= pr_map.get(ex["name"], -1)
            except ValueError:
                pass
            self.exercise_tree.insert("", "end",
                values=(ex["name"], ex["sets"], ex["reps"],
                        f"{kg_val} kg" if kg_val != "" else "-",
                        "** PR **" if is_pr else "-"),
                tags=("pr_row",) if is_pr else ()
            )

    def _auto_save_notes(self, event=None):
        if self.selected_workout_index is None:
            return
        self.workouts[self.selected_workout_index]["notes"] = \
            self.notes_text.get("1.0", tk.END).strip()
        save_json(DATA_FILE, self.workouts)

    # ── WORKOUT ACTIONS ───────────────────────────────────────────────────────
    def _on_workout_select(self, event):
        sel = self.workout_listbox.curselection()
        if not sel:
            return
        self.selected_workout_index = sel[0]
        workout = self.workouts[self.selected_workout_index]
        self.workout_title_var.set(f"{workout['name'].upper()}  --  {workout['date']}")
        self._refresh_exercise_table()
        self.notes_text.delete("1.0", tk.END)
        self.notes_text.insert("1.0", workout.get("notes", ""))

    def _add_workout(self):
        name = simpledialog.askstring(
            "New Workout", "Workout name:", parent=self.root
        )
        if not name or not name.strip():
            return
        self.workouts.append({
            "name": name.strip(), "date": date.today().strftime("%d/%m/%Y"),
            "exercises": [], "notes": ""
        })
        save_json(DATA_FILE, self.workouts)
        self._refresh_workout_list()
        self.workout_listbox.select_set(tk.END)
        self.workout_listbox.event_generate("<<ListboxSelect>>")

    def _delete_workout(self):
        if self.selected_workout_index is None:
            messagebox.showwarning("No Selection", "Select a workout first.")
            return
        name = self.workouts[self.selected_workout_index]["name"]
        if messagebox.askyesno("Delete", f"Delete '{name}'? Cannot be undone."):
            self.workouts.pop(self.selected_workout_index)
            save_json(DATA_FILE, self.workouts)
            self.selected_workout_index = None
            self.workout_title_var.set("<- Select or create a workout")
            self.exercise_tree.delete(*self.exercise_tree.get_children())
            self.notes_text.delete("1.0", tk.END)
            self._refresh_workout_list()

    def _rename_workout(self):
        if self.selected_workout_index is None:
            messagebox.showwarning("No Selection", "Select a workout first.")
            return
        current  = self.workouts[self.selected_workout_index]["name"]
        new_name = simpledialog.askstring("Rename", "New name:",
                                          initialvalue=current, parent=self.root)
        if new_name and new_name.strip():
            self.workouts[self.selected_workout_index]["name"] = new_name.strip()
            save_json(DATA_FILE, self.workouts)
            self._refresh_workout_list()
            self._on_workout_select(None)

    # ── EXERCISE ACTIONS ──────────────────────────────────────────────────────
    def _add_exercise(self):
        if self.selected_workout_index is None:
            messagebox.showwarning("No Workout", "Select a workout first.")
            return
        ExerciseDialog(self.root, on_save=self._save_new_exercise)

    def _save_new_exercise(self, data):
        self.workouts[self.selected_workout_index]["exercises"].append(data)
        save_json(DATA_FILE, self.workouts)
        self._refresh_exercise_table()

    def _edit_exercise(self, event):
        sel = self.exercise_tree.focus()
        if not sel:
            return
        idx = self.exercise_tree.index(sel)
        ex  = self.workouts[self.selected_workout_index]["exercises"][idx]
        ExerciseDialog(self.root, existing=ex,
                       on_save=lambda d: self._update_exercise(idx, d))

    def _update_exercise(self, idx, data):
        self.workouts[self.selected_workout_index]["exercises"][idx] = data
        save_json(DATA_FILE, self.workouts)
        self._refresh_exercise_table()

    def _delete_exercise(self, event):
        sel = self.exercise_tree.focus()
        if not sel:
            return
        idx = self.exercise_tree.index(sel)
        ex  = self.workouts[self.selected_workout_index]["exercises"][idx]
        if messagebox.askyesno("Delete Exercise", f"Remove '{ex['name']}'?"):
            self.workouts[self.selected_workout_index]["exercises"].pop(idx)
            save_json(DATA_FILE, self.workouts)
            self._refresh_exercise_table()


# ─── EXERCISE DIALOG ──────────────────────────────────────────────────────────
class ExerciseDialog:
    def __init__(self, parent, on_save, existing=None):
        self.on_save = on_save
        self.win = tk.Toplevel(parent)
        self.win.title("Exercise")
        self.win.configure(bg=BG)
        self.win.geometry("380x295")
        self.win.resizable(False, False)
        self.win.grab_set()

        tk.Label(self.win,
                 text="ADD EXERCISE" if not existing else "EDIT EXERCISE",
                 font=FONT_HEAD, bg=BG, fg=ACCENT).pack(pady=(20, 12))

        ff = tk.Frame(self.win, bg=BG)
        ff.pack(fill="x", padx=28)

        self.name_var = tk.StringVar(value=existing["name"] if existing else "")
        self.sets_var = tk.StringVar(value=str(existing["sets"]) if existing else "")
        self.reps_var = tk.StringVar(value=str(existing["reps"]) if existing else "")
        self.kg_var   = tk.StringVar(value=str(existing["kg"])   if existing else "")

        for label, var in [("Exercise name", self.name_var), ("Sets", self.sets_var),
                            ("Reps", self.reps_var),          ("Weight (kg)", self.kg_var)]:
            row = tk.Frame(ff, bg=BG)
            row.pack(fill="x", pady=4)
            tk.Label(row, text=label, font=FONT_SMALL, bg=BG,
                     fg=SUBTEXT, width=14, anchor="w").pack(side="left")
            tk.Entry(row, textvariable=var, bg=CARD, fg=TEXT,
                     font=FONT_BODY, relief="flat", insertbackground=ACCENT,
                     bd=4).pack(side="left", fill="x", expand=True)

        tk.Button(
            self.win, text="SAVE EXERCISE", command=self._save,
            bg=ACCENT, fg=BG, font=FONT_BTN, relief="flat", bd=0,
            padx=16, pady=8, activebackground=TEXT, cursor="hand2"
        ).pack(pady=(16, 0))

    def _save(self):
        name = self.name_var.get().strip()
        if not name:
            messagebox.showwarning("Missing", "Exercise name is required.", parent=self.win)
            return
        try:
            sets = int(self.sets_var.get()) if self.sets_var.get().strip() else 0
            reps = int(self.reps_var.get()) if self.reps_var.get().strip() else 0
        except ValueError:
            messagebox.showwarning("Invalid", "Sets and Reps must be whole numbers.",
                                   parent=self.win)
            return
        self.on_save({"name": name, "sets": sets, "reps": reps,
                      "kg": self.kg_var.get().strip()})
        self.win.destroy()


# ─── ENTRY POINT ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    root = tk.Tk()
    app = GymManagerApp(root)
    root.mainloop()