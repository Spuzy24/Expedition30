#!/usr/bin/env python3
"""Scan flight-deal / error-fare feeds for Japan deals (optionally from our region).

Deal sites catch flash sales and mistake fares that normal searching misses
(they disappear in hours). Run this at the start of every hunt and whenever
monitoring. It only reads public RSS feeds. Feeds known to block bots
(Secret Flying, Jack's Flight Club) must be checked in a browser instead.

Usage:
  python3 deals.py                 # Japan deals, last 120 days, all feeds
  python3 deals.py --days 30 --region   # only items that also mention a region origin
  python3 deals.py --any-asia      # widen to Asia hubs (Seoul, Taipei, Beijing...) for self-transfer ideas
  python3 deals.py --json

Benchmarks: the fly4free.pl "japonia" tag feed is a long history of Japan
fares from Poland in PLN. Useful to judge what "cheap" means. Convert with fx.py.
"""
import argparse
import datetime as dt
import email.utils
import html
import json
import re
import sys
import time
import urllib.request
import xml.etree.ElementTree as ET

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Safari/537.36"

# (name, url, language). Tested 2026-10-04. Status noted where flaky.
FEEDS = [
    ("fly4free.com Europe", "https://www.fly4free.com/flights/flight-deals/europe/feed/", "en"),
    ("fly4free.com Asia", "https://www.fly4free.com/flights/flight-deals/asia/feed/", "en"),
    ("fly4free.com all", "https://www.fly4free.com/feed/", "en"),
    ("fly4free.pl Japonia tag", "https://www.fly4free.pl/tag/japonia/feed/", "pl"),
    ("fly4free.pl all", "https://www.fly4free.pl/feed/", "pl"),
    ("urlaubspiraten.de", "https://www.urlaubspiraten.de/feed", "de"),
    ("urlaubspiraten.at", "https://www.urlaubspiraten.at/feed", "de"),
    ("travel-dealz.de search japan", "https://travel-dealz.de/?s=japan&feed=rss2", "de"),
    ("travel-dealz.de", "https://travel-dealz.de/feed/", "de"),
    ("travel-dealz.com", "https://travel-dealz.com/feed/", "en"),
    ("piratinviaggio.it", "https://www.piratinviaggio.it/feed", "it"),
    ("travelpirates.com", "https://www.travelpirates.com/feed", "en"),
    ("theflightdeal.com", "https://www.theflightdeal.com/feed/", "en"),
    ("loyaltylobby.com", "https://loyaltylobby.com/feed/", "en"),
]

JAPAN = [
    "japan", "japon", "japón", "japão", "giappone", "japonia", "japonii", "japonsko", "japán",
    "japonska", "japanu", "japana", "tokyo", "tokio", "tokija", "osaka", "osace", "osaki", "nagoya", "nagoji", "fukuoka",
    "sapporo", "okinawa", "naha", "narita", "haneda", "kansai", "kyoto", "kioto",
    r"\bnrt\b", r"\bhnd\b", r"\bkix\b", r"\bngo\b", r"\bfuk\b", r"\bcts\b", r"\boka\b",
]
ASIA_HUBS = [
    "seoul", "incheon", "korea", "korei", "südkorea", "taipei", "taiwan", "tajwan", "beijing", "peking", "pekin",
    "shanghai", "szanghaj", "guangzhou", "chengdu", "hong kong", "hongkong", "bangkok", "manila",
    "singapore", "singapur", "kuala lumpur", "tashkent", "taszkent", "almaty", r"\bicn\b", r"\btpe\b", r"\bpek\b",
    r"\bpvg\b", r"\bhkg\b", r"\bbkk\b",
]
# Non-flight noise (hotel, cruise, package-tour, eSIM, voucher posts)
NOISE = [
    "hotel", "resort", "/double", "cruise", "kreuzfahrt", "nächte", "esim", "gutschein", "pacchett",
    "tour del", "rundreise", "pauschal", "noclegi", "wycieczk", "hostel", "ryokan",
]
REGION = [
    "zagreb", "zagrzeb", "zagabria", "ljubljana", "lublana", "lubiana", "laibach", "graz", "vienna", "wien",
    "wiedeń", "vídeň", "bécs", "budapest", "budapeszt", "venice", "venezia", "venedig", "wenecja", "treviso",
    "trieste", "triest", "munich", "münchen", "monachium", "mnichov", "belgrade", "belgrad", "beograd",
    "bratislava", "bratysława", "pressburg", "prague", "prag", "praga", "praha", "milan", "milano", "mailand",
    "bologna", "klagenfurt", "rijeka", "pula", "split", "zadar", "sarajevo", "bergamo",
    r"\bzag\b", r"\blju\b", r"\bgrz\b", r"\bvie\b", r"\bbud\b", r"\bvce\b", r"\btsf\b", r"\bmuc\b",
    r"\bbeg\b", r"\bbts\b", r"\bprg\b", r"\bmxp\b", r"\bbgy\b",
]


def rx(words):
    return re.compile("|".join(w if w.startswith("\\b") else re.escape(w) for w in words), re.I)


def fetch(url, timeout=25):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/rss+xml,application/xml,*/*"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def parse(raw):
    root = ET.fromstring(raw)
    items = []
    for it in root.iter("item"):
        g = lambda tag: (it.findtext(tag) or "").strip()
        desc = re.sub(r"<[^>]+>", " ", html.unescape(g("description")))
        items.append({"title": html.unescape(g("title")), "link": g("link"),
                      "date": g("pubDate"), "text": re.sub(r"\s+", " ", desc)[:400]})
    ns = {"a": "http://www.w3.org/2005/Atom"}
    for e in root.iter("{http://www.w3.org/2005/Atom}entry"):
        link = e.find("a:link", ns)
        items.append({"title": (e.findtext("a:title", "", ns) or "").strip(),
                      "link": link.get("href") if link is not None else "",
                      "date": e.findtext("a:updated", "", ns), "text": ""})
    return items


def age_days(datestr):
    try:
        d = email.utils.parsedate_to_datetime(datestr)
    except Exception:
        try:
            d = dt.datetime.fromisoformat(datestr.replace("Z", "+00:00"))
        except Exception:
            return None
    if d.tzinfo is None:
        d = d.replace(tzinfo=dt.timezone.utc)
    return (dt.datetime.now(dt.timezone.utc) - d).days


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--days", type=int, default=120)
    p.add_argument("--region", action="store_true", help="require a home-region origin mention")
    p.add_argument("--any-asia", action="store_true", help="also match Asian hubs")
    p.add_argument("--include-noise", action="store_true", help="keep hotel/cruise/package posts")
    p.add_argument("--json", action="store_true")
    a = p.parse_args()

    dest_rx = rx(JAPAN + (ASIA_HUBS if a.any_asia else []))
    reg_rx = rx(REGION)
    noise_rx = rx(NOISE)
    seen, hits, status = set(), [], []
    for name, url, _lang in FEEDS:
        try:
            items = parse(fetch(url))
            status.append((name, f"ok {len(items)}"))
        except Exception as e:
            status.append((name, f"FAIL {type(e).__name__}: {str(e)[:60]}"))
            continue
        for it in items:
            blob = f"{it['title']} {it['text']}"
            if not dest_rx.search(blob):
                continue
            if not a.include_noise and noise_rx.search(it["title"]):
                continue
            if a.region and not reg_rx.search(blob):
                continue
            ad = age_days(it["date"])
            if ad is not None and ad > a.days:
                continue
            key = it["link"] or it["title"]
            if key in seen:
                continue
            seen.add(key)
            it.update(feed=name, age_days=ad, region_match=bool(reg_rx.search(blob)))
            hits.append(it)
        time.sleep(0.5)

    hits.sort(key=lambda h: (h["age_days"] if h["age_days"] is not None else 9999))
    if a.json:
        print(json.dumps({"feeds": status, "hits": hits}, ensure_ascii=False, indent=1))
        return
    for name, st in status:
        print(f"  [{st}] {name}", file=sys.stderr)
    print(f"\n{len(hits)} matching deals (≤{a.days} days old)\n")
    for h in hits:
        flag = "★REGION " if h["region_match"] else ""
        print(f"{h['age_days'] if h['age_days'] is not None else '?':>4}d  {flag}{h['title']}\n       {h['feed']} | {h['link']}")


if __name__ == "__main__":
    main()
