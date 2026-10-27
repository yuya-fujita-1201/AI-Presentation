manual/assets/ の画像一覧（すべて PNG。生成手順は下記コマンドをこの順に実行すれば再現できる）

type-01-title.png ... スライドタイプ title のサムネイル（640x360）。examples/template-sample を acn-slide-master テーマでビルドし、preview_deck.py の1枚目PNGを縮小したもの。
type-02-agenda.png ... スライドタイプ agenda のサムネイル（640x360）。同上、2枚目。
type-03-section.png ... スライドタイプ section のサムネイル（640x360）。同上、3枚目。
type-04-bullets.png ... スライドタイプ bullets のサムネイル（640x360）。同上、4枚目。
type-05-two_column.png ... スライドタイプ two_column のサムネイル（640x360）。同上、5枚目。
type-06-table.png ... スライドタイプ table のサムネイル（640x360）。同上、6枚目。
type-07-code.png ... スライドタイプ code のサムネイル（640x360）。同上、7枚目。
type-08-quote.png ... スライドタイプ quote のサムネイル（640x360）。同上、8枚目。
type-09-image.png ... スライドタイプ image のサムネイル（640x360）。同上、9枚目。
type-10-image_text.png ... スライドタイプ image_text のサムネイル（640x360）。同上、10枚目。
type-11-steps.png ... スライドタイプ steps のサムネイル（640x360）。同上、11枚目。
type-12-matrix.png ... スライドタイプ matrix のサムネイル（640x360）。同上、12枚目。
type-13-cards.png ... スライドタイプ cards のサムネイル（640x360）。同上、13枚目。
type-14-swimlane_legend.png ... swimlane の凡例ページ（自動挿入分） のサムネイル（640x360）。同上、14枚目。
type-15-swimlane.png ... スライドタイプ swimlane のサムネイル（640x360）。同上、15枚目。
type-16-architecture.png ... スライドタイプ architecture のサムネイル（640x360）。同上、17枚目。
type-17-dataflow.png ... スライドタイプ dataflow のサムネイル（640x360）。同上、19枚目。
type-18-lifecycle.png ... スライドタイプ lifecycle のサムネイル（640x360）。同上、21枚目。
type-19-sequence.png ... スライドタイプ sequence のサムネイル（640x360）。同上、23枚目。
type-20-schedule.png ... スライドタイプ schedule のサムネイル（640x360）。同上、24枚目。
type-21-status_table.png ... スライドタイプ status_table のサムネイル（640x360）。同上、25枚目。
type-22-closing.png ... スライドタイプ closing のサムネイル（640x360）。同上、26枚目。

生成コマンド（type-*.png の元データ。scratchpad 上で実施。2026-10-08 に schedule / status_table 追加に合わせて全数を再生成）:
  1) examples/template-sample をビルドする（meta.theme は既に acn-slide-master）
  2) python tools/build_deck.py examples/template-sample
  3) python tools/preview_deck.py examples/template-sample   （全26枚PNG化。deck.json 21枚＋swimlane 凡例1枚＋図解4タイプの凡例ページ4枚）
  4) 図解の凡例ページ（diagram_legend）4枚を除いた22枚を掲載順に Pillow で 640x360 にリサイズし type-NN-<type>.png として保存
     （NN は凡例ページを除いた掲載順 01〜22、<type> はそのページの実際のタイプ名。swimlane の凡例ページのみ swimlane_legend）

gallery.png ... 上記22枚のサムネイルを6列×4行（最終行は4枚。各セルの下にタイプ名ラベル、余白12px、枠線 #D2D2D8、背景白、ラベルは Meiryo UI Bold 19px）に並べた一覧画像（1600x764px）。Pillow の Image.paste + ImageDraw で作成。

terminal-setup.png ... 「python setup_deps.py --check」の実際の出力をターミナル風HTMLに流し込みPlaywrightでスクリーンショットしたもの（2倍解像度）。表示パスはユーザー環境を想定しWindows風（C:\Users\you\...）に置換済み、コマンド自体の出力内容（OK/未判定など）は実行結果そのまま。
terminal-build.png ... scratchpad に作った小さなデッキ decks/kickoff に対する「python build_deck.py decks/kickoff」の実際の出力をターミナル風HTMLに流し込みPlaywrightでスクリーンショットしたもの（2倍解像度、パスはWindows風に置換）。
terminal-preview.png ... 同デッキに対する「python preview_deck.py decks/kickoff 1 2」の実際の出力を同様にスクリーンショットしたもの（2倍解像度、パスはWindows風に置換）。

folder-project.png ... ユーザーのデッキフォルダ（decks/kickoff）の実際の構成（deck.json / assets/logo.png / build/kickoff.html・kickoff.pptx / build/preview/slide-01,02.png）を find で確認し、tree風テキストとしてターミナル風HTMLに書き起こしPlaywrightでスクリーンショットしたもの（2倍解像度）。
folder-plugin.png ... プラグイン本体（plugins/slide-deck）の実際のトップレベル構成（README.md / requirements.txt / USER-GUIDE.html / skills 5種 / tools 主要ファイル / templates / references / examples / manual）を find で確認し、同様にtree風テキストとして画像化したもの（2倍解像度）。tools 配下は build_deck.py / preview_deck.py / check_layout.py / check_theme.py / export_pdf.py の5個を名指しし、残りは「...(他N個)」と要約表記（2026-10-08時点で tools/*.py は合計22個なのでN=17）。references は deck-schema.md / diagram-guide.md / themes.md / content-guide.md の4個。
  【運用ルール】tools/ 配下の .py ファイルを増減させたら、このNの値も同時に見直す（`ls plugins/slide-deck/tools/*.py | wc -l` から名指し5個を引いた数）。画像の再生成は上記「生成コマンド」と同じ要領で、元HTML（テキストのみ編集）をPlaywrightで2倍解像度スクリーンショットし直す。

chat-request-image.png ... Claude Code とのやり取りの例を示すイメージ図（「来週の勉強会向けに、生成AI導入の効果を10枚で。聞き手は営業部門、目的は試験導入の承認」という依頼→確認質問→deck.json作成→ビルド→パスを返す、という流れを簡潔に表現したモックアップ。実際の応答文言そのままではなく要約した簡潔な内容。右上に「イメージ」バッジ）。チャット風HTMLを自作しPlaywrightでスクリーンショット（2倍解像度）。

共通事項:
- すべて Pillow で最終的にリサイズ・最適化済み（サムネイルは640x360固定、その他は横1600px以下にクランプ）。
- 合計サイズは約2.2MB（3MB以内の目安を満たす）。
- 生成後、Read で全画像を目視し文字が読めることを確認済み。
