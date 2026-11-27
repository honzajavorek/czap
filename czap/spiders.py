import json
import subprocess
from pathlib import Path
from typing import cast
import html
from urllib.parse import quote

import scrapy
from scrapy.exceptions import CloseSpider


PROFILE_FORM_ID = "5485226"

MEMBERSHIP_ID = "FunctionalBlock1_ctl00_ctl00_memberProfile_membershipDetails"

ADDRESS_FIELD_ID = "_TextBoxLabel12682798"

CITY_FIELD_ID = "_TextBoxLabel12682799"

AVAILABILITY_FIELD_ID = "_RadioLabel13576980"

# More members than this without a public profile suggests czap.cz hides
# profiles site-wide, so stop rather than export degraded data
MAX_PRIVATE_PROFILES = 10


def profile_url(member_id):
    return f"https://czap.cz/Sys/PublicProfile/{member_id}/{PROFILE_FORM_ID}"


def profile_request(member_id, member, callback):
    return scrapy.Request(
        profile_url(member_id),
        callback,
        cb_kwargs=dict(member_id=member_id, member=member),
        # Don't follow redirects to the login page, so that they get retried
        meta=dict(
            dont_redirect=True,
            handle_httpstatus_list=[301, 302, 303, 307, 308],
        ),
    )


def is_public_profile(response):
    return response.status == 200 and bool(response.css(f"#{MEMBERSHIP_ID}"))


def get_text(response, css):
    if response is None:
        return None
    text = response.css(f"{css}::text").get()
    return text.strip() if text else None


class CZAPSpider(scrapy.Spider):
    name = "czap"

    private_profiles = 0

    async def start(self):
        yield scrapy.FormRequest(
            method="POST",
            url="https://czap.cz/Sys/MemberDirectory/LoadMembers?t=1703710499816",
            formdata=dict(formId="5485226"),
            callback=self.parse,
        )

    def parse(self, response):
        text = response.text[9:]  # remove "while(1);" from the beginning
        json_structure = json.loads(text)["JsonStructure"]

        self.logger.info(
            f"Parsing {len(json_structure)} characters of JavaScript object literal using Node.js"
        )
        script_path = Path(__file__).parent / 'parse_js.js'
        result = subprocess.run(
            ['node', str(script_path)],
            input=json_structure,
            capture_output=True,
            text=True,
            timeout=60  # seconds
        )
        
        if result.returncode != 0:
            raise RuntimeError(f"Failed to parse JavaScript: {result.stderr}")
        
        data = cast(dict, json.loads(result.stdout))
        self.logger.info("Successfully parsed JavaScript object")

        members, ids = data["members"]
        self.logger.info(f"Processing {len(members)} members")
        for i, member in enumerate(members):
            member_id = ids[i]
            yield profile_request(member_id, member, self.parse_member)

    def parse_member(self, response, member_id, member):
        # Sometimes czap.cz redirects a public profile to the login page.
        # Retry without the HTTP cache. If it persists, the member most likely
        # made their profile private, so fall back to the directory listing.
        if not is_public_profile(response):
            retries = response.meta.get("profile_retries", 0)
            if retries < self.settings.getint("RETRY_TIMES"):
                self.logger.warning(
                    f"Member {member_id} not served as a public profile "
                    f"(HTTP {response.status}), retrying"
                )
                request = profile_request(member_id, member, self.parse_member)
                request.meta.update(profile_retries=retries + 1, dont_cache=True)
                yield request.replace(dont_filter=True)
                return
            self.logger.warning(
                f"Member {member_id} not served as a public profile "
                f"(HTTP {response.status}) after {retries} retries, "
                "using the directory listing"
            )
            self.private_profiles += 1
            if self.private_profiles > MAX_PRIVATE_PROFILES:
                raise CloseSpider("too_many_private_profiles")
            response = None

        # Prefer the profile page over the directory listing, which can lag
        # behind it, so that street and city always come from the same source
        city = get_text(response, f"[id*='{CITY_FIELD_ID}']") or html.unescape(
            member["c2"][0]["v"]
        )
        address = get_text(response, f"[id*='{ADDRESS_FIELD_ID}']")
        membership = get_text(response, f"#{MEMBERSHIP_ID}") or html.unescape(
            member["c1"][2]["v"]
        )
        availability = get_text(
            response, f"[id*='{AVAILABILITY_FIELD_ID}']"
        ) or html.unescape(member["c3"][0]["v"])
        self.logger.debug(f"Location: {city!r} / {address!r}")
        location = get_location(address, city)
        if location:
            mapycom_url = f"https://mapy.com/zakladni?q={quote(location)}"
            googlemaps_url = f"https://www.google.com/maps?q={quote(location)}"
        else:
            mapycom_url = None
            googlemaps_url = None
        yield {
            "id": member_id,
            "url": profile_url(member_id),
            "name": html.unescape(member["c1"][0]["v"]),
            "membership": membership,
            "location": location,
            "mapycom_url": mapycom_url,
            "googlemaps_url": googlemaps_url,
            "availability": availability,
        }


def get_location(address, city):
    if is_empty_location(city):
        return None
    if is_empty_location(address) or address == city:
        return city
    return f"{address}, {city}"


def is_empty_location(value):
    if not value:
        return True
    if "online" in value.lower() or "on-line" in value.lower():
        return True
    if value.lower() in [
        "na",
        "n/a",
        "-",
        "000",
        "neuvedeno",
        "xxx",
        "x",
        "momentálně nemám fyzické pracoviště",
    ]:
        return True
    return False
