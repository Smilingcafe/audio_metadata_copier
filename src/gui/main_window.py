"""主窗口 GUI — Fusion 暗色主题 + 自绘边框 (QMCDecoder 模式)"""

import logging
import os
import sys
from datetime import datetime
from typing import List, Optional, Set

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QDragEnterEvent, QDropEvent, QMouseEvent, QColor
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGroupBox, QLabel, QLineEdit, QPushButton, QCheckBox,
    QTreeWidget, QTreeWidgetItem, QProgressBar, QPlainTextEdit,
    QFileDialog, QMessageBox, QFrame, QSizeGrip,
    QGraphicsDropShadowEffect,
    QHeaderView, QMenu, QAbstractItemView,
)

from .theme import DARK_THEME, generate_stylesheet
from .worker import ScanWorker, CopyWorker, MetadataPreviewWorker
from ..core.matcher import MatchResult, ScanResult
from ..core.metadata import AudioMetadata, SUPPORTED_EXTENSIONS

logger = logging.getLogger(__name__)

_TITLE_HEIGHT = 38

class MainWindow(QMainWindow):
    """音频元数据复制工具主窗口"""

    APP_TITLE = "音频元数据复制器"
    APP_VERSION = "1.0.0"

    def __init__(self):
        super().__init__()
        self._drag_pos = None

        # FramelessHint + setMask 实现圆角无边框窗口 (不用 WA_TranslucentBackground,
        # 因为它创建分层窗口导致 OLE 拖放完全不可用)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)

        self._source_path: str = ""
        self._source_metadata: Optional[AudioMetadata] = None
        self._target_path: str = ""
        self._matches: List[MatchResult] = []
        self._scan_worker: Optional[ScanWorker] = None
        self._copy_worker: Optional[CopyWorker] = None
        self._preview_worker: Optional[MetadataPreviewWorker] = None

        self._init_ui()
        self._setup_connections()
        self._apply_theme()

    # ── 窗口拖拽 ──
    def mousePressEvent(self, e: QMouseEvent):
        if e.button() == Qt.MouseButton.LeftButton and e.position().toPoint().y() < _TITLE_HEIGHT:
            self._drag_pos = e.globalPosition().toPoint() - self.frameGeometry().topLeft()
        else:
            self._drag_pos = None
        super().mousePressEvent(e)

    def mouseMoveEvent(self, e: QMouseEvent):
        if self._drag_pos is not None:
            self.move(e.globalPosition().toPoint() - self._drag_pos)
        super().mouseMoveEvent(e)

    def mouseReleaseEvent(self, e: QMouseEvent):
        self._drag_pos = None
        super().mouseReleaseEvent(e)

    def mouseDoubleClickEvent(self, e: QMouseEvent):
        if e.position().toPoint().y() < _TITLE_HEIGHT:
            self.showNormal() if self.isMaximized() else self.showMaximized()
        super().mouseDoubleClickEvent(e)

    def _init_ui(self):
        self.setWindowTitle(f"{self.APP_TITLE} v{self.APP_VERSION}")
        self.setMinimumSize(900, 760)
        self.resize(1050, 880)

        # ── 外层容器 (圆角 + 阴影) ──
        outer = QWidget()
        outer.setObjectName("outerFrame")
        outer.setStyleSheet(
            f"#outerFrame {{ background: {DARK_THEME['bg_primary']}; border-radius: 10px; }}"
        )
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(24)
        shadow.setColor(QColor(0, 0, 0, 120))
        shadow.setOffset(0, 2)
        outer.setGraphicsEffect(shadow)
        self.setCentralWidget(outer)

        ml = QVBoxLayout(outer)
        ml.setSpacing(0)
        ml.setContentsMargins(0, 0, 0, 0)

        # ── 标题栏 ──
        tb = QFrame()
        tb.setFixedHeight(_TITLE_HEIGHT)
        tb.setStyleSheet(
            f"QFrame {{ background: {DARK_THEME['bg_primary']}; "
            f"border-top-left-radius: 10px; border-top-right-radius: 10px; "
            f"border-bottom: 1px solid {DARK_THEME['border']}; }}"
        )
        tl = QHBoxLayout(tb)
        tl.setContentsMargins(12, 0, 4, 0)
        tl.setSpacing(6)

        icon = QLabel("🎵")
        icon.setStyleSheet("font-size: 16px; background: transparent;")
        tl.addWidget(icon)

        title = QLabel(self.APP_TITLE)
        title.setStyleSheet(
            "font-size: 13px; font-weight: bold; color: " + DARK_THEME["text_primary"] + "; background: transparent;"
        )
        tl.addWidget(title)
        tl.addStretch()

        for glyph, slot in [
            ("─", self.showMinimized),
            ("□", lambda: self.showNormal() if self.isMaximized() else self.showMaximized()),
            ("✕", self.close),
        ]:
            btn = QPushButton(glyph)
            btn.setFixedSize(28, 24)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(
                "QPushButton {"
                "  background: transparent; border: none; border-radius: 4px;"
                "  font-size: 12px; padding: 0;"
                "  min-width: 28px; max-width: 28px;"
                "  min-height: 24px; max-height: 24px;"
                "  color: " + DARK_THEME["text_secondary"] + ";"
                "}"
                "QPushButton:hover {"
                "  background: " + ("#e81123" if glyph == "✕" else DARK_THEME["bg_hover"]) + ";"
                "  color: white;"
                "}"
            )
            btn.clicked.connect(slot)
            tl.addWidget(btn)

        ml.addWidget(tb)

        # ── 内容区 ──
        content = QWidget()
        cl = QVBoxLayout(content)
        cl.setSpacing(8)
        cl.setContentsMargins(12, 8, 12, 6)

        source_group = QGroupBox("源文件（从此文件读取元数据）")
        source_layout = QHBoxLayout(source_group)
        source_layout.setSpacing(6)
        self._source_edit = QLineEdit()
        self._source_edit.setPlaceholderText("选择或拖放源音频文件...")
        self._source_edit.setMinimumHeight(36)
        source_layout.addWidget(self._source_edit, 1)
        browse_src_btn = QPushButton("浏览...")
        browse_src_btn.clicked.connect(self._browse_source)
        source_layout.addWidget(browse_src_btn)
        preview_btn = QPushButton("预览元数据")
        preview_btn.clicked.connect(self._preview_metadata)
        source_layout.addWidget(preview_btn)
        cl.addWidget(source_group)

        io_group = QGroupBox("目标与选项")
        io_outer = QVBoxLayout(io_group)
        io_outer.setSpacing(8)

        io_row1 = QHBoxLayout()
        io_row1.setSpacing(8)
        self._chk_recursive = QCheckBox("递归扫描子目录")
        self._chk_recursive.setChecked(True)
        self._chk_recursive.setToolTip("扫描目标目录的所有子目录，关闭则仅扫描顶层")
        io_row1.addWidget(self._chk_recursive)
        self._chk_cover = QCheckBox("复制专辑封面")
        self._chk_cover.setChecked(True)
        self._chk_cover.setToolTip("将源文件的专辑封图写入目标文件")
        io_row1.addWidget(self._chk_cover)
        io_row1.addStretch()
        io_outer.addLayout(io_row1)

        io_row2 = QHBoxLayout()
        io_row2.setSpacing(6)
        self._target_edit = QLineEdit()
        self._target_edit.setPlaceholderText("选择或拖放目标目录（将自动扫描匹配）...")
        self._target_edit.setMinimumHeight(36)
        io_row2.addWidget(self._target_edit, 1)
        browse_target_btn = QPushButton("浏览...")
        browse_target_btn.clicked.connect(self._browse_target)
        io_row2.addWidget(browse_target_btn)
        scan_btn = QPushButton("扫描匹配")
        scan_btn.setObjectName("primaryBtn")
        scan_btn.clicked.connect(self._start_scan)
        io_row2.addWidget(scan_btn)
        io_outer.addLayout(io_row2)

        io_row3 = QHBoxLayout()
        io_row3.setSpacing(6)
        io_row3.addWidget(QLabel("目标格式:"))
        self._format_checks: dict[str, QCheckBox] = {}
        formats = [("mp3", "MP3"), ("flac", "FLAC"), ("ogg", "OGG"),
                    ("m4a", "M4A/AAC"), ("wav", "WAV"), ("wma", "WMA")]
        for fmt_id, fmt_label in formats:
            cb = QCheckBox(fmt_label)
            cb.setChecked(True)
            self._format_checks[fmt_id] = cb
            io_row3.addWidget(cb)
        sep2 = QLabel("│")
        sep2.setStyleSheet("color: " + DARK_THEME["border"] + "; font-size: 14px; padding: 0 6px;")
        io_row3.addWidget(sep2)
        self._chk_backup = QCheckBox("创建备份")
        self._chk_backup.setChecked(False)
        self._chk_backup.setToolTip("写入前为目标文件创建 .bak 备份")
        io_row3.addWidget(self._chk_backup)
        self._chk_skip_existing = QCheckBox("跳过已有元数据的文件")
        self._chk_skip_existing.setChecked(False)
        self._chk_skip_existing.setToolTip("如果目标文件已有标签信息则跳过，避免覆盖")
        io_row3.addWidget(self._chk_skip_existing)
        io_row3.addStretch()
        io_outer.addLayout(io_row3)
        cl.addWidget(io_group)

        results_group = QGroupBox("匹配结果")
        results_layout = QVBoxLayout(results_group)
        results_layout.setSpacing(8)
        select_row = QHBoxLayout()
        select_row.setSpacing(6)
        select_all_btn = QPushButton("全选")
        select_all_btn.clicked.connect(self._select_all)
        select_row.addWidget(select_all_btn)
        deselect_all_btn = QPushButton("取消全选")
        deselect_all_btn.clicked.connect(self._deselect_all)
        select_row.addWidget(deselect_all_btn)
        invert_btn = QPushButton("反选")
        invert_btn.clicked.connect(self._invert_selection)
        select_row.addWidget(invert_btn)
        self._result_count_label = QLabel("未扫描")
        select_row.addWidget(self._result_count_label)
        select_row.addStretch()
        results_layout.addLayout(select_row)

        self._results_tree = QTreeWidget()
        self._results_tree.setHeaderLabels(["", "文件名", "格式", "匹配类型", "路径"])
        self._results_tree.setRootIsDecorated(True)
        self._results_tree.setAlternatingRowColors(True)
        self._results_tree.setMinimumHeight(200)
        self._results_tree.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self._results_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._results_tree.customContextMenuRequested.connect(self._show_context_menu)
        header = self._results_tree.header()
        header.setStretchLastSection(True)
        self._results_tree.setColumnWidth(0, 30)
        self._results_tree.setColumnWidth(1, 300)
        self._results_tree.setColumnWidth(2, 70)
        self._results_tree.setColumnWidth(3, 100)
        self._results_tree.setColumnWidth(4, 250)
        results_layout.addWidget(self._results_tree)
        cl.addWidget(results_group, 1)

        self._progress_bar = QProgressBar()
        self._progress_bar.setVisible(False)
        self._progress_bar.setTextVisible(True)
        cl.addWidget(self._progress_bar)

        action_row = QHBoxLayout()
        action_row.setSpacing(6)
        self._copy_btn = QPushButton("▶  开始复制元数据")
        self._copy_btn.setObjectName("primaryBtn")
        self._copy_btn.setMinimumHeight(40)
        self._copy_btn.setMinimumWidth(200)
        self._copy_btn.setEnabled(False)
        self._copy_btn.clicked.connect(self._start_copy)
        action_row.addWidget(self._copy_btn)
        self._stop_btn = QPushButton("停止")
        self._stop_btn.setEnabled(False)
        self._stop_btn.clicked.connect(self._stop_operation)
        action_row.addWidget(self._stop_btn)
        self._clear_btn = QPushButton("清除")
        self._clear_btn.clicked.connect(self._clear_results)
        action_row.addWidget(self._clear_btn)
        open_target_btn = QPushButton("打开目标目录")
        open_target_btn.clicked.connect(self._open_target_dir)
        action_row.addWidget(open_target_btn)
        action_row.addStretch()
        cl.addLayout(action_row)

        log_group = QGroupBox("日志")
        log_layout = QVBoxLayout(log_group)
        log_layout.setContentsMargins(8, 12, 8, 8)
        self._log_text = QPlainTextEdit()
        self._log_text.setReadOnly(True)
        self._log_text.setMaximumBlockCount(500)
        self._log_text.setMinimumHeight(80)
        self._log_text.setMaximumHeight(150)
        log_layout.addWidget(self._log_text)
        cl.addWidget(log_group)

        # ── 状态栏 + 缩放手柄 ──
        status_row = QHBoxLayout()
        status_row.setContentsMargins(0, 4, 0, 0)
        self._status_label = QLabel("就绪")
        self._status_label.setObjectName("statusLabel")
        self._status_label.setStyleSheet(
            "color: " + DARK_THEME["text_dimmed"] + "; font-size: 12px; padding: 2px 0;"
        )
        status_row.addWidget(self._status_label)
        status_row.addStretch()
        grip = QSizeGrip(self)
        grip.setStyleSheet("background: transparent;")
        status_row.addWidget(grip)
        cl.addLayout(status_row)

        ml.addWidget(content, 1)

        self.setAcceptDrops(True)

    def _setup_connections(self):
        self._source_edit.textChanged.connect(self._on_source_changed)

    def _on_source_changed(self, text: str):
        self._source_path = text.strip()
        self._source_metadata = None
        self._copy_btn.setEnabled(False)
        if not self._source_path:
            self._status_label.setText("请选择源文件")
            return
        if os.path.isfile(self._source_path):
            src_dir = os.path.dirname(os.path.abspath(self._source_path))
            self._target_edit.setText(src_dir)
            self._target_path = src_dir
            self._status_label.setText(f"目标目录 → {src_dir}")

    def _browse_source(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择源音频文件", "",
            "音频文件 (*.mp3 *.flac *.ogg *.oga *.m4a *.mp4 *.wav *.wma);;所有文件 (*.*)"
        )
        if file_path:
            self._source_edit.setText(file_path)
            self._source_path = file_path
            self._auto_preview_metadata()

    def _browse_target(self):
        dir_path = QFileDialog.getExistingDirectory(self, "选择目标目录", "")
        if dir_path:
            self._target_edit.setText(dir_path)
            self._target_path = dir_path

    def _preview_metadata(self):
        if not self._source_path or not os.path.isfile(self._source_path):
            QMessageBox.warning(self, "提示", "请先选择有效的源文件")
            return
        self._auto_preview_metadata()

    def _auto_preview_metadata(self):
        if not self._source_path:
            return
        self._log(f"正在读取元数据: {os.path.basename(self._source_path)}", "info")
        self._status_label.setText("读取中...")
        self._preview_worker = MetadataPreviewWorker(self._source_path)
        self._preview_worker.result.connect(self._on_preview_ready)
        self._preview_worker.error.connect(self._on_preview_error)
        self._preview_worker.start()

    def _on_preview_ready(self, meta: AudioMetadata):
        self._source_metadata = meta
        lines = [f"源文件元数据预览 ({os.path.basename(self._source_path)}):"]
        if meta.title: lines.append(f"  标题: {meta.title}")
        if meta.artist: lines.append(f"  歌手: {meta.artist}")
        if meta.album: lines.append(f"  专辑: {meta.album}")
        if meta.albumartist: lines.append(f"  专辑歌手: {meta.albumartist}")
        if meta.date: lines.append(f"  年份: {meta.date}")
        if meta.tracknumber:
            trk = meta.tracknumber
            if meta.tracktotal: trk += f"/{meta.tracktotal}"
            lines.append(f"  曲目: {trk}")
        if meta.genre: lines.append(f"  风格: {meta.genre}")
        if meta.composer: lines.append(f"  作曲: {meta.composer}")
        if meta.has_cover:
            size_kb = len(meta.cover_data) / 1024
            lines.append(f"  封面: {meta.cover_mime} ({size_kb:.1f} KB)")
        if not meta.has_any_data():
            lines.append("  (无元数据)")
        for line in lines:
            self._log(line, "info")
        self._status_label.setText(f"已读取源文件元数据 - {len(meta.to_dict())} 个字段")
        self._update_copy_button()

    def _on_preview_error(self, err: str):
        self._log(f"读取失败: {err}", "error")
        self._status_label.setText(f"读取失败: {err}")

    def _start_scan(self):
        target_dir = self._target_edit.text().strip()
        if not target_dir or not os.path.isdir(target_dir):
            QMessageBox.warning(self, "提示", "请先选择有效的目标目录")
            return
        if not self._source_path or not os.path.isfile(self._source_path):
            QMessageBox.warning(self, "提示", "请先选择有效的源文件")
            return
        self._target_path = target_dir
        self._clear_results()
        self._log(f"开始扫描目录: {target_dir}", "info")
        formats = self._get_selected_formats()
        self._log(f"格式筛选: {', '.join(sorted(formats)) if formats else '全部'}", "info")
        self._status_label.setText("扫描中...")
        self._progress_bar.setVisible(True)
        self._progress_bar.setRange(0, 0)
        self._scan_worker = ScanWorker(
            self._source_path, target_dir,
            formats=formats,
            recursive=self._chk_recursive.isChecked(),
        )
        self._scan_worker.finished.connect(self._on_scan_finished)
        self._scan_worker.error.connect(self._on_scan_error)
        self._scan_worker.start()

    def _on_scan_finished(self, result: ScanResult):
        self._progress_bar.setVisible(False)
        self._matches = result.matches
        for match in self._matches:
            self._add_result_item(match)
        self._result_count_label.setText(
            f"匹配: {result.total_matched} 个（共扫描 {result.total_found} 个音频文件, {result.scanned_dirs} 个目录）"
        )
        self._status_label.setText(f"扫描完成 - {result.total_matched} 个匹配")
        self._log(f"扫描完成: {result.scanned_dirs} 个目录, {result.total_found} 个音频文件", "info")
        if result.total_matched > 0:
            self._log(f"匹配到 {result.total_matched} 个目标文件:", "success")
            for m in result.matches:
                self._log(f"  [{m.target_format.upper()}] {m.target_relative}", "info")
        else:
            self._log(f"未找到匹配文件（已跳过源文件自身）", "warning")
            self._log(f"提示: 源文件名为 \"{result.source_stem}\"，目标文件名必须完整包含此字符串", "warning")
        for fpath, err in result.error_files:
            self._log(f"扫描错误 [{fpath}]: {err}", "error")
        self._update_copy_button()

    def _on_scan_error(self, err: str):
        self._progress_bar.setVisible(False)
        self._log(f"扫描失败: {err}", "error")
        self._status_label.setText("扫描失败")
        QMessageBox.critical(self, "扫描错误", err)

    def _add_result_item(self, match: MatchResult):
        item = QTreeWidgetItem(self._results_tree)
        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
        item.setCheckState(0, Qt.CheckState.Checked)
        item.setText(0, "")
        item.setText(1, match.target_name)
        item.setText(2, match.target_format.upper())
        item.setText(3, "精确匹配" if match.match_type == "exact" else "子串匹配")
        item.setText(4, match.target_relative)
        item.setData(0, Qt.ItemDataRole.UserRole, match)

    def _start_copy(self):
        selected = self._get_selected_matches()
        if not selected:
            QMessageBox.warning(self, "提示", "请在匹配结果中勾选要处理的目标文件")
            return
        if not self._source_path or not os.path.isfile(self._source_path):
            QMessageBox.warning(self, "提示", "源文件已不存在")
            return
        count = len(selected)
        reply = QMessageBox.question(
            self, "确认操作",
            f"即将复制元数据到 {count} 个文件。\n\n"
            f"源文件: {os.path.basename(self._source_path)}\n"
            f"复制封面: {'是' if self._chk_cover.isChecked() else '否'}\n"
            f"创建备份: {'是' if self._chk_backup.isChecked() else '否'}\n\n"
            f"继续？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        self._log(f"\n{'='*50}", "info")
        self._log(f"开始复制元数据: {os.path.basename(self._source_path)}", "info")
        self._log(f"目标文件数: {count}", "info")
        self._progress_bar.setVisible(True)
        self._progress_bar.setRange(0, count)
        self._progress_bar.setValue(0)
        self._copy_btn.setEnabled(False)
        self._stop_btn.setEnabled(True)
        self._status_label.setText("复制中...")
        self._copy_worker = CopyWorker(
            self._source_path, selected,
            copy_cover=self._chk_cover.isChecked(),
            create_backup=self._chk_backup.isChecked(),
            skip_existing=self._chk_skip_existing.isChecked(),
        )
        self._copy_worker.progress.connect(self._on_copy_progress)
        self._copy_worker.file_done.connect(self._on_file_done)
        self._copy_worker.finished.connect(self._on_copy_finished)
        self._copy_worker.log_message.connect(lambda msg: self._log(msg, "info"))
        self._copy_worker.start()

    def _stop_operation(self):
        if self._copy_worker and self._copy_worker.isRunning():
            self._copy_worker.cancel()
        if self._scan_worker and self._scan_worker.isRunning():
            self._scan_worker.terminate()
            self._scan_worker.wait()

    def _on_copy_progress(self, done: int, total: int, filename: str):
        self._progress_bar.setValue(done)
        self._status_label.setText(f"处理中: {done}/{total} - {filename}")

    def _on_file_done(self, filepath: str, success: bool, error: str):
        for i in range(self._results_tree.topLevelItemCount()):
            item = self._results_tree.topLevelItem(i)
            match: MatchResult = item.data(0, Qt.ItemDataRole.UserRole)
            if match and match.target_path == filepath:
                item.setText(0, "✅" if success else "❌")
                if not success:
                    item.setToolTip(0, f"失败: {error}")
                break

    def _on_copy_finished(self, success: int, fail: int, skip: int):
        self._progress_bar.setVisible(False)
        self._copy_btn.setEnabled(True)
        self._stop_btn.setEnabled(False)
        msg = f"复制完成: 成功 {success}, 失败 {fail}, 跳过 {skip}"
        self._status_label.setText(msg)
        self._log(msg, "success" if fail == 0 else "warning")
        if fail > 0:
            QMessageBox.warning(self, "操作完成",
                f"部分文件处理失败\n\n成功: {success}\n失败: {fail}\n跳过: {skip}")
        else:
            QMessageBox.information(self, "操作完成",
                f"所有文件处理完成！\n\n成功: {success}\n跳过: {skip}")

    def dragEnterEvent(self, event: QDragEnterEvent):
        has = event.mimeData().hasUrls()
        self._status_label.setText(f"[DnD] dragEnter hasUrls={has}")
        if has:
            event.acceptProposedAction()
            self._status_label.setText(f"[DnD] dragEnter ACCEPTED")

    def dropEvent(self, event: QDropEvent):
        urls = event.mimeData().urls()
        if not urls:
            self._status_label.setText(f"[DnD] dropEvent: no URLs")
            return
        path = urls[0].toLocalFile()
        self._status_label.setText(f"[DnD] dropEvent: {os.path.basename(path)}")
        widget_pos = event.position().toPoint()
        mid_y = self.height() // 2
        if widget_pos.y() < mid_y / 2:
            if os.path.isfile(path):
                self._source_edit.setText(path)
                self._source_path = path
                self._auto_preview_metadata()
            else:
                QMessageBox.warning(self, "提示", "请拖放音频文件到源文件区域")
        else:
            self._target_edit.setText(path)
            self._target_path = path

    def _get_selected_formats(self) -> Optional[Set[str]]:
        if all(cb.isChecked() for cb in self._format_checks.values()):
            return None
        return {fmt for fmt, cb in self._format_checks.items() if cb.isChecked()}

    def _get_selected_matches(self) -> List[MatchResult]:
        selected = []
        for i in range(self._results_tree.topLevelItemCount()):
            item = self._results_tree.topLevelItem(i)
            if item.checkState(0) == Qt.CheckState.Checked:
                match = item.data(0, Qt.ItemDataRole.UserRole)
                if match:
                    selected.append(match)
        return selected

    def _update_copy_button(self):
        has_source = bool(self._source_path and os.path.isfile(self._source_path))
        has_targets = len(self._matches) > 0
        self._copy_btn.setEnabled(has_source and has_targets)

    def _select_all(self):
        for i in range(self._results_tree.topLevelItemCount()):
            self._results_tree.topLevelItem(i).setCheckState(0, Qt.CheckState.Checked)

    def _deselect_all(self):
        for i in range(self._results_tree.topLevelItemCount()):
            self._results_tree.topLevelItem(i).setCheckState(0, Qt.CheckState.Unchecked)

    def _invert_selection(self):
        for i in range(self._results_tree.topLevelItemCount()):
            item = self._results_tree.topLevelItem(i)
            current = item.checkState(0)
            item.setCheckState(0, Qt.CheckState.Unchecked if current == Qt.CheckState.Checked else Qt.CheckState.Checked)

    def _clear_results(self):
        self._matches.clear()
        self._results_tree.clear()
        self._result_count_label.setText("未扫描")
        self._copy_btn.setEnabled(False)
        self._progress_bar.setVisible(False)

    def _open_target_dir(self):
        if self._target_path:
            target = self._target_path
            if os.path.isfile(target):
                target = os.path.dirname(target)
            if os.path.isdir(target):
                try:
                    if sys.platform == "win32":
                        os.startfile(target)
                    elif sys.platform == "darwin":
                        import subprocess; subprocess.run(["open", target])
                    else:
                        import subprocess; subprocess.run(["xdg-open", target])
                except Exception as e:
                    self._log(f"无法打开目录: {e}", "error")

    def _show_context_menu(self, pos):
        menu = QMenu(self)
        select_action = menu.addAction("全选")
        deselect_action = menu.addAction("取消全选")
        invert_action = menu.addAction("反选")
        menu.addSeparator()
        select_match_action = menu.addAction("仅选精确匹配")
        select_sub_action = menu.addAction("仅选子串匹配")
        action = menu.exec(self._results_tree.viewport().mapToGlobal(pos))
        if action == select_action:
            self._select_all()
        elif action == deselect_action:
            self._deselect_all()
        elif action == invert_action:
            self._invert_selection()
        elif action == select_match_action:
            for i in range(self._results_tree.topLevelItemCount()):
                item = self._results_tree.topLevelItem(i)
                match = item.data(0, Qt.ItemDataRole.UserRole)
                if match and match.match_type == "exact":
                    item.setCheckState(0, Qt.CheckState.Checked)
                else:
                    item.setCheckState(0, Qt.CheckState.Unchecked)
        elif action == select_sub_action:
            for i in range(self._results_tree.topLevelItemCount()):
                item = self._results_tree.topLevelItem(i)
                match = item.data(0, Qt.ItemDataRole.UserRole)
                if match and match.match_type == "substring":
                    item.setCheckState(0, Qt.CheckState.Checked)
                else:
                    item.setCheckState(0, Qt.CheckState.Unchecked)

    def _log(self, message: str, level: str = "info"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        prefix = {"info": "  ", "success": "✅", "warning": "⚠️", "error": "❌"}.get(level, "  ")
        log_line = f"[{timestamp}] {prefix} {message}"
        self._log_text.appendPlainText(log_line)
        scrollbar = self._log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def _apply_theme(self):
        self.setStyleSheet(generate_stylesheet(DARK_THEME))

    def closeEvent(self, event):
        self._stop_operation()
        event.accept()
