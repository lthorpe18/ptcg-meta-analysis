#!/usr/bin/env python3
"""Add the current archetype-share page to the concise research site."""
from __future__ import annotations

import html
import json
import re
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed" / "current-archetype-prediction.json"
DASHBOARD = ROOT / "dashboard"

EXTRA_CSS = r"""
.deck-page{max-width:900px}.deck-picker{margin:28px 0 26px}.deck-picker label{display:block;font-weight:800;margin-bottom:9px}.deck-picker select{width:100%;max-width:560px;background:#0d1b2a;color:#f3f6fa;border:1px solid #365675;border-radius:13px;padding:13px 42px 13px 14px;font:inherit;font-weight:700;outline:none}.deck-picker select:focus{border-color:#69b7ff;box-shadow:0 0 0 3px rgba(105,183,255,.14)}
.deck-result{background:linear-gradient(135deg,#102944,#0b1d30);border:1px solid #315c7f;border-radius:22px;padding:28px}.deck-title{display:flex;align-items:center;gap:18px;min-height:76px}.deck-title h2{font-size:32px;letter-spacing:-.03em;margin:0}.sprite-wrap{position:relative;display:inline-block;flex:0 0 78px;width:78px;height:78px}.sprite-wrap img{image-rendering:pixelated;object-fit:contain}.sprite-primary{position:absolute;left:7px;top:7px;width:64px;height:64px}.sprite-badge{position:absolute;right:-2px;bottom:-2px;width:40px;height:40px;border:3px solid rgba(255,255,255,.95);border-radius:50%;background:#dff8e8;display:grid;place-items:center;box-shadow:0 2px 6px rgba(0,0,0,.25)}.sprite-badge img{width:29px;height:29px}.sprite-fallback{display:grid;place-items:center;width:72px;height:72px;border-radius:50%;background:#162b42;color:#9fb0c3;font-size:28px;font-weight:850}
.share-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px;margin-top:26px}.share-card{background:#081522;border:1px solid #243b55;border-radius:17px;padding:20px}.share-card.predicted{border-color:#3f8c67;background:linear-gradient(180deg,#0d2a24,#091a1a)}.share-label{font-size:13px;color:#9fb0c3;font-weight:750}.share-number{font-size:42px;line-height:1;font-weight:850;letter-spacing:-.04em;margin:11px 0 8px}.share-card.predicted .share-number{color:#7bd8a6}.share-note{font-size:12px;color:#71869a}.forecast-context{margin-top:20px;padding-top:18px;border-top:1px solid #31506d;color:#b9c9da;font-size:14px}.forecast-context strong{color:#f3f6fa}.context-row{display:flex;flex-wrap:wrap;gap:8px 16px}.research-note{margin-top:12px;color:#8096aa;font-size:12px}
@media(max-width:760px){.share-grid{grid-template-columns:1fr}.deck-result{padding:22px}.deck-title h2{font-size:27px}}
"""

EXACT = {
    "Mega Excadrill": ["excadrill-mega"], "Dragapult": ["dragapult"], "Festival Lead": ["dipplin"],
    "Dragapult Blaziken": ["dragapult", "blaziken"], "Slowking": ["slowking"], "Alakazam Dudunsparce": ["alakazam", "dudunsparce"],
    "Dragapult Dusknoir": ["dragapult", "dusknoir"], "N's Zoroark": ["zoroark"], "Grimmsnarl Froslass": ["grimmsnarl", "froslass"],
    "Dhelmise": ["dhelmise"], "Toucannon": ["toucannon"], "Raging Bolt Ogerpon": ["raging-bolt"], "Mega Lucario": ["lucario-mega"],
    "Lucario Hariyama": ["lucario", "hariyama"], "Mega Greninja": ["greninja-mega"], "Basic Box": ["ogerpon"],
    "Ogerpon Meganium Hydrapple": ["meganium", "hydrapple"], "Rocket's Honchkrow": ["honchkrow"], "Cynthia's Garchomp": ["garchomp"],
    "Mega Chandelure": ["chandelure-mega"], "Beedrill": ["beedrill"], "Mega Absol Box": ["absol"],
    "Kangaskhan Bouffalant": ["kangaskhan", "bouffalant"], "Manectric Eelektrik": ["manectric", "eelektrik"], "Crustle": ["crustle"],
    "Ethan's Typhlosion": ["typhlosion"], "Greninja": ["greninja"], "Rocket's Mewtwo": ["mewtwo"], "Hop's Trevenant": ["trevenant"],
    "Toxtricity Box": ["toxtricity"], "Ceruledge": ["ceruledge"], "Starmie Froslass": ["starmie", "froslass"], "Mega Venusaur": ["venusaur-mega"],
    "Ogerpon Meganium Arboliva": ["meganium", "arboliva"], "Dragapult Dudunsparce": ["dragapult", "dudunsparce"],
    "Lopunny Dudunsparce": ["lopunny", "dudunsparce"], "Lopunny Dusknoir": ["lopunny", "dusknoir"], "Mega Starmie": ["starmie"],
    "Mega Darkrai": ["darkrai"], "Starmie Dusknoir": ["starmie", "dusknoir"], "Cinccino": ["cinccino"], "Toxtricity": ["toxtricity"],
    "Blaziken Zoroark": ["blaziken", "zoroark"], "Steven's Metagross": ["metagross"], "Miraidon ex": ["miraidon"],
}
TOKENS = [
    ("mega excadrill","excadrill-mega"),("cynthia","garchomp"),("festival lead","dipplin"),("dragapult","dragapult"),
    ("slowking","slowking"),("garchomp","garchomp"),("excadrill","excadrill"),("blaziken","blaziken"),("dusknoir","dusknoir"),
    ("dudunsparce","dudunsparce"),("alakazam","alakazam"),("zoroark","zoroark"),("grimmsnarl","grimmsnarl"),
    ("froslass","froslass"),("dhelmise","dhelmise"),("toucannon","toucannon"),("raging bolt","raging-bolt"),("lucario","lucario"),
    ("greninja","greninja"),("ogerpon","ogerpon"),("meganium","meganium"),("hydrapple","hydrapple"),("honchkrow","honchkrow"),
    ("chandelure","chandelure"),("beedrill","beedrill"),("absol","absol"),("kangaskhan","kangaskhan"),("bouffalant","bouffalant"),
    ("manectric","manectric"),("eelektrik","eelektrik"),("crustle","crustle"),("typhlosion","typhlosion"),("mewtwo","mewtwo"),
    ("trevenant","trevenant"),("toxtricity","toxtricity"),("ceruledge","ceruledge"),("starmie","starmie"),("venusaur","venusaur"),
    ("arboliva","arboliva"),("lopunny","lopunny"),("darkrai","darkrai"),("cinccino","cinccino"),("metagross","metagross"),
    ("miraidon","miraidon"),("gardevoir","gardevoir"),("charizard","charizard"),
]


def sprite_slugs(name: str) -> list[str]:
    if name in EXACT:
        return EXACT[name][:2]
    lower = name.lower()
    out = []
    for token, slug in TOKENS:
        if token in lower and slug not in out:
            out.append(slug)
        if len(out) == 2:
            break
    return out


def human_date(value: str) -> str:
    d = date.fromisoformat(value)
    return f"{d.day} {d.strftime('%b %Y')}"


def patch_nav(text: str) -> str:
    if 'href="archetype.html"' in text:
        return text
    needle = '<a class="" href="evidence.html">Evidence</a>'
    if needle in text:
        return text.replace(needle, '<a class="" href="archetype.html">Deck shares</a>' + needle, 1)
    # Defensive fallback if class formatting changes.
    return re.sub(r'(<nav class="navlinks">.*?<a[^>]+href="index\.html"[^>]*>Answer</a>)', r'\1<a class="" href="archetype.html">Deck shares</a>', text, count=1, flags=re.S)


def main() -> None:
    data = json.loads(DATA.read_text(encoding="utf-8"))
    index_path = DASHBOARD / "index.html"
    base = index_path.read_text(encoding="utf-8")
    style_match = re.search(r"<style>(.*?)</style>", base, flags=re.S)
    if not style_match:
        raise RuntimeError("Could not find research-site stylesheet")
    css = style_match.group(1) + EXTRA_CSS

    for filename in ("index.html", "evidence.html", "method.html"):
        path = DASHBOARD / filename
        if path.exists():
            path.write_text(patch_nav(path.read_text(encoding="utf-8")), encoding="utf-8")

    enriched = []
    for row in data["archetypes"]:
        enriched.append({**row, "sprites": sprite_slugs(row["name"])})
    enriched.sort(key=lambda r: r["blended_pct"], reverse=True)
    options = "".join(
        f'<option value="{html.escape(r["key"], quote=True)}">{html.escape(r["name"])}</option>'
        for r in enriched
    )

    latest = data["latest_irl"]
    irl_w = data["weights"]["irl"] * 100
    online_w = data["weights"]["online"] * 100
    context = (
        f'{html.escape(data["format"])} · Forecast {human_date(data["forecast_date"])} · '
        f'Online evidence through {human_date(data["online_evidence_through"])}'
    )
    nav = (
        '<header><div class="nav"><div class="brand">PTCG Meta Research</div><nav class="navlinks">'
        '<a class="" href="index.html">Answer</a><a class="active" href="archetype.html">Deck shares</a>'
        '<a class="" href="evidence.html">Evidence</a><a class="" href="method.html">Method</a>'
        '</nav></div></header>'
    )
    payload = json.dumps(enriched, ensure_ascii=False).replace("</", "<\\/")
    body = f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Deck shares · PTCG Meta Research</title><style>{css}</style></head><body>{nav}<main class="deck-page">
<section class="hero"><div class="eyebrow">Current forecast</div><h1>Choose a deck. See what each signal says.</h1><p>Select an archetype to compare its latest in-person field share, its Online share since that major, and the blended Day-1 prediction.</p></section>
<section class="deck-picker"><label for="deckSelect">Archetype</label><select id="deckSelect">{options}</select></section>
<section class="deck-result"><div class="deck-title"><div id="sprite"></div><div><div class="small">Expected Day-1 share</div><h2 id="deckName"></h2></div></div>
<div class="share-grid"><div class="share-card"><div class="share-label">Latest in-person major</div><div class="share-number" id="irlShare"></div><div class="share-note">{html.escape(latest["name"])}</div></div><div class="share-card"><div class="share-label">Online since that major</div><div class="share-number accent" id="onlineShare"></div><div class="share-note">{data["online_event_count"]} qualifying Online events</div></div><div class="share-card predicted"><div class="share-label">Predicted field share</div><div class="share-number" id="blendShare"></div><div class="share-note">Current blended estimate</div></div></div>
<div class="forecast-context"><div class="context-row"><span>{context}</span><span><strong>{irl_w:.0f}% in-person / {online_w:.0f}% Online</strong></span></div><div class="research-note">The blend uses our current best historical fit. The direction is stronger evidence than the exact weighting.</div></div></section>
</main><footer>Historical walk-forward research for PTCG Tools. Decision first; audit trail available when needed.</footer>
<script>const DATA={payload};const BASE='https://r2.limitlesstcg.net/pokemon/gen9';const byKey=new Map(DATA.map(x=>[x.key,x]));const sel=document.getElementById('deckSelect');function fmt(v){{return Number(v).toFixed(1)+'%'}}function spriteHtml(row){{const s=row.sprites||[];if(!s.length)return '<span class="sprite-fallback">'+(row.name||'?').trim().charAt(0).toUpperCase()+'</span>';const p='<img class="sprite-primary" src="'+BASE+'/'+encodeURIComponent(s[0])+'.png" alt="" onerror="this.style.display=\'none\'">';const b=s[1]?'<span class="sprite-badge"><img src="'+BASE+'/'+encodeURIComponent(s[1])+'.png" alt="" onerror="this.style.display=\'none\'"></span>':'';return '<span class="sprite-wrap">'+p+b+'</span>'}}function draw(){{const r=byKey.get(sel.value)||DATA[0];if(!r)return;document.getElementById('deckName').textContent=r.name;document.getElementById('irlShare').textContent=fmt(r.irl_pct);document.getElementById('onlineShare').textContent=fmt(r.online_pct);document.getElementById('blendShare').textContent=fmt(r.blended_pct);document.getElementById('sprite').innerHTML=spriteHtml(r)}}sel.addEventListener('change',draw);draw();</script></body></html>'''
    (DASHBOARD / "archetype.html").write_text(body, encoding="utf-8")
    print(json.dumps({"page": "dashboard/archetype.html", "archetypes": len(enriched), "default": enriched[0]["name"] if enriched else None}, indent=2))


if __name__ == "__main__":
    main()
