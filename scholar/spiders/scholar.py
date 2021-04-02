# -*- coding: utf-8 -*-
import scrapy
import re
from urllib.parse import urlencode
import sys

from ..configs import API_KEY

# API_KEY = "5489bb46717bb979378a0475db1e0d69"


def get_url(url):
    payload = {
        "api_key": API_KEY,
        "url": url,
    }
    proxy_url = "http://api.scraperapi.com/?" + urlencode(payload)
    return proxy_url


class ExampleSpider(scrapy.Spider):
    name = "scholar"
    allowed_domains = ["api.scraperapi.com"]

    def url_params(self, position=None):
        params = {
            "hl": "en",
            # "num": 20,
            "as_vis": 1,  # not including citations
            "q": self.keyword,
        }
        if hasattr(self, "year_from"):
            params["as_ylo"] = self.year_from
        if hasattr(self, "year_to"):
            params["as_yhi"] = self.year_to
        if position:
            params["start"] = position
        return params

    def start_requests(self):
        url = "https://scholar.google.com/scholar?" + urlencode(self.url_params())
        yield scrapy.Request(
            get_url(url),
            callback=self.parse,
            dont_filter=True,
            meta={"position": 0, "results": None, "frozen_steps":0, "prev_pos":0},
        )

    def parse(self, response):
        print(response.url)
        if not response.meta["results"]:
            results = "".join(
                response.xpath('.//div[@class="gs_ab_mdw"]//text()').extract()
            )
            results = int(results.split(" ")[1].replace(",", ""))
        else:
            results = response.meta["results"]
        position = response.meta["position"]
        frozen_steps = response.meta["frozen_steps"]
        for res in response.xpath("//*[@data-rp]"):
            link = res.xpath(".//h3/a/@href").extract_first()
            temp = res.xpath(".//h3/a//text()").extract()
            if not temp:
                title = "[C] " + "".join(res.xpath(".//h3/span[@id]//text()").extract())
            else:
                title = "".join(temp)
            published_data = "".join(
                res.xpath('.//div[@class="gs_a"]//text()').extract()
            )
            try:
                year = re.findall("\d{4}", published_data)[-1]
            except:
                year = None
            position += 1
            item = {"title": title, "link": link, "year": year, "position": position,"doi":"","filename":"", "keyword":self.keyword}
            yield item
        # next_page = response.xpath('//td[@align="left"]/a/@href').extract_first()
        if position < results - 9 and position < 991:
            url = "https://scholar.google.com/scholar?" + urlencode(
                self.url_params(position)
            )
            if response.meta["prev_pos"]==position:
                frozen_steps+=1
            if frozen_steps >=5:
                return
            yield scrapy.Request(
                get_url(url),
                callback=self.parse,
                dont_filter=True,
                meta={"position": position, "results": results, "prev_pos":position,"frozen_steps":frozen_steps},
            )
