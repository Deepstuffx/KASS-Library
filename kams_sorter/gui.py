from __future__ import annotations

"""Simple Tkinter GUI wrapper to run the organizer.

This module lazy-loads tkinter inside launch_gui() to avoid importing
tkinter on platforms where it may crash at import time (older macOS/Tk builds).
"""

from pathlib import Path
from typing import Optional
from .core import DB, iter_media, Job, process, ensure_base_structure


def launch_gui() -> None:
    """Create and run the Tkinter GUI. tkinter is imported lazily here.

    This avoids importing Tk on macOS at program start where some Tk builds
    can crash the process. Use the launcher probe before calling this on
    platforms where Tk may be problematic.
    """
    import threading
    import tkinter as tk
    from tkinter import ttk, filedialog, scrolledtext
    import os
    from concurrent.futures import ThreadPoolExecutor, as_completed

    class OrganizerGUI(ttk.Frame):
        def __init__(self, master=None):
            super().__init__(master)
            self.master = master
            self.pack(fill='both', expand=True)

            # Styles
            style = ttk.Style(master)
            try:
                style.theme_use('clam')
            except Exception:
                pass

            # Fonts (best-effort)
            try:
                import tkinter.font as tkfont
                self.header_font = tkfont.nametofont('TkHeadingFont') if 'TkHeadingFont' in tkfont.names() else tkfont.Font(size=14, weight='bold')
                self.body_font = tkfont.nametofont('TkTextFont') if 'TkTextFont' in tkfont.names() else tkfont.Font(size=11)
                style.configure('Header.TLabel', font=self.header_font)
                style.configure('Body.TLabel', font=self.body_font)
                style.configure('Accent.TButton', font=self.body_font)
            except Exception:
                self.header_font = None
                self.body_font = None

            # macOS dark-mode friendly tweaks and border color improvements
            try:
                import platform as _platform
                if _platform.system() == 'Darwin' or True:
                    # darker background and light text for logs and frames
                    style.configure('TFrame', background='#1c1c1e', bordercolor='#333347')
                    style.configure('TLabel', background='#1c1c1e', foreground='#e6e6e6')
                    style.configure('TEntry', fieldbackground='#2c2c2e', foreground='#e6e6e6', bordercolor='#333347')
                    style.configure('TButton', background='#2c2c2e', foreground='#e6e6e6', bordercolor='#333347')
                    style.configure('TCheckbutton', background='#1c1c1e', foreground='#e6e6e6', bordercolor='#333347')
                    style.configure('TMenubutton', background='#2c2c2e', foreground='#e6e6e6', bordercolor='#333347')
            except Exception:
                pass

            # internal state
            self.worker_thread: Optional[threading.Thread] = None
            self.stop_requested = False
            # config file for GUI preferences
            self._cfg_path = Path.home() / '.sample_organizer.json'
            self.appearance = 'dark'  # default; may be overridden by config
            # load stored config
            try:
                import json
                if self._cfg_path.exists():
                    with self._cfg_path.open('r', encoding='utf-8') as fh:
                        d = json.load(fh)
                        if isinstance(d, dict) and d.get('appearance') in ('dark', 'light'):
                            self.appearance = d.get('appearance')
            except Exception:
                pass

            self.create_widgets()

        def create_widgets(self) -> None:
            # Use a paned window: left controls, right log/progress
            paned = ttk.Panedwindow(self, orient='horizontal')
            paned.pack(fill='both', expand=True, padx=8, pady=8)
            # LEFT: controls card
            left = ttk.Frame(paned, padding=(12, 12))
            left.columnconfigure(0, weight=1)
            paned.add(left, weight=0)

            ttk.Label(left, text='Sample Library Organizer', style='Header.TLabel').grid(column=0, row=0, sticky='w', pady=(0, 8))

            ttk.Label(left, text='Source packs folder:', style='Body.TLabel').grid(column=0, row=1, sticky='w')
            self.src_var = tk.StringVar()
            # recent sources combobox
            try:
                from kams_sorter.core import load_memory
                mem = load_memory()
                recent_srcs = mem.get('recent_srcs', [])
            except Exception:
                mem = {'recent_srcs': [], 'recent_dests': [], 'last_src': None, 'last_dest': None}
                recent_srcs = mem.get('recent_srcs', [])
            self._mem = mem
            self.src_combo = ttk.Combobox(left, textvariable=self.src_var, values=recent_srcs)
            self.src_combo.grid(column=0, row=2, sticky='we', pady=(4, 8))
            ttk.Button(left, text='Browse', command=self.browse_src).grid(column=0, row=3, sticky='we')

            ttk.Label(left, text='Destination library:', style='Body.TLabel').grid(column=0, row=4, sticky='w', pady=(8, 0))
            self.dest_var = tk.StringVar()
            try:
                recent_dests = self._mem.get('recent_dests', [])
            except Exception:
                recent_dests = []
            self.dest_combo = ttk.Combobox(left, textvariable=self.dest_var, values=recent_dests)
            self.dest_combo.grid(column=0, row=5, sticky='we', pady=(4, 8))
            ttk.Button(left, text='Browse', command=self.browse_dest).grid(column=0, row=6, sticky='we')

            self.dry_var = tk.BooleanVar(value=True)
            ttk.Checkbutton(left, text='Dry run (no files copied)', variable=self.dry_var).grid(column=0, row=7, sticky='w', pady=(8, 0))
            self.tag_var = tk.BooleanVar(value=False)
            ttk.Checkbutton(left, text='Tag source pack name', variable=self.tag_var).grid(column=0, row=8, sticky='w')
            # Fast mode: skip expensive audio analysis (if integrated)
            self.fast_var = tk.BooleanVar(value=True)
            ttk.Checkbutton(left, text='Fast mode (skip deep analysis)', variable=self.fast_var).grid(column=0, row=9, sticky='w', pady=(4,0))


            # Buttons (use grid so buttons remain reachable when resizing)
            btn_row = ttk.Frame(left)
            btn_row.grid(column=0, row=11, sticky='we', pady=(12, 0))
            btn_row.columnconfigure(0, weight=1)
            btn_row.columnconfigure(1, weight=0)
            btn_row.columnconfigure(2, weight=0)
            btn_row.columnconfigure(3, weight=0)
            # Appearance toggle (persisted)
            self._appearance_var = tk.StringVar(value=self.appearance)
            ap_frm = ttk.Frame(left)
            ap_frm.grid(column=0, row=12, sticky='we', pady=(8,0))
            ttk.Label(ap_frm, text='Appearance:', style='Body.TLabel').grid(column=0, row=0, sticky='w')
            self.appear_opt = ttk.OptionMenu(ap_frm, self._appearance_var, self.appearance, 'dark', 'light', command=self._on_appearance_change)
            self.appear_opt.grid(column=1, row=0, sticky='e')
            self.start_btn = ttk.Button(btn_row, text='▶ Start', style='Accent.TButton', command=self.start)
            self.start_btn.grid(column=0, row=0, sticky='we')
            self.stop_btn = ttk.Button(btn_row, text='■ Stop', command=self.request_stop, state='disabled')
            self.stop_btn.grid(column=1, row=0, sticky='e', padx=(8, 0))
            self.clear_btn = ttk.Button(btn_row, text='Clear Log', command=self.clear_log)
            self.clear_btn.grid(column=2, row=0, sticky='e', padx=(8, 0))
            self.cache_btn = ttk.Button(btn_row, text='Clear Cache', command=self.clear_cache)
            self.cache_btn.grid(column=3, row=0, sticky='e', padx=(8, 0))

            # RIGHT: log and progress
            right = ttk.Frame(paned, padding=(6, 6))
            right.columnconfigure(0, weight=1)
            right.rowconfigure(1, weight=1)
            paned.add(right, weight=1)

            # Progress (large). Use two columns so the label stays visible and the
            # bar can expand/shrink independently.
            right.columnconfigure(0, weight=1)
            right.columnconfigure(1, weight=0)
            self.progress = ttk.Progressbar(right, orient='horizontal', mode='determinate')
            self.progress.grid(column=0, row=0, sticky='we', pady=(0, 6), padx=(0,4))
            self.progress_label = ttk.Label(right, text='0 / 0')
            self.progress_label.grid(column=1, row=0, sticky='e')

            # Large log area (wrap text so lines reflow and don't disappear off-screen)
            self.log = scrolledtext.ScrolledText(right, height=20, wrap='word')
            self.log.grid(column=0, row=1, columnspan=2, sticky='nsew')
            # apply fonts/colors where available
            try:
                bf = getattr(self, 'body_font', None)
                if bf is not None:
                    self.log.configure(font=bf)
            except Exception:
                pass
            try:
                import platform as _platform
                if _platform.system() == 'Darwin':
                    # dark background for the text area
                    self.log.configure(bg='#111114', fg='#e6e6e6', insertbackground='#e6e6e6')
            except Exception:
                pass
            # Ensure appearance is applied after widgets exist
            try:
                self._apply_appearance(self.appearance)
            except Exception:
                pass

        def browse_src(self) -> None:
            try:
                init = self._mem.get('last_src') if getattr(self, '_mem', None) else None
            except Exception:
                init = None
            p = filedialog.askdirectory(initialdir=init)
            if p:
                self.src_var.set(p)

        def browse_dest(self) -> None:
            try:
                init = self._mem.get('last_dest') if getattr(self, '_mem', None) else None
            except Exception:
                init = None
            p = filedialog.askdirectory(initialdir=init)
            if p:
                self.dest_var.set(p)

        def clear_cache(self) -> None:
            import tkinter.messagebox as mb
            from kams_sorter.core import clear_memory
            if mb.askyesno('Clear Cache', 'Are you sure you want to clear the cache of processed files? This will force a full rescan next run.'):
                ok = clear_memory(confirm=True)
                if ok:
                    self.log_message('Cache cleared. All files will be considered next run.')
                else:
                    self.log_message('Cache was already clear or could not be cleared.')

        def clear_log(self) -> None:
            self.log.delete('1.0', tk.END)

        def log_message(self, msg: str) -> None:
            try:
                self.log.insert(tk.END, msg + "\n")
                self.log.see(tk.END)
            except Exception:
                pass

        def _update_progress(self, completed: int, total: int) -> None:
            if total <= 0:
                self.progress['value'] = 0
                self.progress_label.config(text='0 / 0')
                return
            percent = int((completed / total) * 100)
            self.progress['maximum'] = 100
            self.progress['value'] = percent
            self.progress_label.config(text=f"{completed} / {total}")

        def start(self) -> None:
            src = self.src_var.get().strip()
            dest = self.dest_var.get().strip()
            if not src or not dest:
                self.log_message('Please select both source and destination directories.')
                return
            srcp = Path(src)
            destp = Path(dest)
            if not srcp.exists():
                self.log_message('Source does not exist.')
                return
            destp.mkdir(parents=True, exist_ok=True)
            ensure_base_structure(destp)

            # disable controls
            self.start_btn.config(state='disabled')
            self.stop_btn.config(state='normal')
            self.clear_btn.config(state='disabled')
            self.stop_requested = False

            # persist recent folders
            try:
                from kams_sorter.core import load_memory, add_recent_src, add_recent_dest, save_memory
                mem = load_memory()
                add_recent_src(mem, str(srcp))
                add_recent_dest(mem, str(destp))
                mem['last_src'] = str(srcp)
                mem['last_dest'] = str(destp)
                save_memory(mem)
                self._mem = mem
            except Exception:
                pass

            # run worker thread
            self.worker_thread = threading.Thread(target=self._run, args=(srcp, destp, self.dry_var.get(), self.tag_var.get(), self.fast_var.get()), daemon=True)
            self.worker_thread.start()

        def request_stop(self) -> None:
            self.stop_requested = True
            self.log_message('Stop requested — waiting for current operations to finish...')
        
        def _run(self, srcp: Path, destp: Path, dry: bool, tag: bool, fast: bool) -> None:
            db_path = destp / '.organizer_state.sqlite'
            db = DB(db_path)
            jobs: list[Job] = []
            try:
                # collect jobs
                for f in iter_media(srcp):
                    # compute a rel_pack: the pack folder name relative to the source root
                    try:
                        rel_pack = str(f.relative_to(srcp).parent)
                    except Exception:
                        rel_pack = ''
                    jobs.append(Job(src=f, rel_pack=rel_pack))

                total = len(jobs)
                completed = 0
                self.master.after(0, lambda: self._update_progress(0, total))

                max_workers = max(1, min(4, os.cpu_count() or 4))
                with ThreadPoolExecutor(max_workers=max_workers) as ex:
                    futs = {ex.submit(process, j, destp, db, dry, tag, self.log_message, deep=(not fast)): j for j in jobs}
                    for fut in as_completed(futs):
                        try:
                            ok, msg = fut.result()
                        except Exception as e:
                            ok, msg = False, f'error: {e}'
                        completed += 1
                        # schedule GUI update on main thread
                        self.master.after(0, lambda c=completed, t=total: self._update_progress(c, t))
                        if self.stop_requested:
                            break
            finally:
                try:
                    db.close()
                except Exception:
                    pass
                self.master.after(0, self._run_finished)

        def _run_finished(self) -> None:
            self.log_message('Run finished.')
            self.start_btn.config(state='normal')
            self.stop_btn.config(state='disabled')
            self.clear_btn.config(state='normal')

        def _on_appearance_change(self, new: str) -> None:
            try:
                self.appearance = str(new)
                self._apply_appearance(self.appearance)
                # persist
                try:
                    import json
                    with self._cfg_path.open('w', encoding='utf-8') as fh:
                        json.dump({'appearance': self.appearance}, fh)
                except Exception:
                    pass
            except Exception:
                pass

        def _apply_appearance(self, which: str) -> None:
            # which == 'dark' or 'light'
            try:
                import platform as _platform
                dark = which == 'dark'
                # apply broadly (platform-specific handling best-effort)
                if True:
                    if dark:
                        bg = '#1c1c1e'
                        sub_bg = '#2c2c2e'
                        text_fg = '#e6e6e6'
                        entry_bg = '#2c2c2e'
                        log_bg = '#0f0f11'
                    else:
                        bg = '#f7f7f7'
                        sub_bg = '#ffffff'
                        text_fg = '#111111'
                        entry_bg = '#ffffff'
                        log_bg = '#ffffff'
                    # frames/labels
                    try:
                        self.master.configure(bg=bg)
                    except Exception:
                        pass
                    try:
                        style = ttk.Style(self.master)
                        style.configure('TFrame', background=bg)
                        style.configure('TLabel', background=bg, foreground=text_fg)
                        style.configure('TEntry', fieldbackground=entry_bg, foreground=text_fg)
                        style.configure('TButton', background=sub_bg, foreground=text_fg)
                    except Exception:
                        pass
                    try:
                        self.log.configure(bg=log_bg, fg=text_fg, insertbackground=text_fg)
                    except Exception:
                        pass
            except Exception:
                pass

    root = tk.Tk()
    root.title('Sample Library Organizer')
    try:
        # set a sensible minimum size so controls (log, buttons) are not hidden
        root.minsize(760, 520)
        import platform as _platform
        if _platform.system() == 'Darwin':
            # set window background to a darker tone for macOS dark-mode feel
            try:
                root.configure(bg='#1c1c1e')
            except Exception:
                pass
    except Exception:
        pass
    OrganizerGUI(master=root)
    root.mainloop()
