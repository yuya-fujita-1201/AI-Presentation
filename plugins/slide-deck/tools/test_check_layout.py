"""check_layout の単体テスト。

純粋関数（分類・整形）は常に、ブラウザ実測の検査（泣き別れ・小さい文字・コントラスト・線と文字・1 文字ラベルの重なり・
画像のはみ出し・clip の誤検出・data-max-lines）は Playwright と Chromium が使えるときだけ、合成した HTML で確かめる。
"""
import sys
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))
import check_layout as CL  # noqa: E402

try:
    from playwright.sync_api import sync_playwright
except ImportError:  # pragma: no cover
    sync_playwright = None

PIXEL = ("data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==")


def slide(inner: str, bg: str = "#ffffff", dtype: str = "x") -> str:
    return (f'<!doctype html><html><head><meta charset="utf-8"></head><body style="margin:0">'
            f'<section class="slide active" data-type="{dtype}" style="position:absolute;left:0;top:0;width:1280px;height:720px;'
            f'overflow:hidden;background:{bg};font-family:sans-serif">{inner}</section></body></html>')


def box(x, y, w, h, extra="", text=""):
    return f'<div style="position:absolute;left:{x}px;top:{y}px;width:{w}px;height:{h}px;{extra}">{text}</div>'


class PureTests(unittest.TestCase):
    def test_classify_hard_and_soft(self):
        report = {"slides": {"slide-01": {
            "clip": [{}], "bleed": [], "overlap": [], "lines": [], "rule": [],
            "spill": [{"over": 5}, {"over": 40}],
            "orphan": [{}, {}], "minfont": [{}], "contrast": [], "linecross": [{}]}}}
        hard, soft = CL.classify(report, spill_fail=12)
        self.assertEqual(hard, 1 + 1)           # clip と、12px を超える spill
        self.assertEqual(soft, 1 + 2 + 1 + 1)   # 12px 以下の spill、orphan×2、minfont、linecross

    def test_format_has_fix_hint(self):
        line = CL.format_item("slide-04", "orphan", {"el": "div", "text": "本文", "last": "す。", "tail": "していま", "lines": 2})
        self.assertIn("slide-04 orphan", line)
        self.assertIn("す。", line)
        self.assertIn("→", line)
        for kind, item in (("minfont", {"el": "div", "text": "x", "size": 8}),
                           ("contrast", {"el": "div", "text": "x", "ratio": 2.6, "need": 4.5, "fg": "#A100FF", "bg": "#460073", "size": 13}),
                           ("linecross", {"line": "line", "text": "x", "x": 1, "y": 2}),
                           ("bleed", {"el": "img", "text": "画像", "over": 10}),
                           ("clip", {"el": "pre", "text": "x", "over_h": 5, "over_w": 0})):
            self.assertIn("→", CL.format_item("slide-01", kind, item), msg=kind)

    def test_shape_bleed_is_collapsed_with_position(self):
        shapes = [{"el": "div.cv-s", "text": "図形", "over": 700 + i, "shape": True, "rect": [900, 100 + i, 400, 50]} for i in range(24)]
        pic = {"el": "img", "text": "画像 a.png", "over": 30}
        report = {"slides": {"slide-01": {"bleed": [pic] + shapes}}}
        lines = CL.format_report(report)
        self.assertEqual(len(lines), 1 + 3 + 1)       # 画像 1 + 図形 3 + 「ほか図形21件」
        self.assertIn("x=900,y=100,w=400,h=50", lines[1])
        self.assertIn("ほか図形21件", lines[-1])
        self.assertEqual(CL.classify(report), (25, 0))   # 不合格の件数は畳まない

    def test_orphan_fix_differs_for_table_cells(self):
        item = {"el": "td", "text": "いろはにほへと", "last": "と", "lines": 2, "tail": "へ"}
        cell = CL.format_item("slide-01", "orphan", item)
        self.assertIn("col_widths", cell)
        self.assertNotIn("本文に \\n", cell)
        para = CL.format_item("slide-01", "orphan", dict(item, el="div.lead"))
        self.assertIn("本文に \\n", para)
        self.assertIn("col_widths", CL.format_item("slide-01", "orphan", dict(item, el="th.x")))

    def test_format_report_shows_failing_spill_before_cap(self):
        small = [{"el": "div", "text": f"s{i}", "over": 3, "box_h": 40} for i in range(6)]
        big = {"el": "div", "text": "big", "over": 40, "box_h": 40}
        report = {"slides": {"slide-01": {"spill": small + [big]}}}
        self.assertEqual(CL.classify(report, spill_fail=12), (1, 6))
        lines = CL.format_report(report, cap=6, spill_fail=12)
        self.assertTrue(any("big" in ln for ln in lines), lines)
        # 警告ぶんは cap まで。不合格 1 件 + 警告 6 件 = 7 行、残りなし
        self.assertEqual(len(lines), 7)
        lines = CL.format_report(report, cap=2, spill_fail=12)
        self.assertEqual(len(lines), 4)   # 不合格 1 + 警告 2 + 「ほか4件」
        self.assertIn("ほか4件", lines[-1])

    def test_keep_mtime_if_same(self):
        import os
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "x.html"
            p.write_text("abc", encoding="utf-8")
            os.utime(p, (1000, 1000))
            snap = CL._snapshot(p)
            p.write_text("abc", encoding="utf-8")     # 同じ内容で上書き（mtime が新しくなる）
            self.assertTrue(CL._keep_mtime_if_same(p, snap))
            self.assertEqual(int(p.stat().st_mtime), 1000)
            p.write_text("abcd", encoding="utf-8")
            self.assertFalse(CL._keep_mtime_if_same(p, snap))
            self.assertNotEqual(int(p.stat().st_mtime), 1000)
            self.assertFalse(CL._keep_mtime_if_same(p, None))

    def test_format_report_caps_soft_kinds(self):
        items = [{"el": "div", "text": f"t{i}", "size": 8} for i in range(10)]
        report = {"slides": {"slide-01": {"minfont": items}}}
        lines = CL.format_report(report, cap=3)
        self.assertEqual(len(lines), 4)
        self.assertIn("ほか7件", lines[-1])
        # 不合格の種別は件数が多くても全部出す
        report = {"slides": {"slide-01": {"bleed": [{"el": "img", "text": "x", "over": 5}] * 10}}}
        self.assertEqual(len(CL.format_report(report, cap=3)), 10)


@unittest.skipIf(sync_playwright is None, "playwright が無い")
class BrowserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pw = sync_playwright().start()
        try:
            cls.browser = cls.pw.chromium.launch()
        except Exception as e:  # noqa: BLE001
            cls.pw.stop()
            raise unittest.SkipTest(f"Chromium を起動できない: {e}")
        cls.page = cls.browser.new_page(viewport={"width": 1280, "height": 720})

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.pw.stop()

    def run_html(self, html, **kw):
        self.page.set_content(html)
        CL.wait_ready(self.page)
        return CL.analyze_page(self.page, **kw)

    # --- 泣き別れ ---------------------------------------------------------------
    def test_orphan_detected_and_not_for_normal_wrap(self):
        r = self.run_html(slide(box(40, 40, 200, 200, "font-size:20px", "あ" * 21)))   # 10 字 × 2 行 + 1 字
        self.assertEqual(len(r["orphan"]), 1)
        self.assertEqual(r["orphan"][0]["last"], "あ")
        r = self.run_html(slide(box(40, 40, 200, 200, "font-size:20px", "あ" * 25)))   # 最終行 5 字
        self.assertEqual(r["orphan"], [])

    def test_orphan_ignores_br_pre_and_single_line(self):
        r = self.run_html(slide(box(40, 40, 400, 200, "font-size:20px", "短い一行目<br>二")))
        self.assertEqual(r["orphan"], [])
        r = self.run_html(slide(box(40, 40, 200, 200, "font-size:20px;white-space:pre", "あ" * 10 + "\n" + "あ")))
        self.assertEqual(r["orphan"], [])
        r = self.run_html(slide(box(40, 40, 400, 60, "font-size:20px", "ひとこと")))
        self.assertEqual(r["orphan"], [])

    # --- 小さい文字 -------------------------------------------------------------
    def test_minfont(self):
        r = self.run_html(slide(box(40, 40, 300, 30, "font-size:7px", "小さい文字") + box(40, 100, 300, 30, "font-size:12px", "普通")))
        self.assertEqual([m["text"] for m in r["minfont"]], ["小さい文字"])
        r = self.run_html(slide(box(40, 40, 300, 30, "font-size:10px", "図解の補助ラベル")))
        self.assertEqual(r["minfont"], [])

    def test_minfont_ignores_symbols(self):
        r = self.run_html(slide(box(40, 40, 30, 30, "font-size:6px", "●")))
        self.assertEqual(r["minfont"], [])

    def test_minfont_svg_uses_scaled_size(self):
        svg = ('<svg style="position:absolute;left:0;top:0" width="400" height="200" viewBox="0 0 1600 800">'
               '<text x="10" y="100" font-size="30">縮小された文字</text></svg>')   # 30 × 0.25 = 7.5px
        r = self.run_html(slide(svg))
        self.assertEqual(len(r["minfont"]), 1)
        self.assertAlmostEqual(r["minfont"][0]["size"], 7.5, places=1)

    # --- コントラスト -----------------------------------------------------------
    def test_contrast_on_sibling_box(self):
        dark = box(40, 40, 300, 60, "background:#460073")
        bad = box(50, 50, 200, 30, "color:#A100FF;font-size:16px", "STEP 1")
        good = box(50, 120, 200, 30, "color:#ffffff;font-size:16px", "白")
        r = self.run_html(slide(dark + bad + box(40, 110, 300, 60, "background:#460073") + good))
        self.assertEqual([c["text"] for c in r["contrast"]], ["STEP 1"])
        self.assertLess(r["contrast"][0]["ratio"], 3.0)

    def test_contrast_own_background_counts(self):
        r = self.run_html(slide(box(40, 40, 200, 30, "background:#460073;color:#ffffff;font-size:16px", "th のような自前の背景")))
        self.assertEqual(r["contrast"], [])
        r = self.run_html(slide(box(40, 40, 200, 30, "background:#ffffff;color:#ffffff;font-size:16px", "白地に白")))
        self.assertEqual(len(r["contrast"]), 1)

    def test_contrast_large_text_uses_lower_threshold(self):
        # #808080 on white = 3.95:1。通常文字（4.5:1）は不合格、24px 以上の大きい文字（3:1）は合格
        r = self.run_html(slide(box(40, 40, 300, 30, "color:#808080;font-size:16px", "小")
                                + box(40, 100, 500, 60, "color:#808080;font-size:40px", "大")))
        self.assertEqual([c["text"] for c in r["contrast"]], ["小"])

    def test_contrast_skips_image_background(self):
        img = f'<img src="{PIXEL}" style="position:absolute;left:0;top:0;width:600px;height:300px">'
        r = self.run_html(slide(img + box(40, 40, 300, 30, "color:#cccccc;font-size:16px", "画像の上の文字")))
        self.assertEqual(r["contrast"], [])

    # --- 線と文字 ---------------------------------------------------------------
    def test_linecross_svg_line_through_text(self):
        svg = ('<svg style="position:absolute;left:0;top:0" width="400" height="200">'
               '<line x1="100" y1="0" x2="100" y2="200" stroke="#000" stroke-width="1"/></svg>')
        text = box(60, 80, 120, 24, "font-size:16px", "貫通される文字")
        r = self.run_html(slide(svg + text))
        self.assertEqual(len(r["linecross"]), 1)
        # 離れていれば出ない
        svg2 = svg.replace('x1="100"', 'x1="300"').replace('x2="100"', 'x2="300"')
        self.assertEqual(self.run_html(slide(svg2 + text))["linecross"], [])

    def test_linecross_not_when_label_has_opaque_background(self):
        svg = ('<svg style="position:absolute;left:0;top:0" width="400" height="200">'
               '<line x1="100" y1="0" x2="100" y2="200" stroke="#000" stroke-width="1"/></svg>')
        label = box(60, 80, 120, 24, "font-size:16px;background:#ffffff", "背景つきラベル")
        self.assertEqual(self.run_html(slide(svg + label))["linecross"], [])

    def test_linecross_html_border_through_text(self):
        frame = box(100, 100, 200, 100, "border:2px solid #000;border-radius:40px")
        text = box(80, 120, 60, 20, "font-size:14px", "01番号")      # 枠の左辺をまたぐ
        r = self.run_html(slide(frame + text))
        self.assertEqual(len(r["linecross"]), 1)
        inside = box(130, 130, 100, 20, "font-size:14px", "枠の内側")
        self.assertEqual(self.run_html(slide(frame + inside))["linecross"], [])

    # --- 重なり（1 文字ラベル） ----------------------------------------------------
    def test_overlap_single_letter_label(self):
        r = self.run_html(slide(box(100, 100, 200, 30, "font-size:16px", "自力復旧可?") + box(150, 105, 20, 20, "font-size:16px", "N")))
        self.assertEqual(len(r["overlap"]), 1)
        # 記号だけの飾り（引用符・●）は従来どおり対象外
        r = self.run_html(slide(box(100, 100, 200, 30, "font-size:16px", "自力復旧可?") + box(150, 105, 20, 20, "font-size:16px", "●")))
        self.assertEqual(r["overlap"], [])

    # --- はみ出し -----------------------------------------------------------------
    def test_image_bleed(self):
        out = f'<img src="{PIXEL}" style="position:absolute;left:1200px;top:600px;width:200px;height:200px">'
        r = self.run_html(slide(out))
        self.assertEqual(len(r["bleed"]), 1)
        inside = f'<img src="{PIXEL}" style="position:absolute;left:100px;top:100px;width:200px;height:200px">'
        self.assertEqual(self.run_html(slide(inside))["bleed"], [])
        full = f'<img src="{PIXEL}" style="position:absolute;left:0;top:0;width:1280px;height:720px">'
        self.assertEqual(self.run_html(slide(full))["bleed"], [])

    def test_image_covering_caption_and_footer_text(self):
        cap = box(100, 560, 600, 30, "font-size:16px", "図1 キャプションの文")
        foot = box(40, 685, 200, 20, "font-size:12px", "1 / 1")
        img = f'<img src="{PIXEL}" style="position:absolute;left:0;top:520px;width:600px;height:190px">'
        r = self.run_html(slide(cap + foot + img))   # 画像が後ろから描かれる文字を覆う
        covered = [o for o in r["overlap"] if o.get("cover")]
        self.assertEqual(len(covered), 2, r["overlap"])
        self.assertTrue(all(o["cover"] == "partial" or o["cover"] == "covered" for o in covered))
        self.assertIn("data-qa-ignore", CL.format_item("slide-01", "overlap", covered[0]))
        self.assertEqual({o["cover"] for o in covered}, {"covered"})
        self.assertIn("手前から覆っている", CL.format_item("slide-01", "overlap", covered[0]))

    def test_image_edge_overlapping_text_on_top_is_partial(self):
        # 実デッキの image スライド: 画像の端がキャプションの途中にかかり、文字は画像の手前に描かれる
        img = f'<img src="{PIXEL}" style="position:absolute;left:546px;top:520px;width:190px;height:190px">'
        cap = box(72, 644, 1136, 28, "font-size:15px;text-align:center", "写真・イラストなどの画像を全幅で大きく配置する長いキャプションの文章")
        r = self.run_html(slide(img + cap))
        self.assertEqual([o["cover"] for o in r["overlap"]], ["partial"])
        self.assertIn("端に文字がかかっている", CL.format_item("slide-01", "overlap", r["overlap"][0]))

    def test_object_fit_contain_uses_painted_rect(self):
        # 箱は 1136 幅でも、1:1 の画像は中央の 190px にだけ描かれる。キャプションが画像の絵の外側なら重なっていない
        img = f'<img src="{PIXEL}" style="position:absolute;left:72px;top:520px;width:1136px;height:190px;object-fit:contain">'
        cap = box(72, 520, 300, 28, "font-size:15px", "左端のキャプション")
        self.assertEqual(self.run_html(slide(img + cap))["overlap"], [])

    def test_text_inside_image_or_on_background_image_is_not_cover(self):
        inner = f'<img src="{PIXEL}" style="position:absolute;left:100px;top:300px;width:400px;height:200px">'
        title = box(120, 320, 300, 30, "font-size:16px", "写真の中に収まる文字")
        self.assertEqual(self.run_html(slide(inner + title))["overlap"], [])

    def test_text_on_top_of_image_is_not_cover(self):
        img = f'<img src="{PIXEL}" style="position:absolute;left:0;top:0;width:1280px;height:720px">'
        cap = box(100, 560, 600, 30, "font-size:16px", "画像の上の文字")
        self.assertEqual(self.run_html(slide(img + cap))["overlap"], [])
        # 画像が文字より手前でも、重ならなければ検出しない
        far = box(100, 20, 300, 30, "font-size:16px", "上の見出し")
        img2 = f'<img src="{PIXEL}" style="position:absolute;left:100px;top:200px;width:300px;height:200px">'
        self.assertEqual(self.run_html(slide(far + img2))["overlap"], [])

    def test_multiline_text_over_image_is_not_cover(self):
        # 複数行の inline の文字は、外接矩形の中心が行末の空白に当たる。そこで文字が拾えなくても、行ごとの矩形で判定して誤検出しない
        img = f'<img src="{PIXEL}" style="position:absolute;left:0;top:0;width:560px;height:720px">'
        txt = ('<div style="position:absolute;left:56px;top:300px;width:300px;font-size:30px;line-height:1.25">'
               '<span>あいうえおかきくけこさしす</span></div>')       # 10 字 + 2 字の 2 行（最終行が短く、外接矩形の中心は空白）
        self.assertEqual(self.run_html(slide(img + txt))["overlap"], [])
        # 画像が文字より手前なら、複数行でも「覆っている」と検出する
        img_front = f'<img src="{PIXEL}" style="position:absolute;left:0;top:0;width:560px;height:720px">'
        self.assertEqual(len([o for o in self.run_html(slide(txt + img_front))["overlap"] if o.get("cover") == "covered"]), 1)

    def test_qa_ignore_overlap_skips_cover(self):
        cap = box(100, 560, 600, 30, "font-size:16px", "合成スライドの文字")
        img = f'<img data-qa-ignore="overlap" src="{PIXEL}" style="position:absolute;left:0;top:520px;width:600px;height:190px">'
        self.assertEqual(self.run_html(slide(cap + img))["overlap"], [])

    def test_opaque_shape_covering_text(self):
        txt = box(100, 100, 300, 30, "font-size:16px", "隠れる文字")
        shape = box(90, 90, 400, 60, "background:#333")
        self.assertEqual(len([o for o in self.run_html(slide(txt + shape))["overlap"] if o.get("cover")]), 1)
        # 塗りが背面（文字が手前）ならよい
        self.assertEqual(self.run_html(slide(shape + txt))["overlap"], [])

    def test_shape_bleed_detected_in_browser_with_rect(self):
        shape = box(900, 100, 700, 50, "background:#333")
        r = self.run_html(slide(shape))
        self.assertEqual(len(r["bleed"]), 1)
        self.assertTrue(r["bleed"][0]["shape"])
        self.assertEqual(r["bleed"][0]["rect"], [900, 100, 700, 50])

    def test_image_bleed_skipped_on_canvas(self):
        out = f'<img src="{PIXEL}" style="position:absolute;left:1200px;top:600px;width:200px;height:200px">'
        self.assertEqual(self.run_html(slide(out, dtype="canvas"))["bleed"], [])

    def test_clip_ignores_padding_only_overflow(self):
        # 文字は箱に収まっているが、下の padding 分だけ scrollHeight が超える箱は切れていない
        fits = box(40, 40, 300, 60, "overflow:hidden;padding-bottom:20px;box-sizing:border-box;font-size:16px;line-height:1.2", "一行だけ")
        self.assertEqual(self.run_html(slide(fits))["clip"], [])
        cut = box(40, 40, 120, 40, "overflow:hidden;font-size:16px;line-height:1.5", "とても長い文章がここに入っていて箱の高さを大きく超えてしまう" * 2)
        self.assertEqual(len(self.run_html(slide(cut))["clip"]), 1)

    def test_qa_ignore_attribute(self):
        a = box(100, 100, 200, 30, "font-size:16px", "自力復旧可?")
        b = box(150, 105, 20, 20, "font-size:16px", "N").replace("style=", 'data-qa-ignore="overlap" style=', 1)
        self.assertEqual(self.run_html(slide(a + b))["overlap"], [])
        c = box(40, 40, 300, 30, "font-size:7px", "小さい").replace("style=", 'data-qa-ignore="minfont" style=', 1)
        self.assertEqual(self.run_html(slide(c))["minfont"], [])

    # --- data-max-lines -----------------------------------------------------------
    def test_max_lines_attribute(self):
        two = box(40, 40, 200, 100, "font-size:20px;line-height:24px", "あ" * 15)   # 10 字 × 2 行
        two = two.replace('style=', 'data-max-lines="1" style=', 1)
        r = self.run_html(slide(two))
        self.assertEqual(len(r["lines"]), 1)
        self.assertEqual(r["lines"][0]["max"], 1)
        self.assertEqual(r["lines"][0]["lines"], 2)

    def test_max_lines_ignores_fixed_box_height(self):
        # 高さ固定の箱（style.height）でも、1 行の文字は 1 行と数える（箱の高さ ÷ 行高ではない）
        for extra in ("height:100px;font-size:20px;line-height:24px",
                      "height:60px;padding:10px;box-sizing:border-box;font-size:20px;line-height:24px"):
            one = box(40, 40, 300, 100, extra, "一行だけ").replace("style=", 'data-max-lines="1" style=', 1)
            self.assertEqual(self.run_html(slide(one))["lines"], [], msg=extra)
        ok2 = box(40, 40, 200, 100, "font-size:20px;line-height:24px", "あ" * 15).replace("style=", 'data-max-lines="2" style=', 1)
        self.assertEqual(self.run_html(slide(ok2))["lines"], [])
        # 子要素に分かれた文字（見出し＋補足）も行ごとに数える
        multi = box(40, 40, 300, 100, "font-size:20px;line-height:24px", "<p style='margin:0'>一行目</p><p style='margin:0'>二行目</p>")
        multi = multi.replace("style=", 'data-max-lines="1" style=', 1)
        self.assertEqual(self.run_html(slide(multi))["lines"][0]["lines"], 2)

    def test_qa_ignore_lines(self):
        two = box(40, 40, 200, 100, "font-size:20px;line-height:24px", "あ" * 15)
        two = two.replace('style=', 'data-max-lines="1" data-qa-ignore="lines" style=', 1)
        self.assertEqual(self.run_html(slide(two))["lines"], [])


if __name__ == "__main__":
    unittest.main()
