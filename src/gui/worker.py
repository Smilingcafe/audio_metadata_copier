"""后台工作线程模块

使用 QThread 处理耗时的元数据操作，保持 GUI 响应。
"""

import logging
import os
from typing import List, Optional, Set

from PyQt6.QtCore import QThread, pyqtSignal

from ..core.metadata import copy_metadata, read_metadata, AudioMetadata
from ..core.matcher import MatchResult

logger = logging.getLogger(__name__)


class ScanWorker(QThread):
    """后台扫描工作线程：扫描目标目录并匹配文件。"""

    # 信号
    progress = pyqtSignal(int, int)       # (当前进度, 总进度)
    match_found = pyqtSignal(object)       # MatchResult
    finished = pyqtSignal(object)          # ScanResult
    error = pyqtSignal(str)               # 错误信息

    def __init__(self, source_path: str, target_dir: str,
                 formats: Optional[Set[str]] = None,
                 recursive: bool = True):
        super().__init__()
        self.source_path = source_path
        self.target_dir = target_dir
        self.formats = formats
        self.recursive = recursive

    def run(self):
        """在后台线程执行扫描"""
        from ..core.matcher import scan_target_directory
        try:
            result = scan_target_directory(
                self.source_path,
                self.target_dir,
                formats=self.formats,
                recursive=self.recursive,
            )
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))
            logger.exception("扫描失败")


class CopyWorker(QThread):
    """后台复制工作线程：逐个复制元数据到目标文件。"""

    # 信号
    progress = pyqtSignal(int, int, str)   # (完成数, 总数, 当前文件名)
    file_done = pyqtSignal(str, bool, str) # (文件路径, 是否成功, 错误信息)
    finished = pyqtSignal(int, int, int)   # (成功数, 失败数, 跳过数)
    log_message = pyqtSignal(str)          # 日志消息

    def __init__(self, source_path: str, matches: List[MatchResult],
                 copy_cover: bool = True,
                 create_backup: bool = False,
                 skip_existing: bool = False):
        super().__init__()
        self.source_path = source_path
        self.matches = matches
        self.copy_cover = copy_cover
        self.create_backup = create_backup
        self.skip_existing = skip_existing
        self._cancelled = False

    def cancel(self):
        """取消操作"""
        self._cancelled = True
        self.log_message.emit("操作已被用户取消")

    def run(self):
        """在后台线程执行批量复制"""
        total = len(self.matches)
        success_count = 0
        fail_count = 0
        skip_count = 0

        self.log_message.emit(f"开始处理 {total} 个文件...")

        for idx, match in enumerate(self.matches):
            if self._cancelled:
                break

            target = match.target_path
            filename = os.path.basename(target)
            self.log_message.emit(f"  [{idx + 1}/{total}] {filename}")

            # 检查是否需要跳过已有元数据的文件
            if self.skip_existing:
                try:
                    existing = read_metadata(target)
                    if existing.has_any_data():
                        self.log_message.emit(f"    → 跳过（已有元数据）")
                        skip_count += 1
                        self.progress.emit(idx + 1, total, filename)
                        continue
                except Exception:
                    pass  # 如果无法读取，尝试写入

            try:
                ok = copy_metadata(
                    self.source_path,
                    target,
                    copy_cover=self.copy_cover,
                    create_backup=self.create_backup,
                )
                if ok:
                    success_count += 1
                    self.log_message.emit(f"    → 成功")
                    self.file_done.emit(target, True, "")
                else:
                    fail_count += 1
                    self.log_message.emit(f"    → 失败（无元数据可复制）")
                    self.file_done.emit(target, False, "源文件无元数据")
            except Exception as e:
                fail_count += 1
                err_msg = str(e)
                self.log_message.emit(f"    → 失败: {err_msg}")
                self.file_done.emit(target, False, err_msg)
                logger.exception("复制失败: %s", target)

            self.progress.emit(idx + 1, total, filename)

        self.log_message.emit(
            f"\n处理完成: 成功 {success_count}, 失败 {fail_count}, 跳过 {skip_count}"
        )
        self.finished.emit(success_count, fail_count, skip_count)


class MetadataPreviewWorker(QThread):
    """后台预览工作线程：读取源文件的元数据用于预览。"""

    result = pyqtSignal(object)    # AudioMetadata
    error = pyqtSignal(str)

    def __init__(self, filepath: str):
        super().__init__()
        self.filepath = filepath

    def run(self):
        """读取元数据"""
        try:
            meta = read_metadata(self.filepath)
            self.result.emit(meta)
        except Exception as e:
            self.error.emit(str(e))
            logger.exception("读取元数据失败")
