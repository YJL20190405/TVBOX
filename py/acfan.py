#!/usr/bin/python
# coding=utf-8
import re, json, requests, base64, hashlib
from urllib.parse import quote, unquote
from base.spider import Spider

class Spider(Spider):
    def __init__(self):
        super().__init__()
        self.name = "AcFan"
        self.host = "https://acf.f76typd0.work"
        self.header = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": self.host + "/",
            "Accept-Language": "zh-CN,zh;q=0.9"
        }
        self.session = requests.Session()
        self.session.headers.update(self.header)
        self.session.verify = False
        self.cat_map = [
            ("3/2072212947517390849", "里番"),
            ("ITEM_LI9_TWI_N6Y/2072654840359600130", "泡面番"),
            ("MOTION_ANIME/2072654931050029058", "Motion Anime"),
            ("2/2072212891277045761", "3DCG"),
            ("2_5D/2072655042194890753", "2.5D"),
            ("2D/2072655119809298434", "2D动画"),
            ("AI/2072655204107608066", "AI生成"),
            ("MMD/2072655243595792385", "MMD"),
            ("GC/2075051039321464834", "国产动漫"),
            ("COSPLAY/2075576278568513538", "Cosplay"),
        ]

    def fix_url(self, url):
        if not url:
            return ""
        if url.startswith("//"):
            return "https:" + url
        if url.startswith("/"):
            return self.host + url
        return url

    def fetch(self, url):
        for _ in range(3):
            try:
                return self.session.get(url, timeout=15).text or ""
            except:
                pass
        return ""

    def extract_list(self, html):
        result, seen = [], set()
        for vod_id, card in re.findall(r'href="/watch/(CNT\d+)"[^>]*>(.*?)</a>', html, re.S):
            if vod_id in seen:
                continue
            seen.add(vod_id)
            nm = re.search(r'<img[^>]*alt="([^"]*)"', card)
            dm = re.search(r'data-video-card-stat="duration"[^>]*>([^<]+)', card) or re.search(r'>(\d{1,3}:\d{2}(?::\d{2})?)</span>', card)
            result.append({
                "vod_id": vod_id,
                "vod_name": nm.group(1) if nm else vod_id,
                "vod_pic": self.host + "/images/default-cover.svg",
                "vod_remarks": dm.group(1).strip() if dm else ""
            })
        return result

    def homeContent(self, filter):
        result = {"class": [{"type_id": tid, "type_name": tname} for tid, tname in self.cat_map], "list": []}
        html = self.fetch(self.host)
        result["list"] = self.extract_list(html)[:24]
        return result

    def homeVideoContent(self):
        html = self.fetch(self.host)
        return {"list": self.extract_list(html)[:24]}

    def categoryContent(self, tid, pg, filter, extend):
        page = int(pg) if pg and str(pg).isdigit() else 1
        url = f"{self.host}/category/{tid}/page/{page}" if page > 1 else f"{self.host}/category/{tid}"
        html = self.fetch(url)
        pages = [int(p) for p in re.findall(r'/category/[^"]+/page/(\d+)', html)]
        pc = max(pages) if pages else 1
        return {"list": self.extract_list(html), "page": page, "pagecount": pc, "limit": 24, "total": pc * 24}

    def detailContent(self, ids):
        vod_id = ids[0] if isinstance(ids, list) else ids
        html = self.fetch(f"{self.host}/watch/{vod_id}")
        vod_name, vod_pic, vod_content, m3u8, cat_name = vod_id, "", "", "", ""
        for jm in re.finditer(r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>', html, re.S):
            try:
                data = json.loads(jm.group(1))
                if isinstance(data, list):
                    for item in data:
                        t = item.get("@type", "")
                        if t == "VideoObject":
                            vod_name = item.get("name", vod_name)
                            vod_content = item.get("description", "")
                            vod_pic = item.get("thumbnailUrl", "")
                            m3u8 = item.get("contentUrl", "")
                        elif t == "BreadcrumbList":
                            els = item.get("itemListElement", [])
                            if len(els) >= 2:
                                cat_name = els[1].get("name", "")
            except:
                pass
        if not vod_pic:
            og = re.search(r'property="og:image"[^>]*content="([^"]*)"', html)
            vod_pic = og.group(1) if og else ""
        if vod_name == vod_id:
            tm = re.search(r'<title>([^<]+)</title>', html)
            vod_name = tm.group(1).replace(" - AcFan", "").strip() if tm else vod_id
        tags = list(dict.fromkeys(re.findall(r'href="/search\?tag=([^"]*)"', html)))
        tag_text = " ".join(unquote(t) for t in tags)
        vod_content = (vod_content + "\n" + tag_text).strip() if vod_content else tag_text
        if cat_name:
            vod_content = f"分类: {cat_name}\n" + vod_content
        play_url = f"播放${m3u8}" if m3u8 else ""
        return {"list": [{"vod_id": vod_id, "vod_name": vod_name, "vod_pic": vod_pic, "vod_content": vod_content, "vod_play_from": "AcFan", "vod_play_url": play_url}]}

    def searchContent(self, key, quick, pg):
        page = int(pg) if pg and str(pg).isdigit() else 1
        html = self.fetch(f"{self.host}/search?q={quote(key)}&page={page}")
        pages = [int(p) for p in re.findall(r'/search\?page=(\d+)', html)]
        pc = max(pages) if pages else 1
        return {"list": self.extract_list(html), "page": page, "pagecount": pc, "limit": 24, "total": pc * 24}

    def playerContent(self, flag, id, vipFlags):
        return {"parse": 0, "playUrl": "", "url": id, "header": json.dumps(self.header)}

    def getName(self):
        return self.name

    def isVideoFormat(self, url):
        if not url:
            return False
        return any(url.lower().endswith(ext) for ext in ['.m3u8', '.mp4', '.avi', '.flv', '.mkv', '.ts']) or 'm3u8' in url.lower()

    def localProxy(self, param):
        return {}
