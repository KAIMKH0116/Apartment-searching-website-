"""
収益不動産 サイト巡回・差分検知クローラー
GitHub Actions で毎日自動実行 → 新着物件を Slack 通知
"""

import csv
import hashlib
import json
import os
import time
from datetime import datetime
from pathlib import Path

import requests
from bs4 import BeautifulSoup

SITES_CSV     = Path("data/sites.csv")
SNAPSHOT_FILE = Path("data/snapshots.json")
RESULTS_FILE  = Path("data/results.json")
SLACK_WEBHOOK = os.environ.get("SLACK_WEBHOOK_URL", "")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}
REQUEST_TIMEOUT = 20
CRAWL_INTERVAL  = 3


def load_json(path):
    if path.exists():
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def page_hash(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def fetch_page(url):
    try:
        resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        resp.encoding = resp.apparent_encoding
        return BeautifulSoup(resp.text, "html.parser")
    except Exception as e:
        print(f"  [ERROR] {url} → {e}")
        return None


def extract_properties(soup, selector, base_url):
    properties = []
    targets = soup.select(selector) if selector else [soup]
    for el in targets:
        links = el.find_all("a", href=True)
        for link in links:
            href = link["href"]
            if href.startswith("/"):
                from urllib.parse import urlparse
                parsed = urlparse(base_url)
                href = f"{parsed.scheme}://{parsed.netloc}{href}"
            elif not href.startswith("http"):
                continue
            title = link.get_text(strip=True)
            if not title:
                continue
            properties.append({
                "title": title,
                "url": href,
                "text_snippet": el.get_text(" ", strip=True)[:200],
            })
    seen = set()
    unique = []
    for p in properties:
        if p["url"] not in seen:
            seen.add(p["url"])
            unique.append(p)
    return unique


def detect_changes(site_key, current_hash, current_props, snapshots):
    prev = snapshots.get(site_key)
    if prev is None:
        return {
            "type": "new_site",
            "message": "初回登録",
            "property_count": len(current_props),
        }
    if prev["hash"] == current_hash:
        return None
    prev_urls = set(p["url"] for p in prev.get("properties", []))
    curr_urls = set(p["url"] for p in current_props)
    added   = curr_urls - prev_urls
    removed = prev_urls - curr_urls
    return {
        "type": "updated",
        "message": f"変化を検知（追加: {len(added)}件 / 消滅: {len(removed)}件）",
        "added_urls": list(added),
        "removed_urls": list(removed),
        "property_count": len(current_props),
    }


def notify_slack(site_name, site_url, area, change):
    if not SLACK_WEBHOOK:
        print("  [SKIP] SLACK_WEBHOOK_URL が未設定のため通知をスキップ")
        return
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    color = "#36a64f" if change["type"] == "updated" else "#439FE0"
    added_lines = ""
    if change.get("added_urls"):
        links = "\n".join(f"• <{u}|物件ページ>" for u in change["added_urls"][:5])
        added_lines = f"\n*新着URL（最大5件）*\n{links}"
    payload = {
        "attachments": [{
            "color": color,
            "title": f"🏠 [{area}] {site_name} に変化あり",
            "title_link": site_url,
            "text": (
                f"*{change['message']}*\n"
                f"現在の物件候補数: {change['property_count']}件"
                f"{added_lines}"
            ),
            "footer": f"不動産リサーチBot | {now}",
        }]
    }
    try:
        resp = requests.post(SLACK_WEBHOOK, json=payload, timeout=10)
        resp.raise_for_status()
        print("  [Slack] 通知送信完了")
    except Exception as e:
        print(f"  [Slack ERROR] {e}")


def main():
    print(f"=== クローラー開始: {datetime.now().isoformat()} ===")
    snapshots = load_json(SNAPSHOT_FILE)
    all_results = []
    changed_count = 0

    with open(SITES_CSV, encoding="utf-8") as f:
        sites = list(csv.DictReader(f))

    print(f"監視サイト数: {len(sites)}")

    for site in sites:
        name     = site["name"]
        url      = site["url"]
        selector = site.get("selector", "").strip()
cat > src/crawler.py << 'EOF'
"""
収益不動産 サイト巡回・差分検知クローラー
GitHub Actions で毎日自動実行 → 新着物件を Slack 通知
"""

import csv
import hashlib
import json
import os
import time
from datetime import datetime
from pathlib import Path

import requests
from bs4 import BeautifulSoup

SITES_CSV     = Path("data/sites.csv")
SNAPSHOT_FILE = Path("data/snapshots.json")
RESULTS_FILE  = Path("data/results.json")
SLACK_WEBHOOK = os.environ.get("SLACK_WEBHOOK_URL", "")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}
REQUEST_TIMEOUT = 20
CRAWL_INTERVAL  = 3


def load_json(path):
    if path.exists():
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def page_hash(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def fetch_page(url):
    try:
        resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        resp.encoding = resp.apparent_encoding
        return BeautifulSoup(resp.text, "html.parser")
    except Exception as e:
        print(f"  [ERROR] {url} → {e}")
        return None


def extract_properties(soup, selector, base_url):
    properties = []
    targets = soup.select(selector) if selector else [soup]
    for el in targets:
        links = el.find_all("a", href=True)
        for link in links:
            href = link["href"]
            if href.startswith("/"):
                from urllib.parse import urlparse
                parsed = urlparse(base_url)
                href = f"{parsed.scheme}://{parsed.netloc}{href}"
            elif not href.startswith("http"):
                continue
            title = link.get_text(strip=True)
            if not title:
                continue
            properties.append({
                "title": title,
                "url": href,
                "text_snippet": el.get_text(" ", strip=True)[:200],
            })
    seen = set()
    unique = []
    for p in properties:
        if p["url"] not in seen:
            seen.add(p["url"])
            unique.append(p)
    return unique


def detect_changes(site_key, current_hash, current_props, snapshots):
    prev = snapshots.get(site_key)
    if prev is None:
        return {
            "type": "new_site",
            "message": "初回登録",
            "property_count": len(current_props),
        }
    if prev["hash"] == current_hash:
        return None
    prev_urls = set(p["url"] for p in prev.get("properties", []))
    curr_urls = set(p["url"] for p in current_props)
    added   = curr_urls - prev_urls
    removed = prev_urls - curr_urls
    return {
        "type": "updated",
        "message": f"変化を検知（追加: {len(added)}件 / 消滅: {len(removed)}件）",
        "added_urls": list(added),
        "removed_urls": list(removed),
        "property_count": len(current_props),
    }


def notify_slack(site_name, site_url, area, change):
    if not SLACK_WEBHOOK:
        print("  [SKIP] SLACK_WEBHOOK_URL が未設定のため通知をスキップ")
        return
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    color = "#36a64f" if change["type"] == "updated" else "#439FE0"
    added_lines = ""
    if change.get("added_urls"):
        links = "\n".join(f"• <{u}|物件ページ>" for u in change["added_urls"][:5])
        added_lines = f"\n*新着URL（最大5件）*\n{links}"
    payload = {
        "attachments": [{
            "color": color,
            "title": f"🏠 [{area}] {site_name} に変化あり",
            "title_link": site_url,
            "text": (
                f"*{change['message']}*\n"
                f"現在の物件候補数: {change['property_count']}件"
                f"{added_lines}"
            ),
            "footer": f"不動産リサーチBot | {now}",
        }]
    }
    try:
        resp = requests.post(SLACK_WEBHOOK, json=payload, timeout=10)
        resp.raise_for_status()
        print("  [Slack] 通知送信完了")
    except Exception as e:
        print(f"  [Slack ERROR] {e}")


def main():
    print(f"=== クローラー開始: {datetime.now().isoformat()} ===")
    snapshots = load_json(SNAPSHOT_FILE)
    all_results = []
    changed_count = 0

    with open(SITES_CSV, encoding="utf-8") as f:
        sites = list(csv.DictReader(f))

    print(f"監視サイト数: {len(sites)}")

    for site in sites:
        name     = site["name"]
        url      = site["url"]
        selector = site.get("selector", "").strip()
        area     = site.get("area", "")
        note     = site.get("note", "")
        key      = hashlib.md5(url.encode()).hexdigest()

        print(f"\n▼ {name} ({area})")
        print(f"  URL: {url}")

        soup = fetch_page(url)
        if soup is None:
            print("  → スキップ（取得失敗）")
            time.sleep(CRAWL_INTERVAL)
            continue

        body_text    = soup.get_text(" ", strip=True)
        current_hash = page_hash(body_text)
        properties   = extract_properties(soup, selector, url)
        print(f"  物件候補: {len(properties)}件")

        change = detect_changes(key, current_hash, properties, snapshots)
        if change:
            print(f"  → {change['message']}")
            changed_count += 1
            notify_slack(name, url, area, change)
        else:
            print("  → 変化なし")

        snapshots[key] = {
            "name":       name,
            "url":        url,
            "hash":       current_hash,
            "properties": properties,
            "checked_at": datetime.now().isoformat(),
        }
        all_results.append({
            "name": name, "url": url, "area": area, "note": note,
            "changed": change is not None, "change": change,
            "properties": properties,
            "checked_at": datetime.now().isoformat(),
        })
        time.sleep(CRAWL_INTERVAL)

    save_json(SNAPSHOT_FILE, snapshots)
    save_json(RESULTS_FILE, all_results)
    print(f"\n=== 完了: 変化検知 {changed_count}/{len(sites)} サイト ===")


if __name__ == "__main__":
    main()
