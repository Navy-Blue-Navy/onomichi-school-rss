import requests
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import urljoin
from datetime import datetime, timezone, timedelta
from email.utils import format_datetime
import re

URL = "https://onomichi.ac.jp/news/"
OUTPUT = Path(__file__).parent / "onomichi.xml"

response = requests.get(URL, timeout=30)
response.raise_for_status()
response.encoding = response.apparent_encoding

soup = BeautifulSoup(response.text, "html.parser")

new_items = []
seen_urls = set()

jst = timezone(timedelta(hours=9))

for a in soup.find_all("a", href=True):

    href = a["href"]
    title = a.get_text(" ", strip=True)

    # 個別記事URLだけ取得
    if "c=topics_view" not in href:
        continue

    if not title:
        continue

    article_url = urljoin(URL, href)

    if article_url in seen_urls:
        continue

    # 記事より前にある掲載日を取得
    previous_text = a.find_previous(
        string=re.compile(r"\d{4}/\d{2}/\d{2}")
    )

    pub_date = ""

    if previous_text:
        match = re.search(
            r"(\d{4})/(\d{2})/(\d{2})",
            previous_text
        )

        if match:
            year, month, day = match.groups()

            dt = datetime(
                int(year),
                int(month),
                int(day),
                0,
                0,
                tzinfo=jst
            )

            pub_date = format_datetime(dt)

    seen_urls.add(article_url)

    new_items.append({
        "title": title,
        "link": article_url,
        "description": "尾道中学校・尾道高等学校 新着情報",
        "date": pub_date,
        "guid": article_url
    })

# 以前のRSSを読み込む
old_items = []

if OUTPUT.exists():
    try:
        old_tree = ET.parse(OUTPUT)
        old_root = old_tree.getroot()

        for item in old_root.findall("./channel/item"):
            old_items.append({
                "title": item.findtext("title", ""),
                "link": item.findtext("link", ""),
                "description": item.findtext("description", ""),
                "date": item.findtext("pubDate", ""),
                "guid": item.findtext("guid", "")
            })
    except Exception:
        old_items = []

# 新着＋過去記事を合体して重複除去
all_items = []
seen = set()

for item in new_items + old_items:
    if item["guid"] in seen:
        continue

    seen.add(item["guid"])
    all_items.append(item)

# 最大300件保存
all_items = all_items[:300]

# RSS作成
rss = ET.Element("rss", version="2.0")
channel = ET.SubElement(rss, "channel")

ET.SubElement(channel, "title").text = "尾道中学校・尾道高等学校 新着情報"
ET.SubElement(channel, "link").text = URL
ET.SubElement(channel, "description").text = "学校法人尾道学園の新着情報"
ET.SubElement(channel, "language").text = "ja"

for item in all_items:
    element = ET.SubElement(channel, "item")

    ET.SubElement(element, "title").text = item["title"]
    ET.SubElement(element, "link").text = item["link"]
    ET.SubElement(element, "description").text = item["description"]

    if item["date"]:
        ET.SubElement(element, "pubDate").text = item["date"]

    guid_element = ET.SubElement(element, "guid")
    guid_element.set("isPermaLink", "false")
    guid_element.text = item["guid"]

tree = ET.ElementTree(rss)
ET.indent(tree, space="  ")

tree.write(
    OUTPUT,
    encoding="utf-8",
    xml_declaration=True
)

print("RSS作成成功")
print("今回取得:", len(new_items), "件")
print("RSS保存件数:", len(all_items), "件")
print("保存先:", OUTPUT)

print()
print("最新5件:")
for item in new_items[:5]:
    print(item["date"], item["title"])