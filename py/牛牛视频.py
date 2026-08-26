#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
牛牛视频 爬虫 v2 (主 API nn.123xiangshang.com, 与 APP 数据一致)
- 分类:   GET /types   (服务端下发, 含 热舞/传媒/吃瓜/福利/午夜/AI短剧 type_id=12)
- 列表:   GET /list    (class/order/type_id/area/year/state/wd/page, 子分类走 class)
- 首页:   GET /main
- 详情:   GET /detail?vod_id=X   (sources[].episodes[].url, 含 player_id)
- 播放:   player_id → 解析器URL → JSON {code,url,headers}
响应 AES/ECB/PKCS5 加密, key = "/path?query" 截断16位(不足补"0")
"""
import base64
import json
import re
import requests
from urllib.parse import quote
 
try:
    from base.spider import Spider as BaseSpider
except Exception:
    class BaseSpider:
        pass
 
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
 
 
class Spider(BaseSpider):
    name = "牛牛视频"
 
    # 主 API 域名(APP 默认 base_url, 可在 extend 中覆盖)
    _HOST = "https://nn.123xiangshang.com:35620"
 
    # 请求头(与 APP 拦截器一致: p/pkg/t/d/v/y/product/sys)
    _HEADERS = {
        "p": "android",
        "pkg": "com.sexy.goddess",
        "t": "",
        "d": "0000000000000000",
        "v": "1.6.2",
        "y": "0",
        "product": "Pixel 7",
        "sys": "13",
        "User-Agent": "okhttp/4.9.3",
    }
 
    # Android Uri.encode(query, "-![.:/,%?&=]") 保留字符集
    _SAFE = "-_.!~*'()[]:/?,%&="
 
    # player_id → 解析器URL模板(%s 为剧集 url), 源配置来自 APP /config
    # 数字型 ep 走三步源第一步(实测直接返回可播放 url)
    _PARSERS = {
        "paopao": "http://116.211.150.40:856/duanju/dj.php?id=%s",      # AI短剧
        "madou": "http://116.211.150.40:5231/cg/jx.php?id=%s",          # 吃瓜
        "meiju": "http://82.156.24.206:12345/jx/jxm.php?url=%s",        # 热舞
        "thzy": "http://198.16.61.170:856/jx/thz.php?id=%s",            # 传媒
        "xj": "http://82.156.24.206:12345/jx/xj22.php?id=%s",           # 福利
        "91gc": "http://198.16.61.170:6100/jx/wy.php?id=%s",            # 午夜
        "djzy": "http://82.156.24.206:12345/jx/dj.php?url=%s",          # 短剧
        "pp": "http://ccs.js.yy.028ncf.cn/jx/ss.php?id=%s",
        "shizi": "http://116.211.150.40:856/zhenxiang/jx.php?id=%s",
        "juzi": "http://116.211.150.40:856/qianduan/jz.php?id=%s",
        "shanju": "http://116.211.150.40:856/jx/sj.php?id=%s",
        "ningmeng": "http://116.211.150.40:856/jx/nm.php?id=%s",
        "leidian": "http://192.144.141.22:12345/cs/db.php?id=%s",
        "douban": "http://198.16.61.170:6100/jx/db.php?url=%s",
        "jm3u8": "http://82.156.24.206:12345/jx/jx.php?url=%s",
        "hm3u8": "http://82.156.24.206:12345/jx/jx.php?url=%s",
        "xm": "http://152.136.196.209:12345/jx/xm.php?url=%s",
        "xhs": "http://152.136.181.200:5500/jx/xhs.php?id=%s",
        "bl": "http://198.16.61.170:6100/jx/ouligei.php?z=bl&id=%s",
        "xrk": "http://198.16.61.170:6100/jx/ouligei.php?z=xrk&id=%s",
        "sg": "http://198.16.61.170:6100/jx/ouligei.php?z=sg&id=%s",
        "cm": "http://198.16.61.170:6100/jx/ouligei.php?z=cm&id=%s",
        "huagu": "http://152.136.196.209:12345/jx/jxh.php?url=%s",
        "hema": "http://ccs.js.tt.didian.site/jx/xc.php?url=%s",
        "ffzy": "http://198.16.61.170:6100/jx/ff.php?url=%s",
        "bfzy": "http://49.232.251.44:894/jx/bf.php?url=%s",
        "jszy": "http://198.16.61.170:6100/jx/jszy.php?url=%s",
        "sdzy": "http://49.232.251.44:894/jx/sd.php?url=%s",
        "snzy": "http://49.232.251.44:894/jx/sn.php?url=%s",
        "jyzy": "http://198.16.61.170:6100/jx/js.php?url=%s",
        "kkzy": "http://198.16.61.170:6100/jx/ff.php?url=%s",
        "wjzy": "http://49.232.251.44:894/jx/wj.php?url=%s",
        "tkzy": "http://198.16.61.170:6100/jx/ff.php?url=%s",
        "lzzy": "http://198.16.61.170:6100/jx/ff.php?url=%s",
        "qyzy": "http://198.16.61.170:6100/jx/qy.php?url=%s",
        "jzzy": "http://154.8.141.13:5560/jx/ht.php?url=%s",
        "hmjc": "http://154.8.141.13:5560/jx/dj.php?url=%s",
        "zbjx": "http://192.144.141.22/jx/migu.php?id=%s",
        "bddj": "http://82.156.24.206:12345/jx/bddj.php?id=%s",
        "qmdj": "http://82.156.24.206:12345/jx/qmdj.php?id=%s",
    }
 
    # 数字型复杂源(hema/xiaocao/xm3u8 需 Src1 token 三步, 不在解析器表内则跳过)
    _SKIP = {"hema", "xiaocao", "xm3u8"}
 
    # 数字型 ep 中已验证"第一步解析即直接返回可播放 url"的源
    # (普通分类的 juzi/shanju 等数字型源返回二级签名 API, 不可用)
    _DIRECT = {"paopao", "madou", "91gc", "xj", "thzy", "meiju", "djzy", "djan", "zbjx"}
 
    def __init__(self):
        self.host = self._HOST
        self._classes = None
        self._filters = {}
        self.page_size = 20
        self.session = requests.Session()
        self.session.verify = False
 
    def init(self, extend=""):
        if extend:
            try:
                cfg = json.loads(extend)
                if cfg.get("host"):
                    self.host = cfg["host"].rstrip("/")
            except Exception:
                pass
 
    def getName(self):
        return self.name
 
    # ========== 加解密与请求 ==========
 
    def _decrypt(self, pathq, text):
        """响应解密: 明文JSON直接返回, 否则 AES/ECB key=pathq截断16补0"""
        text = (text or "").strip()
        if not text:
            return {}
        try:
            return json.loads(text)
        except Exception:
            pass
        try:
            key = (pathq if len(pathq) >= 16 else pathq + "0" * (16 - len(pathq)))[:16]
            ct = base64.b64decode(text)
            cipher = AES.new(key.encode("utf-8"), AES.MODE_ECB)
            return json.loads(unpad(cipher.decrypt(ct), AES.block_size).decode("utf-8"))
        except Exception:
            return {}
 
    def _get(self, path, params=None):
        """GET 主API, 返回解密后的 dict"""
        raw_q = "&".join("%s=%s" % (k, v) for k, v in (params or {}).items())
        encoded_q = quote(raw_q, safe=self._SAFE)
        url = self.host + "/" + path + ("?" + encoded_q if encoded_q else "")
        pathq = "/" + path + ("?" + encoded_q if encoded_q else "")
        try:
            r = self.session.get(url, headers=self._HEADERS, timeout=15)
            return self._decrypt(pathq, r.text)
        except Exception:
            return {}
 
    # ========== 分类与筛选 ==========
 
    def _load_classes(self):
        if self._classes:
            return self._classes
        arr = []
        j = self._get("types")
        for m in (j or {}).get("data") or []:
            tid = m.get("type_id")
            name = m.get("type_name")
            if tid is not None and name:
                arr.append({"type_id": str(tid), "type_name": str(name),
                            "type_extend": m.get("type_extend") or {}})
        self._classes = arr
        return arr
 
    def _filters_of(self, types_extend):
        """type_extend → TVBox filters(class/area/lang/year + order)"""
        filters = []
        if types_extend.get("class"):
            filters.append({
                "key": "class", "name": "类型",
                "value": [{"n": v, "v": v} for v in str(types_extend["class"]).split(",")],
            })
        if types_extend.get("area"):
            filters.append({
                "key": "area", "name": "地区",
                "value": [{"n": v, "v": v} for v in str(types_extend["area"]).split(",")],
            })
        if types_extend.get("year"):
            filters.append({
                "key": "year", "name": "年份",
                "value": [{"n": v, "v": v} for v in str(types_extend["year"]).split(",")],
            })
        filters.append({
            "key": "order", "name": "排序",
            "value": [
                {"n": "最新", "v": "最新"},
                {"n": "最热", "v": "最热"},
                {"n": "评分", "v": "评分"},
            ],
        })
        return filters
 
    # ========== TVBox 接口 ==========
 
    def homeContent(self, filter):
        classes = []
        for c in self._load_classes():
            classes.append({"type_id": c["type_id"], "type_name": c["type_name"]})
        filters = {c["type_id"]: self._filters_of(c["type_extend"]) for c in self._classes}
 
        # 首页推荐: /main 板块列表
        items = []
        j = self._get("main")
        for block in (j or {}).get("data") or []:
            for v in block.get("list") or []:
                items.append(self._vod_from_list(v))
        if not items:
            j = self._get("list", {"class": "", "order": "最新", "type_id": "5",
                                   "area": "", "year": "", "state": "", "wd": "", "page": "1"})
            items = [self._vod_from_list(v) for v in (j or {}).get("data") or []]
 
        return {"class": classes, "filters": filters, "list": items[:40]}
 
    def homeVideoContent(self):
        j = self._get("list", {"class": "", "order": "最新", "type_id": "5",
                               "area": "", "year": "", "state": "", "wd": "", "page": "1"})
        items = [self._vod_from_list(v) for v in (j or {}).get("data") or []]
        return {"list": items}
 
    def categoryContent(self, tid, pg, filter, extend):
        extend = extend or {}
        pg = int(pg) if str(pg).isdigit() else 1
        params = {
            "class": str(extend.get("class") or ""),
            "order": str(extend.get("order") or "最新"),
            "type_id": str(tid),
            "area": str(extend.get("area") or ""),
            "year": str(extend.get("year") or ""),
            "state": "",
            "wd": "",
            "page": str(pg),
        }
        j = self._get("list", params)
        lst = (j or {}).get("data") or []
        items = [self._vod_from_list(v) for v in lst]
        pagecount = pg + 1 if len(items) >= self.page_size else pg
        return {
            "page": pg,
            "pagecount": pagecount,
            "limit": self.page_size,
            "total": 99999,
            "list": items,
        }
 
    def detailContent(self, ids):
        vid = str(ids[0])
        j = self._get("detail", {"vod_id": vid})
        d = (j or {}).get("data") or {}
        if not d.get("vod_name"):
            return {"list": []}
 
        vod = {
            "vod_id": str(d.get("vod_id") or vid),
            "vod_name": d.get("vod_name", ""),
            "vod_pic": d.get("vod_pic", ""),
            "vod_year": str(d.get("vod_year") or ""),
            "vod_area": d.get("vod_area", ""),
            "type_name": d.get("vod_class", ""),
            "vod_actor": d.get("vod_actor", ""),
            "vod_director": d.get("vod_director", ""),
            "vod_content": d.get("vod_content", "") or d.get("vod_blurb", ""),
            "vod_remarks": d.get("vod_remarks", ""),
        }
 
        sources = []
        for s_ in d.get("sources") or []:
            pid = s_.get("player_id")
            if not pid or pid in self._SKIP:
                continue
            eps = s_.get("episodes") or []
            if not eps:
                continue
            # URL 型 ep 直接可播; 数字型 ep 仅保留已验证直接可播的源
            first_url = eps[0].get("url") or ""
            if not first_url.startswith("http") and pid not in self._DIRECT:
                continue
            sources.append({"player_id": pid, "prio": int(s_.get("prio") or 999),
                            "episodes": eps})
 
        if not sources:
            return {"list": []}
 
        # 按 prio 排序(小→大), 最多保留 4 个可切换源
        sources.sort(key=lambda x: x["prio"])
        sources = sources[:4]
 
        play_from = []
        play_urls = []
        for s_ in sources:
            pid = s_["player_id"]
            play_from.append(pid)
            eps_str = "#".join(
                "%s$%s@@%s" % (e.get("name") or "第%02d集" % (i + 1), e.get("url"), pid)
                for i, e in enumerate(s_["episodes"])
            )
            play_urls.append(eps_str)
        vod["vod_play_from"] = "#".join(play_from)
        vod["vod_play_url"] = "#".join(play_urls)
        return {"list": [vod]}
 
    def searchContent(self, key, quick, pg="1"):
        pg = int(pg) if str(pg).isdigit() else 1
        j = self._get("list", {"class": "", "order": "最新", "type_id": "",
                               "area": "", "year": "", "state": "", "wd": str(key),
                               "page": str(pg)})
        lst = (j or {}).get("data") or []
        items = [self._vod_from_list(v) for v in lst]
        pagecount = pg + 1 if len(items) >= self.page_size else pg
        return {
            "page": pg,
            "pagecount": pagecount,
            "limit": self.page_size,
            "total": 99999,
            "list": items,
        }
 
    def playerContent(self, flag, id, vipFlags):
        s = str(id)
        if "@@" in s:
            ep, player = s.rsplit("@@", 1)
        else:
            ep, player = s, str(flag)
 
        # URL 型 ep(m3u8/mp4/ts)直接可播
        if ep.startswith("http") and re.search(r"\.(m3u8|mp4|ts|flv)(\?|$)", ep):
            return {"parse": 0, "playUrl": "", "url": ep, "header": "{}"}
 
        tpl = self._PARSERS.get(player)
        if not tpl:
            return {"parse": 1, "playUrl": "", "url": ""}
 
        url = tpl.replace("%s", ep)
        try:
            r = self.session.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
            j = r.json()
        except Exception:
            return {"parse": 1, "playUrl": "", "url": ""}
 
        play = (j or {}).get("url") or ""
        if not play:
            return {"parse": 1, "playUrl": "", "url": ""}
 
        headers = self._parse_headers((j or {}).get("headers") or "")
        return {"parse": 0, "playUrl": "", "url": play, "header": json.dumps(headers)}
 
    def isVideoContent(self):
        return True
 
    # ========== 内部方法 ==========
 
    @staticmethod
    def _parse_headers(s):
        """解析器响应的 headers 字符串(换行/回车分隔 key:value) → dict"""
        out = {}
        if not s:
            return out
        for line in str(s).replace("\r", "").split("\n"):
            if ":" in line:
                k, _, v = line.partition(":")
                k = k.strip()
                if k:
                    out[k] = v.strip()
        return out
 
    @staticmethod
    def _vod_from_list(v):
        return {
            "vod_id": str(v.get("vod_id") or ""),
            "vod_name": v.get("vod_name", ""),
            "vod_pic": v.get("vod_pic", ""),
            "vod_remarks": v.get("vod_remarks", ""),
        }