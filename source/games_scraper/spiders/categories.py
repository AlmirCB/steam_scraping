import scrapy
from bs4 import BeautifulSoup

class Categories(scrapy.Spider):
    name="categories"

    def start_requests(self):
        """Using just one URL, we are going to crawl one item"""
        urls = [self.settings.attributes['LINKS'].value['index']]
        for url in urls:
            yield scrapy.Request(url=url, callback=self.parse)

    def parse(self, response):
        """ Categories names and urls will be taken here """

        def clean_url(url:str) -> str:
            """Removes attributes from given url, deleting from "?" symbol in advance

            Args:
                url (str): url to be cleaned 

            Returns:
                str: cleaned url
            """
            res = url.split("?")[0]
            if "category" not in url.split("/"):
                res = None

            return res
    
        # Just checking the headers so we can see correct language (spanish)
        # and user agent.
        self.logger.info(f"Request user agent: {response.request.headers}")

        soup = BeautifulSoup(response.text, features="lxml")
        genre_selector = soup.find(id="genre_flyout")
        categories_dict = {}
        for el in genre_selector.find_all(class_="popup_menu_item"):
            try:
                categories_dict[el.text.strip()] = el.attrs['href']
            except KeyError as e:
                pass
            except Exception as e:
                print(e)
                print(el)

        res = {
            k:clean_url(v) 
            for k,v in categories_dict.items() 
            if clean_url(v) is not None
        }
        yield res
        

