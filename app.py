"""Launcher script for the Sample Library Organizer GUI or CLI fallback.

This launcher prefers the Qt GUI (if available) for a modern macOS look,
falls back to Tk GUI on systems without PyQt, and finally to the CLI if GUI
startup fails or is unsafe.
"""
import os
import sys
import platform
import subprocess
import signal
import shutil
from pathlib import Path
from typing import Optional

def _mac_compatible_for_tk() -> bool:
    # Heuristic: avoid GUI on macOS older than 10.14/10.15 (Darwin < 18/19) or
    # when the environment variable FORCE_GUI is not set. This is conservative
    # and avoids triggering Tk C-level aborts on older systems.
    if platform.system() != 'Darwin':
        return True
    ver = platform.mac_ver()[0]
    try:
        parts = [int(x) for x in ver.split('.') if x.isdigit()]
        major = parts[0] if parts else 0
        # macOS 10.14 Mojave -> mac_ver '10.14' -> treat >=10.14 as safe
        if major >= 11:
            return True
        if major == 10 and len(parts) > 1 and parts[1] >= 14:
            return True
    except Exception:
        pass
    # allow explicit override
    return bool(os.environ.get('SAMPLE_ORGANIZER_FORCE_GUI'))


def _can_import_pyqt(timeout: float = 5.0) -> bool:
    """Probe PyQt6 (preferred) or PyQt5 import in a subprocess safely."""
    try:
        # Try PyQt6 first
        cmd = [sys.executable, '-c', 'import PyQt6']
        p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)
        if p.returncode == 0:
            return True
    except Exception:
        pass
    try:
        # Fallback to PyQt5
        cmd = [sys.executable, '-c', 'import PyQt5']
        p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)
        return p.returncode == 0
    except Exception:
        return False


def _launch_qt_gui_subprocess() -> bool:
    """Try launching the Qt GUI in a subprocess. Returns True on success."""
    try:
        code = 'from kams_sorter.gui_qt import launch_qt_gui; launch_qt_gui()'
        cmd = [sys.executable, '-c', code]
        p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if p.stdout:
            try:
                print(p.stdout.decode('utf-8', errors='replace'))
            except Exception:
                print(p.stdout)
        if p.returncode == 0:
            return True
        err = p.stderr.decode('utf-8', errors='replace') if p.stderr else ''
        print('Qt GUI failed to start (subprocess). stderr:\n' + err, file=sys.stderr)
        return False
    except Exception as e:
        print('Qt GUI failed to start:', e, file=sys.stderr)
        return False


def main():
    # Prefer launching the GUI by default when no args are provided.
    # To force GUI (advanced users), set SAMPLE_ORGANIZER_FORCE_GUI=1 in the environment.
    force_gui = bool(os.environ.get('SAMPLE_ORGANIZER_FORCE_GUI'))
    def _can_import_tk(timeout: float = 3.0) -> bool:
        """Try importing tkinter in a subprocess to avoid a native abort in the main process.
        Returns True if import succeeded (exit 0) within timeout.
        """
        try:
            cmd = [sys.executable, '-c', 'import tkinter; print(getattr(tkinter, "TkVersion", "ok"))']
            p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)
            if p.returncode == 0:
                return True
            # print stderr to help diagnose native Tk failures (e.g. mismatched Tcl/Tk)
            try:
                err = p.stderr.decode('utf-8', errors='replace')
            except Exception:
                err = '<could not decode subprocess stderr>'
            if err:
                print('tkinter probe stderr:\n' + err, file=sys.stderr)
            else:
                print('tkinter probe failed with exit code ' + str(p.returncode), file=sys.stderr)
            return False
        except Exception:
            return False

    # If no args, try GUI immediately (Qt preferred, then Tk). Only fall back if both fail.
    if len(sys.argv) == 1 and not force_gui:
        if _can_import_pyqt():
            if _launch_qt_gui_subprocess():
                return
        if _can_import_tk():
            try:
                cmd = [sys.executable, '-c', 'from kams_sorter.gui import launch_gui; launch_gui()']
                p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                if p.stdout:
                    try:
                        print(p.stdout.decode('utf-8', errors='replace'))
                    except Exception:
                        print(p.stdout)
                if p.returncode == 0:
                    return
                err = p.stderr.decode('utf-8', errors='replace') if p.stderr else ''
                print('Tk GUI failed to start (subprocess). stderr:\n' + err, file=sys.stderr)
            except Exception as e:
                print('Tk GUI failed to start:', e, file=sys.stderr)

    if force_gui:
        # Honor explicit GUI request; try Qt first, then Tk.
        if _can_import_pyqt():
            if _launch_qt_gui_subprocess():
                return
            else:
                print('Qt GUI failed. Trying Tk GUI...', file=sys.stderr)
        # Probe tkinter safely before importing the GUI module into this process.
        if not _can_import_tk():
            print('Environment requests GUI, but GUI imports failed or are unsafe. Falling back to CLI.', file=sys.stderr)
        else:
            try:
                cmd = [sys.executable, '-c', 'from kams_sorter.gui import launch_gui; launch_gui()']
                p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                if p.stdout:
                    try:
                        print(p.stdout.decode('utf-8', errors='replace'))
                    except Exception:
                        print(p.stdout)
                if p.returncode == 0:
                    return
                err = p.stderr.decode('utf-8', errors='replace') if p.stderr else ''
                print('Forced Tk GUI launch failed (subprocess). stderr:\n' + err, file=sys.stderr)
            except Exception as e:
                print('Forced GUI launch failed, falling back to CLI:', e, file=sys.stderr)

    # If no args were provided, offer an interactive choice to the user
    # Globals used for graceful shutdown / subprocess control
    current_subproc = {'p': None}
    stop_requested = {'v': False}

    # Install a global SIGINT handler: if a child subprocess is running, ask to confirm
    def _handle_sigint(sig, frame):
        # If no subprocess running, ask to confirm quit
        p = current_subproc.get('p')
        if p is None:
            try:
                resp = input('\nQuit requested (Ctrl+C). Exit launcher? [y/N]: ').strip().lower()
            except Exception:
                resp = 'y'
            if resp == 'y':
                print('Exiting.')
                try:
                    sys.exit(0)
                except SystemExit:
                    os._exit(0)
            else:
                print('Continuing...')
                return
        else:
            # subprocess is running: send SIGINT to it, then ask whether to undo changes
            try:
                print('\nForwarding interrupt to running process...')
                p.send_signal(signal.SIGINT)
            except Exception:
                pass
            try:
                resp = input('Process interrupted. Quit and undo any changes made during this run? [y/N]: ').strip().lower()
            except Exception:
                resp = 'n'
            stop_requested['v'] = True
            if resp == 'y':
                print('Will attempt to undo changes and exit.')
                try:
                    p.terminate()
                except Exception:
                    pass
                # mark that caller should perform undo after subprocess returns
            else:
                print('Continuing; let process finish or interrupt again to prompt undo.')
            return
    signal.signal(signal.SIGINT, _handle_sigint)

    if len(sys.argv) == 1:
        # As a fallback (if both GUIs failed), offer interactive options
        script_path = os.path.join(os.path.dirname(__file__), 'Core Script')
        if not os.path.exists(script_path):
            # fallback to cwd name
            script_path = os.path.join(os.getcwd(), 'Core Script')

        print('\nSample Library Organizer Launcher')
        print('Press Ctrl+C at any time to quit.')
        print('Choose an action:')
        print('  1) Launch GUI (Qt if available, else Tk)')
        print('  2) Run interactive setup wizard')
        print('  3) Run CLI now (provide src/dest)')
        print('  q) Quit')
        choice = input('Select [1/2/3/q]: ').strip().lower()
        if choice == '1':
            # Prefer Qt if present
            if _can_import_pyqt():
                if _launch_qt_gui_subprocess():
                    return
                else:
                    print('Qt GUI failed. Trying Tk GUI...', file=sys.stderr)
            if not _can_import_tk() and not _can_import_pyqt():
                print('No usable GUI backend detected (PyQt/Tk).')
            else:
                try:
                    cmd = [sys.executable, '-c', 'from kams_sorter.gui_qt import launch_qt_gui; launch_qt_gui()'] if _can_import_pyqt() else [sys.executable, '-c', 'from kams_sorter.gui import launch_gui; launch_gui()']
                    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    if p.stdout:
                        try:
                            print(p.stdout.decode('utf-8', errors='replace'))
                        except Exception:
                            print(p.stdout)
                    if p.returncode == 0:
                        return
                    err = p.stderr.decode('utf-8', errors='replace') if p.stderr else ''
                    print('GUI failed to start (subprocess). stderr:\n' + err, file=sys.stderr)
                except Exception as e:
                    print('GUI failed to start:', e, file=sys.stderr)
        elif choice == '2':
            if not os.path.exists(script_path):
                print('Unable to locate the interactive script (Core Script) to run the wizard.', file=sys.stderr)
            else:
                # Prepare snapshot of destination (none for wizard because wizard will ask for paths)
                subprocess.run([sys.executable, script_path, '--wizard'])
                return
        elif choice == '3':
            src = input('Source packs folder: ').strip()
            dest = input('Destination library folder: ').strip()
            if not src or not dest:
                print('Source and destination are required. Exiting.')
                return
            cmd = [sys.executable, script_path, src, dest]
            dry = input('Dry run? (Y/n): ').strip().lower()
            if dry and dry[0:1] != 'n':
                cmd.append('--dry-run')
            tag = input('Tag source pack name to filenames? (y/N): ').strip().lower()
            if tag and tag[0:1] == 'y':
                cmd.append('--tag-source')

            # Snapshot destination state (list files) and backup DB/logs so we can undo if requested
            dest_path = Path(dest).expanduser().resolve()
            pre_files = set()
            if dest_path.exists():
                for root, _, files in os.walk(dest_path):
                    for fn in files:
                        full = os.path.join(root, fn)
                        try:
                            rel = os.path.relpath(full, dest_path)
                        except Exception:
                            rel = full
                        pre_files.add(rel)
            # backup DB and logs
            db_path = dest_path / '.organizer_state.sqlite'
            db_backup = None
            if db_path.exists():
                try:
                    db_backup = str(db_path) + '.bak'
                    shutil.copy2(str(db_path), db_backup)
                except Exception as e:
                    print('Warning: failed to backup DB:', e)
            logs_path = dest_path / '.organizer_logs.txt'
            logs_backup = None
            if logs_path.exists():
                try:
                    logs_backup = str(logs_path) + '.bak'
                    shutil.copy2(str(logs_path), logs_backup)
                except Exception as e:
                    print('Warning: failed to backup logs:', e)

            # Launch subprocess and keep reference for SIGINT handler
            try:
                p = subprocess.Popen(cmd)
                current_subproc['p'] = p
                rc = p.wait()
                current_subproc['p'] = None
            except Exception as e:
                print('Failed to run process:', e, file=sys.stderr)
                current_subproc['p'] = None
                return

            # If user requested undo via SIGINT handler, perform best-effort undo
            if stop_requested['v']:
                try:
                    print('Undoing changes made during the run...')
                    # remove files that are new
                    if dest_path.exists():
                        for root, _, files in os.walk(dest_path):
                            for fn in files:
                                full = os.path.join(root, fn)
                                try:
                                    rel = os.path.relpath(full, dest_path)
                                except Exception:
                                    rel = full
                                if rel not in pre_files:
                                    try:
                                        os.remove(full)
                                    except Exception:
                                        pass
                    # restore DB
                    if db_backup and os.path.exists(db_backup):
                        try:
                            shutil.move(db_backup, str(db_path))
                        except Exception as e:
                            print('Warning: failed to restore DB backup:', e)
                    # restore logs
                    if logs_backup and os.path.exists(logs_backup):
                        try:
                            shutil.move(logs_backup, str(logs_path))
                        except Exception as e:
                            print('Warning: failed to restore logs backup:', e)
                    print('Undo complete.')
                except Exception as e:
                    print('Undo failed:', e)
            return
        else:
            print('Goodbye.')
            return
    # fallback: run CLI module
    try:
        from kams_sorter import cli
        cli.main()
    except Exception as e:
        print('Failed to run CLI:', e, file=sys.stderr)


if __name__ == '__main__':
    main()
