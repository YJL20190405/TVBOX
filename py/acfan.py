#!/usr/bin/python
# coding=utf-8
import re, json, requests
from urllib.parse import quote
from base.spider import Spider

class Spider(Spider):
    def __init__(self):
        super().__init__()
        self.name = "AcFan"
        self.host = "https://acf.f76typd0.work"
        self.header = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
            "Origin": self.host,
            "Referer": self.host + "/",
            "Accept": "*/*",
            "Accept-Language": "zh-CN,zh;q=0.9"
        }
        self.class_list = [
            {"type_name": "里番", "type_id": "3/2072212947517390849"},
            {"type_name": "泡面番", "type_id": "ITEM_LI9_TWI_N6Y/2072654840359600130"},
            {"type_name": "Motion Anime", "type_id": "MOTION_ANIME/2072654931050029058"},
            {"type_name": "3DCG", "type_id": "2/2072212891277045761"},
            {"type_name": "2.5D", "type_id": "2_5D/2072655042194890753"},
            {"type_name": "2D动画", "type_id": "2D/2072655119809298434"},
            {"type_name": "AI生成", "type_id": "AI/2072655204107608066"},
            {"type_name": "MMD", "type_id": "MMD/2072655243595792385"},
            {"type_name": "国产动漫", "type_id": "GC/2075051039321464834"},
            {"type_name": "Cosplay", "type_id": "COSPLAY/2075576278568513538"}
        ]

    def getName(self):
        return self.name

    def fix_url(self, url):
        if not url: return ""
        if url.startswith("//"): return "https:" + url
        if url.startswith("/"): return self.host + url
        return url

    def clean_text(self, text):
        return re.sub(r'\s+', ' ', text or "").strip()

    def homeContent(self, filter):
        return {"class": self.class_list, "list": []}

    def homeVideoContent(self):
        return self.categoryContent(self.class_list[0]["type_id"], "1", False, {})

    def categoryContent(self, tid, pg, filter, extend):
        result = {"list": [], "page": pg, "pagecount": 999, "limit": 24, "total": 9999}
        url = f"{self.host}/category/{tid}" if str(pg) == "1" else f"{self.host}/category/{tid}/page/{pg}"
        try:
            r = requests.get(url, headers=self.header, timeout=15, verify=False)
            html = r.text
            seen = set()
            ids = re.findall(r'/watch/(CNT\d+)', html)
            names = re.findall(r'###\s*([^\n<#]{2,80})', html)
            for i, vod_id in enumerate(ids):
                if vod_id in seen: continue
                seen.add(vod_id)
                name = self.clean_text(names[i]) if i < len(names) else vod_id
                result["list"].append({"vod_id": vod_id, "vod_name": name, "vod_pic": "", "vod_remarks": ""})
            m = re.search(r'(\d+)\s*/\s*(\d+)\s*页', html)
            if m: result["pagecount"] = int(m.group(2))
        except:
            pass
        return result

    def detailContent(self, ids):
        vod_id = ids[0] if isinstance(ids, list) else ids
        url = f"{self.host}/watch/{vod_id}"
        vod = {"vod_id": vod_id, "vod_name": vod_id, "vod_pic": "", "vod_play_from": "AcFan", "vod_play_url": f"正片${url}"}
        try:
            r = requests.get(url, headers=self.header, timeout=15, verify=False)
            t = re.search(r'>([^<]{4,100})</h1>', r.text) or re.search(r'([^\n<]{4,80})\s*={2,}', r.text)
            if t: vod["vod_name"] = self.clean_text(t.group(1))
        except:
            pass
        return {"list": [vod]}

    def searchContent(self, key, quick, pg="1"):
        result = {"list": [], "page": pg, "pagecount": 1, "limit": 24, "total": 0}
        try:
            r = requests.get(f"{self.host}/search?q={quote(key)}", headers=self.header, timeout=15, verify=False)
            seen = set()
            for vod_id in re.findall(r'/watch/(CNT\d+)', r.text):
                if vod_id in seen: continue
                seen.add(vod_id)
                result["list"].append({"vod_id": vod_id, "vod_name": vod_id, "vod_pic": "", "vod_remarks": ""})
        except:
            pass
        return result

    def playerContent(self, flag, id, vipFlags):
        h = json.dumps(self.header)
        if ".m3u8" in str(id):
            return {"parse": 0, "url": id, "header": h}
        if str(id).startswith("http"):
            return {"parse": 1, "url": id, "header": h}
        return {"parse": 1, "url": f"{self.host}/watch/{id}", "header": h}

    def localProxy(self, param):
        return []