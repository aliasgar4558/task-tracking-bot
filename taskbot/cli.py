"""CLI entrypoint for TaskBot."""

from __future__ import annotations

import argparse
import sys

from .core import (
    append_task,
    format_report_table,
    load_tasks,
    normalize_optional,
    sorted_today_tasks,
    validate_efforts,
)


def add_task_flow() -> None:
    while True:
        project = input("Project [optional]: ").strip()
        title = ""
        while not title.strip():
            title = input("Task title: ").strip()
            if not title:
                print("Task title is required.")

        desc = normalize_optional(input("Task description [optional]: "))
        blockers = normalize_optional(input("Any challenges/blockers [optional]: "))

        efforts: float | None = None
        while efforts is None:
            raw_eff = input("Efforts in hrs: ")
            efforts = validate_efforts(raw_eff)
            if efforts is None:
                print("Efforts must be a non-negative number (e.g. 2 or 2.5).")

        ok, msg = append_task(project, title, desc, blockers, efforts)
        if not ok:
            print(msg, file=sys.stderr)
            sys.exit(1)

        print(msg)
        again = ""
        while again not in ("y", "n"):
            again = input("Do you want to add another task? (y/n): ").strip().lower()
            if again not in ("y", "n"):
                print("Please enter y or n.")
        if again == "n":
            print("Goodbye.")
            break


def show_report() -> None:
    data = load_tasks()
    got = sorted_today_tasks(data, group_by_project=True)
    if got is None:
        print("No tasks found for today.")
        return

    date_str, tasks = got
    text = format_report_table(date_str, tasks)
    print(text)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="taskbot",
        description="Local Daily Task Logger — log tasks and view daily reports (offline).",
    )
    sub = parser.add_subparsers(dest="command", metavar="COMMAND")

    sub.add_parser("add", help="Add one or more tasks for today")
    sub.add_parser("report", help="Show today's consolidated report")
    sub.add_parser("list", help="List today's tasks (same table as report)")
    sub.add_parser("help", help="Show this help message")

    args, unknown = parser.parse_known_args()

    if unknown:
        print(f"Unknown arguments: {' '.join(unknown)}", file=sys.stderr)
        parser.print_help()
        sys.exit(2)

    cmd = args.command
    if cmd is None or cmd == "help":
        parser.print_help()
        if cmd is None:
            sys.exit(2)
        return

    if cmd == "add":
        add_task_flow()
    elif cmd in ("report", "list"):
        show_report()
    else:
        parser.print_help()
        sys.exit(2)


if __name__ == "__main__":
    main()

