#!/usr/bin/env python3
"""Desktop window for the Daily Task Logger (tkinter)."""

from __future__ import annotations

import sys

try:
    import tkinter as tk
    from tkinter import messagebox, ttk
    from tkinter import filedialog
except ImportError as exc:
    pv = f"{sys.version_info.major}.{sys.version_info.minor}"
    print(
        "Tkinter is not available for this Python build (missing Tcl/Tk / _tkinter).\n\n"
        "macOS + Homebrew Python: install the matching Tk binding, then retry:\n"
        f"  brew install python-tk@{pv}\n"
        "  # If `python3 gui.py` still fails, use that formula's Python:\n"
        f'  "$(brew --prefix python-tk@{pv})/bin/python3" gui.py\n\n'
        "Alternatively install Python from https://www.python.org/downloads/ "
        "(installer bundles Tk).\n\n"
        f"Original error: {exc}",
        file=sys.stderr,
    )
    sys.exit(1)

from core import (
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


class TaskLoggerApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Daily Task Logger")
        self.minsize(720, 520)
        self.geometry("840x560")
        self._status_var = tk.StringVar(value="")
        self._all_projects: list[str] = []
        self._autocomplete_lock = False

        self._notebook = ttk.Notebook(self)
        self._notebook.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        self._add_tab = ttk.Frame(self._notebook, padding=8)
        self._report_tab = ttk.Frame(self._notebook, padding=8)
        self._notebook.add(self._add_tab, text="Add task")
        self._notebook.add(self._report_tab, text="Today's report")

        self._build_add_tab()
        self._build_report_tab()

        self._notebook.bind("<<NotebookTabChanged>>", self._on_tab_changed)
        self._refresh_project_values()

    def _build_add_tab(self) -> None:
        f = self._add_tab
        row = 0

        ttk.Label(f, text="Project:").grid(row=row, column=0, sticky="nw", pady=(0, 4))
        self._project_var = tk.StringVar()
        self._project_box = ttk.Combobox(
            f,
            textvariable=self._project_var,
            width=54,
            state="normal",
            postcommand=self._project_postcommand,
        )
        self._project_box.grid(row=row, column=1, sticky="ew", pady=(0, 4))
        self._refresh_project_values()
        # Autocomplete: filter the dropdown values as user types.
        # We do not forcibly open the dropdown on each keystroke.
        self._project_var.trace_add("write", self._on_project_change)
        self._project_box.bind("<Alt-Down>", self._open_project_dropdown)
        self._project_box.bind("<Control-space>", self._open_project_dropdown)
        self._bind_editing_shortcuts(self._project_box)
        row += 1

        ttk.Label(f, text="Task title:").grid(row=row, column=0, sticky="nw", pady=(0, 4))
        self._title_var = tk.StringVar()
        self._title_entry = ttk.Entry(f, textvariable=self._title_var, width=56)
        self._title_entry.grid(
            row=row, column=1, sticky="ew", pady=(0, 4)
        )
        self._bind_editing_shortcuts(self._title_entry)
        row += 1

        ttk.Label(f, text="Task description [optional]:").grid(row=row, column=0, sticky="nw")
        self._desc_text = tk.Text(f, height=4, width=56, wrap=tk.WORD)
        self._desc_text.grid(row=row, column=1, sticky="ew", pady=(0, 6))
        self._bind_editing_shortcuts(self._desc_text)
        row += 1

        ttk.Label(f, text="Challenges / blockers [optional]:").grid(row=row, column=0, sticky="nw")
        self._block_text = tk.Text(f, height=3, width=56, wrap=tk.WORD)
        self._block_text.grid(row=row, column=1, sticky="ew", pady=(0, 6))
        self._bind_editing_shortcuts(self._block_text)
        row += 1

        ttk.Label(f, text="Efforts (hrs):").grid(row=row, column=0, sticky="w")
        self._eff_var = tk.StringVar()
        self._eff_entry = ttk.Entry(f, textvariable=self._eff_var, width=16)
        self._eff_entry.grid(row=row, column=1, sticky="w")
        self._bind_editing_shortcuts(self._eff_entry)
        row += 1

        btn_row = ttk.Frame(f)
        btn_row.grid(row=row, column=1, sticky="w", pady=(12, 0))
        ttk.Button(btn_row, text="Save task", command=self._save_task).pack(side=tk.LEFT)
        ttk.Button(btn_row, text="Clear", command=self._clear_and_status).pack(side=tk.LEFT, padx=(8, 0))
        row += 1

        status = ttk.Label(f, textvariable=self._status_var, foreground="#0b6b0b")
        status.grid(row=row, column=0, columnspan=2, sticky="w", pady=(10, 0))

        f.columnconfigure(1, weight=1)

    def _bind_editing_shortcuts(self, w: tk.Widget) -> None:
        # Word delete (back/forward) and line delete (back) for mac + others.
        for seq in ("<Alt-BackSpace>", "<Control-BackSpace>"):
            w.bind(seq, self._delete_prev_word, add=True)
        for seq in ("<Alt-Delete>", "<Control-Delete>"):
            w.bind(seq, self._delete_next_word, add=True)
        for seq in ("<Command-BackSpace>", "<Control-u>"):
            w.bind(seq, self._delete_to_line_start, add=True)

    def _delete_prev_word(self, event: tk.Event) -> str:
        w = event.widget
        if isinstance(w, tk.Text):
            try:
                w.delete("insert wordstart", "insert")
            except tk.TclError:
                return "break"
            return "break"
        if isinstance(w, (tk.Entry, ttk.Entry, ttk.Combobox)):
            s = w.get()
            i = int(w.index(tk.INSERT))
            j = i
            while j > 0 and s[j - 1].isspace():
                j -= 1
            while j > 0 and (s[j - 1].isalnum() or s[j - 1] in ("_", "-", ".")):
                j -= 1
            if j == i and j > 0:
                j -= 1
            w.delete(j, i)
            return "break"
        return "break"

    def _delete_next_word(self, event: tk.Event) -> str:
        w = event.widget
        if isinstance(w, tk.Text):
            try:
                w.delete("insert", "insert wordend")
            except tk.TclError:
                return "break"
            return "break"
        if isinstance(w, (tk.Entry, ttk.Entry, ttk.Combobox)):
            s = w.get()
            i = int(w.index(tk.INSERT))
            j = i
            n = len(s)
            while j < n and s[j].isspace():
                j += 1
            while j < n and (s[j].isalnum() or s[j] in ("_", "-", ".")):
                j += 1
            if j == i and j < n:
                j += 1
            w.delete(i, j)
            return "break"
        return "break"

    def _delete_to_line_start(self, event: tk.Event) -> str:
        w = event.widget
        if isinstance(w, tk.Text):
            try:
                w.delete("insert linestart", "insert")
            except tk.TclError:
                return "break"
            return "break"
        if isinstance(w, (tk.Entry, ttk.Entry, ttk.Combobox)):
            i = int(w.index(tk.INSERT))
            w.delete(0, i)
            return "break"
        return "break"

    def _build_report_tab(self) -> None:
        f = self._report_tab
        top = ttk.Frame(f)
        top.pack(fill=tk.X)
        self._date_var = tk.StringVar()
        ttk.Label(top, textvariable=self._date_var, font=("TkDefaultFont", 11, "bold")).pack(
            side=tk.LEFT
        )
        ttk.Button(top, text="Export", command=self._export_report).pack(side=tk.RIGHT, padx=(8, 0))
        ttk.Button(top, text="Refresh", command=self._refresh_report).pack(side=tk.RIGHT)

        cols = ("seq", "project", "title", "desc", "blockers", "hrs")
        tree_frame = ttk.Frame(f)
        tree_frame.pack(fill=tk.BOTH, expand=True, pady=(8, 0))

        self._tree = ttk.Treeview(
            tree_frame,
            columns=cols,
            show="headings",
            height=14,
            selectmode="browse",
        )
        self._tree.heading("seq", text="#")
        self._tree.heading("project", text="Project")
        self._tree.heading("title", text="Task Title")
        self._tree.heading("desc", text="Task Description")
        self._tree.heading("blockers", text="Challenges / Blockers")
        self._tree.heading("hrs", text="Efforts hrs")

        self._tree.column("seq", width=40, anchor="center", stretch=False)
        self._tree.column("project", width=120, stretch=True)
        self._tree.column("title", width=140, stretch=True)
        self._tree.column("desc", width=160, stretch=True)
        self._tree.column("blockers", width=140, stretch=True)
        self._tree.column("hrs", width=90, anchor="e", stretch=False)

        vsb = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self._tree.yview)
        self._tree.configure(yscrollcommand=vsb.set)
        self._tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)

        self._total_var = tk.StringVar(value="Total Efforts: —")
        ttk.Label(f, textvariable=self._total_var).pack(anchor="w", pady=(8, 0))

        self._refresh_report()

    def _on_tab_changed(self, _event: tk.Event | None = None) -> None:
        try:
            idx = self._notebook.index("current")
        except tk.TclError:
            return
        if idx == 1:
            self._refresh_report()

    def _clear_form(self) -> None:
        self._project_var.set("")
        self._title_var.set("")
        self._desc_text.delete("1.0", tk.END)
        self._block_text.delete("1.0", tk.END)
        self._eff_var.set("")
        # keep status text after save; clear only on explicit Clear button
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
        self._project_box["values"] = self._all_projects
        # keep what user typed, but ensure dropdown options match it
        if current.strip():
            self._apply_project_filter(open_dropdown=False)

    def _project_postcommand(self) -> None:
        # Called right before the dropdown opens.
        self._apply_project_filter(open_dropdown=False)

    def _on_project_change(self, *_args: object) -> None:
        self._apply_project_filter(open_dropdown=False)

    def _apply_project_filter(self, *, open_dropdown: bool) -> None:
        if self._autocomplete_lock:
            return
        typed = self._project_var.get()
        if not typed.strip():
            self._project_box["values"] = self._all_projects
            return
        needle = typed.strip().lower()
        matches = [p for p in self._all_projects if p.lower().startswith(needle)]
        if not matches:
            matches = [p for p in self._all_projects if needle in p.lower()]
        self._project_box["values"] = matches
        # open_dropdown kept for future tweaks; no enforced dropdown popping.
        del open_dropdown

    def _open_project_dropdown(self, _event: tk.Event | None = None) -> None:
        try:
            self._project_box.event_generate("<Down>")
        except Exception:
            pass

    def _save_task(self) -> None:
        project = self._project_var.get()
        title = self._title_var.get().strip()
        if not title:
            messagebox.showerror("Missing title", "Task title is required.")
            return

        desc = self._desc_text.get("1.0", tk.END)
        blockers = self._block_text.get("1.0", tk.END)
        raw_eff = self._eff_var.get()

        efforts = validate_efforts(raw_eff)
        if efforts is None:
            messagebox.showerror(
                "Invalid effort",
                "Efforts must be a non-negative number (for example 2 or 2.5).",
            )
            return

        ok, msg = append_task(project, title, desc, blockers, efforts)
        if not ok:
            messagebox.showerror("Cannot save", msg)
            return

        self._refresh_report()
        self._status_var.set(msg)
        self._refresh_project_values()
        self._title_var.set("")
        self._desc_text.delete("1.0", tk.END)
        self._block_text.delete("1.0", tk.END)
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
            )
        self._total_var.set(f"Total Efforts: {format_hours(total)} hrs")

    def _export_report(self) -> None:
        data = load_tasks()
        got = sorted_today_tasks(data, group_by_project=True)
        if got is None:
            messagebox.showerror("Nothing to export", "No tasks found for today.")
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
                # fall back to CSV with same basename
                csv_path = path.rsplit(".", 1)[0] + ".csv"
                ok, msg = export_report_csv(csv_path, date_str, tasks)

        if ok:
            self._status_var.set(msg)
        else:
            messagebox.showerror("Export failed", msg)


def main() -> None:
    app = TaskLoggerApp()
    app.mainloop()


if __name__ == "__main__":
    main()
