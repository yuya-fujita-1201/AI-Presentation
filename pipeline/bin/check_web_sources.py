#!/usr/bin/env python3
"""research_web成果（candidates.json）の検査。通過分を .verified.json に出力する。
検査: HTTPS・必須フィールド・extract長・重複URL・注入シグナル・source_tier付与（自己申告禁止・ラッパー付与）"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

INJECTION_PATTERNS = [
    r"ignore (all )?(previous|prior|above)", r"disregard .*instruction",
    r"system ?prompt", r"あなたは今から", r"指示(を|に)無視", r"以下の指示に従",
    r"outbox-v1", r"\{\{[A-Z_]+\}\}", r"```json[\s\S]{0,200}run_id",
]


def main():
    if len(sys.argv) < 2:
        print("usage: check_web_sources.py <candidates.json> --theme <id>")
        sys.exit(2)
    cand_f = sys.argv[1]
    theme_id = sys.argv[sys.argv.index("--theme") + 1] if "--theme" in sys.argv else "pe"
    import yaml
    theme = yaml.safe_load(open(os.path.join(ROOT, "pipeline", "themes", f"{theme_id}.yaml")))
    primary_domains = set(theme.get("primary_domains", []))
    try:
        data = json.load(open(cand_f))
    except Exception as e:
        print("NG: candidates.jsonがJSONでない:", e)
        sys.exit(1)
    cands = data.get("candidates", [])
    seen_urls = set()
    verified, rejected = [], []
    for c in cands:
        url = str(c.get("url", ""))
        why = None
        if not url.startswith("https://"):
            why = "not_https"
        elif url in seen_urls:
            why = "duplicate_url"
        elif not c.get("title") or not c.get("publisher") or not c.get("retrieved"):
            why = "missing_fields"
        else:
            extract = str(c.get("extract", ""))
            quote = str(c.get("quote", ""))
            if len(extract) < 2000:
                why = f"extract_short({len(extract)})"
            elif len(extract) > 12000:
                why = "extract_too_long"
            elif not quote:
                why = "no_quote"
            else:
                for pat in INJECTION_PATTERNS:
                    if re.search(pat, extract + quote, re.I):
                        why = f"injection_signal({pat[:20]})"
                        break
        seen_urls.add(url)
        if why:
            rejected.append({"url": url, "reason": why})
            continue
        host = re.match(r"https://([^/]+)", url).group(1).lower().removeprefix("www.")
        c["source_tier"] = "primary" if any(host == d or host.endswith("." + d) or d in host
                                            for d in primary_domains) else "secondary"
        verified.append(c)
    out = cand_f + ".verified.json"
    with open(out, "w") as f:
        json.dump({"verified": verified, "rejected": rejected}, f, ensure_ascii=False, indent=2)
    print(f"check_web_sources: verified {len(verified)} / rejected {len(rejected)}")
    for r in rejected[:10]:
        print("  reject:", r["url"][:60], r["reason"])
    sys.exit(0)


if __name__ == "__main__":
    main()
