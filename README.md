# Local Daily Task Logger Bot (V1)

Offline task logger: **CLI** + **desktop GUI** ([CustomTkinter](https://github.com/TomSchimansky/CustomTkinter)). No cloud or AI.

**Repo:** [aliasgar4558/task-tracking-bot](https://github.com/aliasgar4558/task-tracking-bot) (flat layout: `pyproject.toml` and `taskbot/` at the root).

## Install

**One step** (needs **Python 3.10+** and **git**; uses a private venv, no global `pip`, no pipx):

```bash
curl -fsSL https://raw.githubusercontent.com/aliasgar4558/task-tracking-bot/master/install.py | python3
```

Replace `master` with your default branch if different.

Afterward run **`taskbot`** and **`taskbot-gui`**. If the installer prints an `export PATH=...` line, add it to your shell config.

Task log file: **`~/.taskbot/task_logs.json`**. The installer puts the venv under `~/.local/share/taskbot` when possible; otherwise **`~/.taskbot`**. If your home folder is locked down, set **`TASKBOT_HOME`** (and optionally **`TASKBOT_BIN`**) to writable paths before running the command above.

**Already cloned the repo?** From the repo root:

```bash
python3 install.py --local
```

(or `./install.sh --local`, same thing.)

Optional extras (install into that same venv later): **`tabulate`**, **`openpyxl`**.

## CLI

| Command | What it does |
|--------|----------------|
| `taskbot add` | Prompts for tasks for today (project optional, title, description, blockers, hours). |
| `taskbot report` | Today's report table (grouped by project). |
| `taskbot list` | Same table as `report`. |
| `taskbot help` | Prints usage. |

```bash
taskbot add
taskbot report
taskbot list
taskbot help
```

Without installing: from repo root **`python3 bot.py`** with the same subcommands; GUI **`python3 gui.py`** or **`taskbot-gui`** after install.

macOS: if the GUI reports missing `_tkinter`, install Tk for your Python (e.g. `brew install python-tk@X.Y` matching `python3 --version`) or use [python.org](https://www.python.org/downloads/) Python.

## JSON shape

Dates are `YYYY-MM-DD` keys; each day is a list of tasks (`id`, `project`, `task_title`, `task_description`, `blockers`, `efforts_hrs`). Empty optionals stored as `"-"`.

## V2 ideas (not built)

Edits/deletes, weekly reports, AI.
