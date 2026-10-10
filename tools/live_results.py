#!/usr/bin/env python3
"""日本水泳連盟 Live Results の速報を index.html に取り込む。

  python3 tools/live_results.py            # 1回だけ取り込む
  python3 tools/live_results.py --today    # 今日（日本時間）の種目だけ見に行く

公式の速報（https://live-results.swim.or.jp/）は日本選手権(25m)と同じ大会コードで、
九州ジュニアは「九州Jr.（小学生）」「九州Jr.（中学生）」のクラスとして載っている。
  予選 … 日本選手権の予選の組の中で泳ぐ。クラスで絞った順位表から九州ジュニアの選手だけ拾う。
  決勝 … 九州Jr.の決勝として別の競技No.がある（1組・8人）。
選手の番号（swimmer_id_for_this_game）はこのアプリの entries[].id と同じ。

何度実行しても同じ結果になるように、毎回「申込データ＋速報」で作り直す。
（前回入れた result と、前回足した決勝の program / entries は消してから入れ直す）
変更があったときだけ index.html と live.json を書き換え、終了コード 0 を返す。変更なしは 3。
"""
import datetime
import json
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HTML = ROOT / "index.html"
LIVE = ROOT / "live.json"
API = "https://live-results.swim.or.jp/api"
GAME = "7026706"
UA = ("Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 "
      "(KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1")
CLASS = {"小学生の部": 10, "中学生の部": 11}
JST = datetime.timezone(datetime.timedelta(hours=9))
SOURCE_NOTE = "結果は日本水泳連盟 Live Results の速報による（正式な記録は公式発表で確認）"
M1, M2 = "/*__DATA__*/", "/*__DATA_END__*/"


def get(path, **params):
    q = "&".join(f"{k}={v}" for k, v in params.items())
    url = f"{API}/{path}" + (f"?{q}" if q else "")
    last = None
    for i in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=20) as r:
                return json.loads(r.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
            last = e
            time.sleep(2 * (i + 1))
    raise RuntimeError(f"取得できませんでした: {url} ({last})")


def tsec(t):
    m = re.match(r"^(?:(\d+):)?(\d+)\.(\d+)$", (t or "").strip())
    return (int(m.group(1) or 0) * 60 + int(m.group(2)) + float("0." + m.group(3))) if m else None


def clean_time(t):
    return (t or "").strip()


def clean_name(n):
    return re.sub(r"[\s　]+", " ", (n or "").strip())


def day_date(day):
    """"10/12(月祝)" → date(2026,10,12)"""
    m = re.match(r"(\d+)/(\d+)", day or "")
    return datetime.date(2026, int(m.group(1)), int(m.group(2))) if m else None


def res_of(row, rank):
    """公式の1行 → アプリの result。棄権・失格は note に入れて順位は付けない。"""
    if (row.get("reason_code") or "0") != "0":
        return {"note": (row.get("reason_code_display_name") or "").strip() or "記録なし"}
    t = clean_time(row.get("result_time"))
    if not t:
        return None
    r = {"time": t}
    if rank:
        r["rank"] = rank
    mk = (row.get("new_record_print_mark") or "").strip()
    if re.search(r"[一-龥]", mk):        # 「大会新」などの文字のときだけ（記号だけの印は出さない）
        r["rec"] = mk
    return r


def main():
    today_only = "--today" in sys.argv
    html = HTML.read_text(encoding="utf-8")
    a = html.index(M1) + len(M1)
    b = html.index(M2)
    data = json.loads(html[a:b])

    # ---- 前回の速報を外して、申込データだけに戻す ----
    data["program"] = [p for p in data["program"] if not p.get("live")]
    data["entries"] = [e for e in data["entries"] if not e.get("live")]
    for e in data["entries"]:
        e.pop("result", None)
    base_progs = sorted(data["program"], key=lambda p: p["no"])
    old_results = {}   # 今日以外を取りに行かないときは、前回の結果をそのまま使う
    if today_only:
        prev = json.loads(html[a:b])
        for e in prev["entries"]:
            if e.get("result"):
                old_results[(tuple(e.get("programNos") or []), e["id"])] = e["result"]
        prev_live_progs = [p for p in prev["program"] if p.get("live")]
        prev_live_entries = [e for e in prev["entries"] if e.get("live")]

    # ---- 公式の競技No.の一覧 ----
    stages = get("result/event_stage_by_prog", game_code=GAME)

    def find(p, division, class_code=None):
        hit = [s for s in stages
               if s["gender_name"] == p["gender"] and s["distance_name"] == p["distance"]
               and s["swimming_style_name"] == p["stroke"] and s["race_division_name"] == division
               and (class_code is None or str(s.get("class_code")) == str(class_code))]
        if len(hit) != 1:
            raise RuntimeError(f"公式の競技No.が決まりません: {p} {division} {class_code} → {len(hit)}件")
        return hit[0]

    today = datetime.datetime.now(JST).date()
    finals = []   # (公式の決勝No., アプリの予選program, 決勝の行)
    for p in base_progs:
        p["round"] = "予選"
        cc = CLASS[p["classGrade"]]
        mine = [e for e in data["entries"] if p["no"] in (e.get("programNos") or [])]
        by_id = {e["id"]: e for e in mine}
        fin_stage = find(p, "決勝", cc)
        if today_only and day_date(p.get("day")) != today:
            # 今日の種目でなければ前回の結果を戻すだけ
            for e in mine:
                r = old_results.get((tuple(e["programNos"]), e["id"]))
                if r:
                    e["result"] = r
            olds = [x for x in prev_live_entries
                    if x.get("liveOf") == p["no"]]
            if olds:
                fp = next(x for x in prev_live_progs if x.get("liveOf") == p["no"])
                finals.append((int(fin_stage["display_program_id"]), p, None, fp, olds))
            continue

        # 予選：クラスで絞った順位表から、この種目の申込者だけ拾い、九州ジュニアの中で順位を付け直す
        pre = find(p, "予選")
        rows = get("result/race_rank_by_prog", game_code=GAME, program_id=pre["program_id"], class_code=cc)
        rows = [r for r in rows if str(r.get("swimmer_id_for_this_game")) in by_id]
        ok = sorted((r for r in rows if (r.get("reason_code") or "0") == "0" and tsec(r.get("result_time")) is not None),
                    key=lambda r: tsec(r["result_time"]))
        rank_of, prev_t, prev_rank = {}, None, 0
        for i, r in enumerate(ok, 1):
            t = tsec(r["result_time"])
            rk = prev_rank if t == prev_t else i
            rank_of[str(r["swimmer_id_for_this_game"])] = rk
            prev_t, prev_rank = t, rk
        # まだ1人も泳いでいない種目は、前もって届いた棄権だけでも「結果」扱いになって並びが変わるので入れない
        for r in (rows if ok else []):
            sid = str(r["swimmer_id_for_this_game"])
            res = res_of(r, rank_of.get(sid))
            if res:
                by_id[sid]["result"] = res

        # 決勝：スタートリスト（レーン）が出ていれば決勝のレースを作る
        heat = get("result/race", game_code=GAME, program_id=fin_stage["program_id"], heat=1, raceStatus=9)
        heat = [r for r in heat if r.get("swimmer_id_for_this_game")]
        if heat:
            finals.append((int(fin_stage["display_program_id"]), p, heat, None, None))

    # ---- 決勝の program / entries を足す（公式の決勝の順に No.33〜） ----
    finals.sort(key=lambda x: x[0])
    next_no = max(p["no"] for p in base_progs) + 1
    for off_no, p, heat, old_prog, old_entries in finals:
        no = next_no
        next_no += 1
        fp = {"no": no, "gender": p["gender"], "distance": p["distance"], "stroke": p["stroke"],
              "classGrade": p["classGrade"], "day": p.get("day"), "round": "決勝",
              "officialNo": off_no, "live": 1, "liveOf": p["no"]}
        data["program"].append(fp)
        if heat is None:   # 今日以外：前回の決勝をそのまま（No.だけ付け直す）
            for x in old_entries:
                x = dict(x)
                x["programNos"] = [no]
                data["entries"].append(x)
            continue
        src = {e["id"]: e for e in data["entries"] if p["no"] in (e.get("programNos") or []) and not e.get("live")}
        for r in sorted(heat, key=lambda r: int(r.get("lane") or 0)):
            sid = str(r["swimmer_id_for_this_game"])
            base = src.get(sid)
            if base:
                x = {k: v for k, v in base.items() if k not in ("result", "programNos")}
                if base.get("result") and "note" not in base["result"]:
                    base["result"]["adv"] = True     # 予選の行に「決勝へ」
            else:   # 申込データにいない人（追加エントリー等）は公式の名前で載せる
                x = {"id": sid, "name": clean_name(r.get("swimmer_name")),
                     "team": (r.get("entry_group_name1") or "").strip(),
                     "gender": p["gender"], "distance": p["distance"], "stroke": p["stroke"],
                     "event": f'{p["distance"]}{p["stroke"]}（{p["classGrade"][:3]}）'}
            x.update({"programNos": [no], "heat": 1, "lane": int(r.get("lane") or 0), "live": 1, "liveOf": p["no"]})
            res = res_of(r, r.get("rank"))
            if res:
                x["result"] = res
            data["entries"].append(x)

    data["program"].sort(key=lambda p: p["no"])
    src = data["meta"].get("source") or ""
    if SOURCE_NOTE not in src:
        data["meta"]["source"] = (src + " ／ " if src else "") + SOURCE_NOTE

    new_json = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    n = sum(1 for e in data["entries"] if e.get("result"))
    if new_json == html[a:b]:
        print(f"変更なし（結果 {n} 件）")
        return 3
    HTML.write_text(html[:a] + new_json + html[b:], encoding="utf-8")
    LIVE.write_text(json.dumps({"n": n, "updated": datetime.datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S")},
                               ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"更新しました（結果 {n} 件・決勝 {len(finals)} 種目）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
