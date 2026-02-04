BOT_NAME = "czap"

SPIDER_MODULES = ["czap.spiders"]

USER_AGENT = "czap (+https://github.com/honzajavorek/czap)"

DOWNLOAD_DELAY = 1

AUTOTHROTTLE_ENABLED = True

HTTPCACHE_ENABLED = True

HTTPCACHE_EXPIRATION_SECS = 60 * 60 * 24  # 1 day (in seconds)

FEED_EXPORTERS = {
    "sorted_json": "czap.exporters.SortedJsonItemExporter",
}

FEEDS = {
    "items.json": {
        "format": "sorted_json",
        "encoding": "utf8",
        "indent": 4,
        "overwrite": True,
    },
    "items.csv": {
        "format": "csv",
        "overwrite": True,
    },
}

CLOSESPIDER_ERRORCOUNT = 1
