#!/usr/bin/env python3
"""Add a compact current archetype-share comparison table to the research site."""
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
.deck-page{max-width:1100px;padding-top:34px}.deck-head{display:flex;align-items:end;justify-content:space-between;gap:20px;margin-bottom:18px}.deck-head h1{font-size:34px;letter-spacing:-.035em;margin:0}.deck-head p{margin:5px 0 0;color:#9fb0c3}.forecast-strip{display:flex;flex-wrap:wrap;gap:7px 18px;padding:11px 14px;margin-bottom:14px;border:1px solid #243b55;border-radius:11px;background:#0b1827;color:#9fb0c3;font-size:13px}.forecast-strip strong{color:#f3f6fa}.deck-table-wrap{overflow:auto;border:1px solid #365470;border-radius:13px;background:#091522}.deck-share-table{width:100%;min-width:760px;border-collapse:separate;border-spacing:0}.deck-share-table th,.deck-share-table td{padding:10px 12px;border-bottom:1px solid #29415a;border-right:1px solid #365470;vertical-align:middle}.deck-share-table th:last-child,.deck-share-table td:last-child{border-right:0}.deck-share-table tr:last-child td{border-bottom:0}.deck-share-table th{background:#19314e;color:#f3f7fb;font-size:13px;font-weight:800}.deck-share-table th.num,.deck-share-table td.num{text-align:right;font-variant-numeric:tabular-nums}.deck-share-table tbody tr:nth-child(even) td{background:#0c1c2d}.deck-share-table tbody tr:hover td{background:#132a42}.deck-cell{display:flex;align-items:center;gap:10px;min-width:330px}.deck-select{width:100%;min-width:250px;background:#0d1b2a;color:#f3f6fa;border:1px solid #365675;border-radius:9px;padding:9px 34px 9px 10px;font:inherit;font-weight:700;outline:none}.deck-select:focus{border-color:#69b7ff;box-shadow:0 0 0 2px rgba(105,183,255,.14)}.share-value{font-size:20px;font-weight:850;letter-spacing:-.02em}.predicted-value{color:#7bd8a6}.sprite-wrap{position:relative;display:inline-block;flex:0 0 42px;width:42px;height:42px}.sprite-wrap img{image-rendering:pixelated;object-fit:contain}.sprite-primary{position:absolute;left:4px;top:4px;width:34px;height:34px}.sprite-badge{position:absolute;right:-1px;bottom:-1px;width:22px;height:22px;border:2px solid rgba(255,255,255,.95);border-radius:50%;background:#dff8e8;display:grid;place-items:center}.sprite-badge img{width:16px;height:16px}.sprite-fallback{display:grid;place-items:center;width:38px;height:38px;border-radius:50%;background:#162b42;color:#9fb0c3;font-size:16px;font-weight:850}.table-actions{display:flex;justify-content:flex-start;margin-top:12px}.add-row{background:#14263a;color:#f3f6fa;border:1px solid #365675;border-radius:10px;padding:9px 13px;font:inherit;font-weight:750;cursor:pointer}.add-row:hover{background:#19314e}.method-note{margin-top:10px;color:#71869a;font-size:12px}
@media(max-width:760px){.deck-page{padding-top:24px}.deck-head{display:block}.deck-head h1{font-size:29px}.deck-head p{font-size:14px}.forecast-strip{font-size:12px}.deck-share-table th,.deck-share-table td{padding:9px 10px}}
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

    enriched = [{**row, "sprites": sprite_slugs(row["name"])} for row in data["archetypes"]]
    enriched.sort(key=lambda r: r["blended_pct"], reverse=True)

    latest = data["latest_irl"]
    irl_w = data["weights"]["irl"] * 100
    online_w = data["weights"]["online"] * 100
    nav = (
        '<header><div class="nav"><div class="brand">PTCG Meta Research</div><nav class="navlinks">'
        '<a class="" href="index.html">Answer</a><a class="active" href="archetype.html">Deck shares</a>'
        '<a class="" href="evidence.html">Evidence</a><a class="" href="method.html">Method</a>'
        '</nav></div></header>'
    )
    payload = json.dumps(enriched, ensure_ascii=False).replace("</", "<\\/")
    default_keys = json.dumps([r["key"] for r in enriched[:10]])
    context = (
        f'{html.escape(data["format"])} · latest IRL: {html.escape(latest["name"])} · '
        f'Online through {human_date(data["online_evidence_through"])} · '
        f'<strong>{irl_w:.0f}% IRL / {online_w:.0f}% Online blend</strong>'
    )

    body = f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Deck shares · PTCG Meta Research</title><style>{css}</style></head><body>{nav}<main class="deck-page">
<section class="deck-head"><div><h1>Deck shares</h1><p>Pick the archetypes you want to compare.</p></div></section>
<div class="forecast-strip"><span>{context}</span></div>
<div class="deck-table-wrap"><table class="deck-share-table"><thead><tr><th>Archetype</th><th class="num">IRL</th><th class="num">Online</th><th class="num">Predicted blend</th></tr></thead><tbody id="deckRows"></tbody></table></div>
<div class="table-actions"><button class="add-row" id="addRow" type="button">+ Add archetype</button></div>
<div class="method-note">IRL = latest same-format major. Online = qualifying Online events since that major. Predicted blend = current best-fit weighting.</div>
</main><footer>Historical walk-forward research for PTCG Tools.</footer>
<script>const DATA={payload};const INITIAL={default_keys};const BASE='https://r2.limitlesstcg.net/pokemon/gen9';const byKey=new Map(DATA.map(x=>[x.key,x]));const tbody=document.getElementById('deckRows');function fmt(v){{return Number(v).toFixed(1)+'%'}}function spriteHtml(row){{const s=row.sprites||[];if(!s.length)return '<span class="sprite-fallback">'+(row.name||'?').trim().charAt(0).toUpperCase()+'</span>';const p='<img class="sprite-primary" src="'+BASE+'/'+encodeURIComponent(s[0])+'.png" alt="" onerror="this.style.display=\'none\'">';const b=s[1]?'<span class="sprite-badge"><img src="'+BASE+'/'+encodeURIComponent(s[1])+'.png" alt="" onerror="this.style.display=\'none\'"></span>':'';return '<span class="sprite-wrap">'+p+b+'</span>'}}function makeOptions(selected){{return DATA.map(r=>'<option value="'+r.key.replace(/&/g,'&amp;').replace(/"/g,'&quot;')+'"'+(r.key===selected?' selected':'')+'>'+r.name.replace(/&/g,'&amp;').replace(/</g,'&lt;')+'</option>').join('')}}function addRow(key){{const chosen=byKey.get(key)||DATA[0];if(!chosen)return;const tr=document.createElement('tr');tr.innerHTML='<td><div class="deck-cell"><div class="sprite-slot"></div><select class="deck-select">'+makeOptions(chosen.key)+'</select></div></td><td class="num share-value irl"></td><td class="num share-value online"></td><td class="num share-value predicted-value blend"></td>';const sel=tr.querySelector('select');function draw(){{const r=byKey.get(sel.value)||DATA[0];tr.querySelector('.sprite-slot').innerHTML=spriteHtml(r);tr.querySelector('.irl').textContent=fmt(r.irl_pct);tr.querySelector('.online').textContent=fmt(r.online_pct);tr.querySelector('.blend').textContent=fmt(r.blended_pct)}}sel.addEventListener('change',draw);tbody.appendChild(tr);draw()}}INITIAL.forEach(addRow);document.getElementById('addRow').addEventListener('click',()=>{{const used=new Set([...tbody.querySelectorAll('select')].map(s=>s.value));const next=DATA.find(r=>!used.has(r.key))||DATA[0];addRow(next.key)}});</script></body></html>'''
    (DASHBOARD / "archetype.html").write_text(body, encoding="utf-8")
    print(json.dumps({"page": "dashboard/archetype.html", "archetypes": len(enriched), "default_rows": min(10, len(enriched))}, indent=2))


if __name__ == "__main__":
    main()
