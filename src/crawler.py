import csv, hashlib, json, os, time, re
from datetime import datetime
from pathlib import Path
import requests
from bs4 import BeautifulSoup
from google.oauth2 import service_account
from googleapiclient.discovery import build

SNAPSHOT_FILE=Path("data/snapshots.json")
RESULTS_FILE=Path("data/results.json")
SLACK_WEBHOOK=os.environ.get("SLACK_WEBHOOK_URL","")
DRIVE_FOLDER_ID=os.environ.get("GOOGLE_DRIVE_FOLDER_ID","")
SERVICE_ACCOUNT_JSON=os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON","")
SHEET_ID=os.environ.get("GOOGLE_SHEET_ID","")
HEADERS={"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
REQUEST_TIMEOUT=20
CRAWL_INTERVAL=3

def get_services():
    if not SERVICE_ACCOUNT_JSON:
        return None, None
    import json as j
    info=j.loads(SERVICE_ACCOUNT_JSON)
    creds=service_account.Credentials.from_service_account_info(
        info,scopes=[
            "https://www.googleapis.com/auth/drive",
            "https://www.googleapis.com/auth/spreadsheets.readonly"
        ])
    drive=build("drive","v3",credentials=creds)
    sheets=build("sheets","v4",credentials=creds)
    return drive,sheets

def load_sites_from_sheet(sheets):
    result=sheets.spreadsheets().values().get(
        spreadsheetId=SHEET_ID,range="A:E").execute()
    rows=result.get("values",[])
    if not rows or len(rows)<2:
        return []
    headers=rows[0]
    sites=[]
    for row in rows[1:]:
        if not row or not row[0]:
            continue
        site={}
        for i,h in enumerate(headers):
            site[h]=row[i] if i<len(row) else ""
        sites.append(site)
    return sites

def load_sites_from_csv():
    path=Path("data/sites.csv")
    if not path.exists():
        return []
    with open(path,encoding="utf-8") as f:
        return list(csv.DictReader(f))

def safe_name(name):
    return re.sub(r'[\\/:*?"<>|]',"_",name)[:50]

def create_drive_folder(drive,name,parent_id):
    today=datetime.now().strftime("%Y%m%d")
    meta={"name":f"{today}_{safe_name(name)}",
          "mimeType":"application/vnd.google-apps.folder",
          "parents":[parent_id]}
    f=drive.files().create(body=meta,fields="id,webViewLink").execute()
    return f["id"],f["webViewLink"]

def load_json(path):
    if path.exists():
        with open(path,encoding="utf-8") as f:
cat > src/crawler.py << 'PYEOF'
import csv, hashlib, json, os, time, re
from datetime import datetime
from pathlib import Path
import requests
from bs4 import BeautifulSoup
from google.oauth2 import service_account
from googleapiclient.discovery import build

SNAPSHOT_FILE=Path("data/snapshots.json")
RESULTS_FILE=Path("data/results.json")
SLACK_WEBHOOK=os.environ.get("SLACK_WEBHOOK_URL","")
DRIVE_FOLDER_ID=os.environ.get("GOOGLE_DRIVE_FOLDER_ID","")
SERVICE_ACCOUNT_JSON=os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON","")
SHEET_ID=os.environ.get("GOOGLE_SHEET_ID","")
HEADERS={"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
REQUEST_TIMEOUT=20
CRAWL_INTERVAL=3

def get_services():
    if not SERVICE_ACCOUNT_JSON:
        return None, None
    import json as j
    info=j.loads(SERVICE_ACCOUNT_JSON)
    creds=service_account.Credentials.from_service_account_info(
        info,scopes=[
            "https://www.googleapis.com/auth/drive",
            "https://www.googleapis.com/auth/spreadsheets.readonly"
        ])
    drive=build("drive","v3",credentials=creds)
    sheets=build("sheets","v4",credentials=creds)
    return drive,sheets

def load_sites_from_sheet(sheets):
    result=sheets.spreadsheets().values().get(
        spreadsheetId=SHEET_ID,range="A:E").execute()
    rows=result.get("values",[])
    if not rows or len(rows)<2:
        return []
    headers=rows[0]
    sites=[]
    for row in rows[1:]:
        if not row or not row[0]:
            continue
        site={}
        for i,h in enumerate(headers):
            site[h]=row[i] if i<len(row) else ""
        sites.append(site)
    return sites

def load_sites_from_csv():
    path=Path("data/sites.csv")
    if not path.exists():
        return []
    with open(path,encoding="utf-8") as f:
        return list(csv.DictReader(f))

def safe_name(name):
    return re.sub(r'[\\/:*?"<>|]',"_",name)[:50]

def create_drive_folder(drive,name,parent_id):
    today=datetime.now().strftime("%Y%m%d")
    meta={"name":f"{today}_{safe_name(name)}",
          "mimeType":"application/vnd.google-apps.folder",
          "parents":[parent_id]}
    f=drive.files().create(body=meta,fields="id,webViewLink").execute()
    return f["id"],f["webViewLink"]

def load_json(path):
    if path.exists():
        with open(path,encoding="utf-8") as f: return json.load(f)
    return {}

def save_json(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    with open(path,"w",encoding="utf-8") as f:
        json.dump(data,f,ensure_ascii=False,indent=2)

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
    if prev is None:
        return {"type":"new","message":"初回登録","property_count":len(props)}
    if prev["hash"]==h: return None
    added=set(p["url"] for p in props)-set(p["url"] for p in prev.get("properties",[]))
    return {"type":"updated","message":f"変化検知（+{len(added)}件）","added_urls":list(added),"property_count":len(props)}

def notify_slack(name,url,area,change,drive_link=None):
    if not SLACK_WEBHOOK: print("  [SKIP] Webhook未設定"); return
    drive_text=f"\n📁 <{drive_link}|Driveフォルダを開く>" if drive_link else ""
    payload={"attachments":[{
        "color":"#36a64f",
        "title":f"🏠 [{area}] {name} に変化あり",
        "title_link":url,
        "text":f"{change['message']}{drive_text}",
        "footer":f"不動産Bot | {datetime.now().strftime('%Y-%m-%d %H:%M')}"}]}
    try:
        requests.post(SLACK_WEBHOOK,json=payload,timeout=10)
        print("  [Slack] 送信完了")
    except Exception as e: print(f"  [Slack ERROR] {e}")

def main():
    print(f"=== 開始: {datetime.now().isoformat()} ===")
    snaps=load_json(SNAPSHOT_FILE); results=[]; changed=0

    drive,sheets=get_services()
    if drive: print("  [Drive] 接続OK")
    else: print("  [Drive] 未設定")

    # スプレッドシートから読み込み（失敗時はCSVにフォールバック）
    if sheets and SHEET_ID:
        try:
            sites=load_sites_from_sheet(sheets)
            print(f"  [Sheet] {len(sites)}件読み込み")
        except Exception as e:
            print(f"  [Sheet ERROR] {e} → CSVで代替")
            sites=load_sites_from_csv()
    else:
        sites=load_sites_from_csv()

    print(f"監視: {len(sites)}サイト")

    for s in sites:
        name=s.get("name","")
        url=s.get("url","")
        sel=s.get("selector","").strip()
        area=s.get("area","")
        if not url: continue

        key=hashlib.md5(url.encode()).hexdigest()
        print(f"\n▼ {name}")
        soup=fetch_page(url)
        if not soup: time.sleep(CRAWL_INTERVAL); continue

        h=page_hash(soup.get_text(" ",strip=True))
        props=[{"title":a.get_text(strip=True),"url":a["href"]}
               for a in soup.select(sel+" a[href]" if sel else "a[href]")
               if a.get_text(strip=True)]
        print(f"  候補: {len(props)}件")

        c=detect_changes(key,h,props,snaps)
        drive_link=None

        if c:
            print(f"  → {c['message']}")
            changed+=1
            if drive and DRIVE_FOLDER_ID:
                try:
                    _,drive_link=create_drive_folder(drive,name,DRIVE_FOLDER_ID)
                    print(f"  [Drive] フォルダ作成: {drive_link}")
                except Exception as e:
                    print(f"  [Drive ERROR] {e}")
            notify_slack(name,url,area,c,drive_link)
        else:
            print("  → 変化なし")

        snaps[key]={"name":name,"url":url,"hash":h,"properties":props,
                    "checked_at":datetime.now().isoformat()}
        results.append({**s,"changed":c is not None,"change":c,
                        "drive_link":drive_link,"checked_at":datetime.now().isoformat()})
        time.sleep(CRAWL_INTERVAL)

    save_json(SNAPSHOT_FILE,snaps)
    save_json(RESULTS_FILE,results)
    print(f"\n=== 完了: {changed}/{len(sites)}サイトで変化 ===")

if __name__=="__main__": main()
