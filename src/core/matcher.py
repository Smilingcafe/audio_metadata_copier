"""文件匹配器模块

实现智能音频文件匹配：
- 基于源文件名（不含扩展名）的严格子串匹配
- 递归目录扫描
- 格式过滤
- 排序和去重
"""

import logging
import os
import re
from pathlib import Path
from typing import List, Set, Optional, Dict, Tuple
from dataclasses import dataclass

from .metadata import SUPPORTED_EXTENSIONS, FORMAT_EXTENSIONS

logger = logging.getLogger(__name__)


@dataclass
class MatchResult:
    """单个匹配结果"""
    source_path: str          # 源文件完整路径
    source_name: str          # 源文件名（含扩展名）
    source_stem: str          # 源文件名（不含扩展名）
    target_path: str          # 目标文件完整路径
    target_name: str          # 目标文件名（含扩展名）
    target_relative: str      # 目标文件相对路径（相对于目标目录）
    target_format: str        # 目标文件格式
    match_type: str           # 'exact' 精确匹配 或 'substring' 子串匹配

    @property
    def display_line(self) -> str:
        """用户友好的单行描述"""
        return f"[{self.target_format.upper()}] {self.target_name}"


@dataclass
class ScanResult:
    """扫描结果汇总"""
    source_path: str
    source_stem: str
    target_dir: str
    matches: List[MatchResult]
    total_found: int          # 找到的音频文件总数（过滤前）
    total_matched: int        # 匹配成功的文件数
    scanned_dirs: int         # 扫描的目录数量
    error_files: List[Tuple[str, str]]  # (文件路径, 错误信息)


def scan_target_directory(
    source_path: str,
    target_dir: str,
    formats: Optional[Set[str]] = None,
    recursive: bool = True,
    exclude_source: bool = True,
) -> ScanResult:
    """扫描目标目录，自动匹配与源文件相关的目标文件。

    匹配规则：目标文件名（不含扩展名）必须完整包含源文件名（不含扩展名）作为子串。
    例如：源文件 "孙燕姿 - 雨天.flac" → 匹配 "孙燕姿 - 雨天_Inst.flac" 但不匹配 "孙燕姿 - 雨天的故事.flac"

    Args:
        source_path: 源音频文件完整路径
        target_dir: 目标目录路径
        formats: 允许的目标格式集合，如 {"mp3", "flac", "ogg"}，None 表示全部支持
        recursive: 是否递归扫描子目录
        exclude_source: 是否排除源文件自身（如果它在目标目录中）

    Returns:
        ScanResult 对象，包含所有匹配结果
    """
    source_path = str(source_path)
    target_dir = str(target_dir)

    if not os.path.isfile(source_path):
        raise FileNotFoundError(f"源文件不存在: {source_path}")
    if not os.path.isdir(target_dir):
        raise NotADirectoryError(f"目标目录不存在: {target_dir}")

    source_name = os.path.basename(source_path)
    source_stem = os.path.splitext(source_name)[0]
    source_stem_normalized = _normalize_for_matching(source_stem)

    # 确定允许的扩展名
    allowed_exts = _get_allowed_extensions(formats)

    matches: List[MatchResult] = []
    error_files: List[Tuple[str, str]] = []
    total_found = 0
    scanned_dirs = 0

    # 递归或非递归扫描
    try:
        for root, dirs, files in os.walk(target_dir):
            scanned_dirs += 1

            # 排序保证结果稳定
            dirs.sort()
            files.sort()

            for filename in files:
                ext = os.path.splitext(filename)[1].lower()
                if ext not in allowed_exts:
                    continue

                total_found += 1
                target_stem = os.path.splitext(filename)[0]
                target_full = os.path.join(root, filename)

                # 跳过源文件自身
                if exclude_source and os.path.normpath(target_full) == os.path.normpath(source_path):
                    continue

                # 严格子串匹配
                if not _is_substring_match(source_stem_normalized, target_stem):
                    continue

                # 确定匹配类型
                match_type = "exact" if target_stem == source_stem else "substring"

                # 确定格式
                fmt = _ext_to_format(ext)
                relative = os.path.relpath(target_full, target_dir)

                matches.append(MatchResult(
                    source_path=source_path,
                    source_name=source_name,
                    source_stem=source_stem,
                    target_path=target_full,
                    target_name=filename,
                    target_relative=relative,
                    target_format=fmt,
                    match_type=match_type,
                ))

            if not recursive:
                break

    except PermissionError as e:
        error_files.append((target_dir, f"权限不足: {e}"))
    except OSError as e:
        error_files.append((target_dir, f"文件系统错误: {e}"))

    return ScanResult(
        source_path=source_path,
        source_stem=source_stem,
        target_dir=target_dir,
        matches=matches,
        total_found=total_found,
        total_matched=len(matches),
        scanned_dirs=scanned_dirs,
        error_files=error_files,
    )


def match_single_file(source_path: str, target_path: str) -> Optional[MatchResult]:
    """手动指定单个目标文件的匹配（不依赖文件名匹配规则）。

    Args:
        source_path: 源文件路径
        target_path: 目标文件路径

    Returns:
        MatchResult 对象，如果目标不是支持的音频格式则返回 None
    """
    source_path = str(source_path)
    target_path = str(target_path)

    if not os.path.isfile(source_path):
        raise FileNotFoundError(f"源文件不存在: {source_path}")
    if not os.path.isfile(target_path):
        raise FileNotFoundError(f"目标文件不存在: {target_path}")

    ext = os.path.splitext(target_path)[1].lower()
    if ext not in SUPPORTED_EXTENSIONS:
        logger.warning("目标文件格式不支持: %s", target_path)
        return None

    source_name = os.path.basename(source_path)
    source_stem = os.path.splitext(source_name)[0]
    target_name = os.path.basename(target_path)

    return MatchResult(
        source_path=source_path,
        source_name=source_name,
        source_stem=source_stem,
        target_path=target_path,
        target_name=target_name,
        target_relative=target_name,
        target_format=_ext_to_format(ext),
        match_type="exact",
    )


# =============================================================================
# 内部辅助函数
# =============================================================================

def _normalize_for_matching(text: str) -> str:
    """标准化文本用于匹配：去除多余空白、转小写。

    注意：对于中文文件名，"孙燕姿 - 雨天" 和 "孙燕姿-雨天" 是不同输入。
    我们不改变空格/连字符以保持精确子串匹配语义。
    """
    # 只去除首尾空白，保持内部结构不变
    text = text.strip()
    # 统一全角/半角？不，保持原文以精确匹配
    text = text.casefold()  # 只做大小写不敏感
    return text


def _is_substring_match(source_stem: str, target_stem: str) -> bool:
    """检查目标文件名是否包含源文件名作为完整子串。

    大小写不敏感，但字符顺序和完整性必须完全一致。
    """
    source_norm = _normalize_for_matching(source_stem)
    target_norm = _normalize_for_matching(target_stem)

    if not source_norm:
        return False

    return source_norm in target_norm


def _get_allowed_extensions(formats: Optional[Set[str]]) -> Set[str]:
    """根据格式选择确定允许的文件扩展名集合。

    Args:
        formats: 格式集合如 {"mp3", "flac"}，或 None 表示全部

    Returns:
        扩展名集合如 {".mp3", ".flac"}
    """
    if formats is None or len(formats) == 0:
        return SUPPORTED_EXTENSIONS

    allowed = set()
    for fmt in formats:
        fmt_lower = fmt.lower().lstrip(".")
        if fmt_lower in FORMAT_EXTENSIONS:
            allowed.update(FORMAT_EXTENSIONS[fmt_lower])
        else:
            # 可能是直接指定扩展名
            ext = f".{fmt_lower}" if not fmt_lower.startswith(".") else fmt_lower
            if ext in SUPPORTED_EXTENSIONS:
                allowed.add(ext)
    return allowed if allowed else SUPPORTED_EXTENSIONS


def _ext_to_format(ext: str) -> str:
    """扩展名转格式标识符"""
    ext = ext.lower().lstrip(".")
    ext_with_dot = f".{ext}"
    for fmt, exts in FORMAT_EXTENSIONS.items():
        if ext_with_dot in exts:
            return fmt
    return ext


def get_all_audio_files(directory: str, formats: Optional[Set[str]] = None,
                        recursive: bool = True) -> List[str]:
    """获取目录下所有指定格式的音频文件（不进行匹配，纯列表）。

    Args:
        directory: 目录路径
        formats: 格式过滤
        recursive: 是否递归

    Returns:
        音频文件完整路径列表
    """
    directory = str(directory)
    if not os.path.isdir(directory):
        return []

    allowed_exts = _get_allowed_extensions(formats)
    files = []

    try:
        for root, dirs, filenames in os.walk(directory):
            dirs.sort()
            for f in sorted(filenames):
                if os.path.splitext(f)[1].lower() in allowed_exts:
                    files.append(os.path.join(root, f))
            if not recursive:
                break
    except (PermissionError, OSError) as e:
        logger.warning("扫描目录错误: %s", e)

    return files


# =============================================================================
# 高级匹配：文件名相似度分析（供调试/预览）
# =============================================================================

def analyze_filename_similarity(source_stem: str, target_stems: List[str]) -> Dict[str, float]:
    """分析源文件名与一组目标文件名的相似度（调试用）。

    使用 difflib.SequenceMatcher 计算相似度比率。

    Args:
        source_stem: 源文件名（不含扩展名）
        target_stems: 目标文件名列表（不含扩展名）

    Returns:
        字典 {target_stem: similarity_ratio}，比率 0.0 ~ 1.0
    """
    from difflib import SequenceMatcher
    result = {}
    source_norm = _normalize_for_matching(source_stem)
    for ts in target_stems:
        target_norm = _normalize_for_matching(ts)
        ratio = SequenceMatcher(None, source_norm, target_norm).ratio()
        result[ts] = ratio
    return dict(sorted(result.items(), key=lambda x: x[1], reverse=True))
