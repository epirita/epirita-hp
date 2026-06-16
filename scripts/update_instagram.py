#!/usr/bin/env python3
import os
import re
import sys
import html
import urllib.request
import xml.etree.ElementTree as ET

FEED_URL = os.environ.get("FEED_URL", "https://rss.app/feeds/JRTiVTLveGseBf9S.xml")
MAX_POSTS = 6
CAP_LEN = 70
ACCOUNT_URL = "https://www.instagram.com/datumo_yokohama/"

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDEX = os.path.join(ROOT, "index.html")
IMG_DIR = os.path.join(ROOT, "assets", "insta")

NS = {"media": "http://search.yahoo.com/mrss/"}
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def shortcode(link):
    m = re.search(r"/p/([^/?#]+)", link or "")
    return m.group(1) if m else None


def get_image(item):
    mc = item.find("media:content", NS)
    if mc is not None and mc.get("url"):
        return mc.get("url")
    desc = item.findtext("description") or ""
    m = re.search(r'<img[^>]+src="([^"]+)"', desc)
    return m.group(1) if m else None


def truncate(text, n):
    text = re.sub(r"\s+", " ", text or "").strip()
    return text if len(text) <= n else text[:n].rstrip() + "…"


def main():
    status = []
    data = fetch(FEED_URL)
    status.append("feed bytes: %d" % len(data))
    root = ET.fromstring(data)
    items = root.findall("./channel/item")[:MAX_POSTS]
    status.append("items: %d" % len(items))

    os.makedirs(IMG_DIR, exist_ok=True)
    for f in os.listdir(IMG_DIR):
        if f.lower().endswith((".jpg", ".jpeg", ".png")):
            os.remove(os.path.join(IMG_DIR, f))

    cards = []
    for it in items:
        link = (it.findtext("link") or "").strip()
        sc = shortcode(link) or (it.findtext("guid") or "post")
        sc = re.sub(r"[^A-Za-z0-9_-]", "", sc)[:40] or "post"
        img_url = get_image(it)
        if not img_url:
            status.append("%s: no image url" % sc)
            continue

        img_src = img_url
        try:
            img_data = fetch(img_url)
            fname = sc + ".jpg"
            with open(os.path.join(IMG_DIR, fname), "wb") as f:
                f.write(img_data)
            img_src = "assets/insta/" + fname
            status.append("%s: downloaded %d bytes" % (sc, len(img_data)))
        except Exception as e:
            status.append("%s: download FAILED (%s); hotlinking" % (sc, e))

        cap = html.escape(truncate(it.findtext("title") or "", CAP_LEN))
        href = html.escape(link or ACCOUNT_URL)
        src = html.escape(img_src)
        cards.append(
            '<div class="insta-card">'
            '<a href="%s" target="_blank" rel="noopener">'
            '<img src="%s" alt="エピリタのInstagram投稿" loading="lazy"></a>'
            '<div class="insta-cap">%s</div>'
            '<div class="insta-more"><a href="%s" target="_blank" rel="noopener">Instagramで見る →</a></div>'
            "</div>" % (href, src, cap, href)
        )

    status.append("cards: %d" % len(cards))
    with open(os.path.join(IMG_DIR, "_status.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(status) + "\n")

    if not cards:
        print("no cards generated", file=sys.stderr)
        return

    block = "\n".join(cards)
    with open(INDEX, encoding="utf-8") as f:
        htmltext = f.read()
    new = re.sub(
        r"(<!-- INSTA:START -->).*?(<!-- INSTA:END -->)",
        lambda m: m.group(1) + "\n" + block + "\n" + m.group(2),
        htmltext,
        flags=re.S,
    )
    with open(INDEX, "w", encoding="utf-8") as f:
        f.write(new)
    print("updated index.html with %d posts" % len(cards))


if __name__ == "__main__":
    main()
