#!/usr/bin/env python3
import json
import os
import re
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from zoneinfo import ZoneInfo

RSS_URL = (
    "https://slickdeals.net/newsearch.php"
    "?q=@title%20%22iPhone%2015%22%20|%20%22iPhone%2016%22%20|%20%22iPhone%2017%22%20"
    "-(case%20|%20controller%20|%20charg*%20|%20protector*%20|%20reader%20|%20adapter%20|%20wallet)"
    "&rss=1"
)
THUMB_THRESHOLD = 5
STATE_FILE = "../seen_guids.json"
DISCORD_WEBHOOK = os.environ.get("DISCORD_WEBHOOK_URL")

NS = {
    "dc": "http://purl.org/dc/elements/1.1/",
    "content": "http://purl.org/rss/1.0/modules/content/",
}


def fetch_rss():
    req = urllib.request.Request(RSS_URL, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read()


def parse_rss(xml_data):
    root = ET.fromstring(xml_data)
    items = []
    for item in root.iter("item"):
        guid = item.findtext("guid", "")
        title = item.findtext("title", "")
        link = item.findtext("link", "")
        creator_el = item.find("dc:creator", NS)
        creator = creator_el.text.strip() if creator_el is not None and creator_el.text else ""
        content_el = item.find("content:encoded", NS)
        content = content_el.text if content_el is not None and content_el.text else ""

        thumb_score = 0
        match = re.search(r"Thumb Score:\s*([+-]?\d+)", content)
        if match:
            thumb_score = int(match.group(1))

        pubdate_el = item.find("pubDate")
        pubdate_str = pubdate_el.text if pubdate_el is not None and pubdate_el.text else ""
        pubdate_utc = None
        pubdate_pst = ""
        if pubdate_str:
            try:
                pubdate_utc = parsedate_to_datetime(pubdate_str)
                pubdate_pst = pubdate_utc.astimezone(
                    ZoneInfo("America/Los_Angeles")
                ).strftime("%b %d, %Y %I:%M %p %Z")
            except (ValueError, TypeError):
                pass

        items.append({
            "guid": guid,
            "title": title,
            "link": link,
            "creator": creator,
            "thumb_score": thumb_score,
            "pubdate_pst": pubdate_pst,
        })
    return items


def load_seen():
    path = os.path.join(os.path.dirname(__file__), STATE_FILE)
    if os.path.exists(path):
        with open(path) as f:
            return set(json.load(f))
    return set()


def save_seen(guids):
    path = os.path.join(os.path.dirname(__file__), STATE_FILE)
    with open(path, "w") as f:
        json.dump(sorted(guids), f)


def notify_discord(items):
    if not DISCORD_WEBHOOK:
        print("DISCORD_WEBHOOK_URL not set, skipping notification")
        return

    for item in items:
        color = 0x00FF00 if item["thumb_score"] >= 10 else 0xFFA500
        embed = {
            "title": item["title"][:256],
            "url": item["link"],
            "color": color,
            "fields": [
                {"name": "Thumb Score", "value": f"+{item['thumb_score']}", "inline": True},
                {"name": "Posted by", "value": item["creator"], "inline": True},
                {"name": "Date (PST)", "value": item["pubdate_pst"], "inline": False},
            ],
        }
        payload = json.dumps({"embeds": [embed]}).encode("utf-8")
        req = urllib.request.Request(
            DISCORD_WEBHOOK,
            data=payload,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "slickdeals-alert/1.0",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                print(f"Sent: {item['title']} (status {resp.status})")
        except urllib.error.HTTPError as e:
            body = e.read().decode(errors="replace")
            print(f"Discord returned {e.code}: {body}")
            raise


def main():
    print("Fetching RSS feed...")
    xml_data = fetch_rss()

    print("Parsing items...")
    items = parse_rss(xml_data)
    print(f"Found {len(items)} items total")

    seen = load_seen()
    print(f"Loaded {len(seen)} previously seen GUIDs")

    qualifying = [i for i in items if i["thumb_score"] >= THUMB_THRESHOLD]
    new_items = [i for i in qualifying if i["guid"] not in seen]

    if new_items:
        print(f"New qualifying items: {len(new_items)}")
        for item in new_items:
            print(f"  {item['title']} (score: +{item['thumb_score']})")
        notify_discord(new_items)
    else:
        print("No new qualifying items")

    all_qualifying_guids = {i["guid"] for i in qualifying}
    seen.update(all_qualifying_guids)
    save_seen(seen)
    print(f"Saved {len(seen)} seen GUIDs")


if __name__ == "__main__":
    main()
