import csv, hashlib, json, os, time
from datetime import datetime
from pathlib import Path
import requests
from bs4 import BeautifulSoup

SITES_CSV=Path("data/sites.csv")
SNAPSHOT_FILE=Path("data/snapshots.json")
RESULTS_FILE=Path("data/results.json")
SLACK_WEBHOOK=os.environ.get("SLACK_WEBHOOK_URL","")
HEADERS={"User-Agent":"Mozilla/5.0"}
REQUEST_TIMEOUT=20
CRAWL_INTERVAL=3

def load_json(path):
    if path.exists():
        with open(path,encoding="utf-8") as f: return json.load(f)
    return {}

def save_json(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    with open(path,"w",encoding="utf-8") as f: json.dump(data,f,ensure_ascii=False,indent=2)

def page_hash(text): return hashlib.sha256(text.encode()).hexdigest()

def fetch_page(url):
    try:
        r=requests.get(url,headers=HEADERS,timeout=REQUEST_TIMEOUT)
        r.raise_for_status(); r.encoding=r.apparent_encoding
        return BeautifulSoup(r.text,"html.parser")
    except Exception as e:
        print(f"  [ERROR] {e}"); return None

def detect_changes(key,h,props,snaps):
    prev=snaps.get(key)
    if prev is None: return {"type":"new","message":"初回登録","property_count":len(props)}
    if prev["hash"]==h: return None
    added=set(p["url"] for p in props)-set(p["url"] for p in prev.get("properties",[]))
    return {"type":"updated","message":f"変化検知（+{len(added)}件）","added_urls":list(added),"property_count":len(props)}

def notify_slack(name,url,area,change):
    if not SLACK_WEBHOOK: print("  [SKIP] Webhook未設定"); return
    payload={"attachments":[{"color":"#36a64f","title":f"[{area}] {name} に変化あり","title_link":url,"text":change["message"],"footer":f"不動産Bot | {datetime.now().strftime('%Y-%m-%d %H:%M')}"}]}
    try: requests.post(SLACK_WEBHOOK,json=payload,timeout=10); print("  [Slack] 送信完了")
    except Exception as e: print(f"  [Slack ERROR] {e}")

def main():
    print(f"=== 開始: {datetime.now().isoformat()} ===")
    snaps=load_json(SNAPSHOT_FILE); results=[]; changed=0
    with open(SITES_CSV,encoding="utf-8") as f: sites=list(csv.DictReader(f))
    print(f"監視: {len(sites)}サイト")
    for s in sites:
        name,url,sel,area=s["name"],s["url"],s.get("selector","").strip(),s.get("area","")
        key=hashlib.md5(url.encode()).hexdigest()
        print(f"\n▼ {name}"); soup=fetch_page(url)
        if not soup: time.sleep(CRAWL_INTERVAL); continue
        h=page_hash(soup.get_text(" ",strip=True))
        props=[{"title":a.get_text(strip=True),"url":a["href"]} for a in soup.select(sel+" a[href]" if sel else "a[href]") if a.get_text(strip=True)]
        print(f"  候補: {len(props)}件")
        c=detect_changes(key,h,props,snaps)
        if c: print(f"  → {c['message']}"); changed+=1; notify_slack(name,url,area,c)
        else: print("  → 変化なし")
        snaps[key]={"name":name,"url":url,"hash":h,"properties":props,"checked_at":datetime.now().isoformat()}
        results.append({**s,"changed":c is not None,"change":c,"checked_at":datetime.now().isoformat()})
        time.sleep(CRAWL_INTERVAL)
    save_json(SNAPSHOT_FILE,snaps); save_json(RESULTS_FILE,results)
    print(f"\n=== 完了: {changed}/{len(sites)}サイトで変化 ===")

if __name__=="__main__": main()
