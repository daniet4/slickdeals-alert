#!/usr/bin/env python3
import json
import os
import re
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from urllib.parse import quote
from zoneinfo import ZoneInfo

CONFIG_FILE = "../config/feeds.json"
STATE_FILE = "../seen_guids.json"
DISCORD_WEBHOOK = os.environ.get("DISCORD_WEBHOOK_URL")
DISCORD_ROLE_ID = os.environ.get("DISCORD_ROLE_ID", "")

NS = {
    "dc": "http://purl.org/dc/elements/1.1/",
    "content": "http://purl.org/rss/1.0/modules/content/",
}


def load_config():
    path = os.path.join(os.path.dirname(__file__), CONFIG_FILE)
    with open(path) as f:
        return json.load(f)


def get_feed_url(feed):
    if "url" in feed:
        url = feed["url"]
        if "rss=1" not in url:
            sep = "&" if "?" in url else "?"
            url = f"{url}{sep}rss=1"
        return url
    filter_str = feed["filter"]
    encoded = quote(filter_str, safe="@|*()-")
    return f"https://slickdeals.net/newsearch.php?q={encoded}&rss=1"


def fetch_rss(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read()


def parse_rss(xml_data, feed_name):
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
            "feed_guid": f"{feed_name}:{guid}",
            "title": title,
            "link": link,
            "creator": creator,
            "thumb_score": thumb_score,
            "pubdate_pst": pubdate_pst,
            "feed_name": feed_name,
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


def process_feed(feed, seen):
    print(f"\n--- {feed['name']} ---")
    url = get_feed_url(feed)
    print(f"Fetching RSS feed...")
    xml_data = fetch_rss(url)

    print("Parsing items...")
    items = parse_rss(xml_data, feed["name"])
    print(f"Found {len(items)} items total")

    threshold = feed.get("thumb_threshold", 5)
    qualifying = [i for i in items if i["thumb_score"] >= threshold]
    new_items = [i for i in qualifying if i["feed_guid"] not in seen]

    if new_items:
        print(f"New qualifying items: {len(new_items)}")
        for item in new_items:
            print(f"  {item['title']} (score: +{item['thumb_score']})")
    else:
        print("No new qualifying items")

    all_qualifying_guids = {i["feed_guid"] for i in qualifying}
    seen.update(all_qualifying_guids)
    return new_items


def send_notifications(items):
    if not items:
        print("Nothing to notify")
        return

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
                {"name": "Feed", "value": item["feed_name"], "inline": True},
                {"name": "Thumb Score", "value": f"+{item['thumb_score']}", "inline": True},
                {"name": "Posted by", "value": item["creator"], "inline": True},
                {"name": "Date (PST)", "value": item["pubdate_pst"], "inline": False},
            ],
        }
        payload_data = {"embeds": [embed]}
        if DISCORD_ROLE_ID:
            payload_data["content"] = f"<@&{DISCORD_ROLE_ID}>"
            payload_data["allowed_mentions"] = {"roles": [DISCORD_ROLE_ID]}
        payload = json.dumps(payload_data).encode("utf-8")
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
    feeds = load_config()
    print(f"Loaded {len(feeds)} feed(s) from config")

    seen = load_seen()
    print(f"Loaded {len(seen)} previously seen GUIDs")

    all_new = []
    for feed in feeds:
        new = process_feed(feed, seen)
        all_new.extend(new)

    print(f"\nTotal new items across all feeds: {len(all_new)}")
    send_notifications(all_new)

    save_seen(seen)
    print(f"Saved {len(seen)} seen GUIDs")


if __name__ == "__main__":
    main()
