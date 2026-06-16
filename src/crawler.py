import csv, hashlib, json, os, time, re
from datetime import datetime
from pathlib import Path
import requests
from bs4 import BeautifulSoup
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaInMemoryUpload

SITES_CSV=Path("data/sites.csv")
SNAPSHOT_FILE=Path("data/snapshots.json")
RESULTS_FILE=Path("data/results.json")
SLACK_WEBHOOK=os.environ.get("SLACK_WEBHOOK_URL","")
DRIVE_FOLDER_ID=os.environ.get("GOOGLE_DRIVE_FOLDER_ID","")
SERVICE_ACCOUNT_JSON=os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON","")
HEADERS={"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
REQUEST_TIMEOUT=20
CRAWL_INTERVAL=3

def get_drive_service():
    if not SERVICE_ACCOUNT_JSON:
        return None
    import json as json_mod
    info=json_mod.loads(SERVICE_ACCOUNT_JSON)
    creds=service_account.Credentials.from_service_account_info(
        info,scopes=["https://www.googleapis.com/auth/drive"])
    return build("drive","v3",credentials=creds)

def safe_name(name):
    return re.sub(r'[\\/:*?"<>|]',"_",name)[:50]

def create_drive_folder(service,name,parent_id):
    today=datetime.now().strftime("%Y%m%d")
    folder_name=f"{today}_{safe_name(name)}"
    meta={"name":folder_name,"mimeType":"application/vnd.google-apps.folder","parents":[parent_id]}
    f=service.files().create(body=meta,fields="id,webViewLink").execute()
    return f["id"],f["webViewLink"]

def upload_text_to_drive(service,folder_id,filename,content):
    media=MediaInMemoryUpload(content.encode("utf-8"),mimetype="text/plain")
    meta={"name":filename,"parents":[folder_id]}
    service.files().create(body=meta,media_body=media,fields="id").execute()

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

def notify_slack(name,url,area,change,drive_link=None):
    if not SLACK_WEBHOOK: print("  [SKIP] Webhook未設定"); return
    drive_text=f"\n <{drive_link}|Driveフォルダを開く>" if drive_link else ""
    payload={"attachments":[{
        "color":"#36a64f",
        "title":f" [{area}] {name} に変化あり",
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
    drive=get_drive_service()
    if drive: print("  [Drive] 接続OK")
    else: print("  [Drive] 未設定")

    with open(SITES_CSV,encoding="utf-8") as f: sites=list(csv.DictReader(f))
    print(f"監視: {len(sites)}サイト")

    for s in sites:
        name,url,sel,area=s["name"],s["url"],s.get("selector","").strip(),s.get("area","")
        key=hashlib.md5(url.encode()).hexdigest()
        print(f"\n {name}"); soup=fetch_page(url)
        if not soup: time.sleep(CRAWL_INTERVAL); continue

        h=page_hash(soup.get_text(" ",strip=True))
        props=[{"title":a.get_text(strip=True),"url":a["href"]}
               for a in soup.select(sel+" a[href]" if sel else "a[href]")
               if a.get_text(strip=True)]
        print(f"  候補: {len(props)}件")

        c=detect_changes(key,h,props,snaps)
        drive_link=None

        if c:
            print(f"   {c['message']}")
            changed+=1

            # Driveにフォルダ作成＆資料保存
            if drive and DRIVE_FOLDER_ID:
                try:
                    folder_id,drive_link=create_drive_folder(drive,name,DRIVE_FOLDER_ID)
                    today=datetime.now().strftime("%Y%m%d")

                    # 物件概要テキスト保存
                    summary=f"サイト名: {name}\nURL: {url}\nエリア: {area}\n取得日時: {datetime.now().isoformat()}\n\n{soup.get_text(separator=chr(10),strip=True)[:5000]}"
                    upload_text_to_drive(drive,folder_id,f"{today}_物件概要.txt",summary)

                    # リンク一覧保存
                    links_text="\n".join(f"{p['title']}\n{p['url']}" for p in props[:50])
                    upload_text_to_drive(drive,folder_id,f"{today}_リンク一覧.txt",links_text)

                    print(f"  [Drive] フォルダ作成: {drive_link}")
                except Exception as e:
                    print(f"  [Drive ERROR] {e}")

            notify_slack(name,url,area,c,drive_link)
        else:
            print("   変化なし")

        snaps[key]={"name":name,"url":url,"hash":h,"properties":props,"checked_at":datetime.now().isoformat()}
        results.append({**s,"changed":c is not None,"change":c,"drive_link":drive_link,"checked_at":datetime.now().isoformat()})
        time.sleep(CRAWL_INTERVAL)

    save_json(SNAPSHOT_FILE,snaps)
    save_json(RESULTS_FILE,results)
    print(f"\n=== 完了: {changed}/{len(sites)}サイトで変化 ===")

if __name__=="__main__": main()
