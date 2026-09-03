---
name: export-pdf
description: ビルド済みの PPTX を PDF に書き出す。ユーザーが「PDFにして」「PDFで書き出して」のように配布用 PDF を求めたときに使う。LibreOffice（soffice）が必要。
allowed-tools: Bash, Read
---

# export-pdf — PPTX を PDF に書き出す

`<deck_dir>/build/<meta.id>.pptx` を PDF に変換する。まだビルドしていない場合は先に `create-deck` の手順3（`build_deck.py <deck_dir>`）でビルドする。

## 実行
```bash
python "${CLAUDE_PLUGIN_ROOT}/tools/export_pdf.py" <deck_dir>
```
`<deck_dir>/build/<meta.id>.pdf` が生成される。内部で LibreOffice（`soffice --headless --convert-to pdf`）を呼ぶ。`soffice` は PATH → Windows の既定インストール先（例: `C:\Program Files\LibreOffice\program\soffice.exe`）→ macOS（`/Applications/LibreOffice.app/Contents/MacOS/soffice`）の順に自動で探す。

## LibreOffice が無い場合
`export_pdf.py` は exit 1 で終了し、代替手段を案内する。次のいずれかで代替する:
- **LibreOffice を導入する**（無償・[libreoffice.org](https://www.libreoffice.org/) からダウンロード）。導入後は追加設定なしで `export_pdf.py` が使える
- **PowerPoint / Keynote で手動書き出し**: `build/<meta.id>.pptx` を開き、「エクスポート」または「名前を付けて保存」から PDF 形式を選ぶ（Windows PowerPoint: ファイル → エクスポート → PDF/XPS の作成。Keynote: ファイル → 書き出す → PDF）
- ユーザーに `build/<meta.id>.html` を直接ブラウザで開いてもらい、ブラウザの印刷機能（1 枚 1 ページで出力される）から PDF 保存してもらう
