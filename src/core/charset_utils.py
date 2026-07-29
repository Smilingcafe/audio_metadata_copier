"""字符集兼容工具模块

处理音频元数据中的多编码问题：
- ID3v2 标签可能使用 latin1、UTF-16、UTF-8 编码
- Vorbis Comments 固定使用 UTF-8
- 修复常见乱码（如 GBK 编码被标记为 latin1）
- 确保输出始终为合法的 UTF-8
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

_ENCODING_GUESS_ORDER = [
    "utf-8", "gbk", "gb2312", "gb18030",
    "shift_jis", "euc-kr", "big5", "latin1",
]


def normalize_text(text: str) -> str:
    if text is None:
        return ""
    if not isinstance(text, str):
        text = str(text)
    text = text.strip()
    text = "".join(ch for ch in text if ch >= " " or ch in "\n\r\t")
    return text


def repair_mojibake(text: str) -> str:
    if not text or text.isspace():
        return text
    cjk_count = sum(1 for ch in text if "\u4e00" <= ch <= "\u9fff"
                    or "\u3040" <= ch <= "\u309f"
                    or "\uac00" <= ch <= "\ud7af")
    if cjk_count > len(text) * 0.3 or text.isascii():
        return text
    try:
        raw_bytes = text.encode("latin1")
    except UnicodeEncodeError:
        return text
    for encoding in _ENCODING_GUESS_ORDER:
        if encoding == "latin1":
            continue
        try:
            decoded = raw_bytes.decode(encoding)
            cjk_in_decoded = sum(1 for ch in decoded if "\u4e00" <= ch <= "\u9fff")
            if cjk_in_decoded > 0 and "\ufffd" not in decoded:
                logger.debug("乱码修复: %s -> %s", repr(text[:50]), repr(decoded[:50]))
                return decoded
        except (UnicodeDecodeError, UnicodeError):
            continue
    return text


def safe_str(value) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, (int, float)):
        return str(int(value)) if isinstance(value, float) and value.is_integer() else str(value)
    if isinstance(value, (list, tuple)):
        for v in value:
            result = safe_str(v)
            if result:
                return result
        return ""
    return str(value)


def ensure_utf8(text: str) -> str:
    if not text:
        return ""
    try:
        text.encode("utf-8")
        return text
    except UnicodeEncodeError:
        return text.encode("utf-8", errors="replace").decode("utf-8")


def process_tag_value(raw_value) -> str:
    text = safe_str(raw_value)
    text = repair_mojibake(text)
    text = normalize_text(text)
    text = ensure_utf8(text)
    return text
