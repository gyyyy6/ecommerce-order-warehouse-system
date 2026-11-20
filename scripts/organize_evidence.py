#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""将验收截图整理到 docs/evidence 对应目录。"""

import os
import shutil


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCREENSHOT_DIR = os.path.join(BASE_DIR, "screenshots")
EVIDENCE_DIR = os.path.join(BASE_DIR, "docs", "evidence")

MOVES = [
    ("1.png", "AC-DB-05", "ERD.png"),
    ("2.png", "UI-01", "order_list_all.png"),
    ("3.png", "UI-02", "order_filter.png"),
    ("4.png", "CON-01", "concurrency_benchmark.png"),
    ("5.png", "IDX-01", "explain_plan.png"),
    ("6.png", "UI-02", "create_success.png"),
    ("7.png", "CRUD-06", "order_detail.png"),
    ("8.png", "DATA-01", "db_count.png"),
    ("9.png", "SEC-03", "permission_denied.png"),
    ("10.png", "SEC-04", "port_isolation.png"),
]

# 兼容当前仓库中已存在的时间戳/中文命名截图；正常环境下仍优先使用 1.png~10.png。
SOURCE_ALIASES = {
    "1.png": "mermaid-diagram-2026-10-26-144813.png",
    "2.png": "屏幕截图 2026-10-26 141856.png",
    "3.png": "屏幕截图 2026-10-26 142100.png",
    "4.png": "屏幕截图 2026-10-26 142341.png",
    "5.png": "屏幕截图 2026-10-26 142513.png",
    "6.png": "屏幕截图 2026-10-26 143735.png",
    "7.png": "屏幕截图 2026-10-26 143907.png",
    "8.png": "屏幕截图 2026-10-26 144038.png",
    "9.png": "屏幕截图 2026-10-26 144226.png",
    "10.png": "屏幕截图 2026-10-26 144350.png",
}


def resolve_source(source_name):
    """返回实际存在的源文件路径，优先使用标准文件名。"""
    source_path = os.path.join(SCREENSHOT_DIR, source_name)
    if os.path.isfile(source_path):
        return source_path

    alias_name = SOURCE_ALIASES.get(source_name)
    if alias_name:
        alias_path = os.path.join(SCREENSHOT_DIR, alias_name)
        if os.path.isfile(alias_path):
            return alias_path

    return source_path


def main():
    if not os.path.isdir(SCREENSHOT_DIR):
        raise SystemExit(f"截图目录不存在: {SCREENSHOT_DIR}")

    resolved_moves = []
    missing_sources = []

    for source_name, evidence_subdir, target_name in MOVES:
        source_path = resolve_source(source_name)
        if os.path.isfile(source_path):
            resolved_moves.append((source_name, source_path, evidence_subdir, target_name))
        else:
            missing_sources.append(source_name)

    if missing_sources:
        missing_text = ", ".join(missing_sources)
        raise SystemExit(f"缺少截图文件: {missing_text}")

    for source_name, source_path, evidence_subdir, target_name in resolved_moves:
        target_dir = os.path.join(EVIDENCE_DIR, evidence_subdir)
        os.makedirs(target_dir, exist_ok=True)
        target_path = os.path.join(target_dir, target_name)
        shutil.move(source_path, target_path)

        target_display = os.path.relpath(target_path, BASE_DIR)
        print(f"[OK] {source_name} -> {target_display}")

    if os.path.isdir(SCREENSHOT_DIR) and not os.listdir(SCREENSHOT_DIR):
        os.rmdir(SCREENSHOT_DIR)
        print("[OK] Removed empty screenshots directory")


if __name__ == "__main__":
    main()
