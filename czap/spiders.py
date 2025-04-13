import itertools
import sys
import threading
import json
import time
from typing import cast
import html
from urllib.parse import quote

import scrapy
import demjson3
from diskcache import Cache


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

        cache_dir = self.settings["DISKCACHE_DIR"]
        cache_expire = self.settings["DISKCACHE_EXPIRATION_SECS"]

        with Cache(cache_dir) as cache:
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
                cache.set("data", data, expire=cache_expire)
                holder["done"] = True

        members, ids = data["members"]
        self.logger.info(f"Processing {len(members)} members")
        for i, member in enumerate(members):
            member_id = ids[i]
            member_url = f"https://czap.cz/Sys/PublicProfile/{member_id}/5485226"
            yield scrapy.Request(
                member_url,
                self.parse_member,
                cb_kwargs=dict(member_id=ids[i], member=member),
            )

    def parse_member(self, response, member_id, member):
        city = html.unescape(member["c2"][0]["v"])
        address = response.css('[id*="_TextBoxLabel12682798"]::text').get()
        self.logger.debug(f"Location: {city!r} / {address!r}")
        if is_empty_location(city):
            location = None
            mapycom_url = None
            googlemaps_url = None
        else:
            if is_empty_location(address):
                location = city
            elif city == address:
                location = city
            else:
                location = f"{address}, {city}"
            mapycom_url = f"https://mapy.com/zakladni?q={quote(location)}"
            googlemaps_url = f"https://www.google.com/maps?q={quote(location)}"
        yield {
            "id": member_id,
            "url": response.url,
            "name": html.unescape(member["c1"][0]["v"]),
            "membership": html.unescape(member["c1"][2]["v"]),
            "location": location,
            "mapycom_url": mapycom_url,
            "googlemaps_url": googlemaps_url,
            "availability": html.unescape(member["c3"][0]["v"]),
        }


def is_empty_location(value):
    if not value:
        return True
    if "online" in value.lower() or "on-line" in value.lower():
        return True
    if value.lower() in ["na", "n/a", "-", "000", "neuvedeno", "xxx"]:
        return True
    return False


def animate(holder):
    for c in itertools.cycle(["|", "/", "-", "\\"]):
        if holder["done"]:
            break
        sys.stdout.write("\rParsing " + c)
        sys.stdout.flush()
        time.sleep(0.1)
    sys.stdout.write("\rDone!     ")
