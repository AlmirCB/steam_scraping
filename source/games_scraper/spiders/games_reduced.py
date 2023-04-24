import scrapy
import os
import re
import json

from bs4 import BeautifulSoup
from scrapy_selenium import SeleniumRequest
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from scrapy import signals


class GamesReduced(scrapy.Spider):
    name="games_reduced"
    n_pages_per_cat = 4
    state_file = "data/games_reduced_state.json"
    ids_file = "data/games_ids.json"
    state = {}
    use_test_dict = False

    # A testing dict 
    test_dict = {
        "singleplayer": "https://store.steampowered.com/category/singleplayer/",
        "multiplayer": "https://store.steampowered.com/category/multiplayer_online_competitive",
    }

    download_images = False

    def __init__(self, *args, **Kwargs):
        super(GamesReduced, self).__init__(*args, **Kwargs)
        
        # As selenium requests can't be serialized with pickle, our own state 
        # management has been implemented. 
        if not os.path.isfile(self.state_file):
            self.logger.warning("No state file used, starting from scratch")
        else:
            with open(self.state_file) as state_file:
                self.state = json.load(state_file)
        
        # Loading the rest of possible attributes.
        self.n_pages_per_cat = int(self.n_pages_per_cat)
        self.use_test_dict = eval(self.use_test_dict)
        if self.use_test_dict:
            self.cat_dict = self.test_dict
        else:
            self.load_cat_dict()

    def start_requests(self):
        """Urls are generated from categories. To have categories url categories spider must have been
        executed first, creating an output file that mast be introduced as self.input_file"""
        cat_dict = self.cat_dict

        for cat, url in cat_dict.items():
            count = 0
            while count < self.n_pages_per_cat:
                if(self.state.get(cat, 0)) < 0:
                    self.logger.warning(f"Category {cat} limited reached, not crawling")
                    break
                self.state[cat] = self.state.get(cat, 0) + 1
                url = self.go_to_page(url, self.state[cat])                
                count +=1

                # Sending a SeleniumRequest that scrolls 2600 px and waits until games have been charged (or 15 seconds)
                yield SeleniumRequest(
                    url=url, 
                    callback=self.parse,
                    script="scroll(0, 2600)",
                    wait_time = 15,
                    wait_until=EC.presence_of_element_located((By.CLASS_NAME, "salepreviewwidgets_SaleItemBrowserRow_y9MSd")),
                )

    def parse(self, response):
        """Method used to parse response and obtain 12 games dict in each page"""

        soup = BeautifulSoup(response.text, features="lxml")
        
        games = soup.find_all(class_="salepreviewwidgets_SaleItemBrowserRow_y9MSd")
        if soup.select_one(".saleitembrowser_EmptyResults_3_IxA") and len(games) == 0:
            # If this element is detected that means that we arrived to the end
            cat = self.get_cat_from_url(response.url)
            self.logger.warning(f"Category {cat} limited reached at page {self.state.get(cat, 'ERROR_PAGE')}")
            self.state[cat] = -10
            return

        for game in games:
            res = self.parse_game(game)
            yield(res)
        
        if len(games) == 0:
            yield({"NO GAMES": "YES! There is an error with JOBDIR and selenium requests"})

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        """With this method we connect spider_closed signal to self.spider_closed method"""
        spider = super(GamesReduced, cls).from_crawler(crawler, *args, **kwargs)
        crawler.signals.connect(spider.spider_closed, signal=signals.spider_closed)
        return spider   

    def spider_closed(self, spider):
        """This method will be called when spider_closed signal arrives.
        In here we save state and all ids we have got"""
        self.logger.info(f"Saving state in {self.state_file}")
        with open(self.state_file, "w") as state_file:
            json.dump(self.state, state_file)

        self.logger.info(f"Saving ids in {self.ids_file}")
        with open(self.ids_file, "w") as ids_file:
            ids_file.write(str(self.state.get("ids", [])))

    @staticmethod
    def next_page(url:str) -> str:
        """Given an url it returns next page. Pages are loaded indicating 
        the argument offset=N, with N as the number of game that will be the 
        first. As we have 12 games per page we just add 12 to current number.

        Args:
            url (str): Url of a given category.

        Returns:
            str: url of next page in the same category.
        """
        base_url = url.split("?")[0]
        p = re.compile("offset=.\d*")
        res = p.search(url)
        next_page = int(res.group(0).split("=")[1]) + 12 if res else 0
        return f"{base_url}?offset={next_page}"
    
    @staticmethod
    def go_to_page(url:str, page:int) -> str:
        """Go to a category page

        Args:
            url (str): Category url
            page (int): Page to go (will be multiplied by 12 as it is the number of games per page)

        Returns:
            str: Url pointing to given page of given category
        """
        base_url = url.split("?")[0]
        return f"{base_url}?offset={page * 12}"

    def get_cat_from_url(self, url:str) -> str:
        """Given an url it category will be returned.

        Args:
            url (str): string url from wich we want to get the category

        Returns:
            str: Category name
        """
        for cat, cat_url in self.cat_dict.items():
            if cat_url in url:
                return cat
            
        self.logger.error(f"Url: {url} does not belong to any category")
        return None
            
    def load_cat_dict(self):
        """Loads cat_dict from self.input_file (json file). This dict has an structure as follows:
            {
                'name': 'category_name', 
                'url': 'url_pointing_to_category_base_page'
            }
            In case no self.input_file an error will be raised.
        """
        if not hasattr(self, 'input_file'):
            raise("No input file given, unable to crawl categories")
            
        
        self.logger.info(f"Getting categories from {self.input_file}")

        with open(self.input_file, "r") as input_file:
            self.cat_dict = json.load(input_file)[0]
    
    def parse_game(self, game):
        """Gets all the info from a game container in a category steam page. 

        Args:
            game (WebElement): Element containing all game info.

        Returns:
            dict: As follows:
                {
                    'id': int
                    'name': str,
                    'link': str,
                    'img_link': str,
                    'description': str,
                    'categories': list,
                    'reviews': tuple,
                    'date': str,
                    'plataforms': list,
                }
        """

        base_selector = "div.salepreviewwidgets_SaleItemBrowserRow_y9MSd:nth-child(1) > "
        def clean_selector(sel):
            return sel.replace(base_selector, "")        

        # Getting url and id. If id in crawled ids return.
        selector = clean_selector("div.salepreviewwidgets_SaleItemBrowserRow_y9MSd:nth-child(1) > div:nth-child(1) > div:nth-child(1) > div:nth-child(1) > div:nth-child(1) > a:nth-child(1)")
        url = game.select_one(selector).attrs["href"]
        id = int(url.split("app/")[1].split("/")[0])
        if id in self.state.get('ids', []):
            return


        # Getting image url
        selector = clean_selector("div.salepreviewwidgets_SaleItemBrowserRow_y9MSd:nth-child(1) > div:nth-child(1) > div:nth-child(1) > div:nth-child(1) > div:nth-child(1) > a:nth-child(1) > div:nth-child(1) > div:nth-child(2) > img:nth-child(1)")
        img_src = game.select_one(selector).attrs["src"]
        image_urls = []
        if self.download_images:
            image_urls = [img_src]

        # Getting name
        selector = clean_selector("div.salepreviewwidgets_SaleItemBrowserRow_y9MSd:nth-child(1) > div:nth-child(1) > div:nth-child(1) > div:nth-child(1) > div:nth-child(2) > div:nth-child(2) > a:nth-child(1) > div:nth-child(1)")
        name = game.select_one(selector).text
        
        # Getting description
        selector = clean_selector("div.salepreviewwidgets_SaleItemBrowserRow_y9MSd:nth-child(1) > div:nth-child(1) > div:nth-child(1) > div:nth-child(1) > div:nth-child(2) > div:nth-child(4)")
        description = game.select_one(selector).text
        
        # Getting tags
        selector = clean_selector("div.salepreviewwidgets_SaleItemBrowserRow_y9MSd:nth-child(1) > div:nth-child(1) > div:nth-child(1) > div:nth-child(1) > div:nth-child(2) > div:nth-child(3) > div:nth-child(1) > a")
        tags = [tag.text for tag in game.select(selector)]
        
        # Getting date
        selector = clean_selector("div.salepreviewwidgets_SaleItemBrowserRow_y9MSd:nth-child(1) > div:nth-child(1) > div:nth-child(1) > div:nth-child(1) > div:nth-child(2) > div:nth-child(3) > div:nth-child(2) > div:nth-child(1)")
        date = game.select_one(selector).text

        # Getting platforms
        selector = clean_selector("div.salepreviewwidgets_SaleItemBrowserRow_y9MSd:nth-child(1) > div:nth-child(1) > div:nth-child(1) > div:nth-child(1) > div:nth-child(2) > div:nth-child(3) > div:nth-child(2) > span:nth-child(2) > svg")
        plat_logos_class_dict = {
                "SVGIcon_Button SVGIcon_WindowsLogo": "windows",
                "SVGIcon_Button SVGIcon_AppleLogo": "mac",
                "SVGIcon_Button SVGIcon_SteamLogo": "steam",
                "SVGIcon_Button": "vr",
                "": "linux",
            }

        
        platforms = []
        for plat in game.select(selector):
            icon_class = " ".join(plat.attrs["class"])
            try:
                platforms.append(
                        plat_logos_class_dict[icon_class]
                    )
            except Exception as e:
                print(e)
                print(f"No icon found in game {name} with class {icon_class}")

        # Getting reviews
        rev_category = None
        try:
            selector = clean_selector("div.salepreviewwidgets_SaleItemBrowserRow_y9MSd:nth-child(1) > div:nth-child(1) > div:nth-child(1) > div:nth-child(1) > div:nth-child(2) > div:nth-child(3) > a:nth-child(3) > div:nth-child(1) > div:nth-child(1)")
            rev_category = game.select_one(selector).text
        except Exception as e:
            self.logger.error(e)
            self.logger.warning(f"rev_category not found for game {id}")

        rev_number = 0
        try:
            selector = clean_selector("div.salepreviewwidgets_SaleItemBrowserRow_y9MSd:nth-child(1) > div:nth-child(1) > div:nth-child(1) > div:nth-child(1) > div:nth-child(2) > div:nth-child(3) > a:nth-child(3) > div:nth-child(1) > div:nth-child(2)")
            rev_number = game.select_one(selector).text
            rev_number = int(rev_number.split(" ")[1].replace(".", ""))
        except Exception as e:
            self.logger.error(e)
            self.logger.warning(f"rev_number not found for game {id}")

        # Getting prices
        offert = None
        offert_price = None

        selector = clean_selector("div.salepreviewwidgets_SaleItemBrowserRow_y9MSd:nth-child(1) > div:nth-child(1) > div:nth-child(1) > div:nth-child(1) > div:nth-child(2) > div:nth-child(5) > div:nth-child(1) > div:nth-child(2) > div:nth-child(1)")
        price = game.select_one(selector).text if game.select_one(selector) else None

        if price and "%" in price:
            offert = price
            selector = clean_selector("div.salepreviewwidgets_Discounted_35-Ub:nth-child(2) > div:nth-child(2) > div:nth-child(1)")
            price = game.select_one(selector).text
            selector = clean_selector("div.salepreviewwidgets_Discounted_35-Ub:nth-child(2) > div:nth-child(2) > div:nth-child(2)")
            offert_price = game.select_one(selector).text
        
        
        # Saving id in crawled ids
        self.state['ids'] = self.state.get('ids', []) + [id]

        return {
            "id": id,
            'image_urls': image_urls,
            'name': name,
            'url': url,
            'img_src': img_src,
            'description': description,
            'tags': tags,
            'reviews_category': rev_category,
            'reviews_number': rev_number,
            'date': date,
            'platforms': platforms,
            'price': price,
            'offert': offert,
            'offert_price':offert_price
        }

   