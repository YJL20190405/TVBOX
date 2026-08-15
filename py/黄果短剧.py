#!/usr/bin/python
# coding=utf-8
import re, json, requests
from urllib.parse import quote
from base.spider import Spider

class Spider(Spider):
    def __init__(self):
        super().__init__()
        self.name = "黄果短剧"
        self.host = "https://huangguoai.com"
        self.header = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": self.host,
            "Accept-Language": "zh-CN,zh;q=0.9"
        }
        self.class_map = {
            "AI成人短剧": "/ai-duanju/",
            "AI成人漫剧": "/ai-manju/",
            "AI换脸": "/ai-huanlian/",
            "AI魔改": "/ai-mogai/",
            "黄果吃瓜": "/chigua/",
            "排行榜": "/ranks/hot/"
        }
        self.filter_map = {"": {}}

    def init(self, extend):
        pass

    def getName(self):
        return self.name

    def homeContent(self, filter):
        class_list = [{"type_id": name, "type_name": name} for name in self.class_map]
        result = {"class": class_list, "list": self._get_cards(f"{self.host}/", 1)[0]}
        return result

    def homeVideoContent(self):
        return self._get_cards(f"{self.host}/", 1)[0]
    def categoryContent(self, tid, pg, filter, extend):
        url = f"{self.host}{self.class_map.get(tid, tid)}"
        if pg > 1:
            url = f"{url}{pg}/"
        vod_list, total = self._get_cards(url, pg)
        return {"list": vod_list, "page": pg, "pagecount": total or 1, "limit": 24, "total": total * 24}

    def detailContent(self, ids):
        vid = ids[0] if isinstance(ids, list) else ids
        m = re.search(r'(\d+)', vid)
        if not m:
            return {"list": []}
        vid = m.group(1)
        url = f"{self.host}/video/{vid}/"
        html = self._get(url)
        data = self._parse_initial_data(html)
        if data and data.get("epPlaySrcs"):
            title = data.get("title") or vid
            pic = data.get("coverSrc") or data.get("posterSrc") or ""
            eps = data.get("epPlaySrcs") or {}
            ep_urls = []
            for ep_id in sorted(eps.keys(), key=lambda x: int(x)):
                ep_urls.append(f"{ep_id}${eps[ep_id]}")
            play_url = "#".join(ep_urls) if ep_urls else ""
            return {"list": [{"vod_id": vid, "vod_name": title, "vod_pic": pic, "vod_play_from": "黄果", "vod_play_url": play_url}]}
        return self._detail_post(vid)

    def searchContent(self, key, quick, pg=1):
        url = f"{self.host}/search/?keyword={quote(key)}"
        if pg > 1:
            url += f"&page={pg}"
        vod_list, total = self._get_cards(url, pg)
        return {"list": vod_list, "page": pg, "pagecount": total or 1, "limit": 24, "total": total * 24}

    def playerContent(self, flag, id, vipFlags):
        return {"parse": 0, "url": id, "header": '{"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36","Referer":"https://huangguoai.com/"}'}

    def localProxy(self, param):
        return [200, "video/mp2t", []]

    def _get(self, url):
        try:
            r = requests.get(url, headers=self.header, timeout=10, verify=False)
            return r.text
        except Exception:
            return ""

    def _parse_initial_data(self, html):
        m = re.search(r'<script id="videoInitialData" type="application/json">(.*?)</script>', html, re.S)
        if not m:
            return None
        try:
            return json.loads(m.group(1))
        except Exception:
            return None

    def _detail_post(self, vid):
        url = f"{self.host}/archives/{vid}/"
        html = self._get(url)
        if not html:
            return {"list": []}
        title_m = re.search(r'<title>(.*?)</title>', html, re.S)
        title = self._clean(title_m.group(1).split("-")[0]) if title_m else vid
        pic_m = re.search(r'<meta property="og:image" content="([^"]+)"', html) or re.search(r'posterSrc":"([^"]+)"', html)
        pic = pic_m.group(1) if pic_m else ""
        srcs = re.findall(r'class="post-video-player"[^>]*data-src="([^"]+)"', html)
        if not srcs:
            srcs = re.findall(r'data-src="(https?://[^"]+\.m3u8[^"]*)"', html)
        ep_urls = []
        for i, src in enumerate(srcs, 1):
            ep_urls.append(f"第{i}集${src}")
        play_url = "#".join(ep_urls) if ep_urls else ""
        return {"list": [{"vod_id": vid, "vod_name": title, "vod_pic": pic, "vod_play_from": "黄果", "vod_play_url": play_url}]}

    def _get_cards(self, url, pg):
        html = self._get(url)
        if not html:
            return [], 0
        html = re.sub(r'<template[\s\S]*?</template>', '', html)
        vod_list = []
        seen = set()
        cards = re.findall(r'<div class="hg-drama-card"[^>]*data-track-id="(\d+)"[^>]*>(.*?)</div>\s*</div>', html, re.S)
        for vid, card in cards:
            try:
                if vid in seen:
                    continue
                seen.add(vid)
                name_m = re.search(r'alt="([^"]*)"', card) or re.search(r'<h2[^>]*>.*?<a[^>]*>([^<]+)</a>', card, re.S)
                name = self._clean(name_m.group(1) if name_m else vid)
                pic_m = re.search(r'data-src="([^"]+)"', card)
                pic = pic_m.group(1) if pic_m else ""
                rem_m = re.search(r'hg-drama-card__episode">([^<]*)<', card)
                rem = self._clean(rem_m.group(1)) if rem_m else ""
                vod_list.append({"vod_id": vid, "vod_name": name, "vod_pic": pic, "vod_remarks": rem})
            except Exception:
                continue
        ranks = re.findall(r'<div class="hg-rank-item"[^>]*data-track-id="(\d+)"[^>]*>(.*?)</div>\s*</div>', html, re.S)
        for vid, card in ranks:
            try:
                if vid in seen:
                    continue
                seen.add(vid)
                name_m = re.search(r'alt="([^"]*)"', card) or re.search(r'<h2[^>]*>.*?<a[^>]*>([^<]+)</a>', card, re.S)
                name = self._clean(name_m.group(1) if name_m else vid)
                pic_m = re.search(r'data-src="([^"]+)"', card)
                pic = pic_m.group(1) if pic_m else ""
                rem_m = re.search(r'<span class="hg-rank-num[^"]*">([^<]*)<', card)
                rem = self._clean(rem_m.group(1)) if rem_m else ""
                vod_list.append({"vod_id": vid, "vod_name": name, "vod_pic": pic, "vod_remarks": rem})
            except Exception:
                continue
        posts = re.findall(r'<a class="hg-post-card" href="/archives/(\d+)/">(.*?)</a>', html, re.S)
        for vid, card in posts:
            try:
                if vid in seen:
                    continue
                seen.add(vid)
                name_m = re.search(r'<h3>(.*?)</h3>', card, re.S) or re.search(r'alt="([^"]*)"', card)
                name = self._clean(name_m.group(1)) if name_m else vid
                pic_m = re.search(r'data-src="([^"]+)"', card)
                pic = pic_m.group(1) if pic_m else ""
                vod_list.append({"vod_id": vid, "vod_name": name, "vod_pic": pic, "vod_remarks": ""})
            except Exception:
                continue
        total = 0
        pages_m = re.search(r'data-pages="(\d+)"', html)
        if pages_m:
            total = int(pages_m.group(1))
        return vod_list, total

    def _clean(self, text):
        return re.sub(r'\s+', ' ', text).strip() if text else ""