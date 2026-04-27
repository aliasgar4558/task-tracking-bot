# Local Daily Task Logger Bot (V1)

Offline task logger with a **CLI** and **Desktop GUI**. The GUI uses [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter). No cloud or AI.

**Repo:** [aliasgar4558/task-tracking-bot](https://github.com/aliasgar4558/task-tracking-bot) (flat layout: `pyproject.toml` and `taskbot/` at the root).

## Install

**Using `python3` command**

```bash
python3 -m pip install "git+https://github.com/aliasgar4558/task-tracking-bot.git"
```

On macOS, make sure the above procss is completed successfully, then you can access `taskbot`, `taskbot-gui` via CLI & Desktop GUIs.

Some dependencies: `tabulate` (nicer CLI tables), `openpyxl` (Excel export in the GUI).

## CLI

Use `taskbot` plus a command:

| Command          | What it does                                                                                                          |
| ---------------- | --------------------------------------------------------------------------------------------------------------------- |
| `taskbot add`    | Prompts for tasks for today (project optional, title, description, blockers, hours). Can add multiple in one session. |
| `taskbot report` | Prints today's report as a table (grouped by project).                                                                |
| `taskbot list`   | Same table as `report`.                                                                                               |
| `taskbot help`   | Prints usage for all commands.                                                                                        |

Examples:

```bash
taskbot add
taskbot report
taskbot list
taskbot help
```

Without installing from PyPI/git, from the repo root use `python3 bot.py` instead of `taskbot` (same subcommands). Desktop GUI: `python3 gui.py` or `taskbot-gui` after install.

## JSON shape

Dates are `YYYY-MM-DD` keys; each day is a list of tasks (`id`, `project`, `task_title`, `task_description`, `blockers`, `efforts_hrs`). Empty optionals stored as `"-"`.

### To Uninstall
```bash
pip3 uninstall taskbot
```

& follow the terminal instructions to remove the package.

## Future Enhancements (V2 - Do Not Implement Now)

- AI-based rephrasing
- Task editing and deletion
- Weekly/monthly reports
- Web interface
- Local AI integration (Ollama)
