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

from .core import DB, iter_media, Job, process, ensure_base_structure

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
    app = QtWidgets.QApplication(sys.argv)
    # macOS: use dark palette by default
    try:
        if platform.system() == 'Darwin':
            _apply_apple_dark_palette(app)
    except Exception:
        pass
    w = MainWindow()
    w.show()
    sys.exit(app.exec())
