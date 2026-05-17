"""
PDF 左半保留工具
功能：選定資料夾後，將資料夾內所有 PDF 每頁只保留左半邊，覆蓋存檔
依賴：pikepdf（pip install pikepdf）
執行：python pdf_crop_left.py
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import threading

try:
    import pikepdf
except ImportError:
    import tkinter as tk
    root = tk.Tk()
    root.withdraw()
    tk.messagebox.showerror(
        "缺少套件",
        "請先安裝 pikepdf：\n\npip install pikepdf\n\n安裝後重新執行本程式。"
    )
    raise SystemExit


# ── 核心處理函式 ──────────────────────────────────────────────

def crop_left_half(filepath: str) -> None:
    """將 PDF 每頁的 cropbox 設為左半邊（覆蓋原檔）"""
    with pikepdf.open(filepath, allow_overwriting_input=True) as pdf:
        for page in pdf.pages:
            mb = page.mediabox
            x0 = float(mb[0])
            y0 = float(mb[1])
            x1 = float(mb[2])
            y1 = float(mb[3])
            mid_x = round((x0 + x1) / 2.0, 2)
            # 設定 CropBox 為左半邊（直接傳數字，pikepdf 自動轉換）
            page.cropbox = pikepdf.Array([x0, y0, mid_x, y1])
        pdf.save(filepath)


def find_pdfs(folder: str) -> list[str]:
    """找出資料夾內所有 PDF（不遞迴）"""
    return sorted([
        os.path.join(folder, f)
        for f in os.listdir(folder)
        if f.lower().endswith(".pdf")
    ])


# ── GUI ──────────────────────────────────────────────────────

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("PDF 左半保留工具")
        self.resizable(False, False)
        self.configure(padx=20, pady=16)

        self.folder_var = tk.StringVar(value="（尚未選擇資料夾）")
        self.status_var = tk.StringVar(value="請先選擇資料夾")
        self.pdf_files: list[str] = []

        self._build_ui()

    # ── UI 建構 ──

    def _build_ui(self):
        # 標題
        tk.Label(self, text="PDF 左半保留工具", font=("", 14, "bold")).grid(
            row=0, column=0, columnspan=2, pady=(0, 12), sticky="w"
        )

        # 選資料夾
        tk.Label(self, text="目標資料夾：").grid(row=1, column=0, sticky="w")
        folder_frame = tk.Frame(self)
        folder_frame.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(2, 10))

        self.folder_label = tk.Label(
            folder_frame, textvariable=self.folder_var,
            width=52, anchor="w", relief="sunken", bg="#f5f5f5", padx=4
        )
        self.folder_label.pack(side="left", fill="x", expand=True)
        tk.Button(
            folder_frame, text="選擇資料夾…", command=self._select_folder
        ).pack(side="left", padx=(6, 0))

        # 檔案清單
        tk.Label(self, text="找到的 PDF：").grid(row=3, column=0, sticky="w")

        list_frame = tk.Frame(self, bd=1, relief="sunken")
        list_frame.grid(row=4, column=0, columnspan=2, sticky="nsew", pady=(2, 10))

        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side="right", fill="y")

        self.listbox = tk.Listbox(
            list_frame, height=10, width=60,
            yscrollcommand=scrollbar.set, selectmode="browse",
            font=("Courier", 10)
        )
        self.listbox.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self.listbox.yview)

        # 進度條
        self.progress = ttk.Progressbar(self, length=480, mode="determinate")
        self.progress.grid(row=5, column=0, columnspan=2, sticky="ew", pady=(0, 6))

        # 狀態文字
        tk.Label(self, textvariable=self.status_var, anchor="w", fg="#444").grid(
            row=6, column=0, columnspan=2, sticky="w", pady=(0, 10)
        )

        # 按鈕區
        btn_frame = tk.Frame(self)
        btn_frame.grid(row=7, column=0, columnspan=2, sticky="e")

        self.btn_start = tk.Button(
            btn_frame, text="✂ 開始處理（覆蓋原檔）",
            font=("", 11, "bold"), bg="#d9534f", fg="white",
            padx=12, pady=4,
            command=self._start_processing,
            state="disabled"
        )
        self.btn_start.pack(side="right")

        tk.Button(
            btn_frame, text="重新選擇",
            padx=8, pady=4,
            command=self._select_folder
        ).pack(side="right", padx=(0, 8))

    # ── 事件處理 ──

    def _select_folder(self):
        folder = filedialog.askdirectory(title="選擇包含 PDF 的資料夾")
        if not folder:
            return
        self.folder_var.set(folder)
        self._load_pdf_list(folder)

    def _load_pdf_list(self, folder: str):
        self.listbox.delete(0, "end")
        self.pdf_files = find_pdfs(folder)

        if not self.pdf_files:
            self.status_var.set("⚠️ 此資料夾內沒有 PDF 檔案")
            self.btn_start.config(state="disabled")
            return

        for p in self.pdf_files:
            self.listbox.insert("end", os.path.basename(p))

        self.status_var.set(f"共找到 {len(self.pdf_files)} 個 PDF，確認後按下「開始處理」")
        self.progress["value"] = 0
        self.btn_start.config(state="normal")

    def _start_processing(self):
        if not self.pdf_files:
            return

        confirm = messagebox.askyesno(
            "確認覆蓋",
            f"即將處理 {len(self.pdf_files)} 個 PDF，\n每頁只保留左半邊並「覆蓋原檔」。\n\n確定要繼續嗎？"
        )
        if not confirm:
            return

        self.btn_start.config(state="disabled")
        self.progress["maximum"] = len(self.pdf_files)
        self.progress["value"] = 0

        thread = threading.Thread(target=self._process_files, daemon=True)
        thread.start()

    def _process_files(self):
        ok_count = 0
        err_count = 0
        errors = []

        for i, filepath in enumerate(self.pdf_files):
            name = os.path.basename(filepath)
            self.status_var.set(f"處理中… ({i+1}/{len(self.pdf_files)}) {name}")
            self.update_idletasks()

            try:
                crop_left_half(filepath)
                self.listbox.itemconfig(i, fg="green")
                ok_count += 1
            except Exception as e:
                self.listbox.itemconfig(i, fg="red")
                errors.append(f"{name}：{e}")
                err_count += 1

            self.progress["value"] = i + 1
            self.update_idletasks()

        # 完成
        if err_count == 0:
            self.status_var.set(f"✅ 全部完成！共處理 {ok_count} 個檔案")
            messagebox.showinfo("完成", f"全部 {ok_count} 個 PDF 處理完成！")
        else:
            self.status_var.set(
                f"完成（{ok_count} 成功 / {err_count} 失敗）"
            )
            messagebox.showwarning(
                "部分失敗",
                f"{ok_count} 個成功，{err_count} 個失敗：\n\n" + "\n".join(errors)
            )

        self.btn_start.config(state="normal")


# ── 入口 ─────────────────────────────────────────────────────

if __name__ == "__main__":
    app = App()
    app.mainloop()
