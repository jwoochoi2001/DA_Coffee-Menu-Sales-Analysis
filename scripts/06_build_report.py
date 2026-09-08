# -*- coding: utf-8 -*-
"""06_build_report.py — report.template.html 의 그림 토큰을 base64로 치환해 report.html 생성"""
import base64, pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
TPL = ROOT / "scripts" / "report.template.html"
FIGDIR = ROOT / "output" / "report"
OUT = ROOT / "output" / "report.html"

html = TPL.read_text(encoding="utf-8")
for png in FIGDIR.glob("*.png"):
    token = "__" + png.stem.upper() + "__"          # r_growth.png -> __R_GROWTH__
    b64 = base64.b64encode(png.read_bytes()).decode("ascii")
    html = html.replace(token, f"data:image/png;base64,{b64}")

assert "__R_" not in html, "치환 안 된 그림 토큰이 남아있음"

# 단독 파일(GitHub Pages·githack·오프라인)로 열 때 표준모드·한글 인코딩 보장.
# Artifact 배포 시엔 래퍼가 자체 <!doctype>/charset 을 앞에 붙이므로 중복돼도 브라우저가 무시.
PRELUDE = ('<!doctype html>\n<meta charset="utf-8">\n'
           '<meta name="viewport" content="width=device-width,initial-scale=1">\n')
OUT.write_text(PRELUDE + html, encoding="utf-8")
print(f"wrote {OUT}  ({(len(PRELUDE)+len(html))/1024:.0f} KB)")
