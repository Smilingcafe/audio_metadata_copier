"""音频元数据复制器 - 主入口"""
import sys, os, traceback, time, tempfile

_STARTUP_LOG = os.path.join(tempfile.gettempdir(), "AudioMetadataCopier_startup.log")

def _startup_log(msg: str):
    try:
        ts = time.strftime("%H:%M:%S")
        os.makedirs(os.path.dirname(_STARTUP_LOG), exist_ok=True)
        with open(_STARTUP_LOG, "a", encoding="utf-8") as f:
            f.write(f"[{ts}] {msg}\n")
    except Exception:
        pass

def _show_error(title: str, message: str):
    try:
        from PyQt6.QtWidgets import QApplication, QMessageBox
        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)
        QMessageBox.critical(None, title, message)
    except Exception:
        try:
            import ctypes
            ctypes.windll.user32.MessageBoxW(0, message, title, 0x10)
        except Exception:
            pass

def main():
    _t0 = time.perf_counter()
    try:
        if getattr(sys, "frozen", False):
            _startup_log("PyInstaller frozen mode, startup begin")
        else:
            try:
                import mutagen; import PyQt6.QtCore
            except ImportError as e:
                _show_error("缺少依赖", f"pip install mutagen PyQt6\n\n{e}")
                sys.exit(1)

        from PyQt6.QtWidgets import QApplication, QStyleFactory
        from PyQt6.QtGui import QPalette, QColor

        app = QApplication(sys.argv)
        app.setStyle(QStyleFactory.create("Fusion"))

        p = QPalette()
        p.setColor(QPalette.ColorRole.Window,          QColor("#080f1e"))
        p.setColor(QPalette.ColorRole.WindowText,      QColor("#dce6f5"))
        p.setColor(QPalette.ColorRole.Base,            QColor("#0d1b33"))
        p.setColor(QPalette.ColorRole.AlternateBase,   QColor("#132544"))
        p.setColor(QPalette.ColorRole.Text,            QColor("#dce6f5"))
        p.setColor(QPalette.ColorRole.Button,          QColor("#132544"))
        p.setColor(QPalette.ColorRole.ButtonText,      QColor("#dce6f5"))
        p.setColor(QPalette.ColorRole.Highlight,       QColor("#4d7cff"))
        p.setColor(QPalette.ColorRole.HighlightedText, QColor("#ffffff"))
        p.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.WindowText, QColor("#5a7099"))
        p.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, QColor("#5a7099"))
        app.setPalette(p)
        app.setApplicationName("音频元数据复制器")

        from src.gui.main_window import MainWindow
        window = MainWindow()
        window.show()

        _startup_log(f"Window shown ({time.perf_counter() - _t0:.2f}s)")
        if os.path.exists(_STARTUP_LOG):
            try: os.remove(_STARTUP_LOG)
            except OSError: pass

        sys.exit(app.exec())
    except Exception:
        err = traceback.format_exc()
        _startup_log(f"FATAL:\n{err}")
        _show_error("启动失败", f"程序启动时发生错误:\n\n{err}")
        sys.exit(1)

if __name__ == "__main__":
    main()
