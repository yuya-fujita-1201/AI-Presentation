#!/usr/bin/env python3
"""レイアウト機械ゲート: ビルド済みHTMLをPlaywrightで開き、各スライドの

不合格（exit 1）になる検査:
  (1) clip    … overflow:hidden の箱から文字がはみ出して切れている（scrollHeight/Width > client）
  (2) bleed   … 文字・画像・図形がステージ（1280x720）の外に出ている（画像がフッターを覆うはみ出しもここ）
  (3) overlap … 文字を持つ要素同士の矩形が重なっている（親子関係を除く。Y/N など 1 文字ラベルも対象）。
                画像・動画・不透明に塗った図形が文字（キャプション・フッター等）を覆っている／画像の端が文字に部分的にかかっている場合も、ここに出す
  (4) lines   … data-max-lines="N" を持つ要素が N 行を超えている（文字の行ボックスを実測。レンダラが属性を出したときだけ働く）
  (5) spill   … 高さ指定のある文字要素で文字実体が割当高さを超えている（closing タイトル2行化など）。12px 超で不合格
  (6) rule    … 文字実体が細い罫線要素（HTML の薄い箱）と交差している

警告（exit 0。直し方つきで表示）:
  (7)  orphan   … 段落の最終行が 1〜2 文字だけ（泣き別れ。「…していま／す。」）。ブラウザの行ボックスを実測
  (7b) wordbreak… 描かれた行の末尾が語の途中になっている（「プラグイ／ン」「担当／者へ」。S5b）。行の実測 + ja_text.can_break（level 3）で判定
  (8)  minfont  … 実際に描かれる文字が小さすぎる（既定 9px 未満。SVG は縮尺込みの実寸）
  (9)  contrast … 文字色と、その背後の実効背景色のコントラスト比が基準未満（通常文字 4.5:1、大きい文字 3:1）。
                  背景が画像・グラデーションで判定できない文字は対象外
  (10) linecross… SVG の線・枠が文字の上を通っている（背後に不透明な塗りが無く、線が文字を貫通して見える）

使い方: python tools/check_layout.py <deck_dir> [--json out.json] [--slides 3 7]
HTML は build_deck.py --html の生成物を使う（無ければ自動ビルド）。
スライド番号は preview_deck.py の PNG（slide-NN.png）と同じ番号（expand_slides() 適用後。
凡例ページの自動挿入・agenda の分割込み）。deck.json の何枚目かとは違うことがある。check_diagram.py も同じ番号。

data-qa-ignore の取り決め（レンダラ・パターン向け）: 意図した重なりの要素に data-qa-ignore="overlap contrast"
のように種別（bleed / overlap / lines / orphan / minfont / contrast / linecross）を空白区切りで付けると、その要素と子孫は
その種別の検査から外れる。

data-max-lines の取り決め（レンダラ向け）: 「最大 N 行」を保証したい要素に data-max-lines="N" を付けると
(4) が行数を実測して検査する。属性が無ければ何もしない。
"""
from __future__ import annotations

import argparse
import json
import os
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
import ja_text  # type: ignore  # wordbreak の判定（ja_text.can_break）


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

# 不合格として数える種別 / 警告として数える種別（spill は 12px を超えたものだけ不合格）
HARD_KINDS = ("clip", "bleed", "overlap", "rule", "lines")
SOFT_KINDS = ("spill", "orphan", "wordbreak", "minfont", "contrast", "linecross")
ALL_KINDS = ("clip", "bleed", "overlap", "lines", "spill", "rule", "orphan", "wordbreak", "minfont", "contrast", "linecross")

# 検査のしきい値の既定値
DEFAULTS = {
    "tol": 2.0,              # はみ出し許容 px
    "overlapMin": 4.0,       # 重なりと見なす最小 px（幅・高さ両方）
    "minFont": 9.0,          # これ未満の実寸文字を警告（図解の補助ラベル既定 10px では誤検出しない値）
    "orphanMax": 2,          # 最終行がこの文字数以下なら泣き別れ
    "orphanPrevMin": 4,      # 直前の行がこの文字数以上のときだけ（極端に狭い箱の 1 字折り返しは別問題）
    "wordbreakLevel": 3,     # wordbreak の判定に使う ja_text.can_break の level（3 = 語の途中で切れているものだけ）
    "contrast": 4.5,         # 通常文字のコントラスト比
    "contrastLarge": 3.0,    # 大きい文字（24px 以上、または太字 18.66px 以上）のコントラスト比
}

JS = r"""
(args) => {
  const {tol, overlapMin, minFont, orphanMax, orphanPrevMin, contrast: cThr, contrastLarge: cThrLarge} = args;
  const slide = document.querySelector('.slide.active');
  if (!slide) return {error: 'no active slide'};
  const stage = slide.getBoundingClientRect();
  const out = {clip: [], bleed: [], overlap: [], lines: [], spill: [], rule: [],
               orphan: [], wordbreak: [], minfont: [], contrast: [], linecross: []};
  // canvas（PPTX 取り込み）は元資料の図形配置をそのまま再現するため、元から存在する重なり・罫線交差・
  // 箱からの文字のはみ出し・線と文字の交差は判定しない。見切れ（clip）とスライド外への文字のはみ出し（bleed）だけを見る
  const isCanvas = slide.dataset.type === 'canvas';
  const all = Array.from(slide.querySelectorAll('*'));
  const cssCache = new Map();
  const gcs = (el) => { let c = cssCache.get(el); if (!c) { c = getComputedStyle(el); cssCache.set(el, c); } return c; };
  const desc = (el) => (el.textContent || '').trim().replace(/\s+/g, ' ').slice(0, 40);
  const tag = (el) => el.tagName.toLowerCase() + (el.className && typeof el.className === 'string' ? '.' + el.className.split(' ')[0] : '');
  const SVGNS = 'http://www.w3.org/2000/svg';
  const inSvg = (el) => el.namespaceURI === SVGNS;
  // 要素単位の検査除外: data-qa-ignore="overlap contrast" のように種別を空白区切りで書くと、その要素と子孫は
  // その種別の検査から外れる（合成スライドで文字を画像の上に重ねる等、意図した重なりのための取り決め）
  const skip = (el, kind) => !!el.closest('[data-qa-ignore~="' + kind + '"]');
  const hasBox = (el) => { const r = el.getBoundingClientRect(); return r.width > 0 || r.height > 0; };
  // elementsFromPoint が pointer-events:none の要素を飛ばさないようにする（検査中だけ）
  const pe = document.createElement('style');
  pe.textContent = '.slide.active, .slide.active * { pointer-events: auto !important; }';
  document.head.appendChild(pe);

  // (1) clip: overflow hidden で中身が溢れている
  for (const el of all) {
    const cs = gcs(el);
    if (cs.display === 'none' || cs.visibility === 'hidden') continue;
    if (el.classList && el.classList.contains('cv-clip')) continue; // canvas の Excel 由来セル: 意図的に隠している
    if (cs.overflow === 'hidden' || cs.overflowY === 'hidden' || cs.overflowX === 'hidden') {
      const dh = el.scrollHeight - el.clientHeight;
      const dw = el.scrollWidth - el.clientWidth;
      if (dh > tol || dw > tol) {
        // scrollHeight は行ボックスの余白・padding も数えるため、文字そのものは箱の中に収まっていても数 px 超える
        // （コード 19〜21 行の pre。A8-21）。文字だけの箱は、文字実体の矩形が箱に収まっていれば切れていないとみなす
        let textFits = false;
        if (!el.querySelector('img, svg, canvas, video, picture') && (el.textContent || '').trim()) {
          try {
            const rg = document.createRange();
            rg.selectNodeContents(el);
            const tr = rg.getBoundingClientRect(), er = el.getBoundingClientRect();
            textFits = tr.width > 0 && tr.bottom <= er.bottom + tol && tr.right <= er.right + tol && tr.top >= er.top - tol && tr.left >= er.left - tol;
          } catch (e) {}
        }
        if (!textFits) out.clip.push({el: tag(el), text: desc(el), over_h: dh, over_w: dw});
      }
    }
  }

  // 文字を直接持つ「葉」要素（子要素を持たない、または直下テキストがある）
  const hasOwnText = (el) => Array.from(el.childNodes).some(n => n.nodeType === 3 && n.textContent.trim());
  const textEls = all.filter(el => {
    const cs = gcs(el);
    if (cs.display === 'none' || cs.visibility === 'hidden') return false;
    return hasOwnText(el) && el.tagName !== 'SCRIPT' && el.tagName !== 'STYLE';
  });
  // 装飾の 1 文字（引用符“・矢印→・記号●など）だけを重なり判定から外す。Y/N・数字などのラベルは対象に残す
  const symbolOnly = (el) => /^[\p{P}\p{S}\s]*$/u.test((el.textContent || '').trim());
  const deco = (el) => (el.textContent || '').trim().length <= 1 && symbolOnly(el);
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

  // (2) bleed: ステージ外（文字）
  for (const {el, box} of rects) {
    if (box.width === 0 || box.height === 0 || skip(el, 'bleed')) continue;
    const over = Math.max(stage.left - box.left, box.right - stage.right, stage.top - box.top, box.bottom - stage.bottom);
    if (over > tol) out.bleed.push({el: tag(el), text: desc(el), over: Math.round(over)});
  }
  // (2b) bleed: ステージ外（画像・図・塗りつぶした図形）。canvas は元資料の背景が端を越えることがあるので対象外。
  //      overflow:hidden の祖先に切り取られる要素は見た目に出ないので対象外
  if (!isCanvas) {
    const clippedByAncestor = (el) => {
      for (let p = el.parentElement; p && p !== slide; p = p.parentElement) {
        const o = gcs(p);
        if (o.overflow !== 'visible' || o.overflowX !== 'visible' || o.overflowY !== 'visible') return true;
      }
      return false;
    };
    const media = all.filter(el => {
      const cs = gcs(el);
      if (cs.display === 'none' || cs.visibility === 'hidden' || !hasBox(el)) return false;
      const t = el.tagName.toLowerCase();
      if (['img', 'video', 'canvas'].includes(t)) return true;
      if (el.classList && el.classList.contains('cv-sh')) return false; // canvas の図形 svg は影・線のための余白を持つ。外枠の .cv-s で見る
      if (t === 'svg') return !el.parentElement.closest('svg');
      if (inSvg(el)) return false;
      if (el.classList && el.classList.contains('cv-s')) return true; // canvas_engine の配置枠（x/y/w/h そのもの）
      const bg = cs.backgroundColor;
      const filled = (bg && bg !== 'rgba(0, 0, 0, 0)' && bg !== 'transparent') || (cs.backgroundImage && cs.backgroundImage !== 'none');
      return filled && !(el.textContent || '').trim();
    });
    for (const el of media) {
      if (clippedByAncestor(el) || skip(el, 'bleed')) continue;
      const r = el.getBoundingClientRect();
      const over = Math.max(stage.left - r.left, r.right - stage.right, stage.top - r.top, r.bottom - stage.bottom);
      if (over > tol) {
        const src = el.getAttribute('src') || '';
        const label = el.tagName.toLowerCase() === 'img' ? ('画像 ' + (src.startsWith('data:') ? '（埋め込み）' : src.split('/').pop().slice(0, 30))) : '図形';
        out.bleed.push({el: tag(el), text: label, over: Math.round(over), shape: label === '図形',
                        rect: [Math.round(r.left - stage.left), Math.round(r.top - stage.top), Math.round(r.width), Math.round(r.height)]});
      }
    }
    // (2c) overlap(cover): 画像・動画・不透明に塗った図形と文字の重なり。
    //      (a) 文字が画像・図形の「手前」ではなく奥にある（= 文字が覆い隠されている）→ 画像も図形も検出
    //      (b) 画像・動画の上に文字が乗っていて、文字の一部だけが画像にかかっている（キャプション・フッターに画像の端が
    //          かかる配置崩れ）→ 検出。文字が画像の中に収まる（写真の上のタイトル等）、ステージの大半を占める背景画像は意図した構図なので対象外
    //      意図して重ねる要素には data-qa-ignore="overlap"
    const opaqueFill = (cs) => {
      const m = /^rgba?\(([^)]*)\)$/.exec(cs.backgroundColor || '');
      if (!m) return false;
      const parts = m[1].split(',').map(v => parseFloat(v));
      const a = parts.length > 3 ? parts[3] : 1;
      return a >= 0.95 && parseFloat(cs.opacity) >= 0.95;
    };
    const covers = media.filter(el => {
      const t = el.tagName.toLowerCase();
      if (t === 'svg' || skip(el, 'overlap')) return false;
      if (['img', 'video', 'canvas'].includes(t)) return parseFloat(gcs(el).opacity) >= 0.95;
      return opaqueFill(gcs(el)) && !(el.classList && el.classList.contains('cv-s'));
    });
    // object-fit:contain の画像は、要素の箱より小さく描かれる（箱の余白は透明）。実際に塗られる矩形で判定する
    const paintedRect = (el) => {
      const r = el.getBoundingClientRect();
      const t = el.tagName.toLowerCase();
      const fit = gcs(el).objectFit;
      const nw = t === 'img' ? el.naturalWidth : t === 'video' ? el.videoWidth : 0;
      const nh = t === 'img' ? el.naturalHeight : t === 'video' ? el.videoHeight : 0;
      if (!nw || !nh || (fit !== 'contain' && fit !== 'scale-down')) return r;
      let k = Math.min(r.width / nw, r.height / nh);
      if (fit === 'scale-down') k = Math.min(k, 1);
      const w = nw * k, h = nh * k;
      const left = r.left + (r.width - w) / 2, top = r.top + (r.height - h) / 2;
      return {left, top, right: left + w, bottom: top + h, width: w, height: h};
    };
    for (const cv of covers) {
      const cr = paintedRect(cv);
      for (const {el, box} of rects) {
        if (box.width === 0 || box.height === 0 || deco(el) || skip(el, 'overlap')) continue;
        if (cv.contains(el) || el.contains(cv)) continue;
        const x0 = Math.max(cr.left, box.left), x1 = Math.min(cr.right, box.right);
        const y0 = Math.max(cr.top, box.top), y1 = Math.min(cr.bottom, box.bottom);
        if (x1 - x0 <= overlapMin || y1 - y0 <= overlapMin) continue;
        // 複数行の文字は外接矩形の中心が行間・行末の空白に当たることがある（elementsFromPoint が文字を返さず誤判定になる）。
        // 行ごとの矩形（getClientRects）のうち、画像と重なる行の中心で判定する（どれか 1 行でも覆われていれば覆われている）
        let pts = [];
        try {
          const rg = document.createRange();
          rg.selectNodeContents(el);
          for (const lr of Array.from(rg.getClientRects())) {
            const lx0 = Math.max(cr.left, lr.left), lx1 = Math.min(cr.right, lr.right);
            const ly0 = Math.max(cr.top, lr.top), ly1 = Math.min(cr.bottom, lr.bottom);
            if (lx1 - lx0 > overlapMin && ly1 - ly0 > overlapMin) pts.push([(lx0 + lx1) / 2, (ly0 + ly1) / 2]);
          }
        } catch (e) {}
        if (!pts.length) pts = [[(x0 + x1) / 2, (y0 + y1) / 2]];
        const isCovered = ([px, py]) => {
          const stack = document.elementsFromPoint(px, py);
          const iCover = stack.findIndex(e => e === cv || cv.contains(e));
          const iText = stack.findIndex(e => e === el || el.contains(e));
          return iCover >= 0 && (iText < 0 || iCover < iText);
        };
        const covered = pts.some(isCovered);
        if (!covered) {
          const isPic = ['img', 'video', 'canvas'].includes(cv.tagName.toLowerCase());
          const inside = box.left >= cr.left - 2 && box.right <= cr.right + 2 && box.top >= cr.top - 2 && box.bottom <= cr.bottom + 2;
          const background = cr.width * cr.height >= 0.85 * stage.width * stage.height;
          if (!isPic || inside || background) continue;
        }
        const src = cv.getAttribute('src') || '';
        const label = cv.tagName.toLowerCase() === 'img' ? ('画像 ' + (src.startsWith('data:') ? '（埋め込み）' : src.split('/').pop().slice(0, 30))) : '図形';
        out.overlap.push({a: tag(cv), a_text: label, b: tag(el), b_text: desc(el), w: Math.round(x1 - x0), h: Math.round(y1 - y0), cover: covered ? 'covered' : 'partial'});
      }
    }
  }

  // (3) overlap: 互いに親子でない文字要素同士
  for (let i = 0; i < (isCanvas ? 0 : rects.length); i++) {
    for (let j = i + 1; j < rects.length; j++) {
      const a = rects[i], b = rects[j];
      if (a.el.contains(b.el) || b.el.contains(a.el)) continue;
      if (deco(a.el) || deco(b.el) || skip(a.el, 'overlap') || skip(b.el, 'overlap')) continue;
      const x = Math.min(a.box.right, b.box.right) - Math.max(a.box.left, b.box.left);
      const y = Math.min(a.box.bottom, b.box.bottom) - Math.max(a.box.top, b.box.top);
      if (x > overlapMin && y > overlapMin) {
        out.overlap.push({a: tag(a.el), a_text: desc(a.el), b: tag(b.el), b_text: desc(b.el), w: Math.round(x), h: Math.round(y)});
      }
    }
  }

  // (5) spill: 高さが明示された文字要素で、文字実体が割り当て高さを超えている（overflow visible でも検出）
  for (const {el, box} of (isCanvas ? [] : rects)) {
    if (!el.style || !el.style.height) continue;
    if (deco(el)) continue;
    const cs = gcs(el);
    if (cs.overflow === 'hidden') continue; // clip 側で検出済み
    const over = box.height - el.clientHeight;
    if (over > tol) out.spill.push({el: tag(el), text: desc(el), over: Math.round(over), box_h: el.clientHeight});
  }

  // (6) rule: 文字実体が、細い罫線要素（文字を持たない・高さまたは幅4px以下）と交差している
  const rules = all.filter(el => {
    if ((el.textContent || '').trim()) return false;
    const r = el.getBoundingClientRect();
    const cs = gcs(el);
    if (cs.display === 'none') return false;
    return (r.height > 0 && r.height <= 4 && r.width > 40) || (r.width > 0 && r.width <= 4 && r.height > 40);
  }).map(el => ({el, box: el.getBoundingClientRect()}));
  for (const {el, box} of (isCanvas ? [] : rects)) {
    for (const ru of rules) {
      if (ru.el.contains(el) || el.contains(ru.el)) continue;
      const x = Math.min(box.right, ru.box.right) - Math.max(box.left, ru.box.left);
      const y = Math.min(box.bottom, ru.box.bottom) - Math.max(box.top, ru.box.top);
      if (x > overlapMin && y > 0) out.rule.push({el: tag(el), text: desc(el), rule_y: Math.round(ru.box.top)});
    }
  }

  // (4) lines: data-max-lines="N" を持つ要素の行数。箱の高さではなく、文字の行ボックスを実測する
  //     （Range.getClientRects で、縦位置の違う行の数を数える。高さ固定の箱でも 1 行の文字は 1 行と数える）
  const countLines = (el) => {
    const tops = [];
    const walker = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
    for (let n = walker.nextNode(); n; n = walker.nextNode()) {
      if (!n.textContent.trim()) continue;
      const rg = document.createRange();
      rg.selectNodeContents(n);
      for (const r of rg.getClientRects()) {
        if (r.width < 1 || r.height < 1) continue;
        if (!tops.some(t => Math.abs(t - r.top) < r.height * 0.5)) tops.push(r.top);
      }
    }
    return tops.length;
  };
  for (const el of all) {
    const want = el.getAttribute && el.getAttribute('data-max-lines');
    if (!want || skip(el, 'lines')) continue;
    const cs = gcs(el);
    if (cs.display === 'none' || cs.visibility === 'hidden') continue;
    const n = countLines(el);
    if (n > parseInt(want)) out.lines.push({el: tag(el), text: desc(el), lines: n, max: parseInt(want)});
  }

  // (7) orphan: 段落の最終行が 1〜2 文字だけ（泣き別れ）。<br> と ブロック子要素で段落を分け、
  //     文字ごとの行ボックスを実測して最終行を取り出す。pre 系・縦書き・SVG は対象外
  const paragraphsOf = (el) => {
    const paras = [[]];
    const walk = (n) => {
      for (const c of n.childNodes) {
        if (c.nodeType === 3) { if (c.textContent.length) paras[paras.length - 1].push(c); }
        else if (c.nodeType === 1) {
          if (c.tagName === 'BR') { if (!c.hasAttribute('data-soft')) paras.push([]); }   // data-soft: パターンエンジンが入れた自動改行（段落を分けない）
          else if (gcs(c).display === 'inline' && !inSvg(c)) walk(c);
          else paras.push([]);
        }
      }
    };
    walk(el);
    return paras.filter(p => p.length);
  };
  const lineCount = (nodes) => {
    const rg = document.createRange();
    rg.setStart(nodes[0], 0);
    const last = nodes[nodes.length - 1];
    rg.setEnd(last, last.textContent.length);
    const tops = [];
    for (const r of rg.getClientRects()) {
      if (r.width < 1 || r.height < 1) continue;
      if (!tops.some(t => Math.abs(t - r.top) < r.height * 0.5)) tops.push(r.top);
    }
    return tops.length;
  };
  for (const el of all) {
    if (inSvg(el)) continue;
    const cs = gcs(el);
    if (cs.display === 'none' || cs.visibility === 'hidden' || cs.display === 'inline') continue;
    if (cs.whiteSpace === 'pre' || cs.whiteSpace === 'pre-line' || !cs.writingMode.startsWith('horizontal') || skip(el, 'orphan')) continue;   // pre-wrap（canvas の文字枠）は折り返すので対象にする
    if (!hasBox(el)) continue;
    for (const nodes of paragraphsOf(el)) {
      if (!nodes.some(n => n.textContent.trim())) continue;
      if (lineCount(nodes) < 2) continue;
      const chars = [];
      const rg = document.createRange();
      for (const node of nodes) {
        const s = node.textContent;
        for (let i = 0; i < s.length; i++) {
          rg.setStart(node, i); rg.setEnd(node, i + 1);
          const rs = rg.getClientRects();
          if (!rs.length) continue;
          const r = rs[0];
          if (r.width === 0 && r.height === 0) continue;
          chars.push({ch: s[i], top: r.top, bottom: r.bottom, h: r.height});
        }
      }
      const lines = [];
      let cur = null;
      for (const c of chars) {
        if (!cur || c.top >= cur.bottom - c.h * 0.5) { cur = {s: '', bottom: c.bottom}; lines.push(cur); }
        cur.s += c.ch; cur.bottom = Math.max(cur.bottom, c.bottom);
      }
      if (lines.length < 2) continue;
      if (!isCanvas && !skip(el, 'wordbreak')) {
        // 行の末尾が語の途中かどうかは Python 側（ja_text.can_break）で判定する。段落の文字列と、行ごとの文字数だけ渡す
        out.wordbreak.push({el: tag(el), text: chars.map(c => c.ch).join(''), lens: lines.map(l => l.s.length),
                            size: parseFloat(cs.fontSize) || 0, cell: el.tagName === 'TD' || el.tagName === 'TH'});
      }
      const lastTxt = lines[lines.length - 1].s.trim();
      const prevTxt = lines[lines.length - 2].s.trim();
      const n = Array.from(lastTxt.replace(/\s/g, '')).length;
      if (n >= 1 && n <= orphanMax && Array.from(prevTxt).length >= orphanPrevMin) {
        out.orphan.push({el: tag(el), text: nodes.map(x => x.textContent).join('').trim().replace(/\s+/g, ' ').slice(0, 40),
                         last: lastTxt, tail: prevTxt.slice(-8), lines: lines.length});
      }
    }
  }

  // 色の扱い（(8)(9)(10) 共通）
  const parseColor = (s) => {
    const m = (s || '').match(/rgba?\(([^)]+)\)/);
    if (!m) return null;
    const p = m[1].split(/[\s,\/]+/).filter(Boolean).map(parseFloat);
    if (p.length < 3 || p.some(isNaN)) return null;
    return {r: p[0], g: p[1], b: p[2], a: p.length > 3 ? p[3] : 1};
  };
  const lum = (c) => {
    const f = (v) => { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); };
    return 0.2126 * f(c.r) + 0.7152 * f(c.g) + 0.0722 * f(c.b);
  };
  const ratio = (a, b) => { const la = lum(a), lb = lum(b); return (Math.max(la, lb) + 0.05) / (Math.min(la, lb) + 0.05); };
  const mix = (under, over, a) => ({r: under.r * (1 - a) + over.r * a, g: under.g * (1 - a) + over.g * a, b: under.b * (1 - a) + over.b * a, a: 1});
  const hex = (c) => '#' + [c.r, c.g, c.b].map(v => Math.round(v).toString(16).padStart(2, '0')).join('').toUpperCase();
  const SVG_SHAPES = new Set(['rect', 'path', 'circle', 'ellipse', 'polygon', 'polyline']);
  // 要素が自分で塗る面: null=塗らない / 'unknown'=画像・グラデーションで色が決まらない / {c, a}
  const layerOf = (e) => {
    const cs = gcs(e);
    if (inSvg(e)) {
      const t = e.tagName.toLowerCase();
      if (t === 'image' || t === 'foreignobject') return 'unknown';
      if (!SVG_SHAPES.has(t)) return null;
      const f = cs.fill;
      if (!f || f === 'none') return null;
      if (f.startsWith('url(')) return 'unknown';
      const c = parseColor(f);
      if (!c) return 'unknown';
      const fo = parseFloat(cs.fillOpacity), op = parseFloat(cs.opacity);
      return {c, a: c.a * (isNaN(fo) ? 1 : fo) * (isNaN(op) ? 1 : op)};
    }
    const t = e.tagName;
    if (t === 'IMG') {
      // 背景画像: build が data-qa-bg に「文字にとって最悪の色」（明るい文字なら画像の明るいところ）を渡していれば、その色の面として扱う
      const q = e.closest('[data-qa-bg]');
      const m = q && (q.getAttribute('data-qa-bg') || '').match(/^#([0-9a-f]{2})([0-9a-f]{2})([0-9a-f]{2})$/i);
      if (m) return {c: {r: parseInt(m[1], 16), g: parseInt(m[2], 16), b: parseInt(m[3], 16), a: 1}, a: 1};
    }
    if (t === 'IMG' || t === 'VIDEO' || t === 'CANVAS' || t === 'PICTURE') return 'unknown';
    if (cs.backgroundImage && cs.backgroundImage !== 'none') return 'unknown';
    const c = parseColor(cs.backgroundColor);
    if (!c || c.a === 0) return null;
    const op = parseFloat(cs.opacity);
    return {c, a: c.a * (isNaN(op) ? 1 : op)};
  };
  const effOpacity = (el) => {
    let o = 1;
    for (let p = el; p && p !== slide.parentElement; p = p.parentElement) { const v = parseFloat(gcs(p).opacity); if (!isNaN(v)) o *= v; }
    return o;
  };
  // 点 (x,y) で、文字 el の背後にある実効背景色。画像などで決まらなければ null
  const bgAt = (el, x, y) => {
    const st = document.elementsFromPoint(x, y);
    let last = -1;
    for (let i = 0; i < st.length; i++) if (st[i] === el || el.contains(st[i])) last = i;
    if (last < 0) return null;
    const layers = [];
    // 文字要素自身の背景（th・ラベルの塗り）も背後の面に数える。子孫（インライン要素）は文字の手前なので除く
    const own = st.indexOf(el);
    for (let i = (own >= 0 ? own : last + 1); i < st.length; i++) {
      const L = layerOf(st[i]);
      if (L === null) continue;
      if (L === 'unknown') return null;
      layers.push(L);
      if (L.a >= 0.99) break;
    }
    if (!layers.length || layers[layers.length - 1].a < 0.99) return null;
    let c = layers[layers.length - 1].c;
    for (let i = layers.length - 2; i >= 0; i--) c = mix(c, layers[i].c, layers[i].a);
    return c;
  };
  // 文字要素 el の「直下の文字ノード」の行ごとの矩形
  const ownLineRects = (el) => {
    const res = [];
    const rg = document.createRange();
    for (const n of el.childNodes) {
      if (n.nodeType !== 3 || !n.textContent.trim()) continue;
      rg.selectNodeContents(n);
      for (const r of rg.getClientRects()) if (r.width >= 1 && r.height >= 1) res.push(r);
    }
    return res;
  };
  const effFont = (el) => {
    let fs = parseFloat(gcs(el).fontSize);
    if (inSvg(el) && el.getScreenCTM) { const m = el.getScreenCTM(); if (m) fs *= Math.hypot(m.a, m.b); }
    return fs;
  };

  // (8) minfont / (9) contrast
  for (const el of textEls) {
    if (!hasBox(el)) continue;
    if (symbolOnly(el) || skip(el, 'minfont') && skip(el, 'contrast')) continue; // ●▲→ などの記号は文字ではなく図形扱い（状態マーク等。文字サイズ・文字コントラストの対象外）
    const cs = gcs(el);
    const fs = effFont(el);
    if (fs < minFont && !skip(el, 'minfont')) out.minfont.push({el: tag(el), text: desc(el), size: Math.round(fs * 10) / 10});
    // コントラスト: 文字色（SVG は fill）と、各行の左・中・右で求めた実効背景色の最悪値
    let fg = parseColor(inSvg(el) ? cs.fill : cs.color);
    if (!fg || (inSvg(el) && (cs.fill || '').startsWith('url('))) continue;
    const fo = inSvg(el) ? parseFloat(cs.fillOpacity) : 1;
    const fa = fg.a * (isNaN(fo) ? 1 : fo) * effOpacity(el);
    if (fa < 0.2 || skip(el, 'contrast')) continue;
    let worst = null;
    let undetermined = false;
    const lr = ownLineRects(el).slice(0, 6);
    for (const r of lr) {
      for (const f of [0.2, 0.5, 0.8]) {
        const x = r.left + r.width * f, y = r.top + r.height / 2;
        if (x < stage.left + 1 || x > stage.right - 1 || y < stage.top + 1 || y > stage.bottom - 1) continue;
        const bg = bgAt(el, x, y);
        if (!bg) { undetermined = true; continue; }
        const fgc = fa >= 0.99 ? fg : mix(bg, fg, fa);
        const k = ratio(fgc, bg);
        if (!worst || k < worst.k) worst = {k, fg: fgc, bg};
      }
    }
    if (!worst || undetermined && !worst) continue;
    const large = fs >= 24 || (fs >= 18.66 && parseInt(cs.fontWeight) >= 700);
    const thr = large ? cThrLarge : cThr;
    if (worst.k < thr - 0.1) { // 0.1 は色の丸めによる誤差の許容
      out.contrast.push({el: tag(el), text: desc(el), ratio: Math.round(worst.k * 100) / 100, need: thr,
                         fg: hex(worst.fg), bg: hex(worst.bg), size: Math.round(fs * 10) / 10});
    }
  }

  // (10) linecross: SVG の線・枠が文字の上を通っている
  if (!isCanvas) {
    const tgt = [];
    for (const el of textEls) {
      if (!hasBox(el)) continue;
      const rs = ownLineRects(el).map(r => {
        const dx = Math.min(1.5, r.width / 4), dy = Math.max(2, r.height * 0.2);
        return {l: r.left + dx, r: r.right - dx, t: r.top + dy, b: r.bottom - dy};
      }).filter(r => r.r > r.l && r.b > r.t);
      if (rs.length) tgt.push({el, rs});
    }
    const after = (a, b) => !!(a.compareDocumentPosition(b) & Node.DOCUMENT_POSITION_FOLLOWING);
    const covered = (line, text, x, y) => {
      for (const e of document.elementsFromPoint(x, y)) {
        if (e === line || e.contains(line)) continue;
        const L = layerOf(e);
        if (!L || L === 'unknown' || L.a < 0.85) continue;
        if (after(line, e) && (e === text || after(e, text))) return true;
      }
      return false;
    };
    const strokeSets = [];
    const strokes = Array.from(slide.querySelectorAll('svg line, svg polyline, svg polygon, svg path, svg rect, svg circle, svg ellipse')).filter(e => {
      const cs = gcs(e);
      if (cs.display === 'none' || cs.visibility === 'hidden') return false;
      if (!cs.stroke || cs.stroke === 'none' || !(parseFloat(cs.strokeWidth) > 0)) return false;
      if (e.closest('defs, marker, clipPath, mask, pattern, symbol')) return false;
      return typeof e.getTotalLength === 'function' && hasBox(e);
    });
    for (const s of strokes) {
      const m = s.getScreenCTM();
      let len = 0;
      try { len = s.getTotalLength(); } catch (e) {}
      if (!m || !(len > 0)) continue;
      const scale = Math.hypot(m.a, m.b) || 1;
      const n = Math.min(Math.ceil(len * scale / 3), 800);
      const pts = [];
      for (let k = 0; k <= n; k++) {
        const p = s.getPointAtLength(len * k / n);
        pts.push({x: m.a * p.x + m.c * p.y + m.e, y: m.b * p.x + m.d * p.y + m.f});
      }
      strokeSets.push({el: s, pts, box: s.getBoundingClientRect()});
    }
    // HTML の枠線（border。角丸つき）も同じように、枠の中心線に沿った点列として扱う
    const radius = (v, w, h) => {
      const parts = (v || '0').split(' ');
      const f = (x, base) => x.endsWith('%') ? parseFloat(x) / 100 * base : parseFloat(x) || 0;
      return [f(parts[0], w), f(parts[1] || parts[0], h)];
    };
    for (const el of all) {
      if (inSvg(el)) continue;
      const cs = gcs(el);
      if (cs.display === 'none' || cs.visibility === 'hidden') continue;
      const bw = [cs.borderTopWidth, cs.borderRightWidth, cs.borderBottomWidth, cs.borderLeftWidth].map(parseFloat);
      const bc = [cs.borderTopColor, cs.borderRightColor, cs.borderBottomColor, cs.borderLeftColor].map(parseColor);
      const bs = [cs.borderTopStyle, cs.borderRightStyle, cs.borderBottomStyle, cs.borderLeftStyle];
      const has = [0, 1, 2, 3].map(i => bw[i] >= 1 && bs[i] !== 'none' && bs[i] !== 'hidden' && bc[i] && bc[i].a > 0.1);
      if (!has.some(Boolean)) continue;
      const r = el.getBoundingClientRect();
      if (r.width < 8 || r.height < 8) continue;
      const rTL = radius(cs.borderTopLeftRadius, r.width, r.height), rTR = radius(cs.borderTopRightRadius, r.width, r.height);
      const rBR = radius(cs.borderBottomRightRadius, r.width, r.height), rBL = radius(cs.borderBottomLeftRadius, r.width, r.height);
      const pts = [];
      const seg = (x0, y0, x1, y1) => {
        const n = Math.max(1, Math.ceil(Math.hypot(x1 - x0, y1 - y0) / 3));
        for (let k = 0; k <= n; k++) pts.push({x: x0 + (x1 - x0) * k / n, y: y0 + (y1 - y0) * k / n});
      };
      const arc = (cx, cy, rx, ry, a0, a1) => {
        const n = Math.max(2, Math.ceil(Math.max(rx, ry) * Math.abs(a1 - a0) / 3));
        for (let k = 0; k <= n; k++) { const a = a0 + (a1 - a0) * k / n; pts.push({x: cx + rx * Math.cos(a), y: cy + ry * Math.sin(a)}); }
      };
      const l = r.left, t = r.top, rt = r.right, b = r.bottom, hw = (i) => bw[i] / 2;
      if (has[0]) seg(l + rTL[0], t + hw(0), rt - rTR[0], t + hw(0));
      if (has[0] && has[1] && (rTR[0] > 0 || rTR[1] > 0)) arc(rt - rTR[0], t + rTR[1], rTR[0] - hw(1), rTR[1] - hw(0), -Math.PI / 2, 0);
      if (has[1]) seg(rt - hw(1), t + rTR[1], rt - hw(1), b - rBR[1]);
      if (has[1] && has[2] && (rBR[0] > 0 || rBR[1] > 0)) arc(rt - rBR[0], b - rBR[1], rBR[0] - hw(1), rBR[1] - hw(2), 0, Math.PI / 2);
      if (has[2]) seg(rt - rBR[0], b - hw(2), l + rBL[0], b - hw(2));
      if (has[2] && has[3] && (rBL[0] > 0 || rBL[1] > 0)) arc(l + rBL[0], b - rBL[1], rBL[0] - hw(3), rBL[1] - hw(2), Math.PI / 2, Math.PI);
      if (has[3]) seg(l + hw(3), b - rBL[1], l + hw(3), t + rTL[1]);
      if (has[3] && has[0] && (rTL[0] > 0 || rTL[1] > 0)) arc(l + rTL[0], t + rTL[1], rTL[0] - hw(3), rTL[1] - hw(0), Math.PI, Math.PI * 1.5);
      if (pts.length) strokeSets.push({el, pts, box: r, html: true});
    }
    const seen = new Set();
    for (const {el: s, pts, box: sb} of strokeSets) {
      const near = tgt.filter(t => !(t.el === s) && t.rs.some(r => r.r > sb.left - 2 && r.l < sb.right + 2 && r.b > sb.top - 2 && r.t < sb.bottom + 2));
      for (const t of near) {
        if (t.el.contains(s)) continue;
        if (skip(t.el, 'linecross') || skip(s, 'linecross')) continue;
        const hit = pts.filter(p => t.rs.some(r => p.x > r.l && p.x < r.r && p.y > r.t && p.y < r.b));
        if (hit.length < 2) continue;
        const mid = hit[Math.floor(hit.length / 2)];
        if (covered(s, t.el, mid.x, mid.y) || covered(s, t.el, hit[0].x, hit[0].y)) continue;
        const key = tag(s) + '|' + desc(t.el);
        if (seen.has(key)) continue;
        seen.add(key);
        out.linecross.push({line: tag(s) + (s.namespaceURI === SVGNS ? '' : '（枠線）'), text: desc(t.el), x: Math.round(mid.x), y: Math.round(mid.y)});
      }
    }
  }
  pe.remove();
  return out;
}
"""

# ページ（フォント・画像）の読み込み完了と、描画の反映を待つ
WAIT_READY_JS = """async () => {
  try { await document.fonts.ready; } catch (e) {}
  await Promise.all(Array.from(document.images).map(i => (i.decode ? i.decode().catch(() => null) : null)));
  await new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)));
}"""


def wait_ready(page) -> None:
    page.evaluate(WAIT_READY_JS)


def wordbreak_items(raw: list, level: int = 3) -> list:
    """JS が集めた段落（text と行ごとの文字数 lens）から、行の末尾が語の途中になっているものを取り出す（S5b）。
    判定は ja_text.can_break(text, i, level)。level 3 は good_break だけ（語の途中・送り仮名・行頭の助詞）。
    和文を含まない段落（英文・URL だけ）は対象外。1 段落につき最初の 1 か所を出す。"""
    out = []
    for c in raw or []:
        text, lens = c.get("text") or "", c.get("lens") or []
        if len(lens) < 2 or not ja_text._has_cjk(text):
            continue
        pos = 0
        for k in range(len(lens) - 1):
            pos += lens[k]
            if 0 < pos < len(text) and "\n" not in text[pos - 1:pos + 1] and not ja_text.can_break(text, pos, level):   # 明示の改行（\n）の前後は自然な折り返しではない
                if text[pos - 1] == "-" and text[pos].isascii() and text[pos].isalnum():
                    continue               # ハイフンの直後の英数字は、ブラウザが折り返してよい位置（"getting-／started"）
                a, b = text[max(0, pos - 6):pos], text[pos:pos + 6]
                out.append({"el": c.get("el", ""), "text": text[:40], "tail": a.strip(), "head": b.strip(), "line": k + 1,
                            "lines": len(lens), "size": round(c.get("size") or 0, 1), "cell": bool(c.get("cell"))})
                break
    return out


def analyze_page(page, **overrides) -> dict:
    """表示中（.slide.active）の 1 枚を検査して種別ごとの検出リストを返す。"""
    a = dict(DEFAULTS)
    a.update(overrides)
    res = page.evaluate(JS, a)
    if isinstance(res, dict) and "wordbreak" in res:
        res["wordbreak"] = wordbreak_items(res["wordbreak"], int(a.get("wordbreakLevel", 3)))
    return res


def classify(report: dict, spill_fail: float = 12.0) -> tuple[int, int]:
    """(不合格件数, 警告件数)。spill は spill_fail を超えたものだけ不合格、残りは警告。"""
    hard = 0
    soft = 0
    for res in report["slides"].values():
        for kind in ALL_KINDS:
            items = res.get(kind, [])
            if kind in HARD_KINDS:
                hard += len(items)
            elif kind == "spill":
                n_hard = sum(1 for it in items if it["over"] > spill_fail)
                hard += n_hard
                soft += len(items) - n_hard
            else:
                soft += len(items)
    return hard, soft


def format_item(sid: str, kind: str, item: dict) -> str:
    """検出 1 件を『slide-NN 種別: 内容 → 直し方』の 1 行にする。"""
    if kind == "overlap" and item.get("cover"):
        verb = "が手前から覆っている" if item["cover"] == "covered" else "の端に文字がかかっている"
        return (f"{sid} {kind}: [{item['a']}]「{item['a_text']}」{verb} 文字 [{item['b']}]「{item['b_text']}」 {item['w']}x{item['h']}px"
                f" → 画像・図形の位置・大きさ（x/y/w/h）を文字から離す。意図した重ね（写真の上の文字など）なら data-qa-ignore=\"overlap\"")
    if kind == "overlap":
        return (f"{sid} {kind}: [{item['a']}]「{item['a_text']}」x [{item['b']}]「{item['b_text']}」 {item['w']}x{item['h']}px"
                f" → どちらかの位置・文字数・size を調整して重ならないようにする")
    if kind == "clip":
        return (f"{sid} {kind}: [{item['el']}]「{item['text']}」 over_h={item['over_h']} over_w={item['over_w']}"
                f" → 文字を減らすか size を下げる、または箱を大きくする")
    if kind == "bleed":
        pos = ""
        if item.get("rect"):
            x, y, w, h = item["rect"]
            pos = f" 位置 x={x},y={y},w={w},h={h}"
        return (f"{sid} {kind}: [{item['el']}]「{item['text']}」{pos} over={item['over']}px"
                f" → スライド内（1280x720）に収まるよう x/y/w/h・size を直す")
    if kind == "spill":
        return (f"{sid} {kind}: [{item['el']}]「{item['text']}」 文字高が箱高{item['box_h']}pxを{item['over']}px超過"
                f" → 文字を短くするか、箱の高さ（h）・size を調整する")
    if kind == "rule":
        return f"{sid} {kind}: [{item['el']}]「{item['text']}」 罫線(y={item['rule_y']})と交差 → 文字か罫線の位置をずらす"
    if kind == "lines":
        return (f"{sid} {kind}: [{item['el']}]「{item['text']}」 {item['lines']}行 (max {item['max']})"
                f" → 文字を短くするか size を下げて {item['max']} 行以内にする")
    if kind == "orphan":
        in_cell = item["el"].split(".")[0] in ("td", "th")
        # 表セルは HTML で \n が空白に畳まれる（改行にならない）ので、\n では直らない
        fix = ("セルの文字を 1〜2 字減らす、または列幅（style.table.col_widths）を広げる（セル内の \\n は HTML では改行にならない）"
               if in_cell else "1行ぶん短くするか、改行位置を変える（本文に \\n、幅・size の調整）")
        return (f"{sid} {kind}: [{item['el']}]「{item['text']}」 最終行が「{item['last']}」の{len(item['last'])}文字だけ"
                f"（{item['lines']}行中、直前は「…{item['tail']}」）"
                f" → {fix}")
    if kind == "wordbreak":
        fix = ("セルの文字を短くする、または列幅（style.table.col_widths）を広げる（文節の切れ目に \\n を入れてもよい）"
               if item.get("cell") else "文を短くする、文節の切れ目に \\n を入れる、箱の幅・size を調整する（style / meta.layout_overrides.common.wrap で自動の文節折り返しの条件を調整できる）")
        return (f"{sid} {kind}: [{item['el']}]「{item['text']}」 {item['line']}行目の終わりが語の途中で折れている"
                f"（「…{item['tail']}／{item['head']}…」、{item['lines']}行中、{item['size']}px）"
                f" → {fix}")
    if kind == "minfont":
        return (f"{sid} {kind}: [{item['el']}]「{item['text']}」 実寸{item['size']}pxで小さすぎる"
                f" → size を上げる（投影・印刷で読めるのは目安 10px 以上）。図解ならノード数・文字量を減らす")
    if kind == "contrast":
        return (f"{sid} {kind}: [{item['el']}]「{item['text']}」 コントラスト比{item['ratio']}:1（基準{item['need']}:1、"
                f"文字{item['fg']} / 背景{item['bg']}、{item['size']}px）"
                f" → 文字色か背景色をテーマトークンで離す（濃い面の上は on_primary 系の明るい色など）")
    if kind == "linecross":
        return (f"{sid} {kind}: [{item['line']}]が「{item['text']}」の上を通っている（約 x={item['x']}, y={item['y']}）"
                f" → ラベルを線から離す・線の経路を変える・ラベルに背景（塗り）を付ける")
    return f"{sid} {kind}: {item}"


SHAPE_BLEED_CAP = 3     # 1 枚で図形の bleed を何件まで個別に出すか


def format_report(report: dict, cap: int = 6, spill_fail: float = 12.0) -> list[str]:
    """検出を 1 行ずつの文字列にする。警告系は 1 枚・1 種別あたり cap 件まで（残りは件数だけ。全件は --json）。
    ただし spill は spill_fail を超えた（= 不合格の）項目を先に全部出し、cap は警告ぶんだけに使う
    （小さい超過が先に並んで、不合格の本体が「ほか N件」に隠れないように）。"""
    lines = []
    for sid, res in report["slides"].items():
        for kind in ALL_KINDS:
            items = res.get(kind, [])
            if kind == "bleed":
                # 位置不明の「図形」が同じ文言で大量に並ぶ（1 つの誤りで数十件になる）ので、1 枚 3 件までに畳む。
                # 文字・画像の bleed は全部出す。不合格の件数（classify）は畳まずに数える
                shapes = [it for it in items if it.get("shape")]
                others = [it for it in items if not it.get("shape")]
                shown = others + shapes[:SHAPE_BLEED_CAP]
                items = others + shapes
            elif kind in HARD_KINDS:
                shown = items
            elif kind == "spill":
                fails = [it for it in items if it["over"] > spill_fail]
                rest = [it for it in items if it["over"] <= spill_fail]
                shown = fails + rest[:cap]
                items = fails + rest
            else:
                shown = items[:cap]
            for item in shown:
                lines.append(format_item(sid, kind, item))
            if len(shown) < len(items):
                more = len(items) - len(shown)
                if kind == "bleed":
                    lines.append(f"{sid} {kind}: …ほか図形{more}件（同じ原因で並ぶことが多い。全件は --json で確認）")
                else:
                    lines.append(f"{sid} {kind}: …ほか{more}件（全件は --json で確認）")
    return lines


def _snapshot(path: Path):
    """(内容, 更新時刻)。無ければ None。再ビルドで内容が変わらなかったときに更新時刻を戻すために使う。"""
    try:
        return path.read_bytes(), path.stat().st_mtime
    except OSError:
        return None


def _keep_mtime_if_same(path: Path, before) -> bool:
    """再ビルド後の HTML が前と同じ内容なら、更新時刻を元に戻す（内容が同じなのに「プレビューが古い」と
    check_visual.py に誤判定されないように）。戻したら True。"""
    if before is None:
        return False
    try:
        if path.read_bytes() != before[0]:
            return False
        os.utime(path, (before[1], before[1]))
        return True
    except OSError:
        return False


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
    ap = argparse.ArgumentParser(
        description="ビルド済み HTML を実測して、はみ出し・重なり・泣き別れ・小さい文字・低コントラスト・線と文字の衝突を検出する",
        epilog="スライド番号は preview_deck.py の PNG（slide-NN.png）と同じ（凡例ページの自動挿入込み）。deck.json の何枚目かではない。")
    ap.add_argument("deck_dir")
    ap.add_argument("--json", help="結果JSONの出力先")
    ap.add_argument("--slides", nargs="*", type=int,
                    help="対象スライド番号（省略=全部。プレビュー PNG の番号。check_diagram.py と同じ体系）")
    ap.add_argument("--tol", type=float, default=DEFAULTS["tol"], help="はみ出し許容px")
    ap.add_argument("--overlap-min", type=float, default=DEFAULTS["overlapMin"], help="重なりと見なす最小px（幅・高さとも）")
    ap.add_argument("--min-font", type=float, default=DEFAULTS["minFont"], help="これ未満の実寸文字を警告（既定 9px）")
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
        before = _snapshot(html_path)
        proc = subprocess.run([PY, str(ROOT / "tools" / "build_deck.py"), str(deck_dir), "--html"],
                               cwd=ROOT, stdout=subprocess.DEVNULL)
        if proc.returncode != 0:
            fail("build_deck.py --html の実行に失敗しました（上のエラーを確認してください）")
        _keep_mtime_if_same(html_path, before)
    total = _slide_total(deck_dir, deck)
    nums = args.slides or list(range(1, total + 1))
    bad = [n for n in nums if not 1 <= n <= total]
    if bad:
        fail(f"スライド番号が範囲外です（1〜{total}。プレビュー PNG と同じ番号で、凡例ページ等の自動挿入込みの枚数）: {bad}")

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        fail(
            "Playwright が未インストールのため check_layout.py を実行できません。\n"
            "  初回セットアップ: /slide-deck:setup --playwright"
        )
    report = {"deck": str(deck_dir), "slides": {}, "summary": {k: 0 for k in ALL_KINDS}}
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 720})
        url = html_path.resolve().as_uri()
        page.goto(f"{url}#{nums[0]}")
        wait_ready(page)
        for n in nums:
            # ページを読み直さずビューアの show() で切り替える（大きいデッキでの高速化）
            page.evaluate("(n) => show(n - 1)", n)
            wait_ready(page)
            res = analyze_page(page, tol=args.tol, overlapMin=args.overlap_min, minFont=args.min_font)
            if any(res.get(k) for k in ALL_KINDS):
                report["slides"][f"slide-{n:02d}"] = res
                for k in report["summary"]:
                    report["summary"][k] += len(res.get(k, []))
        browser.close()

    if args.json:
        Path(args.json).write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    s = report["summary"]
    for line in format_report(report, spill_fail=args.spill_fail):
        print(line)
    hard, soft = classify(report, args.spill_fail)
    print(f"check_layout: {len(nums)}枚 clip={s['clip']} bleed={s['bleed']} overlap={s['overlap']} spill={s['spill']} "
          f"rule={s['rule']} lines={s['lines']} orphan={s['orphan']} wordbreak={s['wordbreak']} minfont={s['minfont']} contrast={s['contrast']} "
          f"linecross={s['linecross']} -> 不合格{hard}件 / 警告{soft}件")
    sys.exit(1 if hard else 0)


if __name__ == "__main__":
    main()
