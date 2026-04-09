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

# PnL stat filters (30-day window)
MIN_WINRATE           = 0.68    # minimum win rate (0.0 – 1.0)
MAX_WINRATE           = 0.89    # maximum win rate — set to 1.0 for no upper limit
MAX_PNL_LT_ND5        = 100       # max trades with PnL < -50%
MAX_PNL_ND5_0X        = 250      # max trades with PnL between -50% and 0%
MIN_PNL_0X_2X         = 3       # min trades with PnL between 0x and 2x
MIN_PNL_2X_5X         = 3       # min trades with PnL between 2x and 5x
MIN_PNL_GT_5X         = 1       # min trades with PnL > 5x

# Social / common stat filters
MIN_FOLLOW_COUNT      = 3       # minimum follower count
MAX_FOLLOW_COUNT      = 75    # maximum follower count — set to None for no limit
MIN_REMARK_COUNT      = 0       # minimum remark count
MAX_REMARK_COUNT      = None    # maximum remark count — set to None for no limit

REQUEST_DELAY_SEC     = 1.2
REQUEST_DELAY_JITTER  = 0.4
# ─────────────────────────────────────────────

STAT_URL = (
    "https://gmgn.ai/pf/api/v1/wallet/base/{address}/profit_stat/30d"
    "?device_id=11f6dfb1-0336-46c4-8e1d-af367e46824e"
    "&fp_did=3193ac961ff03f6fedd3dbc953744c51"
    "&client_id=gmgn_web_20260325-12049-2069c3a"
    "&from_app=gmgn&app_ver=20260325-12049-2069c3a"
    "&tz_name=Africa%2FLagos&tz_offset=3600"
    "&app_lang=en-US&os=web&worker=0"
)

COMMON_STAT_URL = (
    "https://gmgn.ai/api/v1/wallet_common_stat/base/{address}"
    "?device_id=11f6dfb1-0336-46c4-8e1d-af367e46824e"
    "&fp_did=3193ac961ff03f6fedd3dbc953744c51"
    "&client_id=gmgn_web_20260325-12049-2069c3a"
    "&from_app=gmgn&app_ver=20260325-12049-2069c3a"
    "&tz_name=Africa%2FLagos&tz_offset=3600"
    "&app_lang=en-US&os=web&worker=0"
)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
    "Referer": "https://gmgn.ai/",
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


def fetch_json(url, address_label):
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        print(f"    [HTTP {e.code}] {address_label}")
    except urllib.error.URLError as e:
        print(f"    [URL ERROR] {address_label}: {e.reason}")
    except Exception as e:
        print(f"    [ERROR] {address_label}: {e}")
    return None


def fetch_pnl_stat(address):
    data = fetch_json(STAT_URL.format(address=address), address)
    if data:
        return data.get("data", {}).get("pnl_detail", None)
    return None


def fetch_common_stat(address):
    data = fetch_json(COMMON_STAT_URL.format(address=address), address)
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
    passed = 0
    failed = 0
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
