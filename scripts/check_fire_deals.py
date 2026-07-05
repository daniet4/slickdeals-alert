#!/usr/bin/env python3
import json
import os
import re
import urllib.request

SEARCH_URL = "https://slickdeals.net/search?q=&searchtype=normal&sort=recent&filters%5Brating%5D%5B%5D=firedeal&filters%5Bdate%5D%5B%5D=7"
THUMB_THRESHOLD = 100
STATE_FILE = "../fire_deals_seen.json"
DISCORD_WEBHOOK = os.environ.get("DISCORD_WEBHOOK_URL")
DISCORD_ROLE_ID = os.environ.get("DISCORD_ROLE_ID", "")


def resolve_nuxt_data(data, ref):
    if isinstance(ref, list):
        return [resolve_nuxt_data(data, item) for item in ref]
    if isinstance(ref, dict):
        return {k: resolve_nuxt_data(data, v) for k, v in ref.items()}
    if isinstance(ref, int) and ref < len(data):
        val = data[ref]
        if isinstance(val, (str, int, float, bool)) or val is None:
            return val
        return resolve_nuxt_data(data, val)
    return ref


def extract_nuxt_data(html):
    match = re.search(
        r'<script[^>]*id="__NUXT_DATA__"[^>]*>(.*?)</script>', html, re.DOTALL
    )
    if not match:
        print("ERROR: Could not find __NUXT_DATA__ in HTML")
        return None
    return json.loads(match.group(1))


def fetch_page(url):
    print(f"  Fetching {url}")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        html = resp.read().decode("utf-8", errors="replace")
    print(f"  Fetched {len(html):,} bytes")
    return html


def get_page_url(base_url, page_num):
    sep = "&" if "?" in base_url else "?"
    return f"{base_url}{sep}page={page_num}"


def parse_deals_from_page(data):
    page_data = resolve_nuxt_data(data, data[4]["pageData"])
    deals_raw = page_data.get("deals", [])
    pagination = page_data.get("pagination", {})

    deals = []
    for deal in deals_raw:
        deal["dealThreadUrl"] = "https://slickdeals.net" + deal.get("dealThreadUrl", "")
        deals.append(deal)

    return deals, pagination


def main():
    print("=== Slickdeals Fire Deals 100+ ===")

    all_deals = []
    html = fetch_page(SEARCH_URL)
    data = extract_nuxt_data(html)
    if not data:
        return

    deals, pagination = parse_deals_from_page(data)
    print(f"  Page {pagination.get('currentPage', 1)}: {len(deals)} deals")
    all_deals.extend(deals)

    total_pages = pagination.get("totalPages", 1)
    for page in range(2, total_pages + 1):
        url = get_page_url(SEARCH_URL, page)
        html = fetch_page(url)
        data = extract_nuxt_data(html)
        if not data:
            continue
        deals, pagination = parse_deals_from_page(data)
        print(f"  Page {pagination.get('currentPage', 1)}: {len(deals)} deals")
        all_deals.extend(deals)

    print(f"\nTotal deals fetched: {len(all_deals)}")

    qualifying = [d for d in all_deals if d.get("socialVoteCount", 0) >= THUMB_THRESHOLD]
    print(f"Qualifying (score >= {THUMB_THRESHOLD}): {len(qualifying)}")

    for d in sorted(qualifying, key=lambda x: x["socialVoteCount"], reverse=True):
        print(f"  +{d['socialVoteCount']:>4} | {d.get('dealTitle', '')[:70]}")


if __name__ == "__main__":
    main()
