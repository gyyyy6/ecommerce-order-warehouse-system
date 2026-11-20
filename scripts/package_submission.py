#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generate the final course submission folder (no archive is created).

Result:
    student-id_曾理/
    ├── data/
    ├── code/
    └── document/
"""

from __future__ import annotations

import shutil
import sys
from dataclasses import dataclass, field
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
STUDENT_ID = "student-id"
STUDENT_NAME = "曾理"
PACKAGE_NAME = f"{STUDENT_ID}_{STUDENT_NAME}"
PACKAGE_ROOT = PROJECT_ROOT / PACKAGE_NAME

APP_SOURCE = PROJECT_ROOT / "app"
SQL_SOURCE = PROJECT_ROOT / "sql"
SCRIPTS_SOURCE = PROJECT_ROOT / "scripts"
DOCS_SOURCE = PROJECT_ROOT / "docs"

IGNORED_DIRS = {".git", ".venv", "venv", "__pycache__", ".pytest_cache",
                ".mypy_cache", ".idea", ".vscode", "node_modules"}
IGNORED_FILES = {".DS_Store", "Thumbs.db"}
IGNORED_SUFFIXES = {".pyc", ".pyo", ".log"}

README_DATA_TEXT = """数据备份说明

因备份文件过大，数据由 scripts/seed_data.py 生成，执行该脚本即可生成 16 万余条初始数据。

提交包内脚本路径：code/seed_data.py。
"""


@dataclass
class ScreenshotSpec:
    dest: str
    label: str
    patterns: tuple[str, ...]
    sanitize: bool = False


SCREENSHOTS = (
    ScreenshotSpec("CRUD-06/order_detail.png", "订单详情（多表 JOIN）", (
        "docs/evidence/CRUD-06/order_detail.png",
        "docs/evidence/**/*order*detail*.png",
    )),
    ScreenshotSpec("IDX-01/explain_plan.png", "索引执行计划", (
        "docs/evidence/IDX-01/explain_plan.png",
        "docs/evidence/**/*explain*.png",
    )),
    ScreenshotSpec("TX-03/stock-insufficient.png", "库存不足回滚", (
        "docs/evidence/TX-03/stock-insufficient.png",
        "docs/evidence/TX-03/stock_insufficient.png",
        "docs/evidence/TX-03/*.png",
        "docs/evidence/**/*stock*insufficient*.png",
        "docs/evidence/**/*oversell*.png",
        "防超卖报错图.png",
        "防超卖*.png",
        "*防超卖*.png",
        "*超卖*.png",
    )),
    ScreenshotSpec("SEC-03/permission_denied.png", "权限拒绝", (
        "docs/evidence/SEC-03/permission_denied.png",
        "docs/evidence/**/*permission*denied*.png",
    )),
    ScreenshotSpec("CON-01/concurrency_benchmark.png", "并发测试", (
        "docs/evidence/CON-01/concurrency_benchmark.png",
        "docs/evidence/**/*concurrency*.png",
    ), sanitize=True),
)


@dataclass
class BuildReport:
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    screenshots: list[str] = field(default_factory=list)
    removed_zips: list[str] = field(default_factory=list)

    def warn(self, message: str) -> None:
        self.warnings.append(message)
        print(f"[WARN] {message}")

    def error(self, message: str) -> None:
        self.errors.append(message)
        print(f"[ERROR] {message}", file=sys.stderr)


def configure_stdout() -> None:
    for name in ("stdout", "stderr"):
        stream = getattr(sys, name, None)
        if stream is not None and hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass


def info(message: str) -> None:
    print(f"[INFO] {message}")


def ok(message: str) -> None:
    print(f"[OK] {message}")


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return str(path)


def remove_old_zips(report: BuildReport) -> None:
    for path in sorted(PROJECT_ROOT.glob("*.zip")):
        if path.is_file():
            path.unlink()
            report.removed_zips.append(path.name)
    if report.removed_zips:
        ok(f"已清理旧 zip：{', '.join(report.removed_zips)}")
    else:
        info("项目根目录没有旧 zip 文件。")


def reset_package_root() -> None:
    expected = (PROJECT_ROOT / PACKAGE_NAME).resolve()
    actual = PACKAGE_ROOT.resolve()
    if actual != expected or PROJECT_ROOT.resolve() not in actual.parents:
        raise RuntimeError(f"拒绝清理意外路径：{actual}")
    if PACKAGE_ROOT.exists():
        shutil.rmtree(PACKAGE_ROOT)
    for name in ("data", "code", "document"):
        (PACKAGE_ROOT / name).mkdir(parents=True)


def copy_file(src: Path, dst: Path, report: BuildReport, required: bool = True) -> bool:
    if not src.is_file():
        message = f"缺少文件：{rel(src)}"
        if required:
            report.error(message)
        else:
            report.warn(message + "，已跳过")
        return False
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    return True


def ignore_app_entry(directory: str, names: list[str]) -> set[str]:
    ignored: set[str] = set()
    base = Path(directory)
    for name in names:
        path = base / name
        if path.is_dir():
            if name in IGNORED_DIRS:
                ignored.add(name)
        elif (name in IGNORED_FILES or name == ".env"
              or (name.startswith(".env.") and name != ".env.example")
              or path.suffix.lower() in IGNORED_SUFFIXES):
            ignored.add(name)
    return ignored


def copy_app(report: BuildReport) -> None:
    dst = PACKAGE_ROOT / "code" / "app"
    if not APP_SOURCE.is_dir():
        report.error("缺少 app/ 目录，无法打包前端与后端代码。")
        return
    shutil.copytree(APP_SOURCE, dst, ignore=ignore_app_entry)
    count = sum(1 for path in dst.rglob("*") if path.is_file())
    ok(f"已复制 app/ 目录（{count} 个文件，已排除缓存与 .env）。")


def copy_data(report: BuildReport) -> None:
    data_dir = PACKAGE_ROOT / "data"
    copy_file(SQL_SOURCE / "01_schema.sql", data_dir / "01_schema.sql", report)
    copy_file(SQL_SOURCE / "02_indexes.sql", data_dir / "02_indexes.sql", report)
    (data_dir / "README_data.txt").write_text(
        README_DATA_TEXT, encoding="utf-8", newline="\r\n"
    )
    ok("已写入 data/README_data.txt。")


def make_start_demo(report: BuildReport) -> None:
    dst = PACKAGE_ROOT / "code" / "start_demo.sh"
    start_demo = SCRIPTS_SOURCE / "start_demo.sh"
    run_app = SCRIPTS_SOURCE / "run_app.sh"
    if start_demo.is_file():
        copy_file(start_demo, dst, report)
    elif run_app.is_file():
        content = """#!/usr/bin/env bash
# Generated from scripts/run_app.sh for the submission layout.
set -euo pipefail

CODE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$CODE_DIR"

if [ -f .env ]; then
  set -a
  . ./.env
  set +a
fi

export FLASK_DEBUG=0

exec python3 -m flask --app app run --host "${FLASK_HOST:-0.0.0.0}" --port "${FLASK_PORT:-5000}" --no-debugger --no-reload
"""
        dst.write_text(content, encoding="utf-8", newline="\n")
        report.warn("源项目没有 scripts/start_demo.sh，已按 run_app.sh 逻辑生成适配 code/ 布局的 start_demo.sh。")
    else:
        report.error("缺少 scripts/start_demo.sh 与 scripts/run_app.sh。")
        return
    try:
        dst.chmod(0o755)
    except OSError:
        pass


def copy_code(report: BuildReport) -> None:
    copy_app(report)
    code_dir = PACKAGE_ROOT / "code"
    copy_file(SCRIPTS_SOURCE / "init_db.py", code_dir / "init_db.py", report)
    copy_file(SCRIPTS_SOURCE / "seed_data.py", code_dir / "seed_data.py", report)
    make_start_demo(report)
    copy_file(PROJECT_ROOT / "requirements.txt", code_dir / "requirements.txt", report)
    ok("已整理 code/：app、init_db.py、seed_data.py、start_demo.sh、requirements.txt。")


def find_first_file(patterns: tuple[str, ...]) -> Path | None:
    for pattern in patterns:
        candidate = PROJECT_ROOT / pattern
        if candidate.is_file():
            return candidate
    for pattern in patterns:
        for match in sorted(PROJECT_ROOT.glob(pattern)):
            if match.is_file():
                return match
    return None


def find_erd() -> Path | None:
    return find_first_file((
        "docs/evidence/AC-DB-05/ERD.png",
        "docs/evidence/AC-DB-05/erd.png",
        "docs/evidence/**/*ERD*.png",
        "docs/evidence/**/*erd*.png",
    ))


def sanitize_concurrency_screenshot(src: Path, dst: Path) -> bool:
    """Black out the terminal lines that contain the demo database password."""
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        return False
    try:
        with Image.open(src) as image:
            rgb = image.convert("RGB")
            width, height = rgb.size
            draw = ImageDraw.Draw(rgb)
            top = max(18, int(height * 0.035))
            bottom = min(height, int(height * 0.175))
            draw.rectangle((0, top, width, bottom), fill=(0, 0, 0))
            try:
                font = ImageFont.load_default(size=max(14, int(height * 0.028)))
            except TypeError:
                font = ImageFont.load_default()
            draw.text((12, top + 5), "CREDENTIALS REDACTED", fill=(255, 90, 90), font=font)
            dst.parent.mkdir(parents=True, exist_ok=True)
            rgb.save(dst, format="PNG", optimize=True)
        return True
    except Exception:
        return False


def copy_screenshots(report: BuildReport) -> None:
    screenshots_dir = PACKAGE_ROOT / "document" / "screenshots"
    for spec in SCREENSHOTS:
        src = find_first_file(spec.patterns)
        if src is None:
            report.error(f"缺少核心截图：{spec.label}")
            continue
        dst = screenshots_dir / spec.dest
        if spec.sanitize:
            if not sanitize_concurrency_screenshot(src, dst):
                report.error(f"{spec.label} 截图脱敏失败（需要 Pillow），为避免泄露密码未复制。")
                continue
        elif not copy_file(src, dst, report):
            continue
        report.screenshots.append(f"{spec.dest}（源：{rel(src)}）")
        info(f"核心截图：{spec.dest} <- {rel(src)}")
    if len(report.screenshots) != 5:
        report.error(f"核心截图数量应为 5，实际为 {len(report.screenshots)}。")
    else:
        ok("已整理 5 张核心截图到 document/screenshots/。")


def copy_document(report: BuildReport) -> None:
    document_dir = PACKAGE_ROOT / "document"
    copy_file(DOCS_SOURCE / "report" / "report.pdf", document_dir / "report.pdf",
              report, required=False)
    copy_file(DOCS_SOURCE / "report" / "report.md", document_dir / "report.md", report)
    erd_path = find_erd()
    if erd_path is None:
        report.error("未找到 ERD 图（docs/evidence/AC-DB-05/ERD.png）。")
    else:
        copy_file(erd_path, document_dir / "ERD.png", report)
        ok(f"已复制 ERD：{rel(erd_path)}")
    copy_screenshots(report)
    ok("已整理 document/：报告、ERD 与核心截图。")


def validate_structure(report: BuildReport) -> None:
    entries = list(PACKAGE_ROOT.iterdir())
    root_dirs = {path.name for path in entries if path.is_dir()}
    root_files = [path.name for path in entries if path.is_file()]
    expected = {"data", "code", "document"}
    if root_dirs != expected:
        report.error(f"根目录文件夹应为 {sorted(expected)}，实际为 {sorted(root_dirs)}")
    if root_files:
        report.error(f"根目录不应包含文件：{', '.join(sorted(root_files))}")
    if root_dirs == expected and not root_files:
        ok("根目录结构校验通过：仅包含 data、code、document 三个文件夹。")

    required = (
        "data/01_schema.sql", "data/02_indexes.sql", "data/README_data.txt",
        "code/app/__init__.py", "code/init_db.py", "code/seed_data.py",
        "code/start_demo.sh", "code/requirements.txt",
        "document/report.md", "document/ERD.png",
    )
    for item in required:
        if not (PACKAGE_ROOT / item).exists():
            report.error(f"提交包缺少必须内容：{item}")

    screenshots = list((PACKAGE_ROOT / "document" / "screenshots").rglob("*.png"))
    if len(screenshots) != 5:
        report.error(f"document/screenshots/ 应为 5 张 PNG，实际为 {len(screenshots)} 张。")

    forbidden = {".git", ".venv", "venv", "__pycache__", ".pytest_cache"}
    for path in PACKAGE_ROOT.rglob("*"):
        relative = path.relative_to(PACKAGE_ROOT)
        if set(relative.parts) & forbidden:
            report.error(f"提交包包含禁止目录：{relative.as_posix()}")
        elif path.is_file() and path.suffix.lower() in (".pyc", ".pyo"):
            report.error(f"提交包包含编译缓存：{relative.as_posix()}")
        elif path.is_file() and path.name == ".env":
            report.error(f"提交包包含真实 .env：{relative.as_posix()}")

    if not report.errors:
        ok("提交包内容与排除项校验全部通过。")


def print_tree(root: Path) -> None:
    print()
    print("=" * 72)
    print("文件夹结构")
    print("=" * 72)

    def walk(directory: Path, prefix: str) -> None:
        entries = sorted(directory.iterdir(), key=lambda item: (item.is_file(), item.name.lower()))
        for index, entry in enumerate(entries):
            last = index == len(entries) - 1
            print(f"{prefix}{'└── ' if last else '├── '}{entry.name}{'/' if entry.is_dir() else ''}")
            if entry.is_dir():
                walk(entry, prefix + ("    " if last else "│   "))

    print(f"{root.name}/")
    walk(root, "")


def print_summary(report: BuildReport) -> None:
    files = [path for path in PACKAGE_ROOT.rglob("*") if path.is_file()]
    total_bytes = sum(path.stat().st_size for path in files)
    print()
    print("=" * 72)
    print("打包结果")
    print("=" * 72)
    print(f"输出目录：{PACKAGE_ROOT}")
    print(f"文件总数：{len(files)}")
    print(f"目录大小：{total_bytes / 1024 / 1024:.2f} MB")
    print("压缩状态：未压缩（请用 WinRAR 手动生成 .rar）")
    if report.removed_zips:
        print(f"已清理旧 zip：{len(report.removed_zips)} 个")
    print(f"警告：{len(report.warnings)} 个")
    print(f"错误：{len(report.errors)} 个")
    for warning in report.warnings:
        print(f"  - {warning}")
    for error in report.errors:
        print(f"  - {error}")
    print("=" * 72)


def main() -> int:
    configure_stdout()
    report = BuildReport()
    info("清理项目根目录旧 zip ...")
    remove_old_zips(report)
    info(f"重建提交根目录 {PACKAGE_NAME} ...")
    reset_package_root()
    info("整理 data/ ...")
    copy_data(report)
    info("整理 code/ ...")
    copy_code(report)
    info("整理 document/ ...")
    copy_document(report)
    info("校验目录结构与内容 ...")
    validate_structure(report)
    print_tree(PACKAGE_ROOT)
    print_summary(report)
    return 1 if report.errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
