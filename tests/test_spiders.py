import json
from pathlib import Path

import pytest
from scrapy import Request
from scrapy.exceptions import CloseSpider
from scrapy.http import HtmlResponse
from scrapy.settings import Settings

from czap.spiders import MAX_REUSED_ITEMS, CZAPSpider, get_location, profile_url


FIXTURES_DIR = Path(__file__).parent

MEMBER_ID = 69010502

# Directory listing data as the spider gets them from LoadMembers
MEMBER = {
    "c1": [{"v": "Škarvadová, Lucie"}, {"v": ""}, {"v": "Kandidátní členství - ve výcviku"}],
    "c2": [{"v": "Praha 2"}],
    "c3": [{"v": "Přijímám nové klienty"}],
}


@pytest.fixture
def spider():
    spider = CZAPSpider()
    spider.settings = Settings({"RETRY_TIMES": 2})
    return spider


def make_response(fixture=None, status=200, meta=None, member_id=MEMBER_ID):
    url = profile_url(member_id)
    request = Request(url, meta=meta or {})
    if fixture:
        body = (FIXTURES_DIR / fixture).read_bytes()
        return HtmlResponse(url, body=body, status=status, request=request)
    headers = {"Location": "/Sys/Login?ReturnUrl=%2fSys%2fPublicProfile"}
    return HtmlResponse(url, status=status, headers=headers, request=request)


def test_parse_member(spider):
    response = make_response("profile.html")
    items = list(spider.parse_member(response, MEMBER_ID, MEMBER))

    assert items == [
        {
            "id": 69010502,
            "url": "https://czap.cz/Sys/PublicProfile/69010502/5485226",
            "name": "Škarvadová, Lucie",
            "membership": "Řádné členství",
            "location": "Lucemburská 3, Praha 2",
            "mapycom_url": "https://mapy.com/zakladni?q=Lucembursk%C3%A1%203%2C%20Praha%202",
            "googlemaps_url": "https://www.google.com/maps?q=Lucembursk%C3%A1%203%2C%20Praha%202",
            "availability": "Info o dostupnosti na vyžádání",
        }
    ]


def test_parse_member_prefers_profile_city_over_listing(spider):
    member = {**MEMBER, "c2": [{"v": "Vracov"}]}
    response = make_response("profile-moved.html", member_id=69158497)
    items = list(spider.parse_member(response, 69158497, member))

    assert items[0]["location"] == "Sochorova 3226/40, Brno"


@pytest.mark.parametrize("status", [301, 302, 303, 307, 308])
def test_parse_member_retries_redirect(spider, status):
    response = make_response(status=status)
    requests = list(spider.parse_member(response, MEMBER_ID, MEMBER))

    assert len(requests) == 1
    request = requests[0]
    assert isinstance(request, Request)
    assert request.url == profile_url(MEMBER_ID)
    assert request.dont_filter is True
    assert request.meta["dont_cache"] is True
    assert request.meta["dont_redirect"] is True
    assert request.meta["profile_retries"] == 1
    assert request.cb_kwargs == dict(member_id=MEMBER_ID, member=MEMBER)


def test_parse_member_retries_page_without_profile(spider):
    response = HtmlResponse(
        profile_url(MEMBER_ID),
        body=b"<html><body><h1>Authorization required</h1></body></html>",
        request=Request(profile_url(MEMBER_ID)),
    )
    requests = list(spider.parse_member(response, MEMBER_ID, MEMBER))

    assert [request.meta["profile_retries"] for request in requests] == [1]


PREVIOUS_ITEM = {
    "id": MEMBER_ID,
    "url": profile_url(MEMBER_ID),
    "name": "Nováková, Jana",
    "membership": "Řádné členství",
    "location": "Ulice 1, Město",
    "mapycom_url": "https://mapy.com/zakladni?q=Ulice%201%2C%20M%C4%9Bsto",
    "googlemaps_url": "https://www.google.com/maps?q=Ulice%201%2C%20M%C4%9Bsto",
    "availability": "Přijímám nové klienty",
}


@pytest.fixture
def previous_items(spider, tmp_path):
    path = tmp_path / "previous-items.json"
    path.write_text(json.dumps([PREVIOUS_ITEM]))
    spider.settings.set("PREVIOUS_ITEMS_PATH", str(path))


def test_parse_member_gives_up_retrying(spider, tmp_path):
    spider.settings.set("PREVIOUS_ITEMS_PATH", str(tmp_path / "missing.json"))
    response = make_response(status=302, meta={"profile_retries": 2})

    with pytest.raises(RuntimeError, match="no previous data"):
        list(spider.parse_member(response, MEMBER_ID, MEMBER))


def test_parse_member_gives_up_retrying_unknown_member(spider, previous_items):
    response = make_response(status=302, meta={"profile_retries": 2}, member_id=1)

    with pytest.raises(RuntimeError, match="no previous data"):
        list(spider.parse_member(response, 1, MEMBER))


def test_parse_member_reuses_previous_item(spider, previous_items):
    response = make_response(status=302, meta={"profile_retries": 2})
    items = list(spider.parse_member(response, MEMBER_ID, MEMBER))

    assert items == [PREVIOUS_ITEM]
    assert spider.reused_items == 1


def test_parse_member_stops_on_too_many_reused_items(spider, previous_items):
    spider.reused_items = MAX_REUSED_ITEMS
    response = make_response(status=302, meta={"profile_retries": 2})

    with pytest.raises(CloseSpider):
        list(spider.parse_member(response, MEMBER_ID, MEMBER))


@pytest.mark.parametrize(
    "address, city, expected",
    [
        ("Lucemburská 3", "Praha 2", "Lucemburská 3, Praha 2"),
        (None, "Praha 2", "Praha 2"),
        ("Praha 2", "Praha 2", "Praha 2"),
        ("online", "Praha 2", "Praha 2"),
        ("Lucemburská 3", None, None),
        ("Lucemburská 3", "neuvedeno", None),
        (None, "On-line", None),
    ],
)
def test_get_location(address, city, expected):
    assert get_location(address, city) == expected
