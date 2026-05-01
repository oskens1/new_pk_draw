"""
stress_test.py
模擬 50 人同時投票 × 10 回合，測試 Supabase 承載能力。
"""

import requests
import uuid
import time
import math
import random
from concurrent.futures import ThreadPoolExecutor, as_completed

# ── 設定 ──
SUPABASE_URL = "https://cnizzgyievmsqdglftrh.supabase.co"
SUPABASE_KEY = "sb_publishable_8_fQGxMNZfoypvHQQGsL6w_cqhvvNXz"
ROUNDS       = 10
VOTERS       = 50

HEADERS = {
    "apikey":        SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type":  "application/json",
    "Prefer":        "return=representation",
}

def rest(method, path, extra_headers=None, **kwargs):
    url = SUPABASE_URL + "/rest/v1/" + path
    h = {**HEADERS, **(extra_headers or {})}
    r = requests.request(method, url, headers=h, timeout=15, **kwargs)
    r.raise_for_status()
    return r.json() if r.text else {}

# ── ELO 計算（與 admin.html 相同邏輯）──
def calc_elo(elo_a, elo_b, winner):
    K = 32
    exp_a = 1 / (1 + 10 ** ((elo_b - elo_a) / 400))
    exp_b = 1 - exp_a
    sa = 1 if winner == 'A' else 0
    sb = 1 - sa
    return round(elo_a + K * (sa - exp_a)), round(elo_b + K * (sb - exp_b))

# ── 取作品清單 ──
def get_works():
    return rest("GET", "works?select=*&order=match_count.asc")

# ── 開始回合 ──
def start_round(works, current_round):
    a = works[0]
    others = sorted(works[1:], key=lambda w: abs(w["elo"] - a["elo"]))
    b = others[0]
    match_id = f"stress_{int(time.time()*1000)}"

    rest("POST", "system_state", extra_headers={"Prefer": "resolution=merge-duplicates,return=representation"}, json={
        "id": "current",
        "status": "voting",
        "match_id": match_id,
        "match_a": {k: a[k] for k in ("id","image_url","filename","elo","match_count","win_count")},
        "match_b": {k: b[k] for k in ("id","image_url","filename","elo","match_count","win_count")},
        "round_number": current_round,
        "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    })

    return match_id, a, b

# ── 單一投票（由 ThreadPoolExecutor 呼叫）──
def cast_vote(match_id, choice, voter_token):
    try:
        rest("POST", "votes", json={
            "match_id":    match_id,
            "choice":      choice,
            "voter_token": voter_token,
        })
        return True, choice
    except Exception as e:
        return False, str(e)

# ── 結算回合 ──
def end_round(match_id, a, b):
    votes = rest("GET", f"votes?select=choice&match_id=eq.{match_id}")
    count_a = sum(1 for v in votes if v["choice"] == "A")
    count_b = sum(1 for v in votes if v["choice"] == "B")
    winner = "A" if count_a >= count_b else "B"

    new_a, new_b = calc_elo(a["elo"], b["elo"], winner)

    rest("PATCH", f"works?id=eq.{a['id']}", json={
        "elo": new_a,
        "match_count": (a["match_count"] or 0) + 1,
        "win_count": (a["win_count"] or 0) + (1 if winner == "A" else 0),
    })
    rest("PATCH", f"works?id=eq.{b['id']}", json={
        "elo": new_b,
        "match_count": (b["match_count"] or 0) + 1,
        "win_count": (b["win_count"] or 0) + (1 if winner == "B" else 0),
    })
    rest("PATCH", "system_state?id=eq.current", json={
        "status": "waiting",
        "match_id": None,
        "match_a": None,
        "match_b": None,
        "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    })

    return count_a, count_b, winner, new_a, new_b

# ── 主程式 ──
def main():
    print(f"=== 壓力測試：{ROUNDS} 回合 × {VOTERS} 票/回合 ===\n")

    # 確認作品數量
    works = get_works()
    if len(works) < 2:
        print(f"❌ 作品不足（目前 {len(works)} 件），請先上傳至少 2 件 PDF")
        return
    print(f"✅ 偵測到 {len(works)} 件作品\n")

    total_ok = 0
    total_fail = 0
    round_times = []

    for r in range(1, ROUNDS + 1):
        print(f"── 第 {r:02d} 回合 ──")
        t0 = time.time()

        # 取最新作品清單（含更新後 ELO）
        works = get_works()

        # 開始回合
        match_id, a, b = start_round(works, r)
        print(f"  配對：{a['filename']}（ELO {a['elo']}）vs {b['filename']}（ELO {b['elo']}）")

        # 產生 50 個不重複 voter_token，隨機分配 A/B
        tokens  = [str(uuid.uuid4()) for _ in range(VOTERS)]
        choices = ["A" if random.random() < 0.5 else "B" for _ in range(VOTERS)]

        # 同時送出 50 票
        ok = fail = 0
        with ThreadPoolExecutor(max_workers=VOTERS) as pool:
            futures = {pool.submit(cast_vote, match_id, c, t): i
                       for i, (t, c) in enumerate(zip(tokens, choices))}
            for future in as_completed(futures):
                success, _ = future.result()
                if success: ok += 1
                else:       fail += 1

        total_ok += ok
        total_fail += fail

        # 結算
        count_a, count_b, winner, new_a, new_b = end_round(match_id, a, b)
        elapsed = time.time() - t0
        round_times.append(elapsed)

        print(f"  投票：A={count_a} B={count_b}  勝方：{'A (' + a['filename'] + ')' if winner=='A' else 'B (' + b['filename'] + ')'}")
        print(f"  ELO 更新：{a['filename']} {a['elo']}→{new_a}  |  {b['filename']} {b['elo']}→{new_b}")
        print(f"  成功/失敗：{ok}/{fail}  耗時：{elapsed:.2f}s\n")

        time.sleep(0.3)  # 稍微間隔，模擬實際使用節奏

    # 最終報告
    avg = sum(round_times) / len(round_times)
    print("=" * 45)
    print(f"✅ 完成 {ROUNDS} 回合測試")
    print(f"   總票數：{total_ok + total_fail}（成功 {total_ok}，失敗 {total_fail}）")
    print(f"   平均每回合耗時：{avg:.2f} 秒")
    print(f"   最慢回合：{max(round_times):.2f} 秒")
    print(f"   最快回合：{min(round_times):.2f} 秒")
    if total_fail == 0:
        print("\n🎉 全部通過！50 人同時投票沒有問題。")
    else:
        print(f"\n⚠️  有 {total_fail} 票失敗，請注意 Supabase RLS 或網路狀況。")

if __name__ == "__main__":
    main()
    input("\n按 Enter 關閉視窗...")
