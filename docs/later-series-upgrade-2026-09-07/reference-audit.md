# 構成とプラグインの調査

reference_auditが読み取り確認。AI-Presentationはplugin配布repo、スライド改訂先はpresentation。

01:53枚、基本→依頼設計→直し方→日常→仕事。02:73枚、定義→基礎→応用トラシュ→事例。03:68枚、定義→実践と恩恵→応用トラシュ→事例。04:55枚7章、05:49枚6章。厳密に全5件が4章ではないが、共通は定義・仕組み・判断・失敗回復・持ち帰り。今回はユーザー指定の4章型を優先。

参考: /Users/yuyafujita/Projects/AI-Presentation/AGENTS.md, README.md, plugins/slide-deck/README.md, skills/create-deck/SKILL.md, skills/review-deck/SKILL.md, references/content-guide.md, references/diagram-guide.md（後4件はplugin配下）。

採用: 1枚1メッセージ、定義先行、比較基準、具体的な動作、図の主経路1本、意味ある矢印・境界、機械チェックと意味の独立レビュー。

保留: architecture/dataflow/lifecycle/sequenceの4typeとArchify自動配線は現在のpresentationビルダー未対応。今回レンダラ移植せず、既存image_textと構造SVG等で適用。
