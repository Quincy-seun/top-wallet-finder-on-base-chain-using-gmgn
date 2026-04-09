"""
GMGN Top Traders Scanner — BASE CHAIN (DEBUG MODE)
====================================================
Run this first to inspect the raw API response and find the correct field names.
Set DEBUG_MODE = False once fields are confirmed.
"""

import json
import time
import random
from collections import defaultdict
from datetime import datetime
import urllib.request
import urllib.error

# ─────────────────────────────────────────────
#  CONFIG
# ─────────────────────────────────────────────
MIN_APPEARANCES       = 3
MIN_PROFIT            = 0
MIN_UNREALIZED_PROFIT = 0
MAX_REALIZED_PROFIT   = 55000    # exclude wallets whose total realized profit exceeds this (USD)
MIN_ETH_BALANCE       = 0.04        # minimum ETH balance to include a wallet (enter as ETH, e.g. 0.1)
MAX_ETH_BALANCE       = 2     # maximum ETH balance — set to None for no limit (e.g. 10.0)
TOP_RANK_FILTER       = 100
REQUEST_DELAY_SEC     = 1.2
REQUEST_DELAY_JITTER  = 0.4
INPUT_FILE            = "base.txt"
OUTPUT_JSON           = "base_results.json"
OUTPUT_CSV            = "base_results.csv"
TIMESTAMP_OUTPUTS     = False

DEBUG_MODE            = False   # prints raw response for first CA, then exits
DEBUG_COINS           = 1      # how many coins to debug before stopping
# ─────────────────────────────────────────────

BASE_URL = (
    "https://gmgn.ai/vas/api/v1/token_traders/base/"
    "{ca}"
    "?device_id=11f6dfb1-0336-46c4-8e1d-af367e46824e"
    "&fp_did=3193ac961ff03f6fedd3dbc953744c51"
    "&client_id=gmgn_web_20260314-11734-a3ed6a7"
    "&from_app=gmgn&app_ver=20260314-11734-a3ed6a7"
    "&tz_name=Africa%2FLagos&tz_offset=3600"
    "&app_lang=en-US&os=web&worker=0"
    "&limit=100&orderby=profit&direction=desc"
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


def load_contracts(filepath):
    with open(filepath, "r") as f:
        lines = [l.strip().lower() for l in f if l.strip() and not l.startswith("#")]
    return lines


def parse_tag_rank(tag):
    if tag and tag.upper().startswith("TOP"):
        try:
            return int(tag[3:])
        except ValueError:
            pass
    return None


def fetch_raw(ca):
    """Fetch and return the full raw parsed JSON response."""
    url = BASE_URL.format(ca=ca)
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw)
    except urllib.error.HTTPError as e:
        print(f"    [HTTP {e.code}] {ca}")
    except urllib.error.URLError as e:
        print(f"    [URL ERROR] {ca}: {e.reason}")
    except Exception as e:
        print(f"    [ERROR] {ca}: {e}")
    return None


def fetch_traders(ca):
    url = BASE_URL.format(ca=ca)
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = resp.read().decode("utf-8")
            data = json.loads(raw)
            return data.get("data", {}).get("list", [])
    except urllib.error.HTTPError as e:
        print(f"    [HTTP {e.code}] {ca}")
    except urllib.error.URLError as e:
        print(f"    [URL ERROR] {ca}: {e.reason}")
    except Exception as e:
        print(f"    [ERROR] {ca}: {e}")
    return None


def debug_response(ca):
    print(f"\n{'='*60}")
    print(f"DEBUG: Fetching {ca}")
    print(f"{'='*60}")

    data = fetch_raw(ca)
    if data is None:
        print("No response received.")
        return

    print("\n--- TOP-LEVEL KEYS ---")
    print(list(data.keys()))

    # Dig into 'data' key
    inner = data.get("data", {})
    print(f"\n--- data KEYS ---")
    print(list(inner.keys()) if isinstance(inner, dict) else f"(not a dict: {type(inner)})")

    # Try to get the list
    trader_list = None
    if isinstance(inner, dict):
        for key in inner:
            val = inner[key]
            if isinstance(val, list) and len(val) > 0:
                print(f"\n--- Found list under data['{key}'] with {len(val)} items ---")
                trader_list = val
                break

    if trader_list is None:
        # Maybe the list is directly under root
        for key in data:
            val = data[key]
            if isinstance(val, list) and len(val) > 0:
                print(f"\n--- Found list directly under root['{key}'] with {len(val)} items ---")
                trader_list = val
                break

    if trader_list:
        print(f"\n--- FIRST TRADER ENTRY (all fields) ---")
        print(json.dumps(trader_list[0], indent=2))
        print(f"\n--- SECOND TRADER ENTRY (all fields) ---")
        if len(trader_list) > 1:
            print(json.dumps(trader_list[1], indent=2))
        print(f"\n--- AVAILABLE FIELD NAMES ---")
        print(list(trader_list[0].keys()))
        print(f"\n--- wallet_tag_v2 values for first 5 traders ---")
        for t in trader_list[:5]:
            print(f"  address={t.get('address','?')[:20]}...  wallet_tag_v2={repr(t.get('wallet_tag_v2'))}")
    else:
        print("\n--- FULL RAW RESPONSE (truncated to 2000 chars) ---")
        print(json.dumps(data, indent=2)[:2000])


def scan(contracts):
    wallet_data = defaultdict(lambda: {
        "appearances": 0,
        "coins": [],
        "total_realized_profit": 0.0,
        "total_unrealized_profit": 0.0,
        "ranks": [],
        "tags": [],
        "native_balance_wei": None,
    })

    total = len(contracts)
    for idx, ca in enumerate(contracts, 1):
        print(f"[{idx}/{total}] Scanning {ca} ...", end=" ", flush=True)
        traders = fetch_traders(ca)

        if traders is None:
            print("skipped (fetch error)")
        else:
            counted = 0
            for position, trader in enumerate(traders, 1):
                tag      = trader.get("wallet_tag_v2", "") or ""
                tag_rank = parse_tag_rank(tag)
                rank     = tag_rank if tag_rank is not None else position

                if rank > TOP_RANK_FILTER:
                    continue

                profit     = float(trader.get("realized_profit", 0) or 0)
                unrealized = float(trader.get("unrealized_profit", 0) or 0)

                if profit < MIN_PROFIT:
                    continue
                if unrealized < MIN_UNREALIZED_PROFIT:
                    continue

                addr = trader.get("address", "")
                if not addr:
                    continue

                wallet_data[addr]["appearances"]             += 1
                wallet_data[addr]["coins"].append(ca)
                wallet_data[addr]["total_realized_profit"]   += profit
                wallet_data[addr]["total_unrealized_profit"] += unrealized
                wallet_data[addr]["ranks"].append(rank)
                if tag:
                    wallet_data[addr]["tags"].append(tag)
                # native_balance is in Wei; store the latest seen value
                nb_raw = trader.get("native_balance", None)
                if nb_raw is not None and str(nb_raw).strip() != "":
                    try:
                        wallet_data[addr]["native_balance_wei"] = int(nb_raw)
                    except (ValueError, TypeError):
                        pass
                counted += 1

            print(f"{counted} qualifying traders")

        sleep_time = REQUEST_DELAY_SEC + random.uniform(
            -REQUEST_DELAY_JITTER, REQUEST_DELAY_JITTER
        )
        time.sleep(max(0.1, sleep_time))

    return wallet_data


def filter_and_rank(wallet_data):
    results = []
    for addr, info in wallet_data.items():
        if info["appearances"] < MIN_APPEARANCES:
            continue
        if info["total_realized_profit"] > MAX_REALIZED_PROFIT:
            continue
        # ETH balance filter
        nb_wei = info["native_balance_wei"]
        nb_eth = nb_wei / 1e18 if nb_wei is not None else None
        if nb_eth is not None and MIN_ETH_BALANCE is not None and nb_eth < MIN_ETH_BALANCE:
            continue
        if nb_eth is not None and MAX_ETH_BALANCE is not None and nb_eth > MAX_ETH_BALANCE:
            continue
        avg_rank = sum(info["ranks"]) / len(info["ranks"]) if info["ranks"] else None
        results.append({
            "address":                 addr,
            "appearances":             info["appearances"],
            "coins":                   info["coins"],
            "total_realized_profit":   round(info["total_realized_profit"],   4),
            "total_unrealized_profit": round(info["total_unrealized_profit"], 4),
            "avg_rank":                round(avg_rank, 2) if avg_rank else None,
            "best_rank":               min(info["ranks"]) if info["ranks"] else None,
            "tags":                    list(set(info["tags"])),
            "eth_balance_eth":         round(nb_eth, 6) if nb_eth is not None else "",
        })
    results.sort(key=lambda x: (-x["appearances"], -x["total_realized_profit"]))
    return results


def make_output_path(base_path):
    if not TIMESTAMP_OUTPUTS:
        return base_path
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    if "." in base_path:
        name, ext = base_path.rsplit(".", 1)
        return f"{name}_{ts}.{ext}"
    return f"{base_path}_{ts}"


def save_json(results, path):
    resolved = make_output_path(path)
    try:
        with open(resolved, "w") as f:
            json.dump(results, f, indent=2)
    except PermissionError:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        name, ext = path.rsplit(".", 1) if "." in path else (path, "json")
        resolved = f"{name}_{ts}.{ext}"
        with open(resolved, "w") as f:
            json.dump(results, f, indent=2)
    return resolved


def save_csv(results, path):
    import csv
    if not results:
        return path

    resolved = make_output_path(path)
    try:
        f_out = open(resolved, "w", newline="")
    except PermissionError:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        name, ext = path.rsplit(".", 1) if "." in path else (path, "csv")
        resolved = f"{name}_{ts}.{ext}"
        f_out = open(resolved, "w", newline="")

    fields = ["address", "appearances", "total_realized_profit",
              "total_unrealized_profit", "eth_balance_eth", "avg_rank", "best_rank", "tags", "coins"]
    with f_out:
        writer = csv.DictWriter(f_out, fieldnames=fields)
        writer.writeheader()
        for row in results:
            row_copy = dict(row)
            row_copy["coins"] = "|".join(row_copy["coins"])
            row_copy["tags"]  = "|".join(row_copy["tags"])
            writer.writerow(row_copy)

    return resolved


def print_summary(results, contracts, json_out, csv_out):
    print("\n" + "=" * 60)
    print(f"  SCAN COMPLETE  [BASE CHAIN]")
    print(f"  Coins scanned     : {len(contracts)}")
    print(f"  Wallets found     : {len(results)}")
    print(f"  Min appearances   : {MIN_APPEARANCES}")
    print(f"  Min profit filter : ${MIN_PROFIT:,.2f}")
    print(f"  Max profit filter : ${MAX_REALIZED_PROFIT:,.2f}")
    print(f"  Min ETH balance   : {MIN_ETH_BALANCE} ETH")
    print(f"  Max ETH balance   : {MAX_ETH_BALANCE} ETH")
    print(f"  Rank filter       : position 1-{TOP_RANK_FILTER}")
    print("=" * 60)
    if results:
        print(f"\n{'ADDRESS':<44} {'APPEAR':>6}  {'TOTAL PROFIT':>14}  {'AVG RANK':>8}")
        print("-" * 78)
        for r in results[:30]:
            print(
                f"{r['address']:<44} "
                f"{r['appearances']:>6}  "
                f"${r['total_realized_profit']:>13,.2f}  "
                f"{r['avg_rank']:>8.1f}"
            )
        if len(results) > 30:
            print(f"  ... and {len(results) - 30} more (see output files)")
    else:
        print("\n  No wallets met the criteria.")

    print(f"\nResults saved:")
    print(f"  JSON -> {json_out}")
    print(f"  CSV  -> {csv_out}")


def main():
    print("GMGN Top Traders Scanner - BASE CHAIN")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    contracts = load_contracts(INPUT_FILE)
    if not contracts:
        print(f"ERROR: {INPUT_FILE} is empty or not found.")
        return

    # ── DEBUG MODE: inspect raw response and exit ──
    if DEBUG_MODE:
        print(f"DEBUG MODE ON — inspecting first {DEBUG_COINS} coin(s)\n")
        for ca in contracts[:DEBUG_COINS]:
            debug_response(ca)
        print(f"\n{'='*60}")
        print("Set DEBUG_MODE = False at the top of the script to run the full scan.")
        return

    print(f"Loaded {len(contracts)} contract address(es) from {INPUT_FILE}\n")
    print(
        f"Config -> min_appearances={MIN_APPEARANCES}, min_profit=${MIN_PROFIT}, "
        f"min_unrealized=${MIN_UNREALIZED_PROFIT}, max_profit=${MAX_REALIZED_PROFIT}, eth={MIN_ETH_BALANCE}-{MAX_ETH_BALANCE}, top_rank=TOP{TOP_RANK_FILTER}\n"
    )

    wallet_data = scan(contracts)
    results     = filter_and_rank(wallet_data)

    json_out = save_json(results, OUTPUT_JSON)
    csv_out  = save_csv(results,  OUTPUT_CSV)

    print_summary(results, contracts, json_out, csv_out)


if __name__ == "__main__":
    main()
