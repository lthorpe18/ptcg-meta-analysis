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
.deck-page{max-width:1100px;padding-top:26px}.deck-head{margin-bottom:12px}.deck-head h1{font-size:32px;letter-spacing:-.035em;margin:0}.deck-head p{margin:4px 0 0;color:#9fb0c3;font-size:15px}.forecast-strip{display:flex;flex-wrap:wrap;gap:5px 14px;padding:9px 12px;margin-bottom:12px;border:1px solid #243b55;border-radius:10px;background:#0b1827;color:#9fb0c3;font-size:12px}.forecast-strip strong{color:#f3f6fa}.deck-table-wrap{border:1px solid #365470;border-radius:12px;background:#091522;overflow:hidden}.deck-share-table{width:100%;border-collapse:separate;border-spacing:0;table-layout:fixed}.deck-share-table col.deck-col{width:46%}.deck-share-table col.metric-col{width:18%}.deck-share-table th,.deck-share-table td{padding:9px 10px;border-bottom:1px solid #29415a;border-right:1px solid #365470;vertical-align:middle}.deck-share-table th:last-child,.deck-share-table td:last-child{border-right:0}.deck-share-table tr:last-child td{border-bottom:0}.deck-share-table th{background:#19314e;color:#f3f7fb;font-size:12px;font-weight:800;white-space:nowrap}.deck-share-table th.num,.deck-share-table td.num{text-align:right;font-variant-numeric:tabular-nums}.deck-share-table tbody tr:nth-child(even) td{background:#0c1c2d}.deck-cell{display:flex;align-items:center;gap:7px;min-width:0}.sprite-slot{flex:0 0 34px}.deck-select{width:100%;min-width:0;max-width:100%;background:#0d1b2a;color:#f3f6fa;border:1px solid #365675;border-radius:8px;padding:8px 26px 8px 8px;font:inherit;font-size:13px;font-weight:700;outline:none;text-overflow:ellipsis}.deck-select:focus{border-color:#69b7ff;box-shadow:0 0 0 2px rgba(105,183,255,.14)}.share-value{font-size:18px;font-weight:850;letter-spacing:-.02em;white-space:nowrap}.predicted-value{color:#7bd8a6}.sprite-wrap{position:relative;display:inline-block;width:34px;height:34px}.sprite-wrap img{image-rendering:pixelated;object-fit:contain}.sprite-primary{position:absolute;left:3px;top:3px;width:28px;height:28px}.sprite-badge{position:absolute;right:-1px;bottom:-1px;width:18px;height:18px;border:2px solid rgba(255,255,255,.95);border-radius:50%;background:#dff8e8;display:grid;place-items:center}.sprite-badge img{width:13px;height:13px}.sprite-fallback{display:grid;place-items:center;width:32px;height:32px;border-radius:50%;background:#162b42;color:#9fb0c3;font-size:13px;font-weight:850}.table-actions{display:flex;justify-content:flex-start;margin-top:10px}.add-row{background:#14263a;color:#f3f6fa;border:1px solid #365675;border-radius:9px;padding:8px 11px;font:inherit;font-size:13px;font-weight:750;cursor:pointer}.method-note{margin-top:9px;color:#71869a;font-size:11px}.mobile-only{display:none}
@media(max-width:760px){
header .nav{padding:10px 12px;align-items:center;gap:8px}.brand{font-size:13px;white-space:nowrap}.navlinks{display:flex;gap:2px;overflow-x:auto;-webkit-overflow-scrolling:touch}.navlinks a{font-size:11px;padding:6px 7px;white-space:nowrap}.deck-page{padding:18px 10px 60px}.deck-head h1{font-size:27px}.deck-head p{font-size:13px}.forecast-strip{font-size:10.5px;line-height:1.35;padding:8px 9px}.deck-share-table col.deck-col{width:49%}.deck-share-table col.metric-col{width:17%}.deck-share-table th,.deck-share-table td{padding:7px 4px}.deck-share-table th{font-size:10px}.deck-cell{gap:4px}.sprite-slot{flex-basis:26px}.sprite-wrap{width:26px;height:26px}.sprite-primary{left:2px;top:2px;width:22px;height:22px}.sprite-badge{width:14px;height:14px;border-width:1px}.sprite-badge img{width:10px;height:10px}.sprite-fallback{width:24px;height:24px;font-size:10px}.deck-select{font-size:11px;padding:7px 18px 7px 5px;border-radius:7px}.share-value{font-size:14px}.desktop-only{display:none}.mobile-only{display:inline}.table-actions{margin-top:8px}.add-row{font-size:12px;padding:7px 10px}.method-note{font-size:10px;line-height:1.4}footer{padding:18px 12px;font-size:11px}
}
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


def option_html(rows: list[dict], selected_key: str) -> str:
    return "".join(
        f'<option value="{html.escape(str(r["key"]), quote=True)}"{" selected" if r["key"] == selected_key else ""}>{html.escape(r["name"])}</option>'
        for r in rows
    )


def sprite_html(row: dict) -> str:
    sprites = row.get("sprites") or []
    if not sprites:
        initial = html.escape((row.get("name") or "?").strip()[:1].upper() or "?")
        return f'<span class="sprite-fallback">{initial}</span>'
    base = "https://r2.limitlesstcg.net/pokemon/gen9"
    primary = f'<img class="sprite-primary" src="{base}/{html.escape(sprites[0], quote=True)}.png" alt="">'
    badge = ""
    if len(sprites) > 1:
        badge = f'<span class="sprite-badge"><img src="{base}/{html.escape(sprites[1], quote=True)}.png" alt=""></span>'
    return f'<span class="sprite-wrap">{primary}{badge}</span>'


def static_row(row: dict, all_rows: list[dict]) -> str:
    return (
        '<tr>'
        f'<td><div class="deck-cell"><div class="sprite-slot">{sprite_html(row)}</div><select class="deck-select">{option_html(all_rows, row["key"])}</select></div></td>'
        f'<td class="num share-value irl">{row["irl_pct"]:.1f}%</td>'
        f'<td class="num share-value online">{row["online_pct"]:.1f}%</td>'
        f'<td class="num share-value predicted-value blend">{row["blended_pct"]:.1f}%</td>'
        '</tr>'
    )


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
    initial_rows = "".join(static_row(row, enriched) for row in enriched[:10])
    context = (
        f'{html.escape(data["format"])} · {irl_w:.0f}/{online_w:.0f} blend · '
        f'IRL: {html.escape(latest["name"])} · Online through {human_date(data["online_evidence_through"])}'
    )

    body = f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Deck shares · PTCG Meta Research</title><style>{css}</style></head><body>{nav}<main class="deck-page">
<section class="deck-head"><h1>Deck shares</h1><p>Choose any archetypes and compare the three estimates.</p></section>
<div class="forecast-strip"><span>{context}</span></div>
<div class="deck-table-wrap"><table class="deck-share-table"><colgroup><col class="deck-col"><col class="metric-col"><col class="metric-col"><col class="metric-col"></colgroup><thead><tr><th>Archetype</th><th class="num">IRL</th><th class="num">Online</th><th class="num"><span class="desktop-only">Predicted blend</span><span class="mobile-only">Blend</span></th></tr></thead><tbody id="deckRows">{initial_rows}</tbody></table></div>
<div class="table-actions"><button class="add-row" id="addRow" type="button">+ Add archetype</button></div>
<div class="method-note">IRL = latest same-format major · Online = events since that major · Blend = current best-fit prediction</div>
</main><footer>Historical walk-forward research for PTCG Tools.</footer>
<script type="application/json" id="forecastData">{payload}</script>
<script>
(() => {{
  const DATA = JSON.parse(document.getElementById('forecastData').textContent);
  const byKey = new Map(DATA.map(x => [x.key, x]));
  const tbody = document.getElementById('deckRows');
  const BASE = 'https://r2.limitlesstcg.net/pokemon/gen9';
  const fmt = v => Number(v).toFixed(1) + '%';
  function spriteHtml(row) {{
    const s = row.sprites || [];
    if (!s.length) return '<span class="sprite-fallback">' + (row.name || '?').trim().charAt(0).toUpperCase() + '</span>';
    const p = '<img class="sprite-primary" src="' + BASE + '/' + encodeURIComponent(s[0]) + '.png" alt="">';
    const b = s[1] ? '<span class="sprite-badge"><img src="' + BASE + '/' + encodeURIComponent(s[1]) + '.png" alt=""></span>' : '';
    return '<span class="sprite-wrap">' + p + b + '</span>';
  }}
  function escapeHtml(value) {{
    return String(value).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
  }}
  function options(selected) {{
    return DATA.map(r => '<option value="' + escapeHtml(r.key) + '"' + (r.key === selected ? ' selected' : '') + '>' + escapeHtml(r.name) + '</option>').join('');
  }}
  function wireRow(tr) {{
    const sel = tr.querySelector('.deck-select');
    if (!sel) return;
    const draw = () => {{
      const r = byKey.get(sel.value) || DATA[0];
      tr.querySelector('.sprite-slot').innerHTML = spriteHtml(r);
      tr.querySelector('.irl').textContent = fmt(r.irl_pct);
      tr.querySelector('.online').textContent = fmt(r.online_pct);
      tr.querySelector('.blend').textContent = fmt(r.blended_pct);
    }};
    sel.addEventListener('change', draw);
  }}
  [...tbody.querySelectorAll('tr')].forEach(wireRow);
  document.getElementById('addRow').addEventListener('click', () => {{
    const used = new Set([...tbody.querySelectorAll('select')].map(s => s.value));
    const r = DATA.find(x => !used.has(x.key)) || DATA[0];
    const tr = document.createElement('tr');
    tr.innerHTML = '<td><div class="deck-cell"><div class="sprite-slot">' + spriteHtml(r) + '</div><select class="deck-select">' + options(r.key) + '</select></div></td>' +
      '<td class="num share-value irl">' + fmt(r.irl_pct) + '</td>' +
      '<td class="num share-value online">' + fmt(r.online_pct) + '</td>' +
      '<td class="num share-value predicted-value blend">' + fmt(r.blended_pct) + '</td>';
    tbody.appendChild(tr);
    wireRow(tr);
  }});
}})();
</script></body></html>'''
    (DASHBOARD / "archetype.html").write_text(body, encoding="utf-8")
    print(json.dumps({"page": "dashboard/archetype.html", "archetypes": len(enriched), "default_rows": min(10, len(enriched))}, indent=2))


if __name__ == "__main__":
    main()
