# Local Daily Task Logger Bot (V1)

Offline task logger: **CLI** + **desktop GUI** ([CustomTkinter](https://github.com/TomSchimansky/CustomTkinter)). No cloud or AI.

**Repo:** [aliasgar4558/task-tracking-bot](https://github.com/aliasgar4558/task-tracking-bot) (flat layout: `pyproject.toml` and `taskbot/` at the root).

## Install

Two options. Data file: `**~/.taskbot/task_logs.json`**.

**1. Script** (venv + symlinks into `~/.local/bin`; add that folder to `PATH` if the script prints the export line):

```bash
curl -fsSL https://raw.githubusercontent.com/aliasgar4558/task-tracking-bot/master/install.sh | bash
```

Already cloned: `./install.sh`, or `./install.sh --local` for editable install. Needs Python **3.10+** and **git** for the remote install.

**2. pipx**

```bash
pipx install "git+https://github.com/aliasgar4558/task-tracking-bot.git"
```

On macOS, once: `brew install pipx && pipx ensurepath`.

Then: `**taskbot**`, `**taskbot-gui**`.

Optional extras (same env as TaskBot): `**tabulate**` (nicer CLI tables), `**openpyxl**` (Excel export in the GUI).

## CLI

Use `**taskbot**` plus a command:


| Command          | What it does                                                                                                          |
| ---------------- | --------------------------------------------------------------------------------------------------------------------- |
| `taskbot add`    | Prompts for tasks for today (project optional, title, description, blockers, hours). Can add multiple in one session. |
| `taskbot report` | Prints today's report as a table (grouped by project).                                                                |
| `taskbot list`   | Same table as `**report**`.                                                                                           |
| `taskbot help`   | Prints usage for all commands.                                                                                        |


Examples:

```bash
taskbot add
taskbot report
taskbot list
taskbot help
```

Without installing from PyPI/git, from the repo root use `**python3 bot.py**` instead of `**taskbot**` (same subcommands). Desktop GUI: `**python3 gui.py**` or `**taskbot-gui**` after install.

macOS: if the GUI fails with `_tkinter` missing, install Tk for your Python (e.g. `brew install python-tk@X.Y` matching `python3 --version`) or use [python.org](https://www.python.org/downloads/) Python.

## JSON shape

Dates are `YYYY-MM-DD` keys; each day is a list of tasks (`id`, `project`, `task_title`, `task_description`, `blockers`, `efforts_hrs`). Empty optionals stored as `"-"`.

## V2 ideas (not built)

Edits/deletes, weekly reports, AI.