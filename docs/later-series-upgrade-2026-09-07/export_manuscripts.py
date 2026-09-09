"""Export readable manuscripts from the canonical decks in this delivery manifest."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent


def inline(value):
    if isinstance(value, dict):
        text = inline(value.get('text', ''))
        return f"[{text}]({value['url']})" if value.get('url') else text
    return str(value).replace('[', '\\[').replace(']', '\\]')


def bullets(items, depth=0):
    result = []
    for item in items:
        result.append('  ' * depth + '- ' + inline(item).replace('\n', '<br>'))
        if isinstance(item, dict):
            result.extend(bullets(item.get('children', []), depth + 1))
    return result


def render(deck, sha):
    result = [f"# {deck['meta']['title']} — スライド原稿", '',
              'この原稿は [deck.json](deck.json) からの書き出し。修正は deck.json に行い、再出力する。', '',
              f"全{len(deck['slides'])}枚。元原稿 SHA-256: `{sha}`。", '',
              '図版はリンク先の画像を参照。補足はHTML用の説明で、PPTXのスピーカーノートには含まれない。', '']
    for number, slide in enumerate(deck['slides'], 1):
        title = inline(slide.get('title', slide.get('text', '引用')))
        result.extend([f"## {number:02d}. {title}", ''])
        for key in ('eyebrow', 'number', 'subtitle', 'meta', 'punch', 'lead'):
            if slide.get(key):
                result.extend([inline(slide[key]), ''])
        if slide.get('bullets'):
            result.extend(bullets(slide['bullets']) + [''])
        for side in ('left', 'right'):
            if side in slide:
                col = slide[side]
                result.extend([f"### {col.get('heading', side)}", ''])
                result.extend(bullets(col.get('bullets', [])) + [''])
        if slide.get('columns'):
            def row(cells):
                return '| ' + ' | '.join(inline(c).replace('|', '\\|').replace('\n', '<br>') for c in cells) + ' |'
            result.extend([row(slide['columns']), row(['---'] * len(slide['columns']))])
            result.extend(row(cells) for cells in slide.get('rows', []))
            result.append('')
        if 'code' in slide:
            result.extend(['````' + slide.get('language', ''), slide['code'], '````', ''])
        if slide.get('path'):
            result.extend([f"![図版]({slide['path']})", ''])
        for key in ('caption', 'attribution', 'message'):
            if slide.get(key):
                result.extend([inline(slide[key]), ''])
        if slide.get('notes'):
            result.extend(['### 参照・説明の補足（HTML用）', '', slide['notes'], ''])
    return '\n'.join(result)


if __name__ == '__main__':
    for topic in json.loads((HERE / 'status.json').read_text())['topics']:
        directory = ROOT / topic['deck']
        raw = (directory / 'deck.json').read_bytes()
        deck = json.loads(raw)
        (directory / 'manuscript.md').write_text(render(deck, hashlib.sha256(raw).hexdigest()))
        print(directory.name, len(deck['slides']), directory / 'manuscript.md')
