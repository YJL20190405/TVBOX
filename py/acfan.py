#!/usr/bin/python
# coding=utf-8
import re, json, requests, base64, hashlib
from urllib.parse import quote, unquote

class Spider(object):
    def init(self, extend=""):
        self.name = "AcFan"
        self.hosts = ["https://acf.f76typd0.work"]
        self.host = self.hosts[0]
        self.img_host = ""
        self.valid_hosts = []
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Linux; Android 12; SM-G9750 Build/SP1A.210812.016; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/89.0.4389.72 MQQBrowser/6.2 TBS/046279 Mobile Safari/537.36",
            "Referer": self.host + "/",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9"
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        self.session.verify = False
        self.cat_map = {
            "guochan": {"name": "国产动漫", "path": "GC/2075051039321464834"},
            "rifan": {"name": "里番", "path": "3/2072212947517390849"},
            "pao": {"name": "泡面番", "path": "ITEM_LI9_TWI_N6Y/2072654840359600130"},
            "motion": {"name": "Motion Anime", "path": "MOTION_ANIME/2072654931050029058"},
            "3dcg": {"name": "3DCG", "path": "2/2072212891277045761"},
            "25d": {"name": "2.5D", "path": "2_5D/2072655042194890753"},
            "2d": {"name": "2D动画", "path": "2D/2072655119809298434"},
            "ai": {"name": "AI生成", "path": "AI/2072655204107608066"},
            "mmd": {"name": "MMD", "path": "MMD/2072655243595792385"},
            "cosplay": {"name": "Cosplay", "path": "COSPLAY/2075576278568513538"},
        }

    def getName(self):
        return self.name

    def isVideoFormat(self, url):
        return bool(re.search(r"\.(m3u8|mp4|flv|avi|mkv|mov|ts)(\?|$)", url or "", re.I))

    def manualVideoCheck(self):
        return False

    def homeContent(self, filter):
        classes = [{"type_name": v["name"], "type_id": k} for k, v in self.cat_map.items()]
        data = []
        for h in self.findHosts():
            h = h.rstrip("/")
            html = self.get(h + "/")
            lst = self.parseList(html)
            if lst:
                self.host = h
                data = lst
                break
        return {"class": classes, "filters": {}, "list": data, "type": "影视"}

    def homeVideoContent(self):
        html = self.get(self.host + "/")
        return {"list": self.parseList(html)[:24]}

    def categoryContent(self, tid, pg, filter, extend):
        page = int(pg) if pg and str(pg).isdigit() else 1
        cat = self.cat_map.get(tid)
        if not cat:
            return {"page": page, "pagecount": 1, "limit": 24, "total": 0, "list": []}
        path = cat["path"]
        if page > 1:
            url = self.host + "/category/" + path + "/page/" + str(page)
        else:
            url = self.host + "/category/" + path
        html = self.get(url)
        pages = [int(p) for p in re.findall(r"/category/[^\"']+/page/(\d+)", html)]
        pc = max(pages) if pages else 1
        return {"page": page, "pagecount": pc, "limit": 24, "total": pc * 24, "list": self.parseList(html)}

    def detailContent(self, ids):
        sid = ids[0] if ids else ""
        ps = sid.split("@@@")
        vid = ps[0] if len(ps) > 0 else sid
        play = ps[1] if len(ps) > 1 else ""
        name = unquote(ps[2]) if len(ps) > 2 else vid
        pic = unquote(ps[3]) if len(ps) > 3 else ""
        if play:
            return {"list": [{
                "vod_id": sid,
                "vod_name": name,
                "vod_pic": pic,
                "vod_content": name,
                "vod_play_from": "AcFan",
                "vod_play_url": "播放$" + play
            }]}
        html = self.get(self.host + "/watch/" + vid)
        vod_name, vod_pic, vod_content, m3u8, cat_name = vid, "", "", "", ""
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
        if vod_name == vid:
            tm = re.search(r"<title>(.*?)</title>", html)
            vod_name = tm.group(1).replace(" - AcFan", "").strip() if tm else vid
        tags = list(dict.fromkeys(re.findall(r'href="/search\?tag=([^"]*)"', html)))
        tag_text = " ".join(unquote(t) for t in tags)
        vod_content = (vod_content + "\n" + tag_text).strip() if vod_content else tag_text
        if cat_name:
            vod_content = "分类: " + cat_name + "\n" + vod_content
        play_url = ("播放$" + m3u8) if m3u8 else ""
        return {"list": [{
            "vod_id": sid,
            "vod_name": vod_name,
            "vod_pic": vod_pic,
            "vod_content": vod_content,
            "vod_play_from": "AcFan",
            "vod_play_url": play_url
        }]}

    def searchContent(self, key, quick, pg="1"):
        page = int(pg) if str(pg).isdigit() else 1
        wd = quote(key)
        html = self.get(self.host + "/search?q=" + wd + "&page=" + str(page))
        pages = [int(p) for p in re.findall(r"/search\?page=(\d+)", html)]
        pc = max(pages) if pages else 1
        return {"list": self.parseList(html), "page": page, "pagecount": pc, "limit": 24, "total": pc * 24}

    def playerContent(self, flag, id, vipFlags):
        sid = id or ""
        ps = sid.split("@@@")
        url = ps[1] if len(ps) > 1 else sid
        if self.isVideoFormat(url):
            return {"parse": 0, "url": url, "header": self.headers}
        html = self.get(self.host + "/watch/" + ps[0])
        m3u8 = ""
        for jm in re.finditer(r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>', html, re.S):
            try:
                data = json.loads(jm.group(1))
                if isinstance(data, list):
                    for item in data:
                        if item.get("@type") == "VideoObject":
                            m3u8 = item.get("contentUrl", "")
                            break
            except:
                pass
        if m3u8:
            return {"parse": 0, "url": m3u8, "header": self.headers}
        return {"parse": 1, "url": url, "header": self.headers}

    def localProxy(self, param):
        return [200, "video/MP2T", {}, ""]

    def destroy(self):
        return "success"

    def findHosts(self):
        if self.valid_hosts:
            return self.valid_hosts
        res = []
        base = [self.host] + [h for h in self.hosts if h != self.host]
        for h in base:
            h = h.rstrip("/")
            if h not in res:
                res.append(h)
        self.valid_hosts = res
        return res

    def get(self, url):
        try:
            r = self.session.get(url, headers=self.headers, timeout=10, verify=False)
            return r.text or ""
        except:
            return ""

    def extractVideoData(self, html):
        data_map = {}
        if not html:
            return data_map
        for pb in re.finditer(r'self\.__next_f\.push\(\[1,"(.*?)"\]\)', html, re.S):
            content = pb.group(1)
            if 'coverUrl' not in content:
                continue
            ids = re.findall(r'(?:\\"id\\"|\\"contentCode\\"):\\"(CNT\d+)\\"', content)
            titles = re.findall(r'\\"title\\":\\"(.*?)\\",\\"(?:authorName|subTitle)', content)
            durations = re.findall(r'\\"duration\\":\\"(.*?)\\"', content)
            covers = re.findall(r'\\"coverUrl\\":\\"(https?://[^\\"]*)\\"', content)
            for i in range(min(len(ids), len(covers))):
                vid = ids[i]
                title = titles[i].replace("\\/", "/").replace('\\"', '"') if i < len(titles) else ""
                duration = durations[i] if i < len(durations) and durations[i] != "$undefined" else ""
                cover = covers[i].replace("\\/", "/")
                data_map[vid] = {"title": title, "cover": cover, "duration": duration}
        return data_map

    def parseList(self, html):
        res = []
        if not html:
            return res
        video_data = self.extractVideoData(html)
        seen = set()
        for m in re.finditer(r'href="/watch/(CNT\d+)"', html):
            vid = m.group(1)
            if vid in seen:
                continue
            seen.add(vid)
            vd = video_data.get(vid, {})
            name = vd.get("title", "")
            if not name:
                block = html[m.start():m.start() + 6000]
                name = (self.match(block, r'<img[^>]*alt="([^"]*)"')
                        or self.match(block, r'title="([^"]*)"')
                        or self.match(block, r'<h3[^>]*>([^<]+)')
                        or vid)
            duration = vd.get("duration", "")
            if not duration:
                block = html[m.start():m.start() + 6000]
                duration = self.match(block, r'>(\d{1,3}:\d{2}(?::\d{2})?)</span>')
            pic = vd.get("cover", "")
            if not pic:
                block = html[m.start():m.start() + 6000]
                pic = self.match(block, r'srcSet="[^"]*media-proxy[^"]*url=([^&"]+)') or ""
                if pic:
                    pic = unquote(unquote(pic))
                    if pic.startswith("/"):
                        pic = self.host + pic
                if not pic:
                    pic = self.host + "/images/default-cover.svg"
            play = ""
            sid = vid + "@@@" + play + "@@@" + quote(name) + "@@@" + quote(pic)
            res.append({
                "vod_id": sid,
                "vod_name": self.clean(name),
                "vod_pic": pic,
                "vod_remarks": self.clean(duration) if duration else ""
            })
        return res

    def extractM3u8FromBlock(self, block, vid):
        m = re.search(r'"contentUrl"\s*:\s*"(https?://[^"]+\.m3u8[^"]*)"', block)
        if m:
            return m.group(1)
        m = re.search(r'(https?://[^"\'\s<>]+\.m3u8[^"\'\s<>]*)', block, re.I)
        if m:
            return m.group(1)
        return ""

    def match(self, text, pat):
        m = re.search(pat, text or "", re.I)
        return m.group(1) if m else ""

    def clean(self, text):
        text = re.sub(r"<[^>]+>", " ", text or "")
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    def fix(self, url):
        url = (url or "").strip().replace("\\/", "/")
        if not url:
            return ""
        if url.startswith("//"):
            return "https:" + url
        if url.startswith("http"):
            return url
        if url.startswith("/"):
            return self.host + url
        return url
