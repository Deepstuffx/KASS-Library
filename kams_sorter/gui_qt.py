from __future__ import annotations

"""PyQt-based GUI for the Sample Library Organizer.

This UI provides a modern, macOS-friendly look with a dark palette inspired by Apple themes.
It mirrors the functionality of the Tk GUI: pick source/destination, choose fast vs deep,
dry run and tagging, run in background, show progress and logs.
"""

import os
import sys
import platform
from pathlib import Path
from typing import Optional

from .core import DB, iter_media, Job, process, ensure_base_structure, clear_memory

try:
    # Prefer PyQt6, fallback to PyQt5
    from PyQt6 import QtCore, QtGui, QtWidgets  # type: ignore
    PYQT_VERSION = 6
except Exception:  # pragma: no cover - fallback
    try:
        from PyQt5 import QtCore, QtGui, QtWidgets  # type: ignore
        PYQT_VERSION = 5
    except Exception:
        # Provide minimal stubs so type checkers don't explode; runtime will exit.
        class _Stub:  # pragma: no cover
            pass
        QtCore = QtGui = QtWidgets = _Stub()  # type: ignore
        PYQT_VERSION = 0

# QAction compatibility across PyQt5/6
if PYQT_VERSION == 6:
    QAction = QtGui.QAction  # type: ignore[attr-defined]
else:
    # PyQt5 provides QAction on QtWidgets
    QAction = QtWidgets.QAction  # type: ignore[attr-defined]


def _apply_apple_dark_palette(app) -> None:
    # Use Fusion style for a consistent baseline across platforms
    app.setStyle("Fusion")
    palette = QtGui.QPalette()
    # Colors tuned for macOS dark-like theme
    base = QtGui.QColor(28, 28, 30)   # #1c1c1e
    alt = QtGui.QColor(44, 44, 46)    # #2c2c2e
    text = QtGui.QColor(230, 230, 230)  # #e6e6e6
    disabled = QtGui.QColor(128, 128, 128)

    role = QtGui.QPalette.ColorRole
    group = QtGui.QPalette.ColorGroup

    palette.setColor(role.Window, base)
    palette.setColor(role.WindowText, text)
    palette.setColor(role.Base, QtGui.QColor(17, 17, 20))
    palette.setColor(role.AlternateBase, alt)
    palette.setColor(role.ToolTipBase, alt)
    palette.setColor(role.ToolTipText, text)
    palette.setColor(role.Text, text)
    palette.setColor(role.Button, alt)
    palette.setColor(role.ButtonText, text)
    palette.setColor(role.BrightText, QtGui.QColor(255, 0, 0))
    palette.setColor(role.Highlight, QtGui.QColor(80, 100, 255))
    palette.setColor(role.HighlightedText, QtGui.QColor(255, 255, 255))

    # Disabled state
    palette.setColor(group.Disabled, role.Text, disabled)
    palette.setColor(group.Disabled, role.ButtonText, disabled)
    palette.setColor(group.Disabled, role.WindowText, disabled)

    app.setPalette(palette)


class Worker(QtCore.QThread):
    progress = QtCore.pyqtSignal(int, int)  # completed, total
    log_msg = QtCore.pyqtSignal(str)
    finished = QtCore.pyqtSignal()

    def __init__(self, src: Path, dest: Path, dry: bool, tag: bool, deep: bool) -> None:
        super().__init__()
        self.src = src
        self.dest = dest
        self.dry = dry
        self.tag = tag
        self.deep = deep
        self._stop = False

    def request_stop(self) -> None:
        self._stop = True

    def run(self) -> None:
        db_path = self.dest / '.organizer_state.sqlite'
        db = DB(db_path)
        jobs: list[Job] = []
        try:
            for f in iter_media(self.src):
                try:
                    rel_pack = str(f.relative_to(self.src).parent)
                except Exception:
                    rel_pack = ''
                jobs.append(Job(src=f, rel_pack=rel_pack))
            total = len(jobs)
            completed = 0
            self.progress.emit(0, total)

            max_workers = max(1, min(4, os.cpu_count() or 4))
            # Use a simple thread pool with Python futures
            from concurrent.futures import ThreadPoolExecutor, as_completed
            with ThreadPoolExecutor(max_workers=max_workers) as ex:
                futs = {ex.submit(process, j, self.dest, db, self.dry, self.tag, self._emit_log, deep=self.deep): j for j in jobs}
                for fut in as_completed(futs):
                    if self._stop:
                        break
                    try:
                        _ok, _msg = fut.result()
                    except Exception as e:  # pragma: no cover
                        self._emit_log(f"error: {e}")
                    completed += 1
                    self.progress.emit(completed, total)
        finally:
            try:
                db.close()
            except Exception:
                pass
            self.finished.emit()

    def _emit_log(self, msg: str) -> None:
        self.log_msg.emit(msg)


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle('Sample Library Organizer')
        self.setMinimumSize(840, 560)
        self._worker: Optional[Worker] = None
        self.clear_cache_before_run = False

        central = QtWidgets.QWidget(self)
        self.setCentralWidget(central)
        layout = QtWidgets.QGridLayout(central)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setHorizontalSpacing(10)
        layout.setVerticalSpacing(8)

        # Source
        layout.addWidget(QtWidgets.QLabel('Source packs folder:'), 0, 0, 1, 1)
        self.src_edit = QtWidgets.QLineEdit()
        self.src_btn = QtWidgets.QPushButton('Browse…')
        self.src_btn.clicked.connect(self._browse_src)
        layout.addWidget(self.src_edit, 1, 0, 1, 2)
        layout.addWidget(self.src_btn, 1, 2, 1, 1)

        # Destination
        layout.addWidget(QtWidgets.QLabel('Destination library:'), 2, 0, 1, 1)
        self.dest_edit = QtWidgets.QLineEdit()
        self.dest_btn = QtWidgets.QPushButton('Browse…')
        self.dest_btn.clicked.connect(self._browse_dest)
        layout.addWidget(self.dest_edit, 3, 0, 1, 2)
        layout.addWidget(self.dest_btn, 3, 2, 1, 1)

        # Options
        self.dry_chk = QtWidgets.QCheckBox('Dry run (no files copied)')
        self.dry_chk.setChecked(True)
        self.tag_chk = QtWidgets.QCheckBox('Tag source pack name')
        self.fast_chk = QtWidgets.QCheckBox('Fast mode (skip deep analysis)')
        self.fast_chk.setChecked(True)
        layout.addWidget(self.dry_chk, 4, 0, 1, 2)
        layout.addWidget(self.tag_chk, 5, 0, 1, 2)
        layout.addWidget(self.fast_chk, 6, 0, 1, 2)

        # Buttons
        self.start_btn = QtWidgets.QPushButton('Start')
        self.stop_btn = QtWidgets.QPushButton('Stop')
        # Compact button sizing
        for b in (self.start_btn, self.stop_btn):
            try:
                b.setMinimumHeight(26)
                b.setMaximumHeight(28)
                b.setStyleSheet("QPushButton { padding: 2px 10px; font-size: 11pt; }")
            except Exception:
                pass
        self.stop_btn.setEnabled(False)
        self.start_btn.clicked.connect(self._start)
        self.stop_btn.clicked.connect(self._stop)
        btn_row = QtWidgets.QHBoxLayout()
        btn_row.addWidget(self.start_btn)
        btn_row.addWidget(self.stop_btn)
        layout.addLayout(btn_row, 7, 0, 1, 3)

        # Progress + label
        self.progress = QtWidgets.QProgressBar()
        self.progress.setRange(0, 100)
        self.progress_label = QtWidgets.QLabel('0 / 0')
        prog_row = QtWidgets.QHBoxLayout()
        prog_row.addWidget(self.progress)
        prog_row.addWidget(self.progress_label)
        layout.addLayout(prog_row, 8, 0, 1, 3)

        # Log
        self.log = QtWidgets.QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setLineWrapMode(QtWidgets.QPlainTextEdit.LineWrapMode.WidgetWidth)
        layout.addWidget(self.log, 9, 0, 1, 3)

        # Menus (macOS menu bar friendly)
        self._build_menus()

    def _build_menus(self) -> None:
        mb = self.menuBar()
        # Application menu (on macOS, this appears under the app name)
        app_menu = mb.addMenu('&Application')
        act_prefs = QAction('Preferences…', self)
        try:
            act_prefs.setShortcut(QtGui.QKeySequence.StandardKey.Preferences)
        except Exception:
            act_prefs.setShortcut('Ctrl+,')
        act_prefs.triggered.connect(self._open_prefs)

        self.act_clear_before = QAction('Clear cache before run', self)
        self.act_clear_before.setCheckable(True)
        self.act_clear_before.toggled.connect(self._toggle_clear_before)

        act_clear_now = QAction('Clear Cache Now…', self)
        act_clear_now.setShortcut('Ctrl+Shift+Backspace')
        act_clear_now.triggered.connect(self._clear_cache_now)

        act_quit = QAction('Quit', self)
        try:
            act_quit.setShortcut(QtGui.QKeySequence.StandardKey.Quit)
        except Exception:
            act_quit.setShortcut('Ctrl+Q')
        act_quit.triggered.connect(QtWidgets.QApplication.instance().quit)

        app_menu.addAction(act_prefs)
        app_menu.addSeparator()
        app_menu.addAction(self.act_clear_before)
        app_menu.addAction(act_clear_now)
        app_menu.addSeparator()
        app_menu.addAction(act_quit)

        # File menu
        file_menu = mb.addMenu('&File')
        act_start = QAction('Start', self)
        act_start.setShortcut('Ctrl+R')
        act_start.triggered.connect(self._start)
        act_stop = QAction('Stop', self)
        act_stop.setShortcut('Ctrl+S')
        act_stop.triggered.connect(self._stop)
        file_menu.addAction(act_start)
        file_menu.addAction(act_stop)

        # View/Options menu
        view_menu = mb.addMenu('&Options')
        self.act_opt_dry = QAction('Dry run (no files copied)', self)
        self.act_opt_dry.setCheckable(True)
        self.act_opt_dry.setChecked(True)
        self.act_opt_dry.toggled.connect(self.dry_chk.setChecked)
        self.dry_chk.toggled.connect(self.act_opt_dry.setChecked)

        self.act_opt_tag = QAction('Tag source pack name', self)
        self.act_opt_tag.setCheckable(True)
        self.act_opt_tag.setChecked(False)
        self.act_opt_tag.toggled.connect(self.tag_chk.setChecked)
        self.tag_chk.toggled.connect(self.act_opt_tag.setChecked)

        self.act_opt_fast = QAction('Fast mode (skip deep analysis)', self)
        self.act_opt_fast.setCheckable(True)
        self.act_opt_fast.setChecked(True)
        self.act_opt_fast.toggled.connect(self.fast_chk.setChecked)
        self.fast_chk.toggled.connect(self.act_opt_fast.setChecked)

        view_menu.addAction(self.act_opt_dry)
        view_menu.addAction(self.act_opt_tag)
        view_menu.addAction(self.act_opt_fast)

        # Help menu
        help_menu = mb.addMenu('&Help')
        act_about = QAction('About', self)
        act_about.triggered.connect(self._show_about)
        help_menu.addAction(act_about)

    def _show_about(self) -> None:
        QtWidgets.QMessageBox.information(self, 'About', 'Kams Auto Sample Sorter\nQt GUI — modern macOS look\nFast vs Deep analysis, dry-run, tagging, and cache controls.')

    def _open_prefs(self) -> None:
        # Simple preferences dialog to mirror options
        dlg = QtWidgets.QDialog(self)
        dlg.setWindowTitle('Preferences')
        lay = QtWidgets.QFormLayout(dlg)
        cb_dry = QtWidgets.QCheckBox('Dry run (no files copied)')
        cb_dry.setChecked(self.dry_chk.isChecked())
        cb_tag = QtWidgets.QCheckBox('Tag source pack name')
        cb_tag.setChecked(self.tag_chk.isChecked())
        cb_fast = QtWidgets.QCheckBox('Fast mode (skip deep analysis)')
        cb_fast.setChecked(self.fast_chk.isChecked())
        cb_clear_before = QtWidgets.QCheckBox('Clear cache before run')
        cb_clear_before.setChecked(self.clear_cache_before_run)
        lay.addRow(cb_dry)
        lay.addRow(cb_tag)
        lay.addRow(cb_fast)
        lay.addRow(cb_clear_before)
        btn_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.StandardButton.Ok | QtWidgets.QDialogButtonBox.StandardButton.Cancel)
        lay.addRow(btn_box)
        btn_box.accepted.connect(dlg.accept)
        btn_box.rejected.connect(dlg.reject)
        if dlg.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            self.dry_chk.setChecked(cb_dry.isChecked())
            self.tag_chk.setChecked(cb_tag.isChecked())
            self.fast_chk.setChecked(cb_fast.isChecked())
            self.clear_cache_before_run = cb_clear_before.isChecked()
            self.act_clear_before.setChecked(self.clear_cache_before_run)

    def _toggle_clear_before(self, checked: bool) -> None:
        self.clear_cache_before_run = bool(checked)

    def _clear_cache_now(self) -> None:
        ok = False
        try:
            ok = clear_memory(confirm=True)
        except Exception:
            ok = False
        if ok:
            self._log('Cache cleared. All files will be considered next run.')
        else:
            self._log('Cache was already clear or could not be cleared.')

    def _browse_src(self) -> None:
        path = QtWidgets.QFileDialog.getExistingDirectory(self, 'Select Source')
        if path:
            self.src_edit.setText(path)

    def _browse_dest(self) -> None:
        path = QtWidgets.QFileDialog.getExistingDirectory(self, 'Select Destination')
        if path:
            self.dest_edit.setText(path)

    def _start(self) -> None:
        src = self.src_edit.text().strip()
        dest = self.dest_edit.text().strip()
        if not src or not dest:
            self._log('Please select both source and destination directories.')
            return
        srcp = Path(src)
        destp = Path(dest)
        if not srcp.exists():
            self._log('Source does not exist.')
            return
        destp.mkdir(parents=True, exist_ok=True)
        ensure_base_structure(destp)

        # Clear cache if requested via menu toggle
        if self.clear_cache_before_run:
            self._log('Clearing cache before run...')
            try:
                clear_memory(confirm=True)
                self._log('Cache cleared.')
            except Exception as e:
                self._log(f'Warning: failed to clear cache: {e}')

        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)

        dry = self.dry_chk.isChecked()
        tag = self.tag_chk.isChecked()
        fast = self.fast_chk.isChecked()
        deep = not fast

        self._worker = Worker(srcp, destp, dry=dry, tag=tag, deep=deep)
        self._worker.progress.connect(self._on_progress)
        self._worker.log_msg.connect(self._log)
        self._worker.finished.connect(self._run_finished)
        self._worker.start()

    def _stop(self) -> None:
        if self._worker is not None:
            self._worker.request_stop()
            self._log('Stop requested — waiting for current operations to finish...')

    @QtCore.pyqtSlot(int, int)
    def _on_progress(self, completed: int, total: int) -> None:
        if total <= 0:
            self.progress.setValue(0)
            self.progress_label.setText('0 / 0')
            return
        percent = int((completed / total) * 100)
        self.progress.setValue(percent)
        self.progress_label.setText(f'{completed} / {total}')

    @QtCore.pyqtSlot()
    def _run_finished(self) -> None:
        self._log('Run finished.')
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self._worker = None

    def _log(self, msg: str) -> None:
        self.log.appendPlainText(msg)


def launch_qt_gui() -> None:
    # Enable high-DPI scaling and use device pixel ratio for crisp rendering on Retina / 4K.
    try:
        QtWidgets.QApplication.setAttribute(QtCore.Qt.ApplicationAttribute.AA_EnableHighDpiScaling, True)
        QtWidgets.QApplication.setAttribute(QtCore.Qt.ApplicationAttribute.AA_UseHighDpiPixmaps, True)
    except Exception:
        pass
    app = QtWidgets.QApplication(sys.argv)
    # Dynamic scale factor (user-adjustable via env SAMPLE_ORGANIZER_SCALE or defaults).
    scale_env = os.environ.get('SAMPLE_ORGANIZER_SCALE')
    scale: float = 1.0
    try:
        if scale_env:
            scale = max(0.5, min(3.0, float(scale_env)))
    except Exception:
        scale = 1.0
    if scale != 1.0:
        # Apply font scaling: iterate over default font and set point size multiplier.
        default_font = app.font()
        try:
            new_size = int(default_font.pointSize() * scale)
            if new_size > 0:
                default_font.setPointSize(new_size)
                app.setFont(default_font)
        except Exception:
            pass
        # Optionally increase base window and layout metrics.
        try:
            app.setStyleSheet(f"QWidget {{ font-size: {int(12*scale)}pt; }}")
        except Exception:
            pass
    # macOS: use dark palette by default
    try:
        if platform.system() == 'Darwin':
            _apply_apple_dark_palette(app)
    except Exception:
        pass
    w = MainWindow()
    # Scale initial window size appropriately
    if scale != 1.0:
        try:
            base_w, base_h = 840, 560
            w.resize(int(base_w*scale), int(base_h*scale))
        except Exception:
            pass
    w.show()
    sys.exit(app.exec())
