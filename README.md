# 💆 czap.cz members

Scraping [czap.cz members](https://czap.cz/adresar) so you can filter available psychotherapists by any criteria you wish:

- [Download JSON](https://raw.githubusercontent.com/honzajavorek/czap/main/items.json)

I wanted to filter a list of Czech psychotherapists according to different criteria than those available at the [registry website](https://czap.cz/adresar). For example, the registry allows to filter by location, but only to the level of region. As there is 700+ therapists in Prague itself, it's not very useful.

I don't think it's useful to monitor changes in the registry, but I used [git scraping](https://simonwillison.net/2020/Oct/9/git-scraping/) nevertheless, because why not:

- [History of changes](https://github.com/honzajavorek/czap/commits/main/items.json)
- [Feed of changes](https://github.com/honzajavorek/czap/commits/main.atom) (aka RSS)

The scraper uses my favorite [Scrapy](https://docs.scrapy.org/) framework. So far I scrape only a few fields. If you want to build on top of the data and you're missing something, let me know in [issues](https://github.com/honzajavorek/czap/issues).
