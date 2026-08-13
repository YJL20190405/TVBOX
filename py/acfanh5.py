#!/usr/bin/python
# coding=utf-8
import re, json, requests, hashlib, time, base64
from urllib.parse import quote, unquote

try:
    from base.spider import Spider as BaseSpider
except:
    class BaseSpider: pass

try:
    from Crypto.Cipher import AES as _AES
    from Crypto.Util.Padding import unpad as _unpad
    _AES_OK = True
except:
    try:
        from Cryptodome.Cipher import AES as _AES
        from Cryptodome.Util.Padding import unpad as _unpad
        _AES_OK = True
    except:
        _AES_OK = False

class Spider(BaseSpider):
    def __init__(self):
        self.host = "https://accfanan.x18c87so.work"
        self.hosts = ["https://accfanan.x18c87so.work"]
        self.name = "AcFanH5"
        self.token = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiI2NTgxMjQ2NyIsImlhdCI6MTc4NjY0NjkwOCwibmJmIjoxNzg2NjQ2OTA4LCJleHAiOjE5NDQzMjY5MDh9.HoXjdxzwQ_ZckKpIfoZcngqkw7auCKkynZBA_dij1lY"
        self.device_id = "ebc9eb027b0453d0adaea4d3f2564edc"
        self.img_domain = "https://wiuuh1425js3.iumigc.com/"
        self.UA = "Mozilla/5.0 (Linux; Android 12; SM-G9750 Build/SP1A.210812.016; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/89.0.4389.72 Mobile Safari/537.36"
        self.session = requests.Session()
        self.session.verify = False
        self.class_list = [
            {"type_name": "精选", "type_id": "jingxuan"},
            {"type_name": "漫画", "type_id": "manhua"},
            {"type_name": "动漫", "type_id": "dongman"},
            {"type_name": "视频", "type_id": "shipin"},
            {"type_name": "里番", "type_id": "rifan"},
        ]
        self.cat_type = {
            "jingxuan": 0, "manhua": 2, "dongman": 1, "shipin": 4, "rifan": 3,
        }
        self.sub_cats = ["同人", "国漫", "3D", "MMD", "原神", "崩坏3", "番剧", "热播", "乱伦", "国产", "网黄", "萝莉", "AV", "传媒", "重口"]
        self._cached_classes = None
        self._cached_filters = None
        self._cached_sub_ids = None

    def _hdr(self):
        t = str(int(time.time() * 1000))
        s = hashlib.md5(t[3:8].encode()).hexdigest()
        return {
            "User-Agent": self.UA,
            "Referer": self.host + "/",
            "Accept": "application/json, text/plain, */*",
            "Origin": self.host,
            "device": "Android",
            "appVersion": "1.9.6",
            "User-Mark": "xhp",
            "deviceId": self.device_id,
            "Authorization": "Bearer " + self.token,
            "t": t,
            "s": s,
        }

    def _dec(self, enc):
        if not enc or not _AES_OK:
            return None
        try:
            k = self.token[2:18].encode()
            raw = base64.b64decode(enc)
            c = _AES.new(k, _AES.MODE_CBC, k)
            d = _unpad(c.decrypt(raw), _AES.block_size).decode()
            return json.loads(d) if d and d[0] in '[{' else d
        except:
            return None

    def _api(self, path, params=None):
        h = self._hdr()
        p = dict(params or {})
        p["_t"] = h["t"]
        try:
            r = self.session.get(self.host + "/api" + path, params=p, headers=h, timeout=10, verify=False)
            j = r.json()
            if isinstance(j, dict) and j.get("encData"):
                d = self._dec(j["encData"])
                return d if d is not None else j.get("data")
            return j.get("data") if isinstance(j, dict) and "data" in j else j
        except:
            return None

    def _img(self, url):
        if not url:
            return ""
        if not url.startswith("http"):
            url = self.img_domain + url
        if "127.0.0.1" in url or "/media-proxy" in url:
            return url
        return self.host + "/media-proxy?url=" + quote(url, safe="")

    def init(self, extend=""):
        pass

    def getName(self):
        return self.name

    def isVideoFormat(self, url):
        return bool(url) and (any(url.lower().endswith(e) for e in [".m3u8", ".mp4", ".ts", ".flv"]) or "m3u8" in url.lower())

    def manualVideoCheck(self):
        return False

    def _fetchSubCats(self):
        if self._cached_sub_ids is not None:
            return self._cached_sub_ids
        ids = {}
        for t in [1, 2, 3, 4]:
            try:
                data = self._api("/video/classifyList", {"type": t})
                if data and isinstance(data, list):
                    for i in data:
                        cid = str(i.get("classifyId") or i.get("id") or "")
                        cname = str(i.get("classifyTitle") or i.get("title") or "")
                        if cid and cname and cname not in ids:
                            ids[cname] = cid
            except:
                pass
        try:
            data = self._api("/comics/other/classList")
            if data and isinstance(data, list):
                for i in data:
                    cid = str(i.get("classId") or i.get("categoryId") or i.get("id") or "")
                    cname = str(i.get("title") or i.get("categoryName") or "")
                    if cid and cname and cname not in ids:
                        ids[cname] = cid
        except:
            pass
        self._cached_sub_ids = ids if ids else None
        return self._cached_sub_ids

    def _buildFilters(self):
        if self._cached_filters is not None:
            return self._cached_filters
        sub_ids = self._fetchSubCats()
        values = [{"n": "全部", "v": ""}]
        for cat in self.sub_cats:
            if sub_ids and cat in sub_ids:
                values.append({"n": cat, "v": sub_ids[cat]})
            else:
                values.append({"n": cat, "v": cat})
        fl = {"classifyId": {"key": "classifyId", "name": "分类", "value": values}}
        self._cached_filters = {
            "jingxuan": {}, "manhua": {}, "dongman": fl, "shipin": fl, "rifan": fl,
        }
        return self._cached_filters

    def homeContent(self, filter):
        classes = self.class_list
        filters = self._buildFilters()
        videos = []
        try:
            data = self._api("/video/getByClassify", {"page": 1, "size": 20})
            items = self._items(data)
            videos = self._parseList(items)
        except:
            pass
        return {"class": classes, "filters": filters, "list": videos}

    def homeVideoContent(self):
        try:
            data = self._api("/video/getByClassify", {"page": 1, "size": 20})
            return {"list": self._parseList(self._items(data))}
        except:
            return {"list": []}

    def _items(self, data):
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            return data.get("list") or data.get("data") or data.get("dataList") or data.get("records") or []
        return []

    def categoryContent(self, tid, pg, filter, extend):
        page = int(pg) if pg and str(pg).isdigit() else 1
        atype = self.cat_type.get(tid, 0)
        cid = ""
        if extend and extend.get("classifyId"):
            cid = extend["classifyId"]
        params = {"page": page, "size": 20}
        if cid:
            params["classifyId"] = cid
        elif atype > 0:
            params["type"] = atype
        if atype == 3 and not cid:
            data = self._api("/comics/other/classList", {"page": page, "size": 20})
        else:
            data = self._api("/video/getByClassify", params)
        items = self._items(data)
        total, pc = 0, 1
        if isinstance(data, dict):
            total = data.get("total") or data.get("totalCount") or 0
            pc = data.get("totalPage") or data.get("pageCount") or data.get("pages") or ((total + 19) // 20 if total else 1)
        return {"page": page, "pagecount": pc, "limit": 20, "total": total, "list": self._parseList(items)}

    def detailContent(self, ids):
        vid = ids[0] if ids else ""
        ps = vid.split("@@@")
        rid = ps[0] if len(ps) > 0 else vid
        play = ps[1] if len(ps) > 1 else ""
        name = unquote(ps[2]) if len(ps) > 2 else rid
        pic = unquote(ps[3]) if len(ps) > 3 else ""
        if play:
            return {"list": [{"vod_id": vid, "vod_name": name, "vod_pic": self._img(pic),
                "vod_content": name, "vod_play_from": "AcFanH5", "vod_play_url": "播放$" + play}]}
        data = None
        for ep in ["/video/detail", "/video/getById", "/video/info"]:
            data = self._api(ep, {"id": rid})
            if data:
                break
        vname, vpic, vcontent, m3u8 = name, pic, "", ""
        if isinstance(data, dict):
            vname = data.get("title") or data.get("name") or vname
            vpic = data.get("coverUrl") or data.get("cover") or data.get("thumbnailUrl") or vpic
            vcontent = data.get("description") or data.get("content") or ""
            m3u8 = data.get("playUrl") or data.get("videoUrl") or data.get("m3u8Url") or data.get("contentUrl") or ""
        elif isinstance(data, list) and data:
            item = data[0] if isinstance(data[0], dict) else {}
            vname = item.get("title") or item.get("name") or vname
            vpic = item.get("coverUrl") or item.get("cover") or vpic
            vcontent = item.get("description") or item.get("content") or ""
            m3u8 = item.get("playUrl") or item.get("videoUrl") or item.get("m3u8Url") or item.get("contentUrl") or ""
        return {"list": [{"vod_id": vid, "vod_name": vname, "vod_pic": self._img(vpic),
            "vod_content": vcontent, "vod_play_from": "AcFanH5",
            "vod_play_url": ("播放$" + m3u8) if m3u8 else ""}]}

    def searchContent(self, key, quick, pg="1"):
        page = int(pg) if str(pg).isdigit() else 1
        data = self._api("/search/search", {"keyword": key, "page": page, "size": 20})
        items = self._items(data)
        return {"list": self._parseList(items), "page": page, "pagecount": 1, "limit": 20, "total": len(items)}

    def playerContent(self, flag, id, vipFlags):
        ps = (id or "").split("@@@")
        url = ps[1] if len(ps) > 1 and ps[1] else ps[0]
        hdr = {"User-Agent": self.UA}
        if self.isVideoFormat(url):
            return {"parse": 0, "url": url, "header": hdr}
        rid = ps[0] if ps else id
        data = None
        for ep in ["/video/detail", "/video/getById", "/video/info"]:
            data = self._api(ep, {"id": rid})
            if data:
                break
        if isinstance(data, dict):
            url = data.get("playUrl") or data.get("videoUrl") or data.get("m3u8Url") or data.get("contentUrl") or url
        if self.isVideoFormat(url):
            return {"parse": 0, "url": url, "header": hdr}
        return {"parse": 1, "url": url, "header": hdr}

    def localProxy(self, param):
        return [200, "text/plain", b""]

    def destroy(self):
        return "success"

    def _parseList(self, items):
        res, seen = [], set()
        for item in (items or []):
            try:
                vid = str(item.get("id") or item.get("videoId") or item.get("classifyId") or "")
                if not vid or vid in seen:
                    continue
                seen.add(vid)
                name = str(item.get("title") or item.get("name") or vid)
                pic = str(item.get("coverUrl") or item.get("cover") or item.get("thumbnailUrl") or item.get("logo") or "")
                dur = str(item.get("duration") or item.get("remarks") or item.get("videoNum") or "")
                sid = vid + "@@@" + "" + "@@@" + quote(name) + "@@@" + quote(pic)
                res.append({"vod_id": sid, "vod_name": name, "vod_pic": self._img(pic),
                    "vod_remarks": dur if dur else ""})
            except:
                continue
        return res
