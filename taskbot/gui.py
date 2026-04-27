#!/usr/bin/env python3
"""Desktop window for the Daily Task Logger (Material-inspired UI via CustomTkinter)."""

from __future__ import annotations

import sys

try:
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk
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
MD_TEXT = "#212121"
MD_TEXT_SECONDARY = "#757575"
ROW_ALT = "#F5F5F5"

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

        self._build_header()
        self._tabview = ctk.CTkTabview(self, corner_radius=12, fg_color=MD_CARD, segmented_button_fg_color=MD_OUTLINE)
        self._tabview.pack(fill="both", expand=True, padx=16, pady=(0, 16))
        self._tabview.configure(command=self._on_tab_changed)

        self._tabview.add("Log task")
        self._tabview.add("Today's report")
        self._add_tab = self._tabview.tab("Log task")
        self._report_tab = self._tabview.tab("Today's report")

        self._setup_tree_style()
        self._build_add_tab()
        self._build_report_tab()

        self._refresh_project_values()

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
        ctk.CTkLabel(inner, text=APP_NAME, font=_md_font(22, "bold"), text_color="white").pack(anchor="w")
        ctk.CTkLabel(
            inner,
            text="Log what you did today. Everything stays on this machine.",
            font=_md_font(13),
            text_color="#B2DFDB",
        ).pack(anchor="w", pady=(4, 0))

    def _setup_tree_style(self) -> None:
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure(
            "Material.Treeview",
            background="#FFFFFF",
            fieldbackground="#FFFFFF",
            foreground=MD_TEXT,
            rowheight=28,
            font=("Segoe UI", 11) if sys.platform == "win32" else ("Helvetica Neue", 11),
        )
        style.configure(
            "Material.Treeview.Heading",
            background="#EEEEEE",
            foreground=MD_TEXT,
            relief="flat",
            font=("Segoe UI", 10, "bold") if sys.platform == "win32" else ("Helvetica Neue", 10, "bold"),
        )
        style.map(
            "Material.Treeview",
            background=[("selected", MD_TEAL)],
            foreground=[("selected", "white")],
        )

    def _build_add_tab(self) -> None:
        f = self._add_tab
        scroll = ctk.CTkScrollableFrame(f, fg_color="transparent")
        scroll.pack(fill="both", expand=True)

        ctk.CTkLabel(
            scroll,
            text="Fill in a task and save. Switch to Today's report to review or export.",
            font=_md_font(12),
            text_color=MD_TEXT_SECONDARY,
        ).pack(anchor="w", pady=(4, 12))

        self._project_var = tk.StringVar()
        basics_outer = ctk.CTkFrame(scroll, fg_color=MD_CARD, corner_radius=12, border_width=1, border_color=MD_OUTLINE)
        basics_outer.pack(fill="x", pady=(0, 12))
        ctk.CTkLabel(
            basics_outer,
            text="What you're working on",
            font=_md_font(13, "bold"),
            text_color=MD_TEXT_SECONDARY,
        ).pack(anchor="w", padx=16, pady=(14, 8))
        basics = ctk.CTkFrame(basics_outer, fg_color="transparent")
        basics.pack(fill="x", padx=16, pady=(0, 14))

        ctk.CTkLabel(basics, text="Project", font=_md_font(12, "bold")).grid(row=0, column=0, sticky="nw")
        self._project_box = ctk.CTkComboBox(
            basics,
            values=[],
            variable=self._project_var,
            width=560,
            height=36,
            corner_radius=8,
            border_width=1,
        )
        self._project_box.grid(row=0, column=1, sticky="ew", pady=(0, 4))
        self._refresh_project_values()
        self._project_var.trace_add("write", self._on_project_change)
        self._project_box.bind("<Alt-Down>", self._open_project_dropdown)
        self._project_box.bind("<Control-space>", self._open_project_dropdown)
        self._bind_editing_shortcuts(self._project_box)
        ctk.CTkLabel(basics, text="Optional — type a new name or pick from the list", font=_md_font(11), text_color=MD_TEXT_SECONDARY).grid(
            row=1, column=1, sticky="w"
        )

        ctk.CTkLabel(basics, text="Task title", font=_md_font(12, "bold")).grid(row=2, column=0, sticky="nw", pady=(12, 0))
        self._title_var = tk.StringVar()
        self._title_entry = ctk.CTkEntry(basics, textvariable=self._title_var, width=560, height=36, corner_radius=8)
        self._title_entry.grid(row=2, column=1, sticky="ew", pady=(12, 0))
        self._bind_editing_shortcuts(self._title_entry)
        basics.columnconfigure(1, weight=1)

        details_outer = ctk.CTkFrame(scroll, fg_color=MD_CARD, corner_radius=12, border_width=1, border_color=MD_OUTLINE)
        details_outer.pack(fill="x", pady=(0, 12))
        ctk.CTkLabel(
            details_outer,
            text="Details (optional)",
            font=_md_font(13, "bold"),
            text_color=MD_TEXT_SECONDARY,
        ).pack(anchor="w", padx=16, pady=(14, 8))
        details = ctk.CTkFrame(details_outer, fg_color="transparent")
        details.pack(fill="x", padx=16, pady=(0, 14))

        ctk.CTkLabel(details, text="Description", font=_md_font(12, "bold")).grid(row=0, column=0, sticky="nw")
        self._desc_text = ctk.CTkTextbox(details, width=560, height=110, corner_radius=8, border_width=1)
        self._desc_text.grid(row=0, column=1, sticky="ew", pady=(0, 10))
        self._bind_editing_shortcuts(self._desc_text)

        ctk.CTkLabel(details, text="Blockers", font=_md_font(12, "bold")).grid(row=1, column=0, sticky="nw")
        self._block_text = ctk.CTkTextbox(details, width=560, height=88, corner_radius=8, border_width=1)
        self._block_text.grid(row=1, column=1, sticky="ew")
        self._bind_editing_shortcuts(self._block_text)
        details.columnconfigure(1, weight=1)

        time_outer = ctk.CTkFrame(scroll, fg_color=MD_CARD, corner_radius=12, border_width=1, border_color=MD_OUTLINE)
        time_outer.pack(fill="x", pady=(0, 12))
        ctk.CTkLabel(time_outer, text="Time", font=_md_font(13, "bold"), text_color=MD_TEXT_SECONDARY).pack(
            anchor="w", padx=16, pady=(14, 8)
        )
        time_row = ctk.CTkFrame(time_outer, fg_color="transparent")
        time_row.pack(fill="x", padx=16, pady=(0, 14))
        ctk.CTkLabel(time_row, text="Efforts (hours)", font=_md_font(12, "bold")).pack(side="left", padx=(0, 12))
        self._eff_var = tk.StringVar()
        self._eff_entry = ctk.CTkEntry(time_row, textvariable=self._eff_var, width=120, height=36, corner_radius=8)
        self._eff_entry.pack(side="left")
        self._bind_editing_shortcuts(self._eff_entry)
        ctk.CTkLabel(time_row, text="  e.g. 2 or 2.5", font=_md_font(11), text_color=MD_TEXT_SECONDARY).pack(side="left", padx=(12, 0))

        btn_row = ctk.CTkFrame(scroll, fg_color="transparent")
        btn_row.pack(fill="x", pady=(4, 12))
        ctk.CTkButton(
            btn_row,
            text="SAVE TASK",
            command=self._save_task,
            fg_color=MD_TEAL,
            hover_color=MD_TEAL_DARK,
            height=42,
            corner_radius=8,
            font=_md_font(13, "bold"),
        ).pack(side="left")
        ctk.CTkButton(
            btn_row,
            text="Clear form",
            command=self._clear_and_status,
            fg_color=MD_OUTLINE,
            text_color=MD_TEXT,
            hover_color="#D0D0D0",
            height=42,
            corner_radius=8,
            font=_md_font(13),
        ).pack(side="left", padx=(12, 0))

        status_card = ctk.CTkFrame(scroll, fg_color="#E8F5E9", corner_radius=10, border_width=1, border_color="#C8E6C9")
        status_card.pack(fill="x", pady=(8, 8))
        ctk.CTkLabel(
            status_card,
            textvariable=self._status_var,
            font=_md_font(12),
            text_color="#2E7D32",
            anchor="w",
            justify="left",
        ).pack(anchor="w", padx=14, pady=12)

        ctk.CTkLabel(
            scroll,
            text="Data file (installed): ~/.taskbot/task_logs.json",
            font=_md_font(11),
            text_color=MD_TEXT_SECONDARY,
        ).pack(anchor="w", pady=(0, 8))

    def _build_report_tab(self) -> None:
        f = self._report_tab
        ctk.CTkLabel(
            f,
            text="Grouped by project. Export to Excel or CSV.",
            font=_md_font(12),
            text_color=MD_TEXT_SECONDARY,
        ).pack(anchor="w", pady=(4, 8))

        top = ctk.CTkFrame(f, fg_color="transparent")
        top.pack(fill="x", pady=(0, 8))

        self._date_var = tk.StringVar()
        ctk.CTkLabel(top, textvariable=self._date_var, font=_md_font(16, "bold"), text_color=MD_TEXT).pack(
            side="left"
        )
        ctk.CTkButton(
            top,
            text="Export",
            command=self._export_report,
            width=100,
            height=36,
            corner_radius=8,
            fg_color=MD_TEAL,
            hover_color=MD_TEAL_DARK,
        ).pack(side="right", padx=(8, 0))
        ctk.CTkButton(
            top,
            text="Refresh",
            command=self._refresh_report,
            width=100,
            height=36,
            corner_radius=8,
            fg_color=MD_OUTLINE,
            text_color=MD_TEXT,
            hover_color="#D0D0D0",
        ).pack(side="right")

        cols = ("seq", "project", "title", "desc", "blockers", "hrs")
        tree_wrap = ctk.CTkFrame(f, fg_color=MD_CARD, corner_radius=12, border_width=1, border_color=MD_OUTLINE)
        tree_wrap.pack(fill="both", expand=True)

        inner = tk.Frame(tree_wrap, bg="#FFFFFF")
        inner.pack(fill="both", expand=True, padx=8, pady=8)

        self._tree = ttk.Treeview(
            inner,
            columns=cols,
            show="headings",
            height=16,
            selectmode="browse",
            style="Material.Treeview",
        )
        self._tree.tag_configure("odd", background=ROW_ALT)
        self._tree.tag_configure("even", background="#FFFFFF")
        self._tree.heading("seq", text="#")
        self._tree.heading("project", text="Project")
        self._tree.heading("title", text="Task Title")
        self._tree.heading("desc", text="Task Description")
        self._tree.heading("blockers", text="Challenges / Blockers")
        self._tree.heading("hrs", text="Efforts hrs")

        self._tree.column("seq", width=44, anchor="center", stretch=False)
        self._tree.column("project", width=120, stretch=True)
        self._tree.column("title", width=140, stretch=True)
        self._tree.column("desc", width=160, stretch=True)
        self._tree.column("blockers", width=130, stretch=True)
        self._tree.column("hrs", width=88, anchor="e", stretch=False)

        vsb = ttk.Scrollbar(inner, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=vsb.set)
        self._tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        self._total_var = tk.StringVar(value="Total Efforts: —")
        ctk.CTkLabel(f, textvariable=self._total_var, font=_md_font(14, "bold"), text_color=MD_TEAL_DARK).pack(
            anchor="w", pady=(12, 8)
        )

        self._refresh_report()

    def _on_tab_changed(self) -> None:
        try:
            name = self._tabview.get()
        except Exception:
            return
        if name == "Today's report":
            self._refresh_report()

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
        self._clear_form()

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

        self._refresh_report()
        self._status_var.set(msg)
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
        for item in self._tree.get_children():
            self._tree.delete(item)

        if got is None:
            self._date_var.set(f"Date: {get_today_date()}")
            self._total_var.set("No tasks for today.")
            return

        date_str, tasks = got
        self._date_var.set(f"Date: {date_str}")
        total = 0.0
        seq = 0
        for t in tasks:
            e = t.get("efforts_hrs")
            try:
                hrs = float(e) if e is not None else 0.0
            except (TypeError, ValueError):
                hrs = 0.0
            total += hrs
            seq += 1
            tag = "odd" if seq % 2 else "even"
            self._tree.insert(
                "",
                tk.END,
                values=(
                    seq,
                    t.get("project", "-"),
                    t.get("task_title", ""),
                    t.get("task_description", ""),
                    t.get("blockers", ""),
                    format_hours(hrs),
                ),
                tags=(tag,),
            )
        self._total_var.set(f"Total Efforts: {format_hours(total)} hrs")

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
            self._status_var.set(msg)
        else:
            messagebox.showerror("Export failed", msg, parent=self)


def main() -> None:
    _try_patch_macos_bundle_name()
    app = TaskLoggerApp()
    app.mainloop()


if __name__ == "__main__":
    main()
