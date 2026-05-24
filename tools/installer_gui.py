"""Internet Generation 日本語化パッチ - tkinter GUI インストーラ

PyInstaller で .exe 化してエンドユーザー配布する想定。
patcher.py の install() / uninstall() / find_game() を呼び出す。
"""
import os
import sys
import threading
import queue
import time
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext

# PyInstaller frozen 環境では、bundle 内の tools/ にパス追加
_BUNDLE = getattr(sys, '_MEIPASS', None)
if _BUNDLE:
    sys.path.insert(0, os.path.join(_BUNDLE, 'tools'))
else:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

import patcher  # noqa: E402


APP_TITLE = 'Internet Generation 日本語化パッチ インストーラ v1.0.0'
APP_GEOMETRY = '780x600'


class InstallerApp:
    def __init__(self, root):
        self.root = root
        self.root.title(APP_TITLE)
        self.root.geometry(APP_GEOMETRY)
        self.root.minsize(680, 500)

        # 状態
        self.game_path = tk.StringVar()
        self.status_text = tk.StringVar(value='未検出')
        self.log_queue = queue.Queue()
        self.worker_thread = None

        self._build_ui()
        self._auto_detect()
        self.root.after(100, self._drain_log_queue)

    # ---------- UI 構築 ----------
    def _build_ui(self):
        # ヘッダ
        header = tk.Frame(self.root, bg='#2b5d3f', pady=10)
        header.pack(fill='x')
        tk.Label(header, text=APP_TITLE, fg='white', bg='#2b5d3f',
                 font=('Yu Gothic UI', 12, 'bold')).pack()
        tk.Label(header,
                 text='非公式日本語化パッチ - InsularLobeGame と無関係、自己責任で利用してください',
                 fg='#cfdac5', bg='#2b5d3f',
                 font=('Yu Gothic UI', 9)).pack()

        # ゲームパス入力
        path_frame = ttk.LabelFrame(self.root, text='ゲームインストール先', padding=10)
        path_frame.pack(fill='x', padx=10, pady=8)

        entry_row = tk.Frame(path_frame)
        entry_row.pack(fill='x')
        tk.Entry(entry_row, textvariable=self.game_path,
                 font=('Consolas', 9)).pack(side='left', fill='x', expand=True, padx=(0, 6))
        ttk.Button(entry_row, text='参照…', command=self._browse).pack(side='left', padx=2)
        ttk.Button(entry_row, text='自動検出', command=self._auto_detect).pack(side='left', padx=2)

        status_row = tk.Frame(path_frame)
        status_row.pack(fill='x', pady=(6, 0))
        tk.Label(status_row, text='ステータス: ').pack(side='left')
        self.status_label = tk.Label(status_row, textvariable=self.status_text,
                                      fg='#666', font=('Yu Gothic UI', 9, 'bold'))
        self.status_label.pack(side='left')

        # 操作ボタン
        btn_frame = ttk.LabelFrame(self.root, text='操作', padding=10)
        btn_frame.pack(fill='x', padx=10, pady=4)

        btn_row = tk.Frame(btn_frame)
        btn_row.pack()
        self.btn_install = ttk.Button(btn_row, text='✅ 日本語化を適用',
                                       command=self._do_install, width=22)
        self.btn_install.pack(side='left', padx=4)
        self.btn_uninstall = ttk.Button(btn_row, text='⏪ 元に戻す',
                                         command=self._do_uninstall, width=16)
        self.btn_uninstall.pack(side='left', padx=4)
        self.btn_verify = ttk.Button(btn_row, text='🔍 検証のみ (dry-run)',
                                      command=self._do_verify, width=22)
        self.btn_verify.pack(side='left', padx=4)

        # 進行状況
        self.progress = ttk.Progressbar(btn_frame, mode='indeterminate', length=400)
        self.progress.pack(pady=(8, 0))

        # ログ
        log_frame = ttk.LabelFrame(self.root, text='ログ', padding=6)
        log_frame.pack(fill='both', expand=True, padx=10, pady=8)

        self.log_text = scrolledtext.ScrolledText(log_frame, wrap='word',
                                                   font=('Consolas', 9),
                                                   bg='#1e1e1e', fg='#d4d4d4',
                                                   insertbackground='white',
                                                   height=15)
        self.log_text.pack(fill='both', expand=True)
        self.log_text.configure(state='disabled')

        log_btn_row = tk.Frame(log_frame)
        log_btn_row.pack(fill='x', pady=(4, 0))
        ttk.Button(log_btn_row, text='クリア', command=self._clear_log).pack(side='left', padx=2)
        ttk.Button(log_btn_row, text='ログ保存…', command=self._save_log).pack(side='left', padx=2)

        # フッタ
        footer = tk.Frame(self.root)
        footer.pack(fill='x', padx=10, pady=(0, 6))
        tk.Label(footer,
                 text='問題報告: https://github.com/hhfcurator/internet-generation-jp-hhf/issues',
                 fg='#666', font=('Yu Gothic UI', 8)).pack(side='left')

    # ---------- ゲームパス検出 ----------
    def _auto_detect(self):
        p = patcher.find_game()
        if p:
            self.game_path.set(str(p))
            self._log(f'自動検出: {p}')
        else:
            self._log('自動検出失敗。「参照」ボタンで手動指定してください。')
        self._refresh_status()

    def _browse(self):
        d = filedialog.askdirectory(
            title='Internet Generation のインストール先フォルダを選択',
            mustexist=True,
        )
        if d:
            self.game_path.set(d)
            self._refresh_status()

    def _refresh_status(self):
        p = self.game_path.get()
        if not p:
            self._set_status('未検出', '#a00')
            return
        path = Path(p)
        if not (path / 'InternetGeneration.exe').exists():
            self._set_status('✗ InternetGeneration.exe が見つかりません', '#a00')
            return
        data_dir = path / 'InternetGeneration_Data'
        if not data_dir.exists():
            self._set_status('✗ InternetGeneration_Data フォルダなし', '#a00')
            return
        # .bak の有無
        dll_bak = data_dir / 'Managed' / 'Assembly-CSharp.dll.bak'
        if dll_bak.exists():
            self._set_status('✓ ゲーム検出済 / バックアップあり (パッチ適用後の状態の可能性)', '#080')
        else:
            self._set_status('✓ ゲーム検出済 / バックアップなし (未パッチ)', '#080')

    def _set_status(self, msg, color):
        self.status_text.set(msg)
        self.status_label.configure(fg=color)

    # ---------- ログ ----------
    def _log(self, msg):
        """スレッドセーフな log 追加。実描画は drain_log_queue で。"""
        self.log_queue.put(msg)

    def _drain_log_queue(self):
        try:
            while True:
                msg = self.log_queue.get_nowait()
                self.log_text.configure(state='normal')
                self.log_text.insert('end', str(msg) + '\n')
                self.log_text.see('end')
                self.log_text.configure(state='disabled')
        except queue.Empty:
            pass
        self.root.after(100, self._drain_log_queue)

    def _clear_log(self):
        self.log_text.configure(state='normal')
        self.log_text.delete('1.0', 'end')
        self.log_text.configure(state='disabled')

    def _save_log(self):
        f = filedialog.asksaveasfilename(
            title='ログを保存',
            defaultextension='.txt',
            filetypes=[('Text', '*.txt'), ('All', '*.*')],
            initialfile=f'igjp_install_log_{time.strftime("%Y%m%d_%H%M%S")}.txt',
        )
        if not f: return
        try:
            Path(f).write_text(self.log_text.get('1.0', 'end'), encoding='utf-8')
            messagebox.showinfo('保存', f'ログを保存しました:\n{f}')
        except OSError as e:
            messagebox.showerror('エラー', f'保存失敗: {e}')

    # ---------- 操作 ----------
    def _check_running(self):
        """ゲーム起動中なら警告 dialog。続行可否を返す。"""
        if patcher.is_game_running():
            return messagebox.askyesno(
                'ゲーム起動中',
                'Internet Generation が起動中です。\n\n'
                'このまま実行するとファイル破損の可能性があります。\n'
                'Steam から完全終了してから再試行することを強く推奨します。\n\n'
                '無視して続行しますか？',
                default='no',
            )
        return True

    def _validate_path(self):
        p = self.game_path.get()
        if not p:
            messagebox.showerror('エラー', 'ゲームインストール先を指定してください。')
            return None
        path = Path(p)
        if not (path / 'InternetGeneration.exe').exists():
            messagebox.showerror('エラー',
                f'指定先に InternetGeneration.exe が見つかりません:\n{p}')
            return None
        return path

    def _busy(self, busy):
        state = 'disabled' if busy else 'normal'
        self.btn_install.configure(state=state)
        self.btn_uninstall.configure(state=state)
        self.btn_verify.configure(state=state)
        if busy: self.progress.start(10)
        else: self.progress.stop()

    def _run_in_thread(self, fn, *args):
        if self.worker_thread and self.worker_thread.is_alive():
            messagebox.showwarning('処理中', '別の処理が実行中です。')
            return
        self._busy(True)
        def runner():
            try:
                fn(*args)
            except Exception as e:
                import traceback
                self._log('[EXCEPTION] ' + traceback.format_exc())
                self.root.after(0, lambda: messagebox.showerror('エラー', str(e)))
            finally:
                self.root.after(0, lambda: self._busy(False))
                self.root.after(0, self._refresh_status)
        self.worker_thread = threading.Thread(target=runner, daemon=True)
        self.worker_thread.start()

    def _do_install(self):
        if not self._check_running(): return
        path = self._validate_path()
        if not path: return
        self._log('\n===== 日本語化パッチ適用開始 =====')
        self._run_in_thread(self._install_worker, str(path), False)

    def _do_verify(self):
        path = self._validate_path()
        if not path: return
        self._log('\n===== 検証 (dry-run) 開始 =====')
        self._run_in_thread(self._install_worker, str(path), True)

    def _do_uninstall(self):
        if not self._check_running(): return
        path = self._validate_path()
        if not path: return
        ok = messagebox.askyesno('確認',
            'バックアップから元の状態に戻します。\n\n'
            '現在の日本語化を破棄します。よろしいですか？',
            default='no')
        if not ok: return
        self._log('\n===== アンインストール開始 =====')
        self._run_in_thread(self._uninstall_worker, str(path))

    def _install_worker(self, game_dir, dry_run):
        ok, msg = patcher.install(game_dir, dry_run=dry_run, output_fn=self._log)
        self.root.after(0, lambda: messagebox.showinfo(
            '完了' if ok else '失敗',
            ('日本語化が完了しました。\nSteam から Internet Generation を起動して確認してください。'
             if ok else f'失敗しました: {msg}\nログを確認してください。')
        ))

    def _uninstall_worker(self, game_dir):
        ok, msg = patcher.uninstall(game_dir, output_fn=self._log)
        self.root.after(0, lambda: messagebox.showinfo(
            '完了' if ok else '失敗',
            'バックアップから復元しました。' if ok else f'失敗しました: {msg}'
        ))


def main():
    root = tk.Tk()
    # アイコン (bundled icon.ico)
    icon_path = None
    if _BUNDLE:
        cand = os.path.join(_BUNDLE, 'icon.ico')
        if os.path.exists(cand): icon_path = cand
    else:
        cand = Path(__file__).resolve().parent.parent / 'icon.ico'
        if cand.exists(): icon_path = str(cand)
    if icon_path:
        try: root.iconbitmap(icon_path)
        except Exception: pass
    app = InstallerApp(root)
    root.mainloop()


if __name__ == '__main__':
    main()
