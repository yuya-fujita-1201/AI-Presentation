# 出典と適用範囲

2026-09-07に一次資料を再確認。具体的な規程・判定表・手順は研修用作例であり、測定済みの導入効果ではない。

- [OWASP Prompt Injection](https://genai.owasp.org/llmrisk/llm01-prompt-injection/): 直接・間接の混入、対策を重ねる考え方と限界
- [OWASP Sensitive Information Disclosure](https://genai.owasp.org/llmrisk/llm022025-sensitive-information-disclosure/): 機密情報と入力・出力への対策
- [OWASP Excessive Agency](https://genai.owasp.org/llmrisk/llm062025-excessive-agency/): 機能・権限・自律的操作の範囲
- [Gemini CLI issue 4586](https://github.com/google-gemini/gemini-cli/issues/4586): ユーザー報告。確定した原因・診断とは扱わない

各ページの見出しを主張の対応単位とする。引用の完全転載は行っていない。

## 本文への対応

|ページ|主張または作例|根拠の扱い|
|---|---|---|
|2|この回は、情報と操作を守る設計|OWASPの情報・権限制御を基にした研修用運用案。|
|3|4章で、任せる範囲を具体化する|OWASPの情報・権限制御を基にした研修用運用案。|
|5|AIセキュリティは、情報と操作を守る対策|OWASPの情報・権限制御を基にした研修用運用案。|
|6|出張相談をAIに渡す場面|OWASPの情報・権限制御を基にした研修用運用案。|
|7|AIは、外部の文章を読んで動くことがある|OWASPの情報・権限制御を基にした研修用運用案。|
|8|出張相談で、何を守りたいか|OWASPの情報・権限制御を基にした研修用運用案。|
|9|安全の設計は、利用目的から始める|OWASPの情報・権限制御を基にした研修用運用案。|
|10|使う前・使う間・使った後をつなぐ|OWASPの情報・権限制御を基にした研修用運用案。|
|11|対策のメリットと、残る限界|OWASPの情報・権限制御を基にした研修用運用案。|
|13|相談メールに含まれる情報|OWASP Sensitive Information Disclosure。架空相談への適用案。|
|14|入力する場所の確認|OWASP Sensitive Information Disclosure。架空相談への適用案。|
|15|名前を消した後の見直し|OWASP Sensitive Information Disclosure。架空相談への適用案。|
|16|送る前に、必要な情報を選ぶ|OWASP Sensitive Information Disclosure。架空相談への適用案。|
|17|保存・共有・学習利用は、別々に確認する|OWASP Sensitive Information Disclosure。架空相談への適用案。|
|18|プロンプトインジェクション|OWASP Prompt Injection。具体的な混入文は無害な教材作例。|
|19|読む資料に混ざった指示|OWASP Prompt Injection。具体的な混入文は無害な教材作例。|
|20|直接と間接の違い|OWASP Prompt Injection。具体的な混入文は無害な教材作例。|
|21|同じ命令形でも役割が違う|OWASP Prompt Injection。具体的な混入文は無害な教材作例。|
|22|資料中の文言から、依頼の範囲を考える|OWASP Prompt Injection。具体的な混入文は無害な教材作例。|
|23|参照資料を、操作の許可へ昇格させない|OWASP Prompt Injection。具体的な混入文は無害な教材作例。|
|24|対策を組み合わせる|OWASP Prompt Injection。具体的な混入文は無害な教材作例。|
|25|一度防げても、全体の証明にはならない|OWASP Prompt Injection。具体的な混入文は無害な教材作例。|
|26|資料を区切る工夫と、権限の制御|OWASP Prompt Injection。具体的な混入文は無害な教材作例。|
|27|読む・下書きする・送る|OWASP Excessive Agency。権限と操作範囲の教材例。|
|28|最小権限は、仕事に必要な許可だけを与えること|OWASP Excessive Agency。権限と操作範囲の教材例。|
|29|プロンプトと権限制限|OWASP Excessive Agency。権限と操作範囲の教材例。|
|30|コピーと隔離には、違う役割がある|OWASP Excessive Agency。権限と操作範囲の教材例。|
|31|送信前に見える情報|OWASP Excessive Agency。権限と操作範囲の教材例。|
|32|承認後に、内容が変わらないか確認する|OWASP Excessive Agency。権限と操作範囲の教材例。|
|33|「送信しました」の確認|Anthropic 評価の解説。発言と最終状態の区別。|
|34|下書きだけを頼む依頼文|OWASP Excessive Agency。権限と操作範囲の教材例。|
|36|想定外の動作があったら、止めて確かめる|OWASPの情報・権限制御を基にした研修用運用案。|
|37|症状ごとに、最初の確認先を変える|OWASPの情報・権限制御を基にした研修用運用案。|
|38|事例：回答だけが「承認済み」に変わった|OWASP Prompt Injection。具体的な混入文は無害な教材作例。|
|39|事例：下書きのつもりが送信された|OWASP Excessive Agency。権限と操作範囲の教材例。|
|40|ファイル整理中の消失を訴えた報告|Gemini CLI issue #4586 の投稿者の報告。原因の確定診断ではない。|
|41|この報告から考える運用|OWASPの情報・権限制御を基にした研修用運用案。|
|42|再開は、原因と制限を確認してから|OWASPの情報・権限制御を基にした研修用運用案。|
|43|安全性の試験にも、期待する結果を置く|OWASPの情報・権限制御を基にした研修用運用案。|
|45|自分の職場で決めておくこと|OWASPの情報・権限制御を基にした研修用運用案。|
|46|最初の試行は、小さく確認できる仕事で|OWASPの情報・権限制御を基にした研修用運用案。|
|47|便利な接続を増やすときの確認|OWASPの情報・権限制御を基にした研修用運用案。|
|48|練習：どこが依頼の範囲外か|OWASPの情報・権限制御を基にした研修用運用案。|
|49|解答：文面の確認と送信を分ける|OWASPの情報・権限制御を基にした研修用運用案。|
|50|依頼前に埋める確認シート|OWASPの情報・権限制御を基にした研修用運用案。|
|51|練習：名前だけ消せば十分か|OWASP Sensitive Information Disclosure。架空相談への適用案。|
|52|解答：必要性と送信条件を両方見る|OWASP Sensitive Information Disclosure。架空相談への適用案。|
|55|この資料で使う用語|OWASPの情報・権限制御を基にした研修用運用案。|
|56|参照した資料|OWASPの情報・権限制御を基にした研修用運用案。|
|57|配布資料と次のテーマ|OWASPの情報・権限制御を基にした研修用運用案。|
