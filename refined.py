"""
GMGN Wallet Refiner — BASE CHAIN
=================================
Reads addresses from base_results.csv (column: "address"),
fetches 7-day profit stats + common stats for each wallet from GMGN,
applies all filters, and saves passing wallets to baserefined.csv.
"""

import csv
import json
import time
import random
import urllib.request
import urllib.error
from datetime import datetime

# ─────────────────────────────────────────────
#  CONFIG
# ─────────────────────────────────────────────
INPUT_CSV             = "base_results.csv"
OUTPUT_CSV            = "baserefined.csv"

# PnL stat filters (7-day window)
MIN_WINRATE           = 0.63
MAX_WINRATE           = 0.9
MAX_PNL_LT_ND5        = 30
MAX_PNL_ND5_0X        = 60
MIN_PNL_0X_2X         = 15
MIN_PNL_2X_5X         = 0
MIN_PNL_GT_5X         = 0

# Social / common stat filters
MIN_FOLLOW_COUNT      = 20
MAX_FOLLOW_COUNT      = 75
MIN_REMARK_COUNT      = 0
MAX_REMARK_COUNT      = None

REQUEST_DELAY_SEC     = 1.9
REQUEST_DELAY_JITTER  = 0.7
# ─────────────────────────────────────────────

# ─────────────────────────────────────────────
#  AUTH — refresh these when 401s start again
#  (~30 min expiry on BEARER and __cf_bm cookie)
# ─────────────────────────────────────────────
DEVICE_ID = "c4ea5ed1-593d-4595-9237-0ac661aa2620"
FP_DID    = "c08073aa11d15b71d86d950c99a0b034"
CLIENT_ID = "gmgn_web_20260531-583-2f19d24"
APP_VER   = "20260531-583-2f19d24"

BEARER = (
    "eyJhbGciOiJFUzI1NiIsInR5cCI6IkpXVCJ9.eyJhdWQiOiJnbWduLmFpL2FjY2VzcyIsImRhdGEiOnsidXNlcl9pZCI6ImM4NjM0ODlkLWM2M2MtNDNjNi1iMDM2LTgwZTVlYjRiNjJhMSIsImNsaWVudF9pZCI6ImdtZ25fd2ViXzIwMjYwNTIyLTM0My00NDNiNTY1IiwiZGV2aWNlX2lkIjoiYzRlYTVlZDEtNTkzZC00NTk1LTkyMzctMGFjNjYxYWEyNjIwIiwiZmF0aGVyX2lkIjoiY2MyYjdhMjUtMDgwNS00NDI0LWEzMmItNTBiODIzZjA4OGY1IiwiZmluZ2VycHJpbnQiOiJ2MTY5MGEwOWI5NThlNjdiYzE2YzAyYmUwMjkwYTZhZGZhIiwiYXBwIjoiZ21nbiIsInBsYXRmb3JtIjoid2ViIn0sImV4cCI6MTc4MDc2NzI2MywiaWF0IjoxNzgwNzY1NDYzLCJpc3MiOiJnbWduLmFpL3NpZ25lciIsImp0aSI6Ijg3NzFiZGQ0LTg5MTAtNDExYy1iNTM5LWRlYzg2Zjc2M2M4ZSIsIm5iZiI6MTc4MDc2NTQ2Mywic3ViIjoiZ21nbi5haS9hY2Nlc3MiLCJ1c2VyX2lkIjoiYzg2MzQ4OWQtYzYzYy00M2M2LWIwMzYtODBlNWViNGI2MmExIiwidmVyIjoiMS4wIn0.8C9Sx56TwU7k9RnMe5hKQrSkeKRcrKtJULuASG6mcJKUgUukxQBFfrn6Gm1mdCSl_-6WBQeevwi_Kom9oQlgjg"
)

COOKIE = (
    "_did=7eda44bcbc92554c7c57b1e1f5f761d4; "
    "sid=gmgn%7Ceb6ac80bd8eb0d4e8add1ae61ecbdafa; "
    "_ga_UGLVBMV4Z0=GS1.2.1780250470573143.95068faaf4c1f302c7b5213087f5cdf2.YIo6MGjouuZChRBkaPLCIg%3D%3D.Zp5cZt5CqQTkUq6MxeJ13Q%3D%3D.qUggdMCrV8iCCqR5uUaKfw%3D%3D.mgZZSbTmwpHPhNU7nTbhDA%3D%3D"
)
# ─────────────────────────────────────────────

BASE_PARAMS = (
    f"?device_id={DEVICE_ID}"
    f"&fp_did={FP_DID}"
    f"&client_id={CLIENT_ID}"
    f"&from_app=gmgn&app_ver={APP_VER}"
    f"&tz_name=Africa%2FLagos&tz_offset=3600"
    f"&app_lang=en-US&os=web&worker=0"
)

STAT_URL        = "https://gmgn.ai/pf/api/v1/wallet/base/{address}/profit_stat/7d" + BASE_PARAMS
COMMON_STAT_URL = "https://gmgn.ai/api/v1/wallet_common_stat/base/{address}" + BASE_PARAMS


def make_headers(address=""):
    return {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/122.0.0.0 Safari/537.36"
        ),
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en;q=0.6",
        "Authorization": f"Bearer {BEARER}",
        "Cookie": COOKIE,
        "Referer": f"https://gmgn.ai/base/address/{address}" if address else "https://gmgn.ai/",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
    }


def load_addresses(filepath):
    addresses = []
    with open(filepath, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            addr = row.get("address", "").strip().lower()
            if addr:
                addresses.append((addr, row))
    return addresses


def fetch_json(url, address_label, address=""):
    req = urllib.request.Request(url, headers=make_headers(address))
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        print(f"    [HTTP {e.code}] {address_label}")
        if e.code == 401:
            print("    ⚠  Bearer token expired — update BEARER and COOKIE in the AUTH block")
    except urllib.error.URLError as e:
        print(f"    [URL ERROR] {address_label}: {e.reason}")
    except Exception as e:
        print(f"    [ERROR] {address_label}: {e}")
    return None


def fetch_pnl_stat(address):
    data = fetch_json(STAT_URL.format(address=address), address, address=address)
    if data:
        return data.get("data", {}).get("pnl_detail", None)
    return None


def fetch_common_stat(address):
    data = fetch_json(COMMON_STAT_URL.format(address=address), address, address=address)
    if data:
        return data.get("data", None)
    return None


def passes_pnl_filters(pnl):
    try:
        winrate    = float(pnl.get("winrate", 0) or 0)
        lt_nd5     = int(pnl.get("pnl_lt_nd5_num", 0) or 0)
        nd5_0x     = int(pnl.get("pnl_nd5_0x_num", 0) or 0)
        pnl_0x_2x = int(pnl.get("pnl_0x_2x_num", 0) or 0)
        pnl_2x_5x = int(pnl.get("pnl_2x_5x_num", 0) or 0)
        pnl_gt_5x = int(pnl.get("pnl_gt_5x_num", 0) or 0)
    except (ValueError, TypeError):
        return False

    if winrate    < MIN_WINRATE:     return False
    if winrate    > MAX_WINRATE:     return False
    if lt_nd5     > MAX_PNL_LT_ND5: return False
    if nd5_0x     > MAX_PNL_ND5_0X: return False
    if pnl_0x_2x < MIN_PNL_0X_2X:  return False
    if pnl_2x_5x < MIN_PNL_2X_5X:  return False
    if pnl_gt_5x < MIN_PNL_GT_5X:  return False
    return True


def passes_common_filters(common):
    try:
        follow_count = int(common.get("follow_count", 0) or 0)
        remark_count = int(common.get("remark_count", 0) or 0)
    except (ValueError, TypeError):
        return False

    if follow_count < MIN_FOLLOW_COUNT:                                  return False
    if MAX_FOLLOW_COUNT is not None and follow_count > MAX_FOLLOW_COUNT: return False
    if remark_count < MIN_REMARK_COUNT:                                  return False
    if MAX_REMARK_COUNT is not None and remark_count > MAX_REMARK_COUNT: return False
    return True


def jitter_sleep():
    time.sleep(max(0.1, REQUEST_DELAY_SEC + random.uniform(-REQUEST_DELAY_JITTER, REQUEST_DELAY_JITTER)))


def main():
    print("GMGN Wallet Refiner — BASE CHAIN")
    print(f"Started : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    print(
        f"PnL     -> winrate=[{MIN_WINRATE}, {MAX_WINRATE}], "
        f"max_lt_nd5={MAX_PNL_LT_ND5}, max_nd5_0x={MAX_PNL_ND5_0X}, "
        f"min_0x_2x={MIN_PNL_0X_2X}, min_2x_5x={MIN_PNL_2X_5X}, min_gt_5x={MIN_PNL_GT_5X}"
    )
    print(
        f"Social  -> follow=[{MIN_FOLLOW_COUNT}, {MAX_FOLLOW_COUNT}], "
        f"remark=[{MIN_REMARK_COUNT}, {MAX_REMARK_COUNT}]\n"
    )

    entries = load_addresses(INPUT_CSV)
    if not entries:
        print(f"ERROR: No addresses found in {INPUT_CSV}")
        return

    print(f"Loaded {len(entries)} address(es) from {INPUT_CSV}\n")

    sample_row = entries[0][1] if entries else {}
    base_fields = list(sample_row.keys())
    extra_fields = [
        "winrate_7d", "token_num_7d",
        "pnl_lt_nd5_num", "pnl_nd5_0x_num",
        "pnl_0x_2x_num", "pnl_2x_5x_num", "pnl_gt_5x_num",
        "follow_count", "remark_count",
    ]
    all_fields = base_fields + [f for f in extra_fields if f not in base_fields]

    refined = []
    passed  = 0
    failed  = 0
    errored = 0

    for idx, (addr, original_row) in enumerate(entries, 1):
        print(f"[{idx}/{len(entries)}] {addr[:20]}... ", end="", flush=True)

        # ── Step 1: PnL filter ──
        pnl = fetch_pnl_stat(addr)
        jitter_sleep()

        if pnl is None:
            print("skipped (pnl fetch error)")
            errored += 1
            continue

        if not passes_pnl_filters(pnl):
            print(f"✗ fail [pnl]  winrate={float(pnl.get('winrate', 0)):.2%}")
            failed += 1
            continue

        # ── Step 2: Common stat filter (only fetched if PnL passed) ──
        common = fetch_common_stat(addr)
        jitter_sleep()

        if common is None:
            print("skipped (common stat fetch error)")
            errored += 1
            continue

        if not passes_common_filters(common):
            follow = common.get("follow_count", "?")
            remark = common.get("remark_count", "?")
            print(f"✗ fail [social]  follows={follow}  remarks={remark}")
            failed += 1
            continue

        # ── PASSED all filters ──
        follow_count = int(common.get("follow_count", 0) or 0)
        remark_count = int(common.get("remark_count", 0) or 0)
        winrate      = float(pnl.get("winrate", 0))
        print(
            f"✓ PASS  winrate={winrate:.2%}  "
            f"follows={follow_count}  remarks={remark_count}  "
            f"gt5x={pnl.get('pnl_gt_5x_num')}"
        )

        row = dict(original_row)
        row["winrate_7d"]     = round(winrate, 6)
        row["token_num_7d"]   = pnl.get("token_num", "")
        row["pnl_lt_nd5_num"] = pnl.get("pnl_lt_nd5_num", "")
        row["pnl_nd5_0x_num"] = pnl.get("pnl_nd5_0x_num", "")
        row["pnl_0x_2x_num"]  = pnl.get("pnl_0x_2x_num", "")
        row["pnl_2x_5x_num"]  = pnl.get("pnl_2x_5x_num", "")
        row["pnl_gt_5x_num"]  = pnl.get("pnl_gt_5x_num", "")
        row["follow_count"]   = follow_count
        row["remark_count"]   = remark_count
        refined.append(row)
        passed += 1

    # ── Save output ──
    if refined:
        with open(OUTPUT_CSV, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=all_fields, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(refined)
        print(f"\nSaved {len(refined)} wallet(s) → {OUTPUT_CSV}")
    else:
        print("\nNo wallets passed the filters. Output file not written.")

    print("\n" + "=" * 55)
    print(f"  REFINE COMPLETE  [BASE CHAIN]")
    print(f"  Input wallets   : {len(entries)}")
    print(f"  Passed filters  : {passed}")
    print(f"  Failed filters  : {failed}")
    print(f"  Fetch errors    : {errored}")
    print(f"  Output file     : {OUTPUT_CSV}")
    print("=" * 55)


if __name__ == "__main__":
    main()
