"""
GMGN Wallet Refiner — BASE CHAIN
=================================
Reads addresses from base_results.csv (column: "address"),
fetches 7-day profit stats for each wallet from GMGN,
applies PnL filters, and saves passing wallets to baserefined.csv.
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
MIN_WINRATE           = 0.68    # minimum win rate (0.0 – 1.0)
MAX_PNL_LT_ND5        = 566       # max trades with PnL < -50%
MAX_PNL_ND5_0X        = 1566      # max trades with PnL between -50% and 0%
MIN_PNL_0X_2X         = 1       # min trades with PnL between 0x and 2x
MIN_PNL_2X_5X         = 0       # min trades with PnL between 2x and 5x
MIN_PNL_GT_5X         = 0       # min trades with PnL > 5x

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


def fetch_pnl_stat(address):
    url = STAT_URL.format(address=address)
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data.get("data", {}).get("pnl_detail", None)
    except urllib.error.HTTPError as e:
        print(f"    [HTTP {e.code}] {address}")
    except urllib.error.URLError as e:
        print(f"    [URL ERROR] {address}: {e.reason}")
    except Exception as e:
        print(f"    [ERROR] {address}: {e}")
    return None


def passes_filters(pnl):
    try:
        winrate      = float(pnl.get("winrate", 0) or 0)
        lt_nd5       = int(pnl.get("pnl_lt_nd5_num", 0) or 0)
        nd5_0x       = int(pnl.get("pnl_nd5_0x_num", 0) or 0)
        pnl_0x_2x   = int(pnl.get("pnl_0x_2x_num", 0) or 0)
        pnl_2x_5x   = int(pnl.get("pnl_2x_5x_num", 0) or 0)
        pnl_gt_5x   = int(pnl.get("pnl_gt_5x_num", 0) or 0)
    except (ValueError, TypeError):
        return False

    if winrate      < MIN_WINRATE:      return False
    if lt_nd5       > MAX_PNL_LT_ND5:  return False
    if nd5_0x       > MAX_PNL_ND5_0X:  return False
    if pnl_0x_2x   < MIN_PNL_0X_2X:   return False
    if pnl_2x_5x   < MIN_PNL_2X_5X:   return False
    if pnl_gt_5x   < MIN_PNL_GT_5X:    return False

    return True


def main():
    print("GMGN Wallet Refiner — BASE CHAIN")
    print(f"Started : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    print(f"Config  -> min_winrate={MIN_WINRATE}, max_lt_nd5={MAX_PNL_LT_ND5}, "
          f"max_nd5_0x={MAX_PNL_ND5_0X}, min_0x_2x={MIN_PNL_0X_2X}, "
          f"min_2x_5x={MIN_PNL_2X_5X}, min_gt_5x={MIN_PNL_GT_5X}\n")

    entries = load_addresses(INPUT_CSV)
    if not entries:
        print(f"ERROR: No addresses found in {INPUT_CSV}")
        return

    print(f"Loaded {len(entries)} address(es) from {INPUT_CSV}\n")

    # Collect all fieldnames from input CSV for passthrough
    sample_row = entries[0][1] if entries else {}
    base_fields = list(sample_row.keys())
    extra_fields = [
        "winrate_7d", "token_num_7d",
        "pnl_lt_nd5_num", "pnl_nd5_0x_num",
        "pnl_0x_2x_num", "pnl_2x_5x_num", "pnl_gt_5x_num",
    ]
    all_fields = base_fields + [f for f in extra_fields if f not in base_fields]

    refined = []
    passed = 0
    failed = 0
    errored = 0

    for idx, (addr, original_row) in enumerate(entries, 1):
        print(f"[{idx}/{len(entries)}] {addr[:20]}... ", end="", flush=True)

        pnl = fetch_pnl_stat(addr)

        if pnl is None:
            print("skipped (fetch error)")
            errored += 1
        elif passes_filters(pnl):
            print(f"✓ PASS  winrate={float(pnl.get('winrate',0)):.2%}  "
                  f"gt5x={pnl.get('pnl_gt_5x_num')}  "
                  f"2x-5x={pnl.get('pnl_2x_5x_num')}")
            row = dict(original_row)
            row["winrate_7d"]       = round(float(pnl.get("winrate", 0) or 0), 6)
            row["token_num_7d"]     = pnl.get("token_num", "")
            row["pnl_lt_nd5_num"]   = pnl.get("pnl_lt_nd5_num", "")
            row["pnl_nd5_0x_num"]   = pnl.get("pnl_nd5_0x_num", "")
            row["pnl_0x_2x_num"]    = pnl.get("pnl_0x_2x_num", "")
            row["pnl_2x_5x_num"]    = pnl.get("pnl_2x_5x_num", "")
            row["pnl_gt_5x_num"]    = pnl.get("pnl_gt_5x_num", "")
            refined.append(row)
            passed += 1
        else:
            print(f"✗ fail  winrate={float(pnl.get('winrate',0)):.2%}")
            failed += 1

        sleep_time = REQUEST_DELAY_SEC + random.uniform(
            -REQUEST_DELAY_JITTER, REQUEST_DELAY_JITTER
        )
        time.sleep(max(0.1, sleep_time))

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
