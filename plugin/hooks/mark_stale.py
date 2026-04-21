#!/usr/bin/env python3
"""
mark_stale.py — 标记 MANIFEST.json 中受 git diff 影响而变 stale 的 sections

用法:
  python3 mark_stale.py file1.py file2.py --manifest .wiki/MANIFEST.json --project-root /path/to/project

逻辑:
  1. 加载 MANIFEST.json
  2. 对每个 changed file，查找 MANIFEST 中 source_files 包含它的 sections
  3. 重新计算 source_hash（MD5 of concatenated contents）
  4. 如果 hash 变化 → 标记 stale: true
  5. 写入 MANIFEST.json（原地更新，保留格式）
"""

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path


def compute_source_hash(file_paths, project_root):
    """计算所有 source file 拼接后的 MD5。"""
    h = hashlib.md5()
    for fp in sorted(file_paths):
        full_path = Path(project_root) / fp
        if full_path.exists():
            h.update(full_path.read_bytes())
    return h.hexdigest()


def load_manifest(manifest_path):
    """加载 MANIFEST.json"""
    with open(manifest_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_manifest(manifest_path, data):
    """保存 MANIFEST.json（保留格式）"""
    with open(manifest_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def mark_stale(changed_files, manifest_path, project_root):
    """标记受影响的 sections 为 stale"""
    manifest = load_manifest(manifest_path)
    changed_set = set(changed_files)

    stale_count = 0
    stale_sections = []

    for section in manifest.get('sections', []):
        source_files = section.get('source_files', [])
        # 检查是否有交集
        if not changed_set.intersection(source_files):
            continue

        # 计算当前 hash
        new_hash = compute_source_hash(source_files, project_root)
        old_hash = section.get('source_hash', '')

        if new_hash != old_hash:
            section['stale'] = True
            section['stale_reason'] = (
                f"source file(s) changed: {', '.join(changed_set.intersection(source_files))} "
                f"at commit {os.environ.get('GIT_COMMIT', 'unknown')}"
            )
            # 更新 hash（下次 mark 时以新 hash 为基准）
            section['source_hash'] = new_hash
            stale_count += 1
            stale_sections.append(f"{section['wiki_file']}#{section['section_id']}")

    if stale_count > 0:
        save_manifest(manifest_path, manifest)
        print(f"[mark_stale] Marked {stale_count} stale section(s):")
        for s in stale_sections:
            print(f"  - {s}")
    else:
        print("[mark_stale] No sections affected by these changes.")

    return stale_count


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Mark wiki sections as stale based on git diff.')
    parser.add_argument('changed_files', nargs='+', help='Changed file paths from git diff')
    parser.add_argument('--manifest', default='.wiki/MANIFEST.json', help='Path to MANIFEST.json')
    parser.add_argument('--project-root', default='.', help='Project root directory')
    args = parser.parse_args()

    try:
        stale = mark_stale(args.changed_files, args.manifest, args.project_root)
        sys.exit(0)
    except Exception as e:
        print(f"[mark_stale] Error: {e}", file=sys.stderr)
        sys.exit(1)
