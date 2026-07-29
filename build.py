"""PyInstaller 打包脚本

使用方法:
    python build.py              # 打包为单文件 EXE (GUI, 无控制台)
    python build.py --folder     # 打包为文件夹模式（启动更快、调试方便）
    python build.py --clean      # 清理构建缓存后重新打包
    python build.py --debug      # 保留控制台窗口（用于调试）

输出:
    dist/AudioMetadataCopier.exe     （单文件模式）
    dist/AudioMetadataCopier/        （文件夹模式）
"""

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).parent.resolve()
MAIN_SCRIPT = PROJECT_ROOT / "main.py"
DIST_DIR = PROJECT_ROOT / "dist"
BUILD_DIR = PROJECT_ROOT / "build"

# EXE 配置
APP_NAME = "AudioMetadataCopier"
APP_EXE_NAME = f"{APP_NAME}.exe"
APP_ICON = None  # 如需图标: PROJECT_ROOT / "icon.ico"
APP_VERSION = "1.0.0"
APP_DESCRIPTION = "Audio Metadata Copier - MP3/FLAC/OGG/M4A/WAV/WMA"


def clean_build():
    """清理构建产物"""
    for d in [DIST_DIR, BUILD_DIR]:
        if d.exists():
            print(f"Clean: {d}")
            shutil.rmtree(d)
    for spec in PROJECT_ROOT.glob("*.spec"):
        print(f"Clean: {spec}")
        spec.unlink()
    for pycache in PROJECT_ROOT.rglob("__pycache__"):
        shutil.rmtree(pycache, ignore_errors=True)
    print("Clean complete")


def get_hidden_imports():
    """仅列出 PyInstaller 可能遗漏的动态/惰性导入。

    注意：PyInstaller 会根据入口脚本的 import 链自动追踪所有依赖。
    这里只添加那些通过 importlib/__import__ 等动态加载的模块。
    """
    return [
        # mutagen 内部通过惰性导入加载子格式模块，需显式声明
        "mutagen.id3",
        "mutagen.flac",
        "mutagen.oggvorbis",
        "mutagen.mp4",
        "mutagen.wave",
        "mutagen.asf",
        # PyQt6 的 sip 桥梁
        "PyQt6.sip",
    ]


def get_excluded_modules():
    """排除不需要的模块以减小体积、加快打包和启动速度。

    注意：只排除确认不会被使用的模块。
    过度排除可能导致 PyQt6 找不到平台插件等运行时错误。
    """
    return [
        # 非目标 GUI 框架
        "tkinter", "PyQt5", "PySide2", "PySide6",
        # PyQt6 重型子模块（本工具不需要）
        "PyQt6.QtWebEngine", "PyQt6.QtWebEngineCore",
        "PyQt6.QtQml", "PyQt6.QtQuick",
        "PyQt6.QtBluetooth", "PyQt6.QtDBus",
        "PyQt6.QtHelp", "PyQt6.QtMultimedia",
        "PyQt6.QtMultimediaWidgets", "PyQt6.QtNetwork",
        "PyQt6.QtNfc", "PyQt6.QtPositioning",
        "PyQt6.QtPrintSupport", "PyQt6.QtRemoteObjects",
        "PyQt6.QtSensors", "PyQt6.QtSerialPort",
        "PyQt6.QtSql", "PyQt6.QtSvg", "PyQt6.QtSvgWidgets",
        "PyQt6.QtTest", "PyQt6.QtTextToSpeech",
        # 第三方重型库
        "numpy", "scipy", "pandas", "matplotlib",
        "PIL", "Pillow", "cffi",
        "lxml", "sqlite3",
        # 测试框架
        "unittest", "pytest", "nose",
    ]


def build(onefile: bool = True, clean: bool = False, debug: bool = False):
    """执行 PyInstaller 打包

    Args:
        onefile: True=单文件 EXE, False=文件夹模式
        clean: True=打包前清理
        debug: True=保留控制台窗口
    """
    if clean:
        clean_build()

    # 验证源文件
    if not MAIN_SCRIPT.exists():
        print(f"ERROR: Entry script not found: {MAIN_SCRIPT}")
        print("Please run this script from the project root directory")
        sys.exit(1)

    print(f"Build: {APP_NAME} v{APP_VERSION}")
    print(f"Mode: {'single-file EXE' if onefile else 'folder'}")
    print(f"Entry: {MAIN_SCRIPT}")
    print("-" * 60)

    # 构建 PyInstaller 命令
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name", APP_NAME,
        "--distpath", str(DIST_DIR),
        "--workpath", str(BUILD_DIR),
        "--specpath", str(PROJECT_ROOT),
        "--noconfirm",
    ]

    # 控制台模式：debug 时保留，否则隐藏
    if not debug:
        cmd.append("--windowed")

    # 打包模式
    if onefile:
        cmd.append("--onefile")
    else:
        cmd.append("--onedir")

    # 添加图标
    if APP_ICON and APP_ICON.exists():
        cmd.extend(["--icon", str(APP_ICON)])

    # 隐藏导入
    for imp in get_hidden_imports():
        cmd.extend(["--hidden-import", imp])

    # 排除模块
    for mod in get_excluded_modules():
        cmd.extend(["--exclude-module", mod])

    # 入口脚本
    cmd.append(str(MAIN_SCRIPT))

    # 打印命令（调试用）
    print("PyInstaller command:")
    print(" \\\n  ".join(cmd[:15]))
    print("  ... (%d total args)" % len(cmd))
    print("-" * 60)

    # 执行打包
    result = subprocess.run(cmd, cwd=str(PROJECT_ROOT))

    if result.returncode == 0:
        # 打包成功
        if onefile:
            exe_path = DIST_DIR / APP_EXE_NAME
        else:
            exe_path = DIST_DIR / APP_NAME / APP_EXE_NAME

        if exe_path.exists():
            size_mb = exe_path.stat().st_size / (1024 * 1024)
            print()
            print("=" * 60)
            print("[OK] Build successful!")
            print(f"     Output: {exe_path}")
            print(f"     Size:   {size_mb:.1f} MB")
            print(f"     Mode:   {'single-file' if onefile else 'folder'}")
            print("=" * 60)
        else:
            print("[WARN] Build completed but output file not found. Check logs.")
            return 1
    else:
        print()
        print(f"[FAIL] Build failed (code={result.returncode})")
        print("Check the build log above for details.")
        return result.returncode

    return 0


def main():
    parser = argparse.ArgumentParser(
        description=f"{APP_NAME} v{APP_VERSION} PyInstaller build tool"
    )
    parser.add_argument(
        "--folder", action="store_true",
        help="Use folder mode (faster startup, easier debugging)"
    )
    parser.add_argument(
        "--clean", action="store_true",
        help="Clean all build caches before building"
    )
    parser.add_argument(
        "--debug", action="store_true",
        help="Keep console window visible (for debugging)"
    )

    args = parser.parse_args()

    print("=" * 60)
    print(f"  {APP_NAME} v{APP_VERSION} - Build Tool")
    print(f"  {APP_DESCRIPTION}")
    print("=" * 60)
    print()

    exit_code = build(
        onefile=not args.folder,
        clean=args.clean,
        debug=args.debug,
    )
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
