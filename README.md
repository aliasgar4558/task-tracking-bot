# Local Daily Task Logger Bot (V1)

Offline task logger: same data for **CLI** and **desktop GUI** (tkinter). No AI, cloud, or network use.

## Setup

Requires Python 3.

This tool runs fine with **zero installs**. If you want prettier tables in the CLI report, install `tabulate` (optional):

```bash
python3 -m pip install tabulate
```

On macOS with Homebrew Python, global install may be blocked (PEP 668). Use a venv:

```bash
python3 -m venv .venv && source .venv/bin/activate && python3 -m pip install tabulate
```

## Usage

```bash
python bot.py add       # Interactive: add task(s) for today
python bot.py report    # Today's report (table + total effort)
python bot.py list      # Same table as report
python bot.py help      # Show help
```

### Desktop window (tkinter)

Shared logic lives in `core.py`. The GUI reads and writes the same `task_logs.json`.

```bash
python gui.py
```

Use the **Add task** tab to save entries (optional **Add another** dialog after each save). Open **Today's report** for a sortable table and total hours (Refresh reloads from disk, including changes from the CLI).

### Export (Excel / CSV)

The GUI report tab has **Export**.

- Excel export (`.xlsx`) uses `openpyxl` if installed:

```bash
python3 -m pip install openpyxl
```

- If `openpyxl` is missing, export auto-falls back to `.csv` (Excel can open it).

### GUI: `ModuleNotFoundError: No module named '_tkinter'` (macOS)

Homebrew’s `python@3.x` does not ship Tk until you add it:

```bash
brew install python-tk@3.13
```

Use the same minor version as `python3 --version` (for example `python-tk@3.14` for Python 3.14). Then run `python3 gui.py` again. If it still fails, run the interpreter from that package:

```bash
"$(brew --prefix python-tk@3.13)/bin/python3" gui.py
```

Or use the official macOS installer from [python.org](https://www.python.org/downloads/), which includes Tk.

### Files

| File | Role |
|------|------|
| `core.py` | Storage, validation, tabulate report text |
| `bot.py` | CLI (`argparse`) |
| `gui.py` | Desktop window |

Data is stored in `task_logs.json` next to these scripts (created on first save).

## JSON shape

Dates are ISO `YYYY-MM-DD` keys; each day holds a list of tasks with `id`, `task_title`, `task_description`, `blockers`, `efforts_hrs`. Empty optional fields are stored as `"-"`.

## V2 ideas (not implemented)

AI rephrasing, edits/deletes, CSV export, weekly/monthly reports.
