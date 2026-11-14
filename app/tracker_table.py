#%% Imports & connections
import streamlit as st
import pandas as pd
from utils import fetch_table_data
import html
import pandas as pd

#%% Get Data
# --------------------------------------------------------------------------

FINAL_YEAR_OFFSET = 10

def load_tracker_data(year: int, fetch=None) -> dict[str, pd.DataFrame]:
    if fetch is None:
        from utils import fetch_table_data as fetch

    bbwaa = fetch(table_name="bbwaa_ballots")
    players = fetch(table_name="players")
    voters = fetch(table_name="voters")
    ballots = fetch(table_name="ballots")

    # Players on this year's ballot, in bbwaa_ballots order (no sorting).
    on_ballot = bbwaa.loc[bbwaa["year"] == year, ["player_id"]].drop_duplicates()
    players = on_ballot.merge(
        players[["player_id", "player_name", "first_year_on_ballot"]],
        on="player_id",
        how="left",
    ).rename(columns={"player_name": "name"})

    cols = [
        "voter_id", "player_id", "year", "is_player_selected",
        "is_anonymous", "include_change_color", "include_in_change_total",
    ]
    this_and_prev = ballots.loc[ballots["year"].isin([year, year - 1]), cols]

    this_year = ballots.loc[ballots["year"] == year]
    anon_voter_ids = set(this_year.loc[this_year["is_anonymous"] == True, "voter_id"])

    voters = (
        voters.loc[voters["voter_id"].isin(this_year["voter_id"]), ["voter_id", "voter_name"]]
        .rename(columns={"voter_name": "name"})
        .assign(voter_is_anonymous=lambda d: d["voter_id"].isin(anon_voter_ids))
    )

    earlier = ballots.loc[ballots["year"] < year, ["voter_id"]].drop_duplicates()
    return {
        "players": players,
        "ballots": this_and_prev,
        "voters": voters,
        "earlier_voters": earlier,
    }


#%% Model
# --------------------------------------------------------------------------
def _b(x) -> bool:
    """NULL-safe bool."""
    if x is None or pd.isna(x):
        return False
    return bool(x)


def _ordinal(n: int) -> str:
    if 10 <= n % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def build_model(data: dict[str, pd.DataFrame], year: int) -> dict:
    players = data["players"]
    ballots = data["ballots"]
    voters = data["voters"]
    earlier = set(data["earlier_voters"]["voter_id"])

    cur, prev = {}, {}
    color_ok, total_ok, anon_ballot_voters = {}, {}, set()
    for r in ballots.itertuples(index=False):
        key = (r.voter_id, r.player_id)
        if r.year == year:
            cur[key] = _b(r.is_player_selected)
            color_ok[key] = _b(r.include_change_color)
            total_ok[key] = _b(r.include_in_change_total)
            if _b(r.is_anonymous):
                anon_ballot_voters.add(r.voter_id)
        else:
            prev[key] = _b(r.is_player_selected)

    plist = []
    for p in players.itertuples(index=False):
        first = int(p.first_year_on_ballot) if pd.notna(p.first_year_on_ballot) else year
        plist.append(
            {
                "id": p.player_id,
                "name": str(p.name),
                "is_new": first == year,
                "is_last": year >= first + FINAL_YEAR_OFFSET,
                "ordinal": _ordinal(year - first + 1),
            }
        )

    # Per-voter rows
    rows, anon_n = [], 0
    gained = {p["id"]: 0 for p in plist}
    lost = {p["id"]: 0 for p in plist}
    votes = {p["id"]: 0 for p in plist}
    on_ballot = {p["id"]: 0 for p in plist}

    for v in voters.itertuples(index=False):
        vid = v.voter_id
        is_anon = _b(v.voter_is_anonymous) or vid in anon_ballot_voters
        if is_anon:
            anon_n += 1
            label = f"Anonymous {anon_n}"
        else:
            label = str(v.name)

        cells = []
        for p in plist:
            pid = p["id"]
            key = (vid, pid)
            sel = cur.get(key)
            if sel is not None:
                on_ballot[pid] += 1
                votes[pid] += int(sel)

            state = ""
            if sel is not None and key in prev and not p["is_new"]:
                if (not prev[key]) and sel:
                    state = "gain"
                elif prev[key] and (not sel):
                    state = "lose"
            if state:
                if total_ok.get(key):
                    (gained if state == "gain" else lost)[pid] += 1
                if not color_ok.get(key):
                    state = ""
            cells.append({"selected": bool(sel), "state": state})

        rows.append(
            {
                "label": label,
                "anon": is_anon,
                "first_time": vid not in earlier,
                "cells": cells,
            }
        )

    stats = []
    for p in plist:
        pid = p["id"]
        pct = votes[pid] / on_ballot[pid] * 100 if on_ballot[pid] else 0.0
        stats.append(
            {
                "votes": votes[pid],
                "pct": pct,
                "gained": gained[pid],
                "lost": lost[pid],
                "net": gained[pid] - lost[pid],
            }
        )
    return {"year": year, "players": plist, "stats": stats, "rows": rows}


#%% HTML
# --------------------------------------------------------------------------

CSS = """
:root{--bg:#0e1b33;--panel:#152a52;--line:rgba(255,255,255,.09);--text:#e8eefb;
--muted:#8ea3c7;--new:#2dd4bf;--gain:#4ade80;--lose:#f87171;--bar:rgba(96,165,250,.38)}
*{box-sizing:border-box}
html,body{margin:0;background:transparent;color:var(--text);
font:13px 'IBM Plex Sans Condensed','Arial Narrow',system-ui,sans-serif}
.legend{display:flex;flex-wrap:wrap;gap:6px 16px;height:30px;align-items:center;
color:var(--muted);font-size:12px;padding:0 2px}
.legend i{display:inline-block;width:11px;height:11px;border-radius:2px;margin-right:6px;
vertical-align:-1px}
.wrap{height:calc(100vh - 34px);overflow:auto;border:1px solid var(--line);
border-radius:6px;background:var(--bg)}
table{border-collapse:separate;border-spacing:0;font-variant-numeric:tabular-nums}
th,td{border-right:1px solid var(--line);border-bottom:1px solid var(--line);
padding:0;text-align:center}
td.c{width:56px;min-width:56px;height:24px}
.stick{position:sticky;left:0;z-index:2;background:var(--bg);text-align:left;
padding:0 10px;width:178px;min-width:178px;max-width:178px;white-space:nowrap;
overflow:hidden;text-overflow:ellipsis}
thead th{position:sticky;top:0;z-index:3;background:var(--panel);padding:6px 2px 5px;
vertical-align:bottom;font-weight:400}
thead th.stick{z-index:5;font-weight:600;font-size:14px}
th .ln{display:block;font-weight:600;font-size:12px;line-height:1.15;overflow-wrap:break-word}
th .fi{display:block;color:var(--muted);font-size:11px;line-height:1.2}
th .yr{display:block;color:var(--muted);font-size:11px;margin-top:3px}
th.new{box-shadow:inset 0 -3px var(--new);background:#14405a}
th.new .yr{color:var(--new);font-weight:600}
th.last .yr{color:var(--lose);font-weight:600}
tr.stat td.stick{color:var(--muted)}
tr.stat td.c{font-weight:600}
td.gain{background:var(--gain);color:#052e16;font-weight:700}
td.lose{background:var(--lose);color:#450a0a;font-weight:700}
td.net-pos{color:var(--gain)}
td.net-neg{color:var(--lose)}
td.pct{background-repeat:no-repeat}
tr.band td{background:var(--panel);height:22px;color:var(--muted);font-size:12px}
tr.band td.stick{background:var(--panel)}
tr.voter td.stick.ft{box-shadow:inset 3px 0 var(--new);color:#99f6e4}
tr.voter td.stick.anon{font-style:italic;color:var(--muted)}
tr.voter:hover td:not(.gain):not(.lose){background:rgba(255,255,255,.04)}
tr.voter:hover td.stick{background:#122342}
@media (max-width:600px){
 .stick{width:120px;min-width:120px;max-width:120px;font-size:12px;padding:0 6px}
 td.c{width:64px;min-width:64px;height:24px}
}
"""

LEGEND = (
    '<div class="legend">'
    '<span><i style="background:var(--gain)"></i>Gained vote</span>'
    '<span><i style="background:var(--lose)"></i>Lost vote</span>'
    '<span><i style="background:var(--new)"></i>First-time voter / first year on ballot</span>'
    '<span><i style="background:transparent;box-shadow:inset 0 0 0 2px var(--lose)"></i>Final year on ballot</span>'
    "</div>"
)


def render_html(m: dict) -> str:
    esc = html.escape
    players, stats, rows = m["players"], m["stats"], m["rows"]
    n = len(players)

    head = [f'<th class="stick">{m["year"]} ballots</th>']
    for p in players:
        cls = " ".join(c for c, on in (("new", p["is_new"]), ("last", p["is_last"])) if on)
        head.append(
            f'<th class="{cls}"><span class="ln">{esc(p["name"])}</span>'
            f'<span class="yr">{p["ordinal"]}</span></th>'
        )

    def stat_row(label, fn, cls=""):
        tds = "".join(fn(s) for s in stats)
        return f'<tr class="stat {cls}"><td class="stick">{label}</td>{tds}</tr>'

    def net_cell(s):
        if not (s["gained"] or s["lost"]):
            return '<td class="c"></td>'
        n = s["net"]
        cls = "net-pos" if n > 0 else "net-neg" if n < 0 else ""
        return f'<td class="c {cls}">{n:+d}</td>' if n else '<td class="c">0</td>'

    body = [
        stat_row("Public votes", lambda s: f'<td class="c">{s["votes"]}</td>'),
        stat_row(
            "% of public ballots",
            lambda s: (
                f'<td class="c pct" style="background-image:linear-gradient(to top,'
                f'var(--bar) {s["pct"]:.1f}%,transparent {s["pct"]:.1f}%)">'
                f'{s["pct"]:.1f}%</td>'
            ),
        ),
        stat_row(
            "Gained votes",
            lambda s: f'<td class="c">{s["gained"] or ""}</td>',
        ),
        stat_row(
            "Lost votes",
            lambda s: f'<td class="c">{s["lost"] or ""}</td>',
        ),
        stat_row("Net +/-", net_cell),
        f'<tr class="band"><td class="stick">Ballots ({len(rows)})</td>'
        f'<td colspan="{n}"></td></tr>',
    ]

    for r in rows:
        classes = " ".join(c for c, on in (("ft", r["first_time"]), ("anon", r["anon"])) if on)
        tds = []
        for c in r["cells"]:
            tds.append(
                f'<td class="c {c["state"]}">{"x" if c["selected"] else ""}</td>'
            )
        body.append(
            f'<tr class="voter"><td class="stick {classes}" title="{esc(r["label"])}">'
            f'{esc(r["label"])}</td>{"".join(tds)}</tr>'
        )

    return (
        "<!doctype html><html><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        "<link rel='stylesheet' href='https://fonts.googleapis.com/css2?"
        "family=IBM+Plex+Sans+Condensed:wght@400;600;700&display=swap'>"
        f"<style>{CSS}</style></head><body>{LEGEND}"
        f"<div class='wrap'><table><thead><tr>{''.join(head)}</tr></thead>"
        f"<tbody>{''.join(body)}</tbody></table></div></body></html>"
    )


# --------------------------------------------------------------------------
# Streamlit entry point
# --------------------------------------------------------------------------
def render_tracker_table(year: int, height: int = 780, fetch=None) -> None:
    import streamlit.components.v1 as components

    model = build_model(load_tracker_data(year, fetch=fetch), year)
    components.html(render_html(model), height=height, scrolling=False)
