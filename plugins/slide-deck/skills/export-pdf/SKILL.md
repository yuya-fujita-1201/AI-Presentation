---
name: export-pdf
description: ビルド済みの PPTX を PDF に書き出す。ユーザーが「PDFにして」「PDFで書き出して」のように配布用 PDF を求めたときに使う。LibreOffice（soffice）が必要。
allowed-tools: Bash, Read
---

# export-pdf — PPTX を PDF に書き出す

`<deck_dir>/build/<meta.id>.pptx` を PDF に変換する。まだビルドしていない場合は、先に `python "${CLAUDE_PLUGIN_ROOT}/tools/build_deck.py" <deck_dir>` でビルドする（`export_pdf.py` は既定で PPTX を最新に作り直してから変換する。作り直さないなら `--no-build`）。

## 実行
```bash
python "${CLAUDE_PLUGIN_ROOT}/tools/export_pdf.py" <deck_dir>
```
`<deck_dir>/build/<meta.id>.pdf` が生成される。内部で LibreOffice（`soffice --headless --convert-to pdf`）を呼ぶ。`soffice` は PATH → Windows の既定インストール先（例: `C:\Program Files\LibreOffice\program\soffice.exe`）→ macOS（`/Applications/LibreOffice.app/Contents/MacOS/soffice`）の順に自動で探す。

## フォントと配布前の確認

- **フォントは固定される**。テーマのフォント（Meiryo など）がこの機械に無いと、LibreOffice は変換のたびに代替フォントを変えることがあった。`export_pdf.py` は一時プロファイルでフォントの置換表を書き、PPTX が使う足りないフォントを、字幅の見積もりに使う代替フォント（例: Hiragino Sans）に固定する。`note: フォント 'Meiryo' がこの環境に無いため、PDF では 'Hiragino Sans' に置き換えて書き出します` と出たら、PDF のフォントは Meiryo ではない。何度変換しても同じフォントになる。フォントが入っている機械（Windows の Meiryo など）では何もしない。PowerPoint 実機の見え方の代わりにはならない。
- **【要確認】が残っていると PDF にも出る**（色つきの太字。下地の黄色は HTML だけ）。配る PDF なら、ビルドの `note: 要確認が N 件あります…` が 0 件になってから書き出す。残して渡すときは、件数と場所を引き渡しの報告に書く。

## LibreOffice が無い場合
`export_pdf.py` は exit 1 で終了し、代替手段を案内する。次のいずれかで代替する:
- **LibreOffice を導入する**（無償・[libreoffice.org](https://www.libreoffice.org/) からダウンロード）。導入後は追加設定なしで `export_pdf.py` が使える
- **PowerPoint / Keynote で手動書き出し**: `build/<meta.id>.pptx` を開き、「エクスポート」または「名前を付けて保存」から PDF 形式を選ぶ（Windows PowerPoint: ファイル → エクスポート → PDF/XPS の作成。Keynote: ファイル → 書き出す → PDF）
- ユーザーに `build/<meta.id>.html` を直接ブラウザで開いてもらい、ブラウザの印刷機能（1 枚 1 ページで出力される）から PDF 保存してもらう
