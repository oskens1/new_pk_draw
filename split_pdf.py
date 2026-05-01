"""
split_pdf.py
將指定資料夾內的所有 PDF 切成「一頁一個 PDF」，原地儲存。
"""

import os
from pypdf import PdfReader, PdfWriter

TARGET_DIR = r"G:\我的雲端硬碟\114-1\17-畫出知識力\114-1-B班\新增資料夾"

def split_pdf(pdf_path):
    reader = PdfReader(pdf_path)
    total = len(reader.pages)
    if total <= 1:
        print(f"  {os.path.basename(pdf_path)}: 只有 1 頁，跳過")
        return

    base = os.path.splitext(pdf_path)[0]
    for i, page in enumerate(reader.pages):
        writer = PdfWriter()
        writer.add_page(page)
        out_path = f"{base}_p{i+1:02d}.pdf"
        with open(out_path, "wb") as f:
            writer.write(f)
        print(f"  建立：{os.path.basename(out_path)}")

    print(f"  完成：共切出 {total} 個 PDF")

if __name__ == "__main__":
    pdfs = [f for f in os.listdir(TARGET_DIR) if f.lower().endswith(".pdf") and "_p" not in f]
    if not pdfs:
        print("找不到 PDF 檔案。")
    else:
        for fname in pdfs:
            full_path = os.path.join(TARGET_DIR, fname)
            print(f"處理：{fname}")
            split_pdf(full_path)
    input("\n完成！按 Enter 關閉視窗...")
