# 独立レビュー B 最終版 — 2026-09-08

自身が制作していない6件をrubric.mdの項目1〜6で再レビューした。deck.jsonの全ページ本文と全contact画像を実際に読み、初回review-b.mdの指摘と照合した。制作ログ、制作意図、他のgraderの採点は参照していない。枚数自体は品質として評価しない。機械ゲートは採点外。

初回13件（中12・小1）は修正確認済み。再レビュー中に見つけた08の付録案内の不整合（項目4・小1）も修正後の実物で解消確認。最終時点で項目1〜6の残存findingsはない。定義欠落・指定章欠落・本文から確認できる重大な誤情報は検出しなかった。これは本範囲の独立内容レビュー結果であり、実際のPowerPoint／Keynote表示と学習者試験は未確認。外部URLを再取得する独立ファクトチェックは実施しておらず、項目6は主張の条件・一次資料の提示・内部整合を審査した。

## ソースと描画の対応

全6件で各ページのPNG更新時刻がdeck.jsonおよびそのページの参照画像以後であること、contact更新時刻が全PNG以後であることを確認した。修正箇所の本文・図は実見した描画と一致。08の追加修正後は63枚版の全11contactを再度開いた。Toolsはp22参照SVGの更新後の当該PNGとcontactが対象。他ページに依存しない画像変更を全ページの古さとは扱わず、ページ別の依存関係で照合した。以下のSHAは最終記録時点の実ファイルから取得。

## 06-rag-expanded

- deck SHA-256: `cc661f31d5f52bd141ddad02cccdaacd500dafd28d1b797c71721920fad9b7b9`
- 全文確認：p1–57。
- verification.jsonのdeck SHA・枚数対応：True。

### 前回指摘の修正確認

- B06-1（項目6・中5）：p32を「交通費の利用日」に統一。利用条件と確認する日が一致。
- B06-2（項目5・中5）：p25は資料・検索と受け渡し・生成の実工程を図示し、照合する記録との対応を確認。
- B06-3（項目3・中5）：p31で取得内容、入力に渡った内容、実際の回答、直す点を記入済みの表にし、休日条件が落ちた箇所を判断できる。

### 残存findings

なし（項目1〜6。大20／中5／小1の残存指摘なし）。

### 本文だけで答える中核概念プローブ

- RAG：質問に関係する資料を検索し、その内容を使って回答を生成する仕組み（p5）。
- 埋め込みモデル：文章を、似た意味の資料を探すための数値ベクトルへ変換するモデル（p16）。
- リランキング：検索で得た候補を再評価して並べ替える処理で、検索されていない資料を取り戻す処理ではない（p19）。

### 実見画像一覧とSHA-256

- `decks/06-rag-expanded/build/contact/sheet-01-06.png` — `fbb6d2ca9c67d26473db0c46fa0618a7b03f3b7397bfb56c5026784774adc416`
- `decks/06-rag-expanded/build/contact/sheet-07-12.png` — `0396e04d7ed000af3676de9b949441e06347f6a4ceeb62ffa5cc1d17c3827cfd`
- `decks/06-rag-expanded/build/contact/sheet-13-18.png` — `7382a7666386c504d12bd8b309056e0df83e26a2ccd254819b6cad8b318c4298`
- `decks/06-rag-expanded/build/contact/sheet-19-24.png` — `3448c40a575b0f5c904c0aabcddd321d1f9e4ade09b555dbb5cd77fff06c7c7a`
- `decks/06-rag-expanded/build/contact/sheet-25-30.png` — `59acac6f79704ebe9fb25bd0fbeffa9f1abde9d9f0d58661c7d78ad5050c4527`
- `decks/06-rag-expanded/build/contact/sheet-31-36.png` — `e953e541a781ef78f9d1d97947ed3a03112d4dac26f062faa65370bdd1187669`
- `decks/06-rag-expanded/build/contact/sheet-37-42.png` — `678211c58dd42a0c0856d05715f7410a530ce7ba496e91cb99f4913af85a04b4`
- `decks/06-rag-expanded/build/contact/sheet-43-48.png` — `a20acd75a18dd236a646322834a543d55bfd0d5ab0ac3bb724a90041e46cb37e`
- `decks/06-rag-expanded/build/contact/sheet-49-54.png` — `bd8939c7ed770646a1790ca58bbba372ca8667c0b73b5333d9cde961cc7a0f2b`
- `decks/06-rag-expanded/build/contact/sheet-55-57.png` — `783063bdbad7505f203ef6b5bc6523e8ea831814a5085446a3a625fddf9ef4ea`
- 追加の個別実見：`decks/06-rag-expanded/build/preview/slide-34.png`。パンチライン末尾「ことがあります。」まで表示を確認。

## 07-okf-expanded

- deck SHA-256: `e4d82591ed875c48a7c3a5a9874cbef73763cb825e18090d1682aa8e87fd5963`
- 全文確認：p1–55。
- verification.jsonのdeck SHA・枚数対応：True。

### 前回指摘の修正確認

- B07-1（項目5・中5）：p9はバンドルの枠内へ目次・知識ファイル・変更履歴を配置。包含関係と参照の経路を識別できる。
- B07-2（項目4・中5）：p20はまとめる／分ける判断を各行で明示し、列と理由の逆転を解消。

### 残存findings

なし（項目1〜6。大20／中5／小1の残存指摘なし）。

### 本文だけで答える中核概念プローブ

- OKF：知識を一定の書式で記録して、人とAIが参照しやすくするための共通形式（p5）。
- 知識ファイル：用途を示す説明、答えとなる本文、確認元の参照先を持つ一件の知識の記録（p8）。
- バンドル：関連する知識ファイルをフォルダ一式としてまとめたもの（p9）。

### 実見画像一覧とSHA-256

- `decks/07-okf-expanded/build/contact/sheet-01-06.png` — `0510afb09f2c69432f30e44df237db58be36328ed7a7500c426fbe640827e3b0`
- `decks/07-okf-expanded/build/contact/sheet-07-12.png` — `fd17bac8b8ad89d65d90416699ba9762f2361f57fdb33ae7d4c18e916893e7c5`
- `decks/07-okf-expanded/build/contact/sheet-13-18.png` — `dc25ad0a000656af5573800c5df36ea26ac9dbccfe272b8edb1a3d89c6bb06d7`
- `decks/07-okf-expanded/build/contact/sheet-19-24.png` — `9f67b06f0e7c06d1677391ef9939236898f46521259458d1b5dee0928026e9f1`
- `decks/07-okf-expanded/build/contact/sheet-25-30.png` — `acaccaaf34d006835de06a89787227bfe216577b23771f40cebb36e654610373`
- `decks/07-okf-expanded/build/contact/sheet-31-36.png` — `9958853b1bf24821b0db88ff2f73224fd4678ba1357deda839f3cce8065ed960`
- `decks/07-okf-expanded/build/contact/sheet-37-42.png` — `519bb019616bd7610ce7b13889bc000b0f9f3c2ede347b24f8a4a0377e176629`
- `decks/07-okf-expanded/build/contact/sheet-43-48.png` — `dcde5d63bdcc7dfa049f8dbfeadc30e730b826f2f3b3e8c94124c7154070dc71`
- `decks/07-okf-expanded/build/contact/sheet-49-54.png` — `2e77cb90905c54901bdf205ec0e044e2297e94cbebf7c3769ba27d83ead485ff`
- `decks/07-okf-expanded/build/contact/sheet-55-55.png` — `adad3719fa3ca9897ef3f830253bae5a4ef44d39e46423fc9d930689175c1f6b`

## 08-okf-practice-expanded

- deck SHA-256: `29c61c32aa585bf25293bd876b0b0be366697c75ee939a50bf17d3bd6e5bf144`
- 全文確認：p1–63。
- verification.jsonのdeck SHA・枚数対応：True。

### 前回指摘の修正確認

- B08-1（項目6・中5）：p28に「上書き前にコミットした版は、Git履歴から確認できる」「保存だけではGit履歴に残らない」。前提条件を説明。
- B08-2（項目4・中5）：p55「合意した変更を要件と決定記録に反映する。未合意案は別に残す」で演習と結論が一致。
- B08-3（項目3・中5）：p38で数量1／0／在庫超過のAI案を要件と照合し、正当な期待値・誤り・根拠のない案を区別。
- 再レビュー追加B08-F1（項目4・小1）：p58が存在しなくなった依頼文⑥を本編へ案内していた。修正後はp59に実文を保持し、p58の案内も「付録：依頼文⑥」へ更新。p58–63の本文・画像とページ番号を再照合し解消を確認。

### 残存findings

なし（項目1〜6。大20／中5／小1の残存指摘なし）。

### 本文だけで答える中核概念プローブ

- OKF：知識を人とAIが参照できる共通形式で記録するための書式（p6）。
- 要件：システムが満たすべき振る舞いや条件の記録（p8）。
- 決定記録：現在の要件とは分けて、変更を決めた理由・時点・関係者を残す記録（p9、具体化p28）。

### 実見画像一覧とSHA-256

- `decks/08-okf-practice-expanded/build/contact/sheet-01-06.png` — `8796460fe42a365dad6d2f6cfa5146c816e12b61c2f7e7a1f8d760b81f0b29f6`
- `decks/08-okf-practice-expanded/build/contact/sheet-07-12.png` — `cb26791783d194cfe7f6c1fe05ef033fa8d98ad30981528b8a1aebace53cf173`
- `decks/08-okf-practice-expanded/build/contact/sheet-13-18.png` — `466587db5c8478b08bbfca6493fa3e1189e1a006c4934e78dabdc2c4f496c09d`
- `decks/08-okf-practice-expanded/build/contact/sheet-19-24.png` — `83f4116b0b4bce569242c7eba986887892b397297be46efed0679952e66b136d`
- `decks/08-okf-practice-expanded/build/contact/sheet-25-30.png` — `36f134c734d5a44ea3af5fe0fe8ffebc59ae5773ed0ff833560dbb5b3a7730e4`
- `decks/08-okf-practice-expanded/build/contact/sheet-31-36.png` — `1558de7722973e040607cb7a22c0ae0331dd58910dd1b4ff25f5e0ddde755bce`
- `decks/08-okf-practice-expanded/build/contact/sheet-37-42.png` — `0f8985278404dc21461c59c88b2f692c30037d49858bb7baab802fe73927bd29`
- `decks/08-okf-practice-expanded/build/contact/sheet-43-48.png` — `08f708e9a729a5350c959500167346d22032fe7640c739d48b018a6285f29b14`
- `decks/08-okf-practice-expanded/build/contact/sheet-49-54.png` — `1f8a1ce56884608476834ce8a7c6ce7948fcabdf1b0458bb3ebdd83642c304da`
- `decks/08-okf-practice-expanded/build/contact/sheet-55-60.png` — `8bedd3b29ce79c1a0eba642bf2b12684166b63b41abb7950560ae6e5b8f78da0`
- `decks/08-okf-practice-expanded/build/contact/sheet-61-63.png` — `11f2c247ecf65cc3ff2b638258d7f90a12bcbd64836240b6cd35deecd411e2c4`

## skills-mcp-cli-expanded

- deck SHA-256: `29ce889826dae2b51dbd4c9e2f8f0de1ecde399d77c4de19b1eeb97f8e1f88f1`
- 全文確認：p1–52。
- verification.jsonのdeck SHA・枚数対応：True。

### 前回指摘の修正確認

- BT-1（項目4・小1）：p10を「計算や対象データが正しいとは限りません」に修正し、不必要な断定を解消。
- BT-2（項目5・中5）：現p22はHost内のClientとServerの要求／応答、売上サービスの位置を図示。検索要求／売上3件のラベルも矢印外にあり、通信方向を識別できる。

### 残存findings

なし（項目1〜6。大20／中5／小1の残存指摘なし）。

### 本文だけで答える中核概念プローブ

- Skill：再利用する指示と関連資料をまとめたフォルダ（p4）。
- MCP：AIアプリと外部の機能やデータをつなぐ通信規格（p4）。
- CLI：文字のコマンドでプログラムを操作する方法（p4）。

### 実見画像一覧とSHA-256

- `decks/skills-mcp-cli-expanded/build/contact/sheet-01-06.png` — `39b0b1117bc9b777a9b28320de9f7ddb4766c3f1db31d687dbef4072b4c15bfc`
- `decks/skills-mcp-cli-expanded/build/contact/sheet-07-12.png` — `86cf47ae1c3ac2b71c2f4bc489f16658704def4e24d6cb5841873cd4ecb0b66a`
- `decks/skills-mcp-cli-expanded/build/contact/sheet-13-18.png` — `adcdd68e7fbed1aff503257b0105313ea3eff887b6f52eea13a1fa3dc9f54694`
- `decks/skills-mcp-cli-expanded/build/contact/sheet-19-24.png` — `4ed29ed5373636fc039cd73d6032f872b393f78b43748c0f21d0349b005a9230`
- `decks/skills-mcp-cli-expanded/build/contact/sheet-25-30.png` — `2386379fac496504a1b86e272ebdb8a50e97c9410aea0d9ffcc41c416bc4224d`
- `decks/skills-mcp-cli-expanded/build/contact/sheet-31-36.png` — `c66abb7d203d3b2aa6e92b41691cfd74013a90b5feba5e1b011255f79e214cb0`
- `decks/skills-mcp-cli-expanded/build/contact/sheet-37-42.png` — `c8086d89278c39784b2f7a5897c9b585e61e895e7912f4a25dfbde250ec5bc02`
- `decks/skills-mcp-cli-expanded/build/contact/sheet-43-48.png` — `387f48a954c6dca9778881cf040f6429827a3c9558bba6d7b96bce38997addc9`
- `decks/skills-mcp-cli-expanded/build/contact/sheet-49-52.png` — `8876df4cbe12b0cadde69cebd4c0569e5ddf04b59a8f952532f43921da9b3db4`

## 09-evaluation-expanded

- deck SHA-256: `5b2ee4ad2b22805c1c7723e9f78266e2daa6f200e4c707ddd53229daa752ad04`
- 全文確認：p1–54。
- verification.jsonのdeck SHA・枚数対応：True。

### 前回指摘の修正確認

- B09-1（項目3・中5）：現p47「その他の精算条件は別途規程で確認します」で、未提示のN04を既知の根拠にしない。
- B09-2（項目3・中5）：p33で変更した指示、海外出張の前後回答と固定した基準を提示し、重大な悪化から保留する判断までつなぐ。p34の集計とも整合。

### 残存findings

なし（項目1〜6。大20／中5／小1の残存指摘なし）。

### 本文だけで答える中核概念プローブ

- 評価・Evals：AIの結果を目的に合う基準で確認し、その確認を問題と基準の組として繰り返す取り組み（p5）。
- ルーブリック：確認項目と判定基準をまとめた表（p16）。
- 回帰テスト：変更後に、以前できていたことが壊れていないか再確認すること（p48、p52）。

### 実見画像一覧とSHA-256

- `decks/09-evaluation-expanded/build/contact/sheet-01-06.png` — `d2631691fab35068e115ba505c1c7702a4adc2fbd2ec47526148cb6c5bbfc8c7`
- `decks/09-evaluation-expanded/build/contact/sheet-07-12.png` — `493b1e7c045f790bbb484a7d6830a07ec77bc5ac8c6cf598822ec44ad646ca91`
- `decks/09-evaluation-expanded/build/contact/sheet-13-18.png` — `ffb60186f6cc1319147ad58a4855ea3ef5a1e56a9f021247f375075d5536a253`
- `decks/09-evaluation-expanded/build/contact/sheet-19-24.png` — `77f62633cc31b487e64b5688e1cbafc7efcff02c5e1d46fa2aceeea82f45c943`
- `decks/09-evaluation-expanded/build/contact/sheet-25-30.png` — `d09e1eefc64585cac546bf83ee5830e1691f7f705b2abd86a0ea0af73533d968`
- `decks/09-evaluation-expanded/build/contact/sheet-31-36.png` — `538c348b9d2986d1eec6026faeadee45d5c5ee718852e339259fe56b50e53e69`
- `decks/09-evaluation-expanded/build/contact/sheet-37-42.png` — `39c84e4dab626b3e56d1591f5d8f6f9509ce4d59b8d2c65be174afccd3c5671e`
- `decks/09-evaluation-expanded/build/contact/sheet-43-48.png` — `4cb6861342a07003ae8093f0cb0b713b341df1a63dc8672796bb365c43422708`
- `decks/09-evaluation-expanded/build/contact/sheet-49-54.png` — `e4bb9c67ce879a1f8ae3f6479b31e4c8faeb2ac3ab23e6131312062e90b2c5fe`

## 10-ai-security-expanded

- deck SHA-256: `d718c34e2375696876723ba9eb903a7e2820231196f4280a47be040895cb1732`
- 全文確認：p1–57。
- verification.jsonのdeck SHA・枚数対応：True。

### 前回指摘の修正確認

- B10-1（項目5・中5）：p23の図は利用者の依頼・実際の権限→操作判断を上側、規程→回答の根拠を下側に分離。資料中の指示が操作許可へ流れる旧経路を解消。

### 残存findings

なし（項目1〜6。大20／中5／小1の残存指摘なし）。

### 本文だけで答える中核概念プローブ

- AIセキュリティ：AI利用に伴う情報漏えいや不正操作などの被害を防ぎ、抑える対策（p5）。
- プロンプトインジェクション：入力に混ざった指示がAIの本来の動作を変えてしまう問題（p18）。
- 最小権限：仕事に必要な許可だけを与える考え方（p28）。

### 実見画像一覧とSHA-256

- `decks/10-ai-security-expanded/build/contact/sheet-01-06.png` — `b75d681ba7bde92ab328c56d53e81d73327cacbd3634efd22c0ad182989269e6`
- `decks/10-ai-security-expanded/build/contact/sheet-07-12.png` — `cafbfb91bffa9bbaaf84351d59c943fcc0d42192e2271a499a7d40ac376aab91`
- `decks/10-ai-security-expanded/build/contact/sheet-13-18.png` — `697da0568311e351231e53845d9f98300527eb40f4504d77521ad68ba7c83900`
- `decks/10-ai-security-expanded/build/contact/sheet-19-24.png` — `4226ff1542255cc2ed84f3ea19be2ed5b8c77382e645c0488b3879485d1fb9a1`
- `decks/10-ai-security-expanded/build/contact/sheet-25-30.png` — `4dac4f97748f5a5352b026afa69740708eaa33a6cb573fc6360d2eb4e795761e`
- `decks/10-ai-security-expanded/build/contact/sheet-31-36.png` — `217ab29a4c53fa177652634ba30e1b7844d7dd45792e16b829e79095ec35b415`
- `decks/10-ai-security-expanded/build/contact/sheet-37-42.png` — `139e9964c26179d273315c7183392c41e2fa44f0cac454e91acb97e6a5742b10`
- `decks/10-ai-security-expanded/build/contact/sheet-43-48.png` — `1ee2189165babc49be61f2cab329d6b6300da7a066152c422c5665cdfaebb9bd`
- `decks/10-ai-security-expanded/build/contact/sheet-49-54.png` — `5d0126b66530ada88757f374af53aa27bc1bd87f50dc152250750a7c7d10abe6`
- `decks/10-ai-security-expanded/build/contact/sheet-55-57.png` — `aac56d76230d46eeba49c12716a36a4d8657006658fd6dc0c82edae8b97b8fe4`
