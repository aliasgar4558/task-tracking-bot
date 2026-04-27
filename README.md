# Local Daily Task Logger Bot (V1)

Offline task logger: same data for **CLI** and **desktop GUI** (tkinter). No AI, cloud, or network use.

**Source:** [aliasgar4558/task-tracking-bot](https://github.com/aliasgar4558/task-tracking-bot)

Repo layout matches a **flat GitHub tree**: `pyproject.toml`, `taskbot/` package, `bot.py` / `gui.py` wrappers at the repo root.

## Setup

Requires Python 3.

This tool runs fine with **zero installs**.

Optional extras:

- Prettier CLI tables: `tabulate`
- Excel export (`.xlsx`) in GUI: `openpyxl`

```bash
python3 -m pip install tabulate openpyxl
```

On macOS with Homebrew Python, global install may be blocked (PEP 668). Use a venv:

```bash
python3 -m venv .venv && source .venv/bin/activate && python3 -m pip install tabulate openpyxl
```

## Usage (without installing)

From the repository root:

```bash
python3 bot.py add
python3 bot.py report
python3 bot.py list
python3 bot.py help
python3 gui.py
```

### Install from GitHub (`pip` / `pipx`)

Everything lives at the **repository root**, so:

```bash
python3 -m pip install "git+https://github.com/aliasgar4558/task-tracking-bot.git"
```

```bash
pipx install "git+https://github.com/aliasgar4558/task-tracking-bot.git"
```

Then:

```bash
taskbot --help
taskbot-gui
```

When installed via `pip`, logs are stored at **`~/.taskbot/task_logs.json`**.

### Editable install (local clone)

```bash
git clone https://github.com/aliasgar4558/task-tracking-bot.git
cd task-tracking-bot
python3 -m pip install -e .
```

#### Troubleshooting: “neither setup.py nor pyproject.toml found”

GitHub must show **`pyproject.toml` at the repo root** plus the **`taskbot/`** package folder. Push this layout, then rerun `pip install`.

Do **not** use `#subdirectory=task_bot` unless ye actually nest the project under a folder named `task_bot` on GitHub.

### Desktop window (tkinter)

```bash
python3 gui.py
```

### Export (Excel / CSV)

The GUI report tab has **Export**. If `openpyxl` is missing, export falls back to `.csv`.

### GUI: `ModuleNotFoundError: No module named '_tkinter'` (macOS)

```bash
brew install python-tk@3.13
```

Match `3.13` to `python3 --version`. Then:

```bash
"$(brew --prefix python-tk@3.13)/bin/python3" gui.py
```

Or use the installer from [python.org](https://www.python.org/downloads/).

### Files (repo root)

| Path | Role |
|------|------|
| `pyproject.toml` | Package metadata; defines `taskbot` and `taskbot-gui` commands |
| `taskbot/` | Core (`core.py`), CLI (`cli.py`), GUI (`gui.py`) |
| `bot.py`, `gui.py` | Thin wrappers when running without `pip install` |

## JSON shape

Dates are ISO `YYYY-MM-DD` keys; each day holds a list of tasks with `id`, `project`, `task_title`, `task_description`, `blockers`, `efforts_hrs`. Empty optional fields are stored as `"-"`.

## V2 ideas (not implemented)

AI rephrasing, edits/deletes, weekly/monthly reports.
