BOT_NAME = "czap"

SPIDER_MODULES = ["czap.spiders"]

USER_AGENT = "czap (+https://github.com/honzajavorek/czap)"

DOWNLOAD_DELAY = 1

AUTOTHROTTLE_ENABLED = True

FEED_EXPORTERS = {
    "sorted_json": "czap.exporters.SortedJsonItemExporter",
}

FEEDS = {
    "items.json": {
        "format": "sorted_json",
        "encoding": "utf-8",
        "indent": 4,
        "overwrite": True,
    },
}

DISKCACHE_DIR = ".cache"
