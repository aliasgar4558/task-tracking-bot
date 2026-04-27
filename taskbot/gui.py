#!/usr/bin/env python3
"""Desktop window for the Daily Task Logger (Material-inspired UI via CustomTkinter)."""

from __future__ import annotations

import sys
try:
    import tkinter as tk
    from tkinter import filedialog, messagebox
except ImportError as exc:
    pv = f"{sys.version_info.major}.{sys.version_info.minor}"
    print(
        "Tkinter is not available for this Python build (missing Tcl/Tk / _tkinter).\n\n"
        "macOS + Homebrew Python: install the matching Tk binding, then retry:\n"
        f"  brew install python-tk@{pv}\n\n"
        f"Original error: {exc}",
        file=sys.stderr,
    )
    sys.exit(1)

try:
    import customtkinter as ctk
except ImportError:
    print(
        "The GUI needs customtkinter. Install it with:\n"
        "  python3 -m pip install customtkinter\n",
        file=sys.stderr,
    )
    sys.exit(1)

from .core import (
    append_task,
    export_report_csv,
    export_report_xlsx,
    format_hours,
    get_today_date,
    list_projects,
    load_tasks,
    sorted_today_tasks,
    validate_efforts,
)

# Material-ish palette (light)
MD_TEAL = "#00897B"
MD_TEAL_DARK = "#00695C"
MD_SURFACE = "#FAFAFA"
MD_CARD = "#FFFFFF"
MD_OUTLINE = "#E0E0E0"
MD_OUTLINE_STRONG = "#BDBDBD"
MD_TEXT = "#212121"
MD_TEXT_SECONDARY = "#757575"
MD_SOFT_TEAL = "#E0F2F1"
IOS_GROUP_BG = "#F2F2F7"
IOS_FIELD_BG = "#FFFFFF"
ROW_ALT = "#F5F5F5"
REPORT_COLS = (
    ("seq", "#", 44, 0),
    ("project", "Project", 120, 1),
    ("title", "Task Title", 160, 2),
    ("desc", "Task Description", 260, 4),
    ("blockers", "Challenges / Blockers", 220, 3),
    ("hrs", "Efforts hrs", 88, 0),
)

APP_NAME = "TaskBot"


def _try_patch_macos_bundle_name() -> None:
    """Best-effort: show APP_NAME instead of Python in the menu bar when using python.org builds."""
    if sys.platform != "darwin":
        return
    try:
        from Foundation import NSBundle  # type: ignore[import-untyped]
    except ImportError:
        return
    bundle = NSBundle.mainBundle()
    if bundle is None:
        return
    info = bundle.localizedInfoDictionary() or bundle.infoDictionary()
    if not info:
        return
    try:
        if info.get("CFBundleName") == "Python":
            info["CFBundleName"] = APP_NAME
    except (KeyError, TypeError, AttributeError):
        pass


def _md_font(size: int, weight: str = "normal") -> ctk.CTkFont:
    return ctk.CTkFont(size=size, weight=weight)


class SmoothScrollableFrame(ctk.CTkScrollableFrame):
    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)
        self.bind_all("<Button-4>", self._mouse_wheel_all, add="+")
        self.bind_all("<Button-5>", self._mouse_wheel_all, add="+")

    def _mouse_wheel_all(self, event: tk.Event) -> None:
        if not self.check_if_master_is_canvas(event.widget):
            return
        if self._parent_canvas.yview() == (0.0, 1.0):
            return

        if getattr(event, "num", None) == 4:
            delta = -1.0
        elif getattr(event, "num", None) == 5:
            delta = 1.0
        else:
            raw_delta = getattr(event, "delta", 0)
            if sys.platform.startswith("win"):
                delta = -(raw_delta / 120)
            else:
                delta = -raw_delta

        first, _last = self._parent_canvas.yview()
        self._parent_canvas.yview_moveto(min(max(first + (delta * 0.035), 0.0), 1.0))


class TaskLoggerApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        ctk.set_appearance_mode("Light")
        ctk.set_default_color_theme("green")

        self.title(APP_NAME)
        self.minsize(820, 640)
        self.geometry("920x680")
        self.configure(fg_color=MD_SURFACE)

        self._setup_macos_menu_bar()

        self._status_var = tk.StringVar(value="")
        self._all_projects: list[str] = []
        self._autocomplete_lock = False
        self._task_count_var = tk.StringVar(value="0")
        self._project_count_var = tk.StringVar(value="0")
        self._today_hours_var = tk.StringVar(value="0")
        self._active_page = "log"
        self._report_dirty = True

        self._build_header()
        self._content = ctk.CTkFrame(self, corner_radius=0, fg_color=MD_SURFACE)
        self._content.pack(fill="both", expand=True)
        self._add_tab = ctk.CTkFrame(self._content, fg_color=IOS_GROUP_BG)
        self._report_tab = ctk.CTkFrame(self._content, fg_color=MD_CARD)

        self._build_add_tab()
        self._build_report_tab()
        self._show_add_tab()
        self.after(120, self._refresh_project_values)

    def _setup_macos_menu_bar(self) -> None:
        """Replace the default 'Python' application menu with APP_NAME (Tk + macOS)."""
        if sys.platform != "darwin":
            return
        menu = tk.Menu(self)
        python_menu = tk.Menu(menu, name="apple")
        menu.add_cascade(menu=python_menu)
        self.configure(menu=menu)
        python_menu.destroy()

        app_menu = tk.Menu(menu, tearoff=False)
        menu.add_cascade(menu=app_menu, label=APP_NAME)
        app_menu.add_command(label=f"About {APP_NAME}", command=self._mac_about)
        app_menu.add_separator()
        app_menu.add_command(label=f"Quit {APP_NAME}", command=self._mac_quit, accelerator="Cmd+Q")

        help_menu = tk.Menu(menu, tearoff=False)
        menu.add_cascade(menu=help_menu, label="Help")
        help_menu.add_command(label=f"{APP_NAME} Help", command=self._mac_about)

        self.bind("<Command-q>", lambda _e: self._mac_quit())

    def _mac_about(self) -> None:
        messagebox.showinfo(
            f"About {APP_NAME}",
            f"{APP_NAME}: daily task logger. Data stays on this machine.",
            parent=self,
        )

    def _mac_quit(self) -> None:
        self.quit()
        self.destroy()

    def _build_header(self) -> None:
        bar = ctk.CTkFrame(self, fg_color=MD_TEAL, corner_radius=0)
        bar.pack(fill="x")
        inner = ctk.CTkFrame(bar, fg_color="transparent")
        inner.pack(fill="x", padx=20, pady=(18, 16))
        title_area = ctk.CTkFrame(inner, fg_color="transparent")
        title_area.pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(title_area, text=APP_NAME, font=_md_font(22, "bold"), text_color="white").pack(anchor="w")
        ctk.CTkLabel(
            title_area,
            text="Log what you did today. Everything stays on this machine.",
            font=_md_font(13),
            text_color="#B2DFDB",
        ).pack(anchor="w", pady=(4, 0))
        actions = ctk.CTkFrame(inner, fg_color="transparent")
        actions.pack(side="right", padx=(16, 0))
        self._log_nav_btn = ctk.CTkButton(
            actions,
            text="+ Log task",
            command=self._show_add_tab,
            width=112,
            height=36,
            corner_radius=8,
            fg_color="white",
            text_color=MD_TEAL_DARK,
            hover_color=MD_SOFT_TEAL,
            font=_md_font(13, "bold"),
        )
        self._log_nav_btn.pack(side="left", padx=(0, 8))
        self._report_nav_btn = ctk.CTkButton(
            actions,
            text="▦ Report",
            command=self._show_report_tab,
            width=96,
            height=36,
            corner_radius=8,
            fg_color=MD_TEAL_DARK,
            hover_color="#004D40",
            font=_md_font(13, "bold"),
        )
        self._report_nav_btn.pack(side="left")

    @staticmethod
    def _set_scroll_canvas_bg(scroll: ctk.CTkScrollableFrame, color: str) -> None:
        canvas = getattr(scroll, "_parent_canvas", None)
        if canvas is not None:
            try:
                canvas.configure(bg=color, highlightthickness=0)
            except tk.TclError:
                pass

    def _build_add_tab(self) -> None:
        f = self._add_tab
        scroll = ctk.CTkScrollableFrame(f, fg_color=IOS_GROUP_BG, corner_radius=0)
        self._set_scroll_canvas_bg(scroll, IOS_GROUP_BG)
        scroll.pack(fill="both", expand=True, padx=16, pady=16)

        hero = ctk.CTkFrame(scroll, fg_color="transparent")
        hero.pack(fill="x", padx=8, pady=(0, 10))
        ctk.CTkLabel(hero, text="New task", font=_md_font(22, "bold"), text_color=MD_TEXT).pack(anchor="w")
        ctk.CTkLabel(
            hero,
            text="Capture the important bits, then save it to today's local report.",
            font=_md_font(12),
            text_color=MD_TEXT_SECONDARY,
        ).pack(anchor="w", pady=(4, 0))

        body = ctk.CTkFrame(scroll, fg_color="transparent")
        body.pack(fill="both", expand=True)
        body.columnconfigure(0, weight=2)
        body.columnconfigure(1, weight=1)

        self._project_var = tk.StringVar()
        basics_outer = ctk.CTkFrame(body, fg_color=IOS_FIELD_BG, corner_radius=14, border_width=1, border_color=MD_OUTLINE)
        basics_outer.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        ctk.CTkLabel(
            basics_outer,
            text="TASK",
            font=_md_font(11, "bold"),
            text_color=MD_TEXT_SECONDARY,
        ).pack(anchor="w", padx=14, pady=(10, 6))
        basics = ctk.CTkFrame(basics_outer, fg_color="transparent")
        basics.pack(fill="x", padx=14, pady=(0, 12))
        basics.columnconfigure(0, weight=3)
        basics.columnconfigure(1, weight=1)

        ctk.CTkLabel(basics, text="Project", font=_md_font(12, "bold"), text_color=MD_TEXT).grid(
            row=0, column=0, sticky="w", pady=(0, 6)
        )
        ctk.CTkLabel(basics, text="Efforts", font=_md_font(12, "bold"), text_color=MD_TEXT).grid(
            row=0, column=1, sticky="w", padx=(14, 0), pady=(0, 6)
        )
        self._project_box = ctk.CTkComboBox(
            basics,
            values=[],
            variable=self._project_var,
            height=40,
            corner_radius=10,
            border_width=1,
            fg_color=IOS_FIELD_BG,
        )
        self._project_box.grid(row=1, column=0, sticky="ew")
        self._project_var.trace_add("write", self._on_project_change)
        self._project_box.bind("<Alt-Down>", self._open_project_dropdown)
        self._project_box.bind("<Control-space>", self._open_project_dropdown)
        self._bind_editing_shortcuts(self._project_box)

        self._eff_var = tk.StringVar()
        self._eff_entry = ctk.CTkEntry(
            basics,
            textvariable=self._eff_var,
            height=40,
            corner_radius=10,
            border_width=1,
            fg_color=IOS_FIELD_BG,
            placeholder_text="2.5",
        )
        self._eff_entry.grid(row=1, column=1, sticky="ew", padx=(14, 0))
        self._bind_editing_shortcuts(self._eff_entry)

        ctk.CTkLabel(
            basics,
            text="Type a new project or pick from your history",
            font=_md_font(11),
            text_color=MD_TEXT_SECONDARY,
        ).grid(row=2, column=0, sticky="w", pady=(4, 0))
        ctk.CTkLabel(basics, text="Hours", font=_md_font(11), text_color=MD_TEXT_SECONDARY).grid(
            row=2, column=1, sticky="w", padx=(14, 0), pady=(4, 0)
        )

        ctk.CTkLabel(basics, text="Task title", font=_md_font(12, "bold"), text_color=MD_TEXT).grid(
            row=3, column=0, columnspan=2, sticky="w", pady=(10, 5)
        )
        self._title_var = tk.StringVar()
        self._title_entry = ctk.CTkEntry(
            basics,
            textvariable=self._title_var,
            height=42,
            corner_radius=10,
            border_width=1,
            fg_color=IOS_FIELD_BG,
            placeholder_text="What did you work on?",
        )
        self._title_entry.grid(row=4, column=0, columnspan=2, sticky="ew")
        self._bind_editing_shortcuts(self._title_entry)

        details = ctk.CTkFrame(basics_outer, fg_color="transparent")
        details.pack(fill="x", padx=16, pady=(0, 12))
        details.columnconfigure(0, weight=1)

        ctk.CTkLabel(details, text="Description", font=_md_font(12, "bold"), text_color=MD_TEXT).grid(
            row=0, column=0, sticky="w", pady=(0, 5)
        )
        self._desc_text = ctk.CTkTextbox(details, height=78, corner_radius=10, border_width=1, fg_color=IOS_FIELD_BG)
        self._desc_text.grid(row=1, column=0, sticky="ew")
        self._bind_editing_shortcuts(self._desc_text)

        ctk.CTkLabel(details, text="Blockers", font=_md_font(12, "bold"), text_color=MD_TEXT).grid(
            row=2, column=0, sticky="w", pady=(10, 5)
        )
        self._block_text = ctk.CTkTextbox(details, height=66, corner_radius=10, border_width=1, fg_color=IOS_FIELD_BG)
        self._block_text.grid(row=3, column=0, sticky="ew", pady=(0, 16))
        self._bind_editing_shortcuts(self._block_text)

        action_panel = ctk.CTkFrame(
            body,
            width=220,
            fg_color=IOS_FIELD_BG,
            corner_radius=14,
            border_width=1,
            border_color=MD_OUTLINE,
        )
        action_panel.grid(row=0, column=1, sticky="new")
        ctk.CTkLabel(
            action_panel,
            text="ACTIONS",
            font=_md_font(11, "bold"),
            text_color=MD_TEXT_SECONDARY,
        ).pack(anchor="w", padx=14, pady=(10, 8))
        ctk.CTkButton(
            action_panel,
            text="+ Save task",
            command=self._save_task,
            fg_color=MD_TEAL,
            hover_color=MD_TEAL_DARK,
            height=40,
            corner_radius=8,
            font=_md_font(13, "bold"),
        ).pack(fill="x", padx=14, pady=(0, 8))
        ctk.CTkButton(
            action_panel,
            text="× Clear",
            command=self._clear_and_status,
            fg_color=MD_OUTLINE,
            text_color=MD_TEXT,
            hover_color="#D0D0D0",
            height=40,
            corner_radius=8,
            font=_md_font(13),
        ).pack(fill="x", padx=14, pady=(0, 8))
        ctk.CTkButton(
            action_panel,
            text="▦ View report",
            command=self._show_report_tab,
            fg_color="transparent",
            text_color=MD_TEAL_DARK,
            hover_color=MD_SOFT_TEAL,
            border_width=1,
            border_color=MD_OUTLINE_STRONG,
            height=40,
            corner_radius=8,
            font=_md_font(13),
        ).pack(fill="x", padx=14, pady=(0, 10))

        status_card = ctk.CTkFrame(action_panel, fg_color="#E8F5E9", corner_radius=12, border_width=1, border_color="#C8E6C9")
        self._status_card = status_card
        ctk.CTkLabel(
            status_card,
            textvariable=self._status_var,
            font=_md_font(12),
            text_color="#2E7D32",
            anchor="w",
            justify="left",
            wraplength=170,
        ).pack(anchor="w", padx=12, pady=8)

        ctk.CTkLabel(
            action_panel,
            text="Data file: ~/.taskbot/task_logs.json",
            font=_md_font(11),
            text_color=MD_TEXT_SECONDARY,
            justify="left",
        ).pack(anchor="w", padx=14, pady=(2, 12))

    def _build_report_tab(self) -> None:
        f = self._report_tab
        ctk.CTkLabel(
            f,
            text="Grouped by project. Review today's work or export it when you're done.",
            font=_md_font(12),
            text_color=MD_TEXT_SECONDARY,
        ).pack(anchor="w", pady=(4, 8))

        metrics = ctk.CTkFrame(f, fg_color="transparent")
        metrics.pack(fill="x", pady=(0, 12))
        self._build_metric_card(metrics, "Tasks", self._task_count_var, "+", 0)
        self._build_metric_card(metrics, "Projects", self._project_count_var, "#", 1)
        self._build_metric_card(metrics, "Hours", self._today_hours_var, "h", 2)

        top = ctk.CTkFrame(f, fg_color="transparent")
        top.pack(fill="x", pady=(0, 8))

        self._date_var = tk.StringVar()
        ctk.CTkLabel(top, textvariable=self._date_var, font=_md_font(16, "bold"), text_color=MD_TEXT).pack(
            side="left"
        )
        ctk.CTkButton(
            top,
            text="⇩ Export",
            command=self._export_report,
            width=100,
            height=36,
            corner_radius=8,
            fg_color=MD_TEAL,
            hover_color=MD_TEAL_DARK,
        ).pack(side="right", padx=(8, 0))
        ctk.CTkButton(
            top,
            text="↻ Refresh",
            command=self._refresh_report,
            width=100,
            height=36,
            corner_radius=8,
            fg_color=MD_OUTLINE,
            text_color=MD_TEXT,
            hover_color="#D0D0D0",
        ).pack(side="right")

        table = ctk.CTkFrame(f, fg_color=MD_CARD, corner_radius=12, border_width=1, border_color=MD_OUTLINE)
        table.pack(fill="both", expand=True)

        header = ctk.CTkFrame(table, fg_color="#EEEEEE", corner_radius=8)
        header.pack(fill="x", padx=8, pady=(8, 0))
        self._configure_report_grid(header)
        for col, (_key, label, width, _weight) in enumerate(REPORT_COLS):
            ctk.CTkLabel(
                header,
                text=label,
                width=width,
                font=_md_font(11, "bold"),
                text_color=MD_TEXT,
                anchor="w",
            ).grid(row=0, column=col, sticky="ew", padx=6, pady=8)

        self._report_rows = SmoothScrollableFrame(table, fg_color=MD_CARD, corner_radius=0)
        self._set_scroll_canvas_bg(self._report_rows, MD_CARD)
        self._report_rows.pack(fill="both", expand=True, padx=8, pady=8)

        self._total_var = tk.StringVar(value="Total Efforts: —")
        ctk.CTkLabel(f, textvariable=self._total_var, font=_md_font(14, "bold"), text_color=MD_TEAL_DARK).pack(
            anchor="w", pady=(12, 8)
        )

    def _build_metric_card(
        self,
        parent: ctk.CTkFrame,
        label: str,
        value_var: tk.StringVar,
        icon: str,
        col: int,
    ) -> None:
        card = ctk.CTkFrame(parent, fg_color=MD_CARD, corner_radius=12, border_width=1, border_color=MD_OUTLINE)
        card.grid(row=0, column=col, sticky="ew", padx=(0, 10) if col < 2 else (0, 0))
        parent.columnconfigure(col, weight=1)

        row = ctk.CTkFrame(card, fg_color="transparent")
        row.pack(fill="x", padx=14, pady=12)
        badge = ctk.CTkLabel(
            row,
            text=icon,
            width=32,
            height=32,
            corner_radius=16,
            fg_color=MD_SOFT_TEAL,
            text_color=MD_TEAL_DARK,
            font=_md_font(14, "bold"),
        )
        badge.pack(side="left", padx=(0, 10))
        text = ctk.CTkFrame(row, fg_color="transparent")
        text.pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(text, text=label, font=_md_font(11), text_color=MD_TEXT_SECONDARY).pack(anchor="w")
        ctk.CTkLabel(text, textvariable=value_var, font=_md_font(20, "bold"), text_color=MD_TEXT).pack(anchor="w")

    def _configure_report_grid(self, frame: ctk.CTkFrame) -> None:
        for col, (_key, _label, _width, weight) in enumerate(REPORT_COLS):
            frame.columnconfigure(col, weight=weight, uniform="report")

    def _report_cell(self, parent: ctk.CTkFrame, value: object, col: int, *, bold: bool = False) -> None:
        _key, _label, width, _weight = REPORT_COLS[col]
        ctk.CTkLabel(
            parent,
            text="" if value is None else str(value),
            width=width,
            wraplength=max(40, width - 12),
            font=_md_font(11, "bold" if bold else "normal"),
            text_color=MD_TEXT,
            anchor="w",
            justify="left",
        ).grid(row=0, column=col, sticky="new", padx=6, pady=10)

    def _clear_report_rows(self) -> None:
        if not hasattr(self, "_report_rows"):
            return
        for child in self._report_rows.winfo_children():
            child.destroy()

    def _add_empty_report_row(self) -> None:
        row = ctk.CTkFrame(self._report_rows, fg_color=MD_CARD, corner_radius=8)
        row.pack(fill="x", pady=(0, 6))
        ctk.CTkLabel(
            row,
            text="No tasks for today.",
            font=_md_font(12),
            text_color=MD_TEXT_SECONDARY,
            anchor="w",
        ).pack(fill="x", padx=14, pady=14)

    def _add_report_row(self, seq: int, task: dict[str, object], hrs: float, is_odd: bool) -> None:
        row = ctk.CTkFrame(
            self._report_rows,
            fg_color=ROW_ALT if is_odd else MD_CARD,
            corner_radius=8,
            border_width=1,
            border_color="#EEEEEE",
        )
        row.pack(fill="x", pady=(0, 6))
        self._configure_report_grid(row)
        self._report_cell(row, seq, 0)
        self._report_cell(row, task.get("project", "-"), 1)
        self._report_cell(row, task.get("task_title", ""), 2, bold=True)
        self._report_cell(row, task.get("task_description", ""), 3)
        self._report_cell(row, task.get("blockers", ""), 4)
        self._report_cell(row, format_hours(hrs), 5)

    def _show_add_tab(self) -> None:
        self._show_page("log")
        if hasattr(self, "_title_entry"):
            try:
                self._title_entry.focus_set()
            except Exception:
                pass

    def _show_report_tab(self) -> None:
        self._show_page("report")
        if hasattr(self, "_report_rows"):
            if self._report_dirty:
                self._refresh_report()

    def _show_page(self, page: str) -> None:
        if not hasattr(self, "_add_tab") or not hasattr(self, "_report_tab"):
            return
        self._add_tab.pack_forget()
        self._report_tab.pack_forget()
        if page == "report":
            self._report_tab.pack(fill="both", expand=True, padx=16, pady=16)
        else:
            self._add_tab.pack(fill="both", expand=True)
            page = "log"
        self._active_page = page
        self._update_nav_buttons()

    def _update_nav_buttons(self) -> None:
        if not hasattr(self, "_log_nav_btn") or not hasattr(self, "_report_nav_btn"):
            return
        active = {
            "fg_color": "white",
            "text_color": MD_TEAL_DARK,
            "hover_color": MD_SOFT_TEAL,
        }
        inactive = {
            "fg_color": MD_TEAL_DARK,
            "text_color": "white",
            "hover_color": "#004D40",
        }
        self._log_nav_btn.configure(**(active if self._active_page == "log" else inactive))
        self._report_nav_btn.configure(**(active if self._active_page == "report" else inactive))

    def _clear_form(self) -> None:
        self._project_var.set("")
        self._title_var.set("")
        self._desc_text.delete("1.0", "end")
        self._block_text.delete("1.0", "end")
        self._eff_var.set("")
        try:
            self._title_entry.focus_set()
        except Exception:
            pass

    def _clear_and_status(self) -> None:
        self._status_var.set("")
        self._hide_status()
        self._clear_form()

    def _show_status(self, message: str) -> None:
        self._status_var.set(message)
        if hasattr(self, "_status_card") and not self._status_card.winfo_ismapped():
            self._status_card.pack(fill="x", padx=14, pady=(0, 8))

    def _hide_status(self) -> None:
        if hasattr(self, "_status_card"):
            self._status_card.pack_forget()

    def _refresh_project_values(self) -> None:
        current = ""
        try:
            current = self._project_var.get()
        except Exception:
            current = ""
        data = load_tasks()
        self._all_projects = list_projects(data)
        self._project_box.configure(values=self._all_projects)
        if current.strip():
            self._apply_project_filter()

    def _on_project_change(self, *_args: object) -> None:
        self._apply_project_filter()

    def _apply_project_filter(self) -> None:
        if self._autocomplete_lock:
            return
        typed = self._project_var.get()
        if not typed.strip():
            self._project_box.configure(values=self._all_projects)
            return
        needle = typed.strip().lower()
        matches = [p for p in self._all_projects if p.lower().startswith(needle)]
        if not matches:
            matches = [p for p in self._all_projects if needle in p.lower()]
        self._project_box.configure(values=matches if matches else self._all_projects)

    def _open_project_dropdown(self, _event: object | None = None) -> None:
        cb = self._project_box
        opener = getattr(cb, "_open_dropdown_menu", None)
        if callable(opener):
            try:
                opener()
                return
            except Exception:
                pass
        entry = getattr(cb, "_entry", None)
        if entry is not None:
            try:
                entry.focus_set()
                entry.event_generate("<Down>")
            except Exception:
                pass

    def _bind_editing_shortcuts(self, w: tk.Misc | ctk.CTkBaseClass) -> None:
        # CTkTextbox forwards bind() to inner tk.Text; macOS Tk often never fires
        # <Control-BackSpace> as a virtual event, so we use KeyPress + modifier bits.
        if isinstance(w, ctk.CTkTextbox):
            inner = w._textbox
            inner.bind("<KeyPress>", self._text_keypress_word_shortcuts, add=True)
            for seq in ("<Command-BackSpace>", "<Control-u>"):
                w.bind(seq, self._delete_to_line_start, add=True)
            return
        for seq in ("<Alt-BackSpace>", "<Control-BackSpace>"):
            w.bind(seq, self._delete_prev_word, add=True)
        for seq in ("<Alt-Delete>", "<Control-Delete>"):
            w.bind(seq, self._delete_next_word, add=True)
        for seq in ("<Command-BackSpace>", "<Control-u>"):
            w.bind(seq, self._delete_to_line_start, add=True)

    def _text_keypress_word_shortcuts(self, event: tk.Event) -> str | None:
        """Word delete on tk.Text: Ctrl/Option + BackSpace/Delete (Tk macOS skips <Control-BackSpace>)."""
        keysym = event.keysym
        if keysym not in ("BackSpace", "KP_BackSpace", "Delete", "KP_Delete"):
            return None
        text = event.widget
        if not isinstance(text, tk.Text):
            return None
        st = getattr(event, "state", 0)
        ctrl = bool(st & 0x0004)
        # Option as word-delete (common on macOS); bit varies by Tk build
        alt_like = bool(st & 0x0008) or bool(st & 0x0010)
        if not (ctrl or alt_like):
            return None
        if keysym in ("BackSpace", "KP_BackSpace"):
            return self._delete_prev_word(event)
        return self._delete_next_word(event)

    def _delete_prev_word(self, event: tk.Event) -> str:
        w = event.widget
        if isinstance(w, ctk.CTkTextbox):
            try:
                w.delete("insert wordstart", "insert")
            except tk.TclError:
                return "break"
            return "break"
        if isinstance(w, (tk.Text, tk.Entry)) or hasattr(w, "_entry"):
            inner = getattr(w, "_entry", None) or getattr(w, "_textbox", None) or w
            if isinstance(inner, tk.Text):
                try:
                    inner.delete("insert wordstart", "insert")
                except tk.TclError:
                    return "break"
                return "break"
            if isinstance(inner, tk.Entry):
                s = inner.get()
                i = int(inner.index(tk.INSERT))
                j = self._word_start_back(s, i)
                inner.delete(j, i)
                return "break"
        return "break"

    def _delete_next_word(self, event: tk.Event) -> str:
        w = event.widget
        if isinstance(w, ctk.CTkTextbox):
            try:
                w.delete("insert", "insert wordend")
            except tk.TclError:
                return "break"
            return "break"
        inner = getattr(w, "_entry", None) or getattr(w, "_textbox", None) or w
        if isinstance(inner, tk.Text):
            try:
                inner.delete("insert", "insert wordend")
            except tk.TclError:
                return "break"
            return "break"
        if isinstance(inner, tk.Entry):
            s = inner.get()
            i = int(inner.index(tk.INSERT))
            j = self._word_end_forward(s, i)
            inner.delete(i, j)
            return "break"
        return "break"

    def _delete_to_line_start(self, event: tk.Event) -> str:
        w = event.widget
        if isinstance(w, ctk.CTkTextbox):
            try:
                w.delete("insert linestart", "insert")
            except tk.TclError:
                return "break"
            return "break"
        inner = getattr(w, "_entry", None) or getattr(w, "_textbox", None) or w
        if isinstance(inner, tk.Text):
            try:
                inner.delete("insert linestart", "insert")
            except tk.TclError:
                return "break"
            return "break"
        if isinstance(inner, tk.Entry):
            i = int(inner.index(tk.INSERT))
            inner.delete(0, i)
            return "break"
        return "break"

    @staticmethod
    def _word_start_back(s: str, i: int) -> int:
        j = i
        while j > 0 and s[j - 1].isspace():
            j -= 1
        while j > 0 and (s[j - 1].isalnum() or s[j - 1] in ("_", "-", ".")):
            j -= 1
        if j == i and j > 0:
            j -= 1
        return j

    @staticmethod
    def _word_end_forward(s: str, i: int) -> int:
        j = i
        n = len(s)
        while j < n and s[j].isspace():
            j += 1
        while j < n and (s[j].isalnum() or s[j] in ("_", "-", ".")):
            j += 1
        if j == i and j < n:
            j += 1
        return j

    def _save_task(self) -> None:
        project = self._project_var.get()
        title = self._title_var.get().strip()
        if not title:
            messagebox.showerror("Missing title", "Task title is required.", parent=self)
            return

        desc = self._desc_text.get("1.0", "end")
        blockers = self._block_text.get("1.0", "end")
        raw_eff = self._eff_var.get()

        efforts = validate_efforts(raw_eff)
        if efforts is None:
            messagebox.showerror(
                "Invalid effort",
                "Efforts must be a non-negative number (for example 2 or 2.5).",
                parent=self,
            )
            return

        ok, msg = append_task(project, title, desc, blockers, efforts)
        if not ok:
            messagebox.showerror("Cannot save", msg, parent=self)
            return

        self._report_dirty = True
        if self._active_page == "report":
            self._refresh_report()
        self._show_status(msg)
        self._refresh_project_values()
        self._title_var.set("")
        self._desc_text.delete("1.0", "end")
        self._block_text.delete("1.0", "end")
        self._eff_var.set("")
        try:
            self._title_entry.focus_set()
        except Exception:
            pass

    def _refresh_report(self) -> None:
        data = load_tasks()
        got = sorted_today_tasks(data, group_by_project=True)
        self._clear_report_rows()

        if got is None:
            self._date_var.set(f"Date: {get_today_date()}")
            self._total_var.set("No tasks for today.")
            self._task_count_var.set("0")
            self._project_count_var.set("0")
            self._today_hours_var.set("0")
            self._add_empty_report_row()
            self._report_dirty = False
            return

        date_str, tasks = got
        self._date_var.set(f"Date: {date_str}")
        total = 0.0
        seq = 0
        projects: set[str] = set()
        for t in tasks:
            e = t.get("efforts_hrs")
            try:
                hrs = float(e) if e is not None else 0.0
            except (TypeError, ValueError):
                hrs = 0.0
            total += hrs
            project = str(t.get("project", "-") or "-").strip()
            if project and project != "-":
                projects.add(project.lower())
            seq += 1
            self._add_report_row(seq, t, hrs, is_odd=bool(seq % 2))
        self._total_var.set(f"Total Efforts: {format_hours(total)} hrs")
        self._task_count_var.set(str(seq))
        self._project_count_var.set(str(len(projects)))
        self._today_hours_var.set(format_hours(total))
        self._report_dirty = False

    def _export_report(self) -> None:
        data = load_tasks()
        got = sorted_today_tasks(data, group_by_project=True)
        if got is None:
            messagebox.showerror("Nothing to export", "No tasks found for today.", parent=self)
            return

        date_str, tasks = got
        default = f"task_report_{date_str}.xlsx"
        path = filedialog.asksaveasfilename(
            title="Export report",
            defaultextension=".xlsx",
            initialfile=default,
            filetypes=[("Excel (.xlsx)", "*.xlsx"), ("CSV (.csv)", "*.csv")],
        )
        if not path:
            return

        if path.lower().endswith(".csv"):
            ok, msg = export_report_csv(path, date_str, tasks)
        else:
            ok, msg = export_report_xlsx(path, date_str, tasks)
            if not ok:
                csv_path = path.rsplit(".", 1)[0] + ".csv"
                ok, msg = export_report_csv(csv_path, date_str, tasks)

        if ok:
            self._show_status(msg)
        else:
            messagebox.showerror("Export failed", msg, parent=self)


def main() -> None:
    _try_patch_macos_bundle_name()
    app = TaskLoggerApp()
    app.mainloop()


if __name__ == "__main__":
    main()
