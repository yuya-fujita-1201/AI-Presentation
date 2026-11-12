# shape-gallery — 形（shape）の比較

同じ 7 枚のデッキを `meta.shape` だけ変えた 4 つのフォルダ（`classic` / `sharp` / `soft` / `editorial`）。角丸・罫線・影・字間・見出しの飾りの違いを見比べるための見本です。色（テーマ）は `meta.theme`（ここでは `acn-slide-master`）で別に決まり、shape とは独立しています。

```bash
python plugins/slide-deck/tools/build_deck.py plugins/slide-deck/examples/shape-gallery/soft
```

`meta.shape` は 1 つのデッキに 1 つしか持てないため、4 つを 1 つのデッキの中に並べることはできません。そのためフォルダを分けています。内容を直すときは 4 つの `deck.json` の `slides` を同じに保ってください。
