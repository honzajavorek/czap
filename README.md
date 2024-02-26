# 💆 czap.cz members

Scraping [czap.cz members](https://czap.cz/adresar) so you can filter available psychotherapists by any criteria you wish:

-   [Download JSON](https://raw.githubusercontent.com/honzajavorek/czap/main/items.json)

I wanted to filter a list of Czech psychotherapists according to different criteria than those available at the [registry website](https://czap.cz/adresar). For example, the registry allows to filter by location, but only to the level of region. As there is 700+ therapists in Prague itself, it's not very useful.

## Monitoring changes

I don't think it's useful to monitor changes in the registry, but I used [git scraping](https://simonwillison.net/2020/Oct/9/git-scraping/) nevertheless, because why not:

-   [History of changes](https://github.com/honzajavorek/czap/commits/main/items.json)
-   [Feed of changes](https://github.com/honzajavorek/czap/commits/main.atom) (aka RSS)

## Notes on development

The scraper uses my favorite [Scrapy](https://docs.scrapy.org/) framework.

So far I scrape only a few fields.
If you want to build on top of the data and you're missing something, let me know in [issues](https://github.com/honzajavorek/czap/issues).
However, because I won't have time to add the fields, you better edit the code and add them yourself.

The scraper first downloads all registry with a single request.
The data is encoded not as a JSON, but as a non-standard JavaScript mess.
I figured out the library `demjson3` can parse it, but it takes long minutes (e.g. 30 min) to get the result.
I added cache so that the parse result stays around at least for a day.

That data contains some info about members.
It is structured, but it's in a very cryptic structure which needs to be reverse-engineered.
If you're the kind of person who is into such thing, look at the end of the `parse()` method, where it iterates over individual members, and feel free to add fields there.

If you prefer good old HTML scraping, look at the `parse_member()` method, where you can access response of individual member profile pages.
There you can use [Scrapy selectors](https://docs.scrapy.org/en/latest/topics/selectors.html) to add fields to the data.
