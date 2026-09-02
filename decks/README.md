# decks — デッキ一覧

1デッキ = 1フォルダ。トップ階層にはそのまま使うデッキだけを表示順で置きます。フォルダ名先頭の2桁が並び順です。

## 収録デッキ

| 順番 | フォルダ | 内容 | 生成物ID |
|---:|---|---|---|
| 10 | [`10-template-sample/`](10-template-sample/) | 全スライドタイプの見本（新規デッキの雛形） | `template-sample` |

`deck.json` の `meta.id` は HTML / PPTX の生成物名として使うため、フォルダ整理では変更しません。

## 新しいデッキを作るには

1. `10-template-sample/` をコピーして `decks/NN-<slug>/` を作る（`NN` は表示順の2桁）
2. `deck.json` の `meta`（`id` / `title` など）と `slides` を書き換える
3. `python tools/build_deck.py decks/NN-<slug>` でビルド、`preview_deck.py` で目視確認

スキーマの詳細は [`docs/deck-schema.md`](../docs/deck-schema.md) を参照。

## 命名ルール

- トップ階層: そのまま使うデッキだけ。`NN-slug` 形式で表示順を固定する
- `build/` 配下は生成物（HTML / PPTX / PNG）。直接編集せず、deck.json を直して再ビルドする（Git 管理外）
