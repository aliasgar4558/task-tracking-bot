#!/usr/bin/env python3
"""
Install TaskBot: create a dedicated venv, pip install from GitHub (or editable),
symlink taskbot / taskbot-gui into ~/.local/bin or ~/bin.

Requires Python 3.10+. Uses only the standard library except packages installed
into the new venv by pip.

Usage:
  curl -fsSL .../install.py | python3
  python3 install.py
  python3 install.py --local          # from repo root (pyproject.toml in cwd)
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

MARK_START = "# >>> taskbot PATH >>>"
MARK_END = "# <<< taskbot PATH <<<"


DEFAULT_REPO = "https://github.com/aliasgar4558/task-tracking-bot.git"


def _repo_url() -> str:
    return os.environ.get("TASKBOT_REPO", DEFAULT_REPO)


def _pick_writable_dir(candidates: list[Path]) -> Path:
    for d in candidates:
        try:
            d = d.expanduser().resolve()
            d.mkdir(parents=True, exist_ok=True)
            probe = d / ".taskbot_write_test"
            probe.write_text("ok", encoding="utf-8")
            probe.unlink()
            return d
        except OSError:
            continue
    print(
        "taskbot install: could not create a writable directory.\n"
        "Set TASKBOT_HOME to a folder you own (and optionally TASKBOT_BIN for scripts).",
        file=sys.stderr,
    )
    sys.exit(1)


def _venv_bin(venv: Path, name: str) -> Path:
    if sys.platform == "win32":
        return venv / "Scripts" / f"{name}.exe"
    return venv / "bin" / name


def _export_path_line(bin_dir: Path) -> str:
    p = str(bin_dir.resolve())
    escaped = p.replace("\\", "\\\\").replace('"', '\\"')
    return f'export PATH="{escaped}:$PATH"'


def _replace_taskbot_path_block(content: str, export_line: str) -> str:
    block = f"{MARK_START}\n{export_line}\n{MARK_END}\n"
    pat = re.compile(
        re.escape(MARK_START) + r"\n.*?\n" + re.escape(MARK_END) + r"\n?",
        re.DOTALL,
    )
    if pat.search(content):
        return pat.sub(block, content, count=1)
    sep = "\n\n" if content.strip() else ""
    return content.rstrip() + sep + block


def _shell_rc_candidates() -> list[Path]:
    home = Path.home()
    shell = os.environ.get("SHELL", "")
    paths: list[Path] = []
    if "zsh" in shell:
        paths.append(home / ".zshrc")
    elif "bash" in shell:
        paths.append(home / ".bashrc")
        if sys.platform == "darwin":
            paths.append(home / ".bash_profile")
    else:
        paths.extend([home / ".zshrc", home / ".bashrc"])
    seen: set[Path] = set()
    out: list[Path] = []
    for p in paths:
        try:
            key = p.resolve()
        except OSError:
            key = p
        if key not in seen:
            seen.add(key)
            out.append(p)
    return out


def _configure_shell_path(bin_dir: Path) -> list[Path]:
    if os.environ.get("TASKBOT_SKIP_SHELL_PATH"):
        return []
    export_line = _export_path_line(bin_dir)
    updated: list[Path] = []
    for rc in _shell_rc_candidates():
        if rc.exists() and rc.is_dir():
            print(f"taskbot install: skip shell hook (not a file): {rc}", file=sys.stderr)
            continue
        try:
            prev = rc.read_text(encoding="utf-8") if rc.exists() else ""
            new_text = _replace_taskbot_path_block(prev, export_line)
            if new_text == prev:
                continue
            rc.parent.mkdir(parents=True, exist_ok=True)
            rc.write_text(new_text, encoding="utf-8")
            updated.append(rc)
        except OSError as e:
            print(f"taskbot install: could not write {rc}: {e}", file=sys.stderr)
    return updated


def _symlink_or_copy(src: Path, dst: Path) -> None:
    src = src.resolve()
    try:
        if dst.exists() or dst.is_symlink():
            dst.unlink()
        os.symlink(src, dst)
    except OSError:
        if dst.exists() or dst.is_symlink():
            dst.unlink()
        shutil.copy2(src, dst)


def main() -> int:
    parser = argparse.ArgumentParser(description="Install TaskBot (venv + PATH commands)")
    parser.add_argument(
        "--local",
        action="store_true",
        help="Install editable from current directory (needs pyproject.toml).",
    )
    args = parser.parse_args()

    home = Path.home()

    if os.environ.get("TASKBOT_HOME"):
        dest_root = Path(os.environ["TASKBOT_HOME"]).expanduser().resolve()
        dest_root.mkdir(parents=True, exist_ok=True)
    else:
        xdg = os.environ.get("XDG_DATA_HOME")
        candidates = []
        if xdg:
            candidates.append(Path(xdg) / "taskbot")
        candidates.extend(
            [
                home / ".local" / "share" / "taskbot",
                home / ".taskbot",
            ]
        )
        dest_root = _pick_writable_dir(candidates)

    venv_path = dest_root / "venv"

    if os.environ.get("TASKBOT_BIN"):
        bin_dir = Path(os.environ["TASKBOT_BIN"]).expanduser().resolve()
        bin_dir.mkdir(parents=True, exist_ok=True)
    else:
        bin_dir = _pick_writable_dir([home / ".local" / "bin", home / "bin"])

    cfg = venv_path / "pyvenv.cfg"
    if not cfg.is_file():
        if venv_path.exists():
            shutil.rmtree(venv_path)
        subprocess.run([sys.executable, "-m", "venv", str(venv_path)], check=True)

    pip = _venv_bin(venv_path, "pip")
    py = _venv_bin(venv_path, "python")

    subprocess.run([str(py), "-m", "pip", "install", "-q", "--upgrade", "pip"], check=True)

    if args.local:
        cwd = Path.cwd().resolve()
        if not (cwd / "pyproject.toml").exists():
            print(
                "taskbot install: --local needs pyproject.toml in the current directory.\n"
                "Clone the repo, cd into it, then run: python3 install.py --local",
                file=sys.stderr,
            )
            return 1
        subprocess.run([str(pip), "install", "-q", "-e", str(cwd)], check=True)
    else:
        if shutil.which("git") is None:
            print(
                "taskbot install: git is required to install from GitHub.\n"
                "Install git, or clone the repo and run: python3 install.py --local",
                file=sys.stderr,
            )
            return 1
        subprocess.run([str(pip), "install", "-q", f"git+{_repo_url()}"], check=True)

    for name in ("taskbot", "taskbot-gui"):
        src = _venv_bin(venv_path, name)
        _symlink_or_copy(src, bin_dir / name)

    print("TaskBot installed.")
    print(f"  Virtualenv: {venv_path}")
    print(f"  Commands:   {bin_dir / 'taskbot'} and {bin_dir / 'taskbot-gui'}")

    bin_s = str(bin_dir.resolve())
    rc_updated = _configure_shell_path(bin_dir)
    path_s = os.environ.get("PATH", "")
    on_path = bin_s in path_s.split(os.pathsep)

    if rc_updated:
        files = ", ".join(str(p) for p in rc_updated)
        print()
        print(f"Added TaskBot to PATH in: {files}")
        print("New terminal windows will have taskbot and taskbot-gui on your PATH.")
        primary = rc_updated[0]
        print()
        print("This terminal only, run once:")
        print(f"  source {primary}")
    elif not on_path:
        sourced = False
        if not os.environ.get("TASKBOT_SKIP_SHELL_PATH"):
            for rc in _shell_rc_candidates():
                try:
                    if rc.is_file() and MARK_START in rc.read_text(encoding="utf-8", errors="replace"):
                        print()
                        print("Load PATH in this terminal:")
                        print(f"  source {rc}")
                        sourced = True
                        break
                except OSError:
                    continue
            if not sourced:
                print()
                print("Could not update your shell startup file automatically.")
                print("Add this line to ~/.zshrc or ~/.bashrc, then open a new terminal:")
                print(f'  export PATH="{bin_s}:$PATH"')

    return 0


if __name__ == "__main__":
    sys.exit(main())
