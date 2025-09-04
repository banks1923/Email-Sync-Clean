#!/usr/bin/env python3
"""
One-shot consolidation helper.

Usage:
  python tools/consolidate.py --dry-run   # print planned moves and rewrites
  python tools/consolidate.py --apply     # perform moves and import rewrites

Notes:
  - Uses refactor/consolidation_map.yaml
  - Moves use shutil (works without git), keep VCS separate
  - Import rewrite: safe full-module replacement on Python files
  - Stops if unresolved old imports remain (apply mode)
"""
import argparse
import os
import re
import sys
import shutil
from pathlib import Path

import json
try:
    import yaml  # type: ignore
except Exception:
    yaml = None

ROOT = Path(__file__).resolve().parents[1]
MAP_DIR = ROOT / 'refactor'
MAP_JSON = MAP_DIR / 'consolidation_map.json'
MAP_YAML = MAP_DIR / 'consolidation_map.yaml'


def load_map():
    if MAP_JSON.exists():
        with MAP_JSON.open('r') as f:
            return json.load(f)
    if MAP_YAML.exists():
        if yaml is None:
            raise SystemExit("Mapping is YAML but PyYAML not available. Provide refactor/consolidation_map.json or install pyyaml.")
        with MAP_YAML.open('r') as f:
            return yaml.safe_load(f)
    raise SystemExit("No mapping file found. Expected refactor/consolidation_map.json or .yaml")


def ensure_package(path: Path):
    if path.is_file():
        path.parent.mkdir(parents=True, exist_ok=True)
        return
    path.mkdir(parents=True, exist_ok=True)
    init = path / '__init__.py'
    if not init.exists():
        init.write_text('')


def list_py_files():
    files = []
    for dp, dn, fn in os.walk(ROOT):
        if any(seg in dp for seg in ['/.git', '/.venv', '/venv', '/__pycache__', '/.pytest_cache']):
            continue
        for f in fn:
            if f.endswith('.py'):
                files.append(Path(dp) / f)
    return files


def rewrite_imports(py_files, import_rewrites, dry_run=True):
    changed = 0
    rules = [(re.escape(r['from']), r['to']) for r in import_rewrites]
    # Build regex to match module tokens in import/from statements only
    pat = re.compile(r"^(\s*(from|import)\s+)([\w\.]+)(.*)$")
    for p in py_files:
        text = p.read_text(encoding='utf-8', errors='ignore')
        lines = text.splitlines()
        updated = []
        dirty = False
        for line in lines:
            m = pat.match(line)
            if m:
                prefix, _, module, suffix = m.groups()
                new_module = module
                for frm, to in rules:
                    if module == frm or module.startswith(frm + '.'):
                        new_module = module.replace(frm, to, 1)
                        break
                if new_module != module:
                    line = f"{prefix}{new_module}{suffix}"
                    dirty = True
            updated.append(line)
        if dirty:
            changed += 1
            if not dry_run:
                p.write_text("\n".join(updated) + "\n", encoding='utf-8')
    return changed


def perform_moves(file_moves, dry_run=True):
    moved = []
    for spec in file_moves:
        src = ROOT / spec['from']
        dst = ROOT / spec['to']
        if src.is_dir():
            ensure_package(dst)
            if dry_run:
                moved.append((src, dst))
            else:
                # Move directory contents
                if dst.exists() and any(dst.iterdir()):
                    # merge dir
                    for child in src.rglob('*'):
                        if child.is_dir():
                            continue
                        rel = child.relative_to(src)
                        target = dst / rel
                        target.parent.mkdir(parents=True, exist_ok=True)
                        shutil.move(str(child), str(target))
                else:
                    shutil.move(str(src), str(dst))
                moved.append((src, dst))
        elif src.is_file():
            dst.parent.mkdir(parents=True, exist_ok=True)
            if dry_run:
                moved.append((src, dst))
            else:
                shutil.move(str(src), str(dst))
                moved.append((src, dst))
        else:
            print(f"WARN: missing source {src}")
    return moved


def delete_globs(patterns, dry_run=True):
    removed = []
    for pat in patterns:
        for p in ROOT.glob(pat):
            if dry_run:
                removed.append(p)
            else:
                if p.is_dir():
                    shutil.rmtree(p, ignore_errors=True)
                else:
                    p.unlink(missing_ok=True)
                removed.append(p)
    return removed


def find_remaining_refs(py_files, import_rewrites):
    remaining = {}
    for rule in import_rewrites:
        frm = rule['from']
        rx = re.compile(rf"^(\s*(from|import)\s+){re.escape(frm)}(\b|\.)")
        count = 0
        for p in py_files:
            for line in p.read_text(encoding='utf-8', errors='ignore').splitlines():
                if rx.search(line):
                    count += 1
                    break
        if count:
            remaining[frm] = count
    return remaining


def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument('--dry-run', action='store_true')
    g.add_argument('--apply', action='store_true')
    args = ap.parse_args()

    m = load_map()
    file_moves = m.get('file_moves', [])
    import_rewrites = m.get('import_rewrites', [])
    delete_patterns = m.get('delete_globs', [])

    print('Consolidation map loaded from', MAP_JSON if MAP_JSON.exists() else MAP_YAML)
    py_files = list_py_files()
    print(f'Python files scanned: {len(py_files)}')

    # Moves
    moved = perform_moves(file_moves, dry_run=args.dry_run)
    print(f"Planned moves: {len(moved)}")
    for src, dst in moved:
        print('  MOVE', src.relative_to(ROOT), '→', dst.relative_to(ROOT))

    # Import rewrites
    changed = rewrite_imports(py_files, import_rewrites, dry_run=args.dry_run)
    print(f"Files to rewrite imports: {changed}")

    # Deletes
    removed = delete_globs(delete_patterns, dry_run=args.dry_run)
    print(f"Planned deletions: {len(removed)}")
    for p in removed[:30]:
        print('  DELETE', p.relative_to(ROOT))
    if len(removed) > 30:
        print(f'  … and {len(removed)-30} more')

    if args.apply:
        # Post-check for remaining references
        py_files = list_py_files()
        remaining = find_remaining_refs(py_files, import_rewrites)
        if remaining:
            print('ERROR: Remaining old import references found:')
            for mod, cnt in remaining.items():
                print(f'  {mod}: {cnt} files')
            sys.exit(2)
        print('Apply complete, no remaining old imports found.')

if __name__ == '__main__':
    main()
