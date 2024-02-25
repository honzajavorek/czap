import itertools
import sys
import threading
import json
import time
from typing import cast
import scrapy
import demjson3
import html
from diskcache import Cache
from urllib.parse import quote


class CZAPSpider(scrapy.Spider):
    name = "czap"

    def start_requests(self):
        yield scrapy.FormRequest(
            method="POST",
            url="https://czap.cz/Sys/MemberDirectory/LoadMembers?t=1703710499816",
            formdata=dict(formId="5485226"),
            callback=self.parse,
        )

    def parse(self, response):
        text = response.text[9:]  # remove "while(1);" from the beginning
        json_structure = json.loads(text)["JsonStructure"]

        with Cache(self.settings["DISKCACHE_DIR"]) as cache:
            try:
                data = cast(dict, cache["data"])
                self.logger.info("Loaded demjson3 data from cache")
            except KeyError:
                self.logger.info(
                    f"Parsing {len(json_structure)} characters by demjson3, this can take several minutes"
                )
                holder = dict(done=False)
                t = threading.Thread(target=animate, args=(holder,))
                t.start()
                data = cast(dict, demjson3.decode(json_structure))  # super super slow
                cache.set("data", data, expire=60 * 60 * 24 * 7)  # 1 week (in seconds)
                holder["done"] = True

        members, ids = data["members"]
        for i, member in enumerate(members):
            member_id = ids[i]
            item = {
                "id": member_id,
                "url": f"https://czap.cz/Sys/PublicProfile/{member_id}/5485226",
                "name": html.unescape(member["c1"][0]["v"]),
                "membership": html.unescape(member["c1"][2]["v"]),
                "location": html.unescape(member["c2"][0]["v"]),
                "availability": html.unescape(member["c3"][0]["v"]),
            }
            yield scrapy.Request(
                item["url"], self.parse_member, cb_kwargs=dict(item=item)
            )

    def parse_member(self, response, item):
        location = response.css('[id*="_TextBoxLabel12682798"]::text').get()
        item["location"] = f'{location}, {item["location"]}'
        item["map_url"] = f"https://mapy.cz/zakladni?q={quote(item['location'])}"
        yield item


def animate(holder):
    for c in itertools.cycle(["|", "/", "-", "\\"]):
        if holder["done"]:
            break
        sys.stdout.write("\rParsing " + c)
        sys.stdout.flush()
        time.sleep(0.1)
    sys.stdout.write("\rDone!     ")
