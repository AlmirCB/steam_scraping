# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface
from itemadapter import ItemAdapter
from games_scraper.spiders import Categories, GamesReduced
import pandas as pd
import logging

class GamesScraperPipeline:
    df = pd.DataFrame()
    def open_spider(self, spider):
        pass
        # if isinstance(spider, GamesReduced):
        #     logging.warning("YEEEEEEES 222222222222222")
        #     logging.warning("\n\n\n")

    def process_item(self, item, spider):
        # logging.warning("\n\n\n")
        # logging.warning(f"PIPELINE: {spider}")
        # logging.warning(spider.name)
        # logging.warning("\n\n\n")
        # logging.warning(item)
        # logging.warning(type(item))

        # if isinstance(spider, GamesReduced):
        #     logging.warning("YEEEEEEES 222222222222222")
        #     logging.warning("\n\n\n")

        return item
