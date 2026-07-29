"""音频元数据读写引擎

支持格式：
- MP3:  ID3v1 + ID3v2（mutagen.id3）
- FLAC: Vorbis Comments + Picture（mutagen.flac）
- OGG:  Vorbis Comments + METADATA_BLOCK_PICTURE（mutagen.oggvorbis）
- M4A:  iTunes atoms（mutagen.mp4）
- WAV:  RIFF INFO（mutagen.wave）+ 有限元数据

所有读/写操作均通过此模块统一接口进行，外部调用者无需关心格式差异。
"""

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Dict, Any, List

import mutagen
from mutagen.id3 import ID3, ID3NoHeaderError
from mutagen.flac import FLAC, Picture
from mutagen.oggvorbis import OggVorbis
from mutagen.mp4 import MP4, MP4Cover
from mutagen.wave import WAVE

from .charset_utils import process_tag_value, normalize_text

logger = logging.getLogger(__name__)

# 支持的音频文件扩展名
SUPPORTED_EXTENSIONS = {".mp3", ".flac", ".ogg", ".oga", ".m4a", ".mp4", ".wav", ".wma"}
# 每种格式对应的扩展名（用于目标格式筛选）
FORMAT_EXTENSIONS = {
    "mp3": [".mp3"],
    "flac": [".flac"],
    "ogg": [".ogg", ".oga"],
    "m4a": [".m4a", ".mp4"],
    "wav": [".wav"],
    "wma": [".wma"],
}


@dataclass
class AudioMetadata:
    """统一的音频元数据结构，屏蔽不同格式的差异。"""

    title: str = ""
    artist: str = ""
    album: str = ""
    albumartist: str = ""
    date: str = ""
    tracknumber: str = ""
    tracktotal: str = ""
    discnumber: str = ""
    disctotal: str = ""
    genre: str = ""
    comment: str = ""
    composer: str = ""
    copyright: str = ""
    encodedby: str = ""
    organization: str = ""

    # 封面数据
    cover_data: Optional[bytes] = None
    cover_mime: str = ""           # 例如 "image/jpeg", "image/png"
    cover_width: int = 0
    cover_height: int = 0
    cover_depth: int = 0
    cover_description: str = ""

    # 额外原始标签（保留未映射的字段）
    extra: Dict[str, Any] = field(default_factory=dict)

    # 源文件信息
    source_format: str = ""
    source_path: str = ""

    @property
    def has_cover(self) -> bool:
        return self.cover_data is not None and len(self.cover_data) > 0

    @property
    def cover_extension(self) -> str:
        """从 MIME 类型推断封面文件扩展名"""
        mime_map = {
            "image/jpeg": ".jpg",
            "image/jpg": ".jpg",
            "image/png": ".png",
            "image/gif": ".gif",
            "image/bmp": ".bmp",
            "image/webp": ".webp",
            "image/tiff": ".tiff",
        }
        return mime_map.get(self.cover_mime.lower(), ".jpg")

    def to_dict(self) -> Dict[str, str]:
        """导出为标准字典（仅文本字段）"""
        return {
            "title": self.title,
            "artist": self.artist,
            "album": self.album,
            "albumartist": self.albumartist,
            "date": self.date,
            "tracknumber": self.tracknumber,
            "tracktotal": self.tracktotal,
            "discnumber": self.discnumber,
            "disctotal": self.disctotal,
            "genre": self.genre,
            "comment": self.comment,
            "composer": self.composer,
            "copyright": self.copyright,
            "encodedby": self.encodedby,
            "organization": self.organization,
        }

    def has_any_data(self) -> bool:
        """检查是否有任何非空元数据"""
        for val in self.to_dict().values():
            if val:
                return True
        return self.has_cover


# =============================================================================
# 格式检测
# =============================================================================

def detect_format(filepath: str) -> str:
    """检测音频文件格式（基于扩展名和文件头）。

    Args:
        filepath: 音频文件路径

    Returns:
        格式标识符: 'mp3', 'flac', 'ogg', 'm4a', 'wav', 或 'unknown'
    """
    ext = Path(filepath).suffix.lower()
    ext_map = {
        ".mp3": "mp3",
        ".flac": "flac",
        ".ogg": "ogg",
        ".oga": "ogg",
        ".m4a": "m4a",
        ".mp4": "m4a",
        ".wav": "wav",
        ".wma": "wma",
    }
    if ext in ext_map:
        return ext_map[ext]

    # 尝试通过文件头检测
    try:
        with open(filepath, "rb") as f:
            header = f.read(12)
        if header[:3] == b"ID3":
            return "mp3"
        if header[:4] == b"fLaC":
            return "flac"
        if header[:4] == b"OggS":
            return "ogg"
        if header[4:8] == b"ftyp":
            return "m4a"
        if header[:4] == b"RIFF" and header[8:12] == b"WAVE":
            return "wav"
    except (IOError, OSError):
        pass

    return "unknown"


# =============================================================================
# 元数据读取
# =============================================================================

def read_metadata(filepath: str) -> AudioMetadata:
    """读取音频文件的完整元数据。

    自动检测文件格式并调用对应的解析器。

    Args:
        filepath: 音频文件路径

    Returns:
        AudioMetadata 对象，包含所有可解析的元数据

    Raises:
        FileNotFoundError: 文件不存在
        ValueError: 不支持的格式
    """
    filepath = str(filepath)
    if not os.path.isfile(filepath):
        raise FileNotFoundError(f"文件不存在: {filepath}")

    fmt = detect_format(filepath)
    if fmt == "unknown":
        raise ValueError(f"不支持的音频格式: {filepath}")

    metadata = AudioMetadata()
    metadata.source_format = fmt
    metadata.source_path = filepath

    try:
        if fmt == "mp3":
            _read_mp3(filepath, metadata)
        elif fmt == "flac":
            _read_flac(filepath, metadata)
        elif fmt == "ogg":
            _read_ogg(filepath, metadata)
        elif fmt == "m4a":
            _read_m4a(filepath, metadata)
        elif fmt == "wav":
            _read_wav(filepath, metadata)
        elif fmt == "wma":
            _read_wma(filepath, metadata)
    except Exception as e:
        logger.warning("读取元数据时发生非致命错误 [%s]: %s", filepath, e)

    return metadata


def _read_mp3(filepath: str, meta: AudioMetadata) -> None:
    """读取 MP3 ID3 标签"""
    try:
        audio = ID3(filepath)
    except ID3NoHeaderError:
        # 无 ID3 标签，尝试读取 ID3v1
        try:
            mp3 = mutagen.mp3.MP3(filepath)
            if mp3.tags is None:
                return
            audio = mp3.tags
        except Exception:
            return

    # ID3v2 帧映射
    frame_map = {
        "TIT2": "title",
        "TPE1": "artist",
        "TALB": "album",
        "TPE2": "albumartist",
        "TDRC": "date",
        "TRCK": "tracknumber",
        "TPOS": "discnumber",
        "TCON": "genre",
        "COMM": "comment",
        "TCOM": "composer",
        "TCOP": "copyright",
        "TENC": "encodedby",
        "TIT1": "grouping",
        "TPUB": "organization",
    }

    for frame_id, attr_name in frame_map.items():
        frame = audio.get(frame_id)
        if frame is not None:
            text = process_tag_value(frame.text[0] if hasattr(frame, "text") and frame.text else str(frame))
            setattr(meta, attr_name, text)

    # 解析曲目号/总数
    if meta.tracknumber and "/" in meta.tracknumber:
        parts = meta.tracknumber.split("/")
        meta.tracknumber = parts[0].strip()
        if len(parts) > 1:
            meta.tracktotal = parts[1].strip()

    # 解析碟号/总数
    if meta.discnumber and "/" in meta.discnumber:
        parts = meta.discnumber.split("/")
        meta.discnumber = parts[0].strip()
        if len(parts) > 1:
            meta.disctotal = parts[1].strip()

    # 日期处理：TDRC 可能是 ID3TimeStamp 对象
    if meta.date:
        meta.date = str(meta.date).split("T")[0].split(" ")[0]

    # 提取封面图
    apic_frames = [audio[k] for k in audio.keys() if k.startswith("APIC")]
    if apic_frames:
        apic = apic_frames[0]
        meta.cover_data = apic.data
        meta.cover_mime = apic.mime
        meta.cover_description = process_tag_value(
            apic.desc if hasattr(apic, "desc") else ""
        )


def _read_flac(filepath: str, meta: AudioMetadata) -> None:
    """读取 FLAC 元数据"""
    audio = FLAC(filepath)

    tag_map = {
        "title": "title",
        "artist": "artist",
        "album": "album",
        "albumartist": "albumartist",
        "date": "date",
        "tracknumber": "tracknumber",
        "tracktotal": "tracktotal",
        "discnumber": "discnumber",
        "disctotal": "disctotal",
        "genre": "genre",
        "comment": "comment",
        "composer": "composer",
        "copyright": "copyright",
        "encodedby": "encodedby",
        "organization": "organization",
    }

    for vorbis_key, attr_name in tag_map.items():
        values = audio.get(vorbis_key)
        if values:
            text = process_tag_value(values[0])
            setattr(meta, attr_name, text)

    # FLAC 内嵌图片
    if audio.pictures:
        pic = audio.pictures[0]
        meta.cover_data = pic.data
        meta.cover_mime = pic.mime
        meta.cover_width = pic.width or 0
        meta.cover_height = pic.height or 0
        meta.cover_depth = pic.depth or 0
        meta.cover_description = process_tag_value(pic.desc or "")


def _read_ogg(filepath: str, meta: AudioMetadata) -> None:
    """读取 OGG Vorbis / Opus 元数据"""
    audio = OggVorbis(filepath)

    tag_map = {
        "title": "title",
        "artist": "artist",
        "album": "album",
        "albumartist": "albumartist",
        "date": "date",
        "tracknumber": "tracknumber",
        "tracktotal": "tracktotal",
        "discnumber": "discnumber",
        "disctotal": "disctotal",
        "genre": "genre",
        "comment": "comment",
        "composer": "composer",
        "copyright": "copyright",
        "encodedby": "encodedby",
        "organization": "organization",
    }

    for vorbis_key, attr_name in tag_map.items():
        values = audio.get(vorbis_key)
        if values:
            text = process_tag_value(values[0])
            setattr(meta, attr_name, text)

    # OGG 封面图通过 METADATA_BLOCK_PICTURE 存储
    if "metadata_block_picture" in audio:
        import base64
        try:
            raw = audio["metadata_block_picture"][0]
            pic_data = base64.b64decode(raw)
            pic = Picture(pic_data)
            meta.cover_data = pic.data
            meta.cover_mime = pic.mime
            meta.cover_width = pic.width or 0
            meta.cover_height = pic.height or 0
        except Exception as e:
            logger.debug("解析 OGG 封面失败: %s", e)


def _read_m4a(filepath: str, meta: AudioMetadata) -> None:
    """读取 M4A/MP4 (AAC/ALAC) iTunes 元数据"""
    audio = MP4(filepath)

    tag_map = {
        "\xa9nam": "title",
        "\xa9ART": "artist",
        "\xa9alb": "album",
        "aART": "albumartist",
        "\xa9day": "date",
        "trkn": "tracknumber",
        "disk": "discnumber",
        "\xa9gen": "genre",
        "\xa9cmt": "comment",
        "\xa9wrt": "composer",
        "cprt": "copyright",
        "\xa9enc": "encodedby",
        "\xa9grp": "grouping",
    }

    for atom_key, attr_name in tag_map.items():
        values = audio.get(atom_key)
        if values:
            if isinstance(values, list) and values:
                val = values[0]
                if isinstance(val, bytes):
                    # MP4 原子可能以字节形式存储
                    try:
                        text = val.decode("utf-8")
                    except UnicodeDecodeError:
                        text = val.decode("latin1")
                    text = process_tag_value(text)
                elif isinstance(val, (list, tuple)):
                    # trkn / disk 是整数元组
                    numbers = [str(int(v)) for v in val if v != 0]
                    text = "/".join(numbers) if numbers else ""
                else:
                    text = process_tag_value(str(val))
                if attr_name in ("tracknumber", "discnumber"):
                    setattr(meta, attr_name, text.split("/")[0] if "/" in text else text)
                    if "/" in text:
                        total_key = "tracktotal" if attr_name == "tracknumber" else "disctotal"
                        setattr(meta, total_key, text.split("/")[1])
                else:
                    setattr(meta, attr_name, text)

    # M4A 封面图 (covr atom)
    if "covr" in audio:
        covers = audio["covr"]
        if covers:
            cover = covers[0]
            meta.cover_data = bytes(cover)
            if cover.imageformat == MP4Cover.FORMAT_JPEG:
                meta.cover_mime = "image/jpeg"
            elif cover.imageformat == MP4Cover.FORMAT_PNG:
                meta.cover_mime = "image/png"
            else:
                meta.cover_mime = "image/jpeg"


def _read_wav(filepath: str, meta: AudioMetadata) -> None:
    """读取 WAV RIFF INFO 元数据（WAV 支持有限）"""
    try:
        audio = WAVE(filepath)
    except Exception:
        return

    tag_map = {
        "TITLE": "title",
        "ARTIST": "artist",
        "ALBUM": "album",
        "DATE": "date",
        "TRACKNUMBER": "tracknumber",
        "GENRE": "genre",
        "COMMENT": "comment",
        "COMPOSER": "composer",
        "COPYRIGHT": "copyright",
        "ENCODEDBY": "encodedby",
    }

    if hasattr(audio, "tags") and audio.tags:
        for info_key, attr_name in tag_map.items():
            if info_key in audio.tags:
                text = process_tag_value(audio.tags[info_key])
                setattr(meta, attr_name, text)

    # WAV 不原生支持封面图，跳过


def _read_wma(filepath: str, meta: AudioMetadata) -> None:
    """读取 WMA/ASF 元数据（使用 mutagen.asf）"""
    try:
        from mutagen.asf import ASF
        audio = ASF(filepath)
    except ImportError:
        logger.warning("mutagen.asf 不可用，跳过 WMA 元数据读取")
        return
    except Exception as e:
        logger.warning("读取 WMA 元数据失败: %s", e)
        return

    tag_map = {
        "Title": "title",
        "Author": "artist",
        "WM/AlbumTitle": "album",
        "WM/AlbumArtist": "albumartist",
        "WM/Year": "date",
        "WM/TrackNumber": "tracknumber",
        "WM/PartOfSet": "discnumber",
        "WM/Genre": "genre",
        "Description": "comment",
        "WM/Composer": "composer",
        "Copyright": "copyright",
        "WM/EncodedBy": "encodedby",
    }

    if hasattr(audio, "tags") and audio.tags:
        for asf_key, attr_name in tag_map.items():
            values = audio.tags.get(asf_key)
            if values:
                text = process_tag_value(values[0])
                setattr(meta, attr_name, text)

    # WMA 封面图 (WM/Picture)
    if hasattr(audio, "tags") and "WM/Picture" in audio.tags:
        try:
            pic = audio.tags["WM/Picture"][0]
            if hasattr(pic, "value") and hasattr(pic, "mime"):
                meta.cover_data = bytes(pic.value)
                meta.cover_mime = pic.mime
        except Exception as e:
            logger.debug("解析 WMA 封面失败: %s", e)


# =============================================================================
# 元数据写入
# =============================================================================

def write_metadata(filepath: str, metadata: AudioMetadata,
                   copy_cover: bool = True,
                   create_backup: bool = False) -> bool:
    """将元数据写入目标音频文件。

    Args:
        filepath: 目标文件路径
        metadata: 要写入的 AudioMetadata 对象
        copy_cover: 是否复制封面图
        create_backup: 是否在写入前创建备份

    Returns:
        写入是否成功
    """
    filepath = str(filepath)
    if not os.path.isfile(filepath):
        raise FileNotFoundError(f"文件不存在: {filepath}")

    # 备份
    if create_backup:
        _create_backup(filepath)

    fmt = detect_format(filepath)
    if fmt == "unknown":
        raise ValueError(f"不支持的目标格式: {filepath}")

    try:
        if fmt == "mp3":
            _write_mp3(filepath, metadata, copy_cover)
        elif fmt == "flac":
            _write_flac(filepath, metadata, copy_cover)
        elif fmt == "ogg":
            _write_ogg(filepath, metadata, copy_cover)
        elif fmt == "m4a":
            _write_m4a(filepath, metadata, copy_cover)
        elif fmt == "wav":
            _write_wav(filepath, metadata, copy_cover)
        elif fmt == "wma":
            _write_wma(filepath, metadata, copy_cover)
        logger.info("元数据写入成功: %s", filepath)
        return True
    except Exception as e:
        logger.error("写入元数据失败 [%s]: %s", filepath, e)
        # 如果写入了备份，保留备份
        return False


def _create_backup(filepath: str) -> str:
    """创建文件备份（.bak 扩展名 + 时间戳）"""
    import shutil
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{filepath}.bak_{timestamp}"
    shutil.copy2(filepath, backup_path)
    logger.info("备份已创建: %s", backup_path)
    return backup_path


def _write_mp3(filepath: str, meta: AudioMetadata, copy_cover: bool) -> None:
    """写入 MP3 ID3v2 标签"""
    from mutagen.id3 import (
        ID3, TIT2, TPE1, TALB, TPE2, TDRC, TRCK, TPOS,
        TCON, COMM, TCOM, TCOP, TENC, TPUB, APIC,
    )

    try:
        audio = ID3(filepath)
    except ID3NoHeaderError:
        # 文件没有 ID3v2 标签，创建新的
        audio = ID3()

    # 文本帧写入
    if meta.title:
        audio["TIT2"] = TIT2(encoding=3, text=meta.title)
    if meta.artist:
        audio["TPE1"] = TPE1(encoding=3, text=meta.artist)
    if meta.album:
        audio["TALB"] = TALB(encoding=3, text=meta.album)
    if meta.albumartist:
        audio["TPE2"] = TPE2(encoding=3, text=meta.albumartist)
    if meta.date:
        audio["TDRC"] = TDRC(encoding=3, text=meta.date)
    if meta.tracknumber:
        trck = f"{meta.tracknumber}/{meta.tracktotal}" if meta.tracktotal else meta.tracknumber
        audio["TRCK"] = TRCK(encoding=3, text=trck)
    if meta.discnumber:
        tpos = f"{meta.discnumber}/{meta.disctotal}" if meta.disctotal else meta.discnumber
        audio["TPOS"] = TPOS(encoding=3, text=tpos)
    if meta.genre:
        audio["TCON"] = TCON(encoding=3, text=meta.genre)
    if meta.comment:
        audio["COMM"] = COMM(encoding=3, lang="eng", desc="", text=meta.comment)
    if meta.composer:
        audio["TCOM"] = TCOM(encoding=3, text=meta.composer)
    if meta.copyright:
        audio["TCOP"] = TCOP(encoding=3, text=meta.copyright)
    if meta.encodedby:
        audio["TENC"] = TENC(encoding=3, text=meta.encodedby)
    if meta.organization:
        audio["TPUB"] = TPUB(encoding=3, text=meta.organization)

    # 封面图
    if copy_cover and meta.has_cover:
        mime = meta.cover_mime or "image/jpeg"
        audio["APIC"] = APIC(
            encoding=3,
            mime=mime,
            type=3,  # Cover (front)
            desc=meta.cover_description or "Cover",
            data=meta.cover_data,
        )

    audio.save(filepath, v2_version=3)


def _write_flac(filepath: str, meta: AudioMetadata, copy_cover: bool) -> None:
    """写入 FLAC Vorbis Comments + Picture"""
    audio = FLAC(filepath)

    # 清除旧标签后写入新标签（保留其他未映射的标签）
    _set_vorbis_tags(audio, meta)

    # 封面图
    if copy_cover and meta.has_cover:
        audio.clear_pictures()
        pic = Picture()
        pic.type = 3  # Cover (front)
        pic.mime = meta.cover_mime or "image/jpeg"
        pic.desc = meta.cover_description or "Cover"
        pic.data = meta.cover_data
        if meta.cover_width:
            pic.width = meta.cover_width
        if meta.cover_height:
            pic.height = meta.cover_height
        audio.add_picture(pic)

    audio.save()


def _write_ogg(filepath: str, meta: AudioMetadata, copy_cover: bool) -> None:
    """写入 OGG Vorbis Comments"""
    audio = OggVorbis(filepath)

    _set_vorbis_tags(audio, meta)

    # OGG 封面图：编码为 METADATA_BLOCK_PICTURE
    if copy_cover and meta.has_cover:
        import base64
        from mutagen.flac import Picture as OGGCover
        pic = OGGCover()
        pic.type = 3
        pic.mime = meta.cover_mime or "image/jpeg"
        pic.desc = meta.cover_description or "Cover"
        pic.data = meta.cover_data
        if meta.cover_width:
            pic.width = meta.cover_width
        if meta.cover_height:
            pic.height = meta.cover_height
        pic_data = pic.write()
        audio["metadata_block_picture"] = [base64.b64encode(pic_data).decode("ascii")]

    audio.save()


def _set_vorbis_tags(audio, meta: AudioMetadata) -> None:
    """设置 Vorbis Comments 标签（FLAC 和 OGG 共用）"""
    tag_map = {
        "title": meta.title,
        "artist": meta.artist,
        "album": meta.album,
        "albumartist": meta.albumartist,
        "date": meta.date,
        "tracknumber": meta.tracknumber,
        "tracktotal": meta.tracktotal,
        "discnumber": meta.discnumber,
        "disctotal": meta.disctotal,
        "genre": meta.genre,
        "comment": meta.comment,
        "composer": meta.composer,
        "copyright": meta.copyright,
        "encodedby": meta.encodedby,
        "organization": meta.organization,
    }

    for key, value in tag_map.items():
        if value:
            audio[key] = value
        elif key in audio:
            # 如果源没有该字段且目标有，保持目标原有值
            # 但如果想要清空，则取消下行注释
            pass


def _write_m4a(filepath: str, meta: AudioMetadata, copy_cover: bool) -> None:
    """写入 M4A/MP4 iTunes 原子标签"""
    audio = MP4(filepath)

    tag_map = {
        "\xa9nam": meta.title,
        "\xa9ART": meta.artist,
        "\xa9alb": meta.album,
        "aART": meta.albumartist,
        "\xa9day": meta.date,
        "\xa9gen": meta.genre,
        "\xa9cmt": meta.comment,
        "\xa9wrt": meta.composer,
        "cprt": meta.copyright,
        "\xa9enc": meta.encodedby,
        "\xa9grp": meta.organization,
    }

    for atom, value in tag_map.items():
        if value:
            audio[atom] = [value]

    # 曲目号（MP4 存储为整数对）
    if meta.tracknumber:
        try:
            tn = int(meta.tracknumber)
            tt = int(meta.tracktotal) if meta.tracktotal else 0
            audio["trkn"] = [(tn, tt)]
        except ValueError:
            pass

    # 碟号
    if meta.discnumber:
        try:
            dn = int(meta.discnumber)
            dt = int(meta.disctotal) if meta.disctotal else 0
            audio["disk"] = [(dn, dt)]
        except ValueError:
            pass

    # 封面图
    if copy_cover and meta.has_cover:
        fmt = MP4Cover.FORMAT_JPEG
        if meta.cover_mime and "png" in meta.cover_mime.lower():
            fmt = MP4Cover.FORMAT_PNG
        audio["covr"] = [MP4Cover(meta.cover_data, imageformat=fmt)]

    audio.save()


def _write_wav(filepath: str, meta: AudioMetadata, copy_cover: bool) -> None:
    """写入 WAV RIFF INFO 元数据"""
    try:
        audio = WAVE(filepath)
    except Exception:
        logger.warning("无法打开 WAV 文件进行写入: %s", filepath)
        return

    # WAV INFO 标签是受限的，字段名长度限制
    tag_map = {
        "TITLE": meta.title,
        "ARTIST": meta.artist,
        "ALBUM": meta.album,
        "DATE": meta.date,
        "TRACKNUMBER": meta.tracknumber,
        "GENRE": meta.genre,
        "COMMENT": meta.comment,
        "COMPOSER": meta.composer,
        "COPYRIGHT": meta.copyright,
        "ENCODEDBY": meta.encodedby,
    }

    if not hasattr(audio, 'tags') or audio.tags is None:
        audio.add_tags()

    for info_key, value in tag_map.items():
        if value:
            try:
                audio.tags[info_key] = value
            except (KeyError, ValueError) as e:
                logger.debug("WAV 标签写入跳过 [%s=%s]: %s", info_key, value, e)

    # WAV 不原生支持内嵌封面图
    if copy_cover and meta.has_cover:
        logger.info("WAV 格式不支持内嵌封面图，已跳过: %s", filepath)

    audio.save()


def _write_wma(filepath: str, meta: AudioMetadata, copy_cover: bool) -> None:
    """写入 WMA/ASF 元数据"""
    try:
        from mutagen.asf import ASF
        audio = ASF(filepath)
    except ImportError:
        logger.warning("mutagen.asf 不可用，跳过 WMA 写入: %s", filepath)
        return
    except Exception as e:
        logger.error("打开 WMA 文件失败: %s", e)
        return

    tag_map = {
        "Title": meta.title,
        "Author": meta.artist,
        "WM/AlbumTitle": meta.album,
        "WM/AlbumArtist": meta.albumartist,
        "WM/Year": meta.date,
        "WM/TrackNumber": meta.tracknumber,
        "WM/PartOfSet": meta.discnumber,
        "WM/Genre": meta.genre,
        "Description": meta.comment,
        "WM/Composer": meta.composer,
        "Copyright": meta.copyright,
    }

    for key, value in tag_map.items():
        if value:
            audio.tags[key] = [value]

    audio.save()


# =============================================================================
# 高层 API
# =============================================================================

def copy_metadata(source_path: str, target_path: str,
                  copy_cover: bool = True,
                  create_backup: bool = False) -> bool:
    """从源文件复制所有元数据到目标文件（一站式 API）。

    Args:
        source_path: 源音频文件路径
        target_path: 目标音频文件路径
        copy_cover: 是否复制封面图
        create_backup: 是否为目标文件创建备份

    Returns:
        是否成功
    """
    logger.info("开始复制元数据: %s → %s", source_path, target_path)

    if not os.path.isfile(source_path):
        raise FileNotFoundError(f"源文件不存在: {source_path}")
    if not os.path.isfile(target_path):
        raise FileNotFoundError(f"目标文件不存在: {target_path}")

    # 读取源元数据
    source_meta = read_metadata(source_path)
    if not source_meta.has_any_data() and not source_meta.has_cover:
        logger.warning("源文件无元数据: %s", source_path)
        return False

    # 写入目标
    return write_metadata(target_path, source_meta,
                         copy_cover=copy_cover,
                         create_backup=create_backup)
