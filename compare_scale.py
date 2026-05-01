"""
PDF scale 比較工具
用途：把同一頁 PDF 分別以 scale 1.0 / 1.5 / 2.0 轉成 JPG，存到桌面讓你比較清晰度
使用方式：在 Anaconda Prompt 執行
    python compare_scale.py "你的PDF路徑"
"""
import sys
import os

try:
    import fitz  # pymupdf
except ImportError:
    print("安裝 pymupdf 中...")
    os.system("pip install pymupdf --break-system-packages -q")
    import fitz

if len(sys.argv) < 2:
    print("用法：python compare_scale.py \"PDF路徑\"")
    sys.exit(1)

pdf_path = sys.argv[1]
desktop = os.path.join(os.path.expanduser("~"), "Desktop")
out_dir = os.path.join(desktop, "pk_scale_compare")
os.makedirs(out_dir, exist_ok=True)

doc = fitz.open(pdf_path)
page = doc[0]

results = []
for scale in [1.0, 1.5, 2.0]:
    mat = fitz.Matrix(scale, scale)
    pix = page.get_pixmap(matrix=mat)
    fname = f"scale_{str(scale).replace('.','_')}.jpg"
    out_path = os.path.join(out_dir, fname)
    pix.save(out_path, jpg_quality=88)
    size_kb = os.path.getsize(out_path) // 1024
    results.append((scale, pix.width, pix.height, size_kb, out_path))
    print(f"scale {scale:3.1f}：{pix.width}x{pix.height} px，{size_kb} KB → {fname}")

doc.close()
print(f"\n三張圖已存到：{out_dir}")
print("請用圖片檢視器比較清晰度！")
