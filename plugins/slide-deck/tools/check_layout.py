#!/usr/bin/env python3
"""レイアウト機械ゲート: ビルド済みHTMLをPlaywrightで開き、各スライドの
  (1) clip   … overflow:hidden の箱から文字がはみ出して切れている（scrollHeight/Width > client）
  (2) bleed  … 要素がステージ（1280x720）の外に出ている
  (3) overlap… 文字を持つ要素同士の矩形が重なっている（親子関係を除く）
  (4) lines  … data-max-lines 属性を持つ要素が指定行数を超えている
  (5) spill  … 高さ指定のある文字要素で文字実体が割当高さを超えている（closing タイトル2行化など）
  (6) rule   … 文字実体が細い罫線要素と交差している
を検出して JSON/テキストで報告する。exit 1 = 検出あり。

使い方: python tools/check_layout.py <deck_dir> [--json out.json] [--slides 3 7]
HTML は build_deck.py --html の生成物を使う（無ければ自動ビルド）。
スライド番号は expand_slides() 適用後（凡例自動挿入等込み）の実際の出力枚数を基準にする。
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS_DIR = Path(__file__).resolve().parent
PY = sys.executable

sys.path.insert(0, str(TOOLS_DIR))
try:
    import build_deck  # type: ignore
except Exception:
    build_deck = None


def _fallback_setup_console():
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def _fallback_fail(msg):
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(1)


def _fallback_warn(msg):
    print(f"warning: {msg}", file=sys.stderr)


def _fallback_note(msg):
    print(f"note: {msg}", file=sys.stderr)


setup_console = getattr(build_deck, "setup_console", None) or _fallback_setup_console
fail = getattr(build_deck, "fail", None) or _fallback_fail
warn = getattr(build_deck, "warn", None) or _fallback_warn
note = getattr(build_deck, "note", None) or _fallback_note

JS = r"""
(args) => {
  const {tol, overlapMin} = args;
  const slide = document.querySelector('.slide.active');
  if (!slide) return {error: 'no active slide'};
  const stage = slide.getBoundingClientRect();
  const out = {clip: [], bleed: [], overlap: [], lines: [], spill: [], rule: []};
  const all = Array.from(slide.querySelectorAll('*'));
  const desc = (el) => (el.textContent || '').trim().replace(/\s+/g, ' ').slice(0, 40);
  const tag = (el) => el.tagName.toLowerCase() + (el.className && typeof el.className === 'string' ? '.' + el.className.split(' ')[0] : '');

  // (1) clip: overflow hidden で中身が溢れている
  for (const el of all) {
    const cs = getComputedStyle(el);
    if (cs.display === 'none' || cs.visibility === 'hidden') continue;
    if (cs.overflow === 'hidden' || cs.overflowY === 'hidden' || cs.overflowX === 'hidden') {
      const dh = el.scrollHeight - el.clientHeight;
      const dw = el.scrollWidth - el.clientWidth;
      if (dh > tol || dw > tol) {
        out.clip.push({el: tag(el), text: desc(el), over_h: dh, over_w: dw});
      }
    }
  }

  // 文字を直接持つ「葉」要素（子要素を持たない、または直下テキストがある）
  const hasOwnText = (el) => Array.from(el.childNodes).some(n => n.nodeType === 3 && n.textContent.trim());
  const textEls = all.filter(el => {
    const cs = getComputedStyle(el);
    if (cs.display === 'none' || cs.visibility === 'hidden') return false;
    return hasOwnText(el) && el.tagName !== 'SCRIPT' && el.tagName !== 'STYLE';
  });
  const deco = (el) => (el.textContent || '').trim().length <= 1; // 装飾1文字（引用符“など）
  const rects = textEls.map(el => {
    const r = el.getBoundingClientRect();
    // テキスト実体の矩形（範囲）を使う。ブロックの余白で誤検出しないため
    let tr = r;
    try {
      const range = document.createRange();
      range.selectNodeContents(el);
      const rr = range.getBoundingClientRect();
      if (rr.width > 0 && rr.height > 0) tr = rr;
    } catch (e) {}
    return {el, box: tr};
  });

  // (2) bleed: ステージ外
  for (const {el, box} of rects) {
    if (box.width === 0 || box.height === 0) continue;
    const over = Math.max(stage.left - box.left, box.right - stage.right, stage.top - box.top, box.bottom - stage.bottom);
    if (over > tol) out.bleed.push({el: tag(el), text: desc(el), over: Math.round(over)});
  }

  // (3) overlap: 互いに親子でない文字要素同士
  for (let i = 0; i < rects.length; i++) {
    for (let j = i + 1; j < rects.length; j++) {
      const a = rects[i], b = rects[j];
      if (a.el.contains(b.el) || b.el.contains(a.el)) continue;
      if (deco(a.el) || deco(b.el)) continue;
      const x = Math.min(a.box.right, b.box.right) - Math.max(a.box.left, b.box.left);
      const y = Math.min(a.box.bottom, b.box.bottom) - Math.max(a.box.top, b.box.top);
      if (x > overlapMin && y > overlapMin) {
        out.overlap.push({a: tag(a.el), a_text: desc(a.el), b: tag(b.el), b_text: desc(b.el), w: Math.round(x), h: Math.round(y)});
      }
    }
  }

  // (5) spill: 高さが明示された文字要素で、文字実体が割り当て高さを超えている（overflow visible でも検出）
  for (const {el, box} of rects) {
    if (!el.style || !el.style.height) continue;
    if (deco(el)) continue;
    const cs = getComputedStyle(el);
    if (cs.overflow === 'hidden') continue; // clip 側で検出済み
    const over = box.height - el.clientHeight;
    if (over > tol) out.spill.push({el: tag(el), text: desc(el), over: Math.round(over), box_h: el.clientHeight});
  }

  // (6) rule: 文字実体が、細い罫線要素（文字を持たない・高さまたは幅4px以下）と交差している
  const rules = all.filter(el => {
    if ((el.textContent || '').trim()) return false;
    const r = el.getBoundingClientRect();
    const cs = getComputedStyle(el);
    if (cs.display === 'none') return false;
    return (r.height > 0 && r.height <= 4 && r.width > 40) || (r.width > 0 && r.width <= 4 && r.height > 40);
  }).map(el => ({el, box: el.getBoundingClientRect()}));
  for (const {el, box} of rects) {
    for (const ru of rules) {
      if (ru.el.contains(el) || el.contains(ru.el)) continue;
      const x = Math.min(box.right, ru.box.right) - Math.max(box.left, ru.box.left);
      const y = Math.min(box.bottom, ru.box.bottom) - Math.max(box.top, ru.box.top);
      if (x > overlapMin && y > 0) out.rule.push({el: tag(el), text: desc(el), rule_y: Math.round(ru.box.top)});
    }
  }

  // (4) lines: data-lines="1" または .one-line を持つ要素の行数
  for (const el of all) {
    const want = el.getAttribute && el.getAttribute('data-max-lines');
    if (!want) continue;
    const cs = getComputedStyle(el);
    const lh = parseFloat(cs.lineHeight) || parseFloat(cs.fontSize) * 1.2;
    const n = Math.round(el.getBoundingClientRect().height / lh);
    if (n > parseInt(want)) out.lines.push({el: tag(el), text: desc(el), lines: n, max: parseInt(want)});
  }
  return out;
}
"""


def _slide_total(deck_dir: Path, deck: dict) -> int:
    """expand_slides() 適用後の実際の総枚数（build_deck が使えなければ deck.json 枚数で妥協）。"""
    if build_deck is not None:
        try:
            _, _, layout = build_deck.load_deck(deck_dir)
            expanded = build_deck.expand_slides(deck, layout)
            return len(expanded["slides"])
        except SystemExit:
            raise
        except Exception:
            pass
    return len(deck.get("slides", []))


def main():
    setup_console()
    ap = argparse.ArgumentParser()
    ap.add_argument("deck_dir")
    ap.add_argument("--json", help="結果JSONの出力先")
    ap.add_argument("--slides", nargs="*", type=int, help="対象スライド番号（省略=全部）")
    ap.add_argument("--tol", type=float, default=2.0, help="はみ出し許容px")
    ap.add_argument("--overlap-min", type=float, default=4.0, help="重なりと見なす最小px（幅・高さとも）")
    ap.add_argument("--no-build", action="store_true")
    ap.add_argument("--spill-fail", type=float, default=12.0, help="spill がこのpxを超えたら不合格（以下は警告のみ）")
    args = ap.parse_args()

    deck_dir = Path(args.deck_dir).resolve()
    deck_json = deck_dir / "deck.json"
    if not deck_json.exists():
        fail(f"{deck_json} が見つかりません")
    deck = json.loads(deck_json.read_text(encoding="utf-8-sig"))
    deck_id = deck.get("meta", {}).get("id") or deck_dir.name
    html_path = deck_dir / "build" / f"{deck_id}.html"
    if not args.no_build or not html_path.exists():
        proc = subprocess.run([PY, str(ROOT / "tools" / "build_deck.py"), str(deck_dir), "--html"],
                               cwd=ROOT, stdout=subprocess.DEVNULL)
        if proc.returncode != 0:
            fail("build_deck.py --html の実行に失敗しました（上のエラーを確認してください）")
    total = _slide_total(deck_dir, deck)
    nums = args.slides or list(range(1, total + 1))
    bad = [n for n in nums if not 1 <= n <= total]
    if bad:
        fail(f"スライド番号が範囲外です（1〜{total}。凡例ページ等の自動挿入込みの枚数）: {bad}")

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        fail(
            "Playwright が未インストールのため check_layout.py を実行できません。\n"
            "  初回セットアップ: /slide-deck:setup --playwright"
        )
    report = {"deck": str(deck_dir), "slides": {}, "summary": {"clip": 0, "bleed": 0, "overlap": 0, "lines": 0, "spill": 0, "rule": 0}}
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 720})
        url = html_path.resolve().as_uri()
        for n in nums:
            page.goto(f"{url}#{n}")
            page.reload()
            page.wait_for_timeout(150)
            res = page.evaluate(JS, {"tol": args.tol, "overlapMin": args.overlap_min})
            if any(res.get(k) for k in ("clip", "bleed", "overlap", "lines", "spill", "rule")):
                report["slides"][f"slide-{n:02d}"] = res
                for k in report["summary"]:
                    report["summary"][k] += len(res.get(k, []))
        browser.close()

    if args.json:
        Path(args.json).write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    s = report["summary"]
    for sid, res in report["slides"].items():
        for kind in ("clip", "bleed", "overlap", "lines", "spill", "rule"):
            for item in res.get(kind, []):
                if kind == "overlap":
                    print(f"{sid} {kind}: [{item['a']}]「{item['a_text']}」x [{item['b']}]「{item['b_text']}」 {item['w']}x{item['h']}px")
                elif kind == "clip":
                    print(f"{sid} {kind}: [{item['el']}]「{item['text']}」 over_h={item['over_h']} over_w={item['over_w']}")
                elif kind == "bleed":
                    print(f"{sid} {kind}: [{item['el']}]「{item['text']}」 over={item['over']}px")
                elif kind == "spill":
                    print(f"{sid} {kind}: [{item['el']}]「{item['text']}」 文字高が箱高{item['box_h']}pxを{item['over']}px超過")
                elif kind == "rule":
                    print(f"{sid} {kind}: [{item['el']}]「{item['text']}」 罫線(y={item['rule_y']})と交差")
                else:
                    print(f"{sid} {kind}: [{item['el']}]「{item['text']}」 {item['lines']}行 (max {item['max']})")
    hard = s["clip"] + s["bleed"] + s["overlap"] + s["rule"] + s["lines"]
    hard += sum(1 for res in report["slides"].values() for it in res.get("spill", []) if it["over"] > args.spill_fail)
    warn = sum(s.values()) - hard
    print(f"check_layout: {len(nums)}枚 clip={s['clip']} bleed={s['bleed']} overlap={s['overlap']} spill={s['spill']} rule={s['rule']} lines={s['lines']} -> 不合格{hard}件 / 警告{warn}件")
    sys.exit(1 if hard else 0)


if __name__ == "__main__":
    main()
