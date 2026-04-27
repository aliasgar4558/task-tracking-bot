# Local Daily Task Logger Bot (V1)

Offline task logger: same data for **CLI** and **desktop GUI** (tkinter). No AI, cloud, or network use.

**Source:** [aliasgar4558/task-tracking-bot](https://github.com/aliasgar4558/task-tracking-bot)

## Setup

Requires Python 3.

This tool runs fine with **zero installs**.

Optional extras:

- Prettier CLI tables: `tabulate`
- Excel export (`.xlsx`) in GUI: `openpyxl`

Install optional bits:

```bash
python3 -m pip install tabulate openpyxl
```

On macOS with Homebrew Python, global install may be blocked (PEP 668). Use a venv:

```bash
python3 -m venv .venv && source .venv/bin/activate && python3 -m pip install tabulate openpyxl
```

## Usage

```bash
python bot.py add       # Interactive: add task(s) for today
python bot.py report    # Today's report (table + total effort)
python bot.py list      # Same table as report
python bot.py help      # Show help
```

### Install as an app (CLI)

From the `task_bot/` folder:

```bash
python3 -m pip install -e .
```

Then run:

```bash
taskbot add
taskbot report
taskbot-gui
```

When installed, logs are stored at `~/.taskbot/task_logs.json`.

### Install from GitHub (public repo)

Repo: **https://github.com/aliasgar4558/task-tracking-bot**

Clone and install from a checkout (recommended if ye already cloned):

```bash
git clone https://github.com/aliasgar4558/task-tracking-bot.git
cd task-tracking-bot/task_bot
python3 -m pip install -e .
```

With `pipx` (install straight from Git without cloning; package lives under `task_bot/` in this repo):

```bash
brew install pipx   # macOS only; Linux: install pipx via your distro
pipx ensurepath
pipx install "git+https://github.com/aliasgar4558/task-tracking-bot.git#subdirectory=task_bot"
```

With `pip` (into a venv):

```bash
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
python3 -m pip install "git+https://github.com/aliasgar4558/task-tracking-bot.git#subdirectory=task_bot"
```

After install:

```bash
taskbot --help
taskbot-gui
```

### Desktop window (tkinter)

Shared logic lives in `core.py`. The GUI reads and writes the same `task_logs.json`.

```bash
python gui.py
```

Use the **Add task** tab to save entries (optional **Add another** dialog after each save). Open **Today's report** for a sortable table and total hours (Refresh reloads from disk, including changes from the CLI).

### Export (Excel / CSV)

The GUI report tab has **Export**.

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

### Files (`task_bot/` layout)

| Path | Role |
|------|------|
| `pyproject.toml` | Package metadata and `taskbot` / `taskbot-gui` scripts |
| `taskbot/` | Core logic (`core.py`), CLI (`cli.py`), GUI (`gui.py`) |
| `bot.py`, `gui.py` | Thin wrappers for running without `pip install` |

When ye run scripts from this folder without installing, logs use `task_logs.json` next to those scripts. After `pip install`, logs use `~/.taskbot/task_logs.json`. Do not commit logs (they are gitignored).

## JSON shape

Dates are ISO `YYYY-MM-DD` keys; each day holds a list of tasks with `id`, `project`, `task_title`, `task_description`, `blockers`, `efforts_hrs`. Empty optional fields are stored as `"-"`.

## V2 ideas (not implemented)

AI rephrasing, edits/deletes, weekly/monthly reports.
