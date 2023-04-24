import scrapy
from bs4 import BeautifulSoup
import pandas as pd
import os

class GamesFull(scrapy.Spider):
    name="games_full"
    cookie = { 
        'wants_mature_content': 1, 
        'birthtime': "786254401", 
        'lastagecheckage': "1-0-1995"
        }
    state = {}

    def __init__(self, *args, **kwargs):
        super(GamesFull, self).__init__(*args, **kwargs)
        if not hasattr(self, 'input_file'):
            self.logger.warning("No input file given, unable to crawl games IDs")

    def start_requests(self):
        """ Scrapy method to set urls to be crawled. Setting them from game ids directly.
        We are getting game ids from self.input_file"""

        ids = [id for id in self.get_input_file_ids() if id not in self.state.get("crawled_ids", [])]
        for id in ids:
            self.state["crawled_ids"] = self.state.get("crawled_ids", []) + [id]
            url = self.get_url(id)
            yield scrapy.Request(url=url, callback=self.parse, cookies=self.cookie)

    def parse(self, response):
        """Scrapy default parse method. Just using css selectors to get the game info from response"""
        soup = BeautifulSoup(response.text, features="lxml")
        
        def get_game_content(el):
            content = el.findChildren("a", recursive=False)
            return [
                {
                    "name": content_el.findChildren("div", recursive=False)[0].text.strip(),
                    "price": content_el.findChildren("div", recursive=False)[1].text.strip()
                }
                for content_el in content
            ]

        def get_langs():
            els = soup.select(".game_language_options > tbody:nth-child(1) > tr")
            res = []
            for el in els:
                chl = el.findChildren("td", recursive=False)
                if len(chl) < 4:
                    continue
                res.append({
                    'name': chl[0].text.strip(),
                    'interface' : True if chl[1].findChildren("span", recursive=False) else False,
                    'voices': True if chl[2].findChildren("span", recursive=False) else False,
                    'subtitles': True if chl[3].findChildren("span", recursive=False) else False,
                })
            return res
        
        def get_web():
            res = None
            try: 
                res =  soup.select_one("a.linkbar:nth-child(1)").attrs['href'].split("url=")[1]
            except:
                pass
            
            return res

        item = {
            'is_dlc': True if "Contenido descargable" in soup.select_one(".blockbg").text else False, # Warning: language spanish required.
            'img_src': soup.select_one(".game_header_image_full").attrs["src"],
            'short_description': soup.select_one(".game_description_snippet").text.strip()
                if soup.select_one(".game_description_snippet") else None,
            'recent_reviews': soup.select_one("#userReviews > div:nth-child(1) > div:nth-child(2) > span:nth-child(1)").text.strip()
                if soup.select_one("#userReviews > div:nth-child(1) > div:nth-child(2) > span:nth-child(1)") else None,
            'recent_reviews_count': soup.select_one("#userReviews > div:nth-child(1) > div:nth-child(2) > span:nth-child(2)").text.strip()
                if soup.select_one("#userReviews > div:nth-child(1) > div:nth-child(2) > span:nth-child(2)") else None,
            'all_reviews': soup.select_one("#userReviews > div:nth-child(2) > div:nth-child(2) > span:nth-child(1)").text.strip()
                if soup.select_one("#userReviews > div:nth-child(2) > div:nth-child(2) > span:nth-child(1)") else None,
            'all_reviews_count': soup.select_one("#userReviews > div:nth-child(2) > div:nth-child(2) > span:nth-child(2)").text.strip()
                if soup.select_one("#userReviews > div:nth-child(2) > div:nth-child(2) > span:nth-child(2)") else None,
            'reviews_anomally': True if soup.select_one("span.review_anomaly_icon:nth-child(3)") else False,
            'release_date': soup.select_one(".date").text
                if soup.select_one(".date") else None,
            'developer': soup.select_one("#developers_list > a:nth-child(1)").text
                if soup.select_one("#developers_list > a:nth-child(1)") else None,
            'developer_url': soup.select_one("#developers_list > a:nth-child(1)").attrs['href']
                if soup.select_one("#developers_list > a:nth-child(1)") else None,
            'publisher': soup.select_one("div.dev_row:nth-child(4) > div:nth-child(2) > a:nth-child(1)").text
                if soup.select_one("div.dev_row:nth-child(4) > div:nth-child(2) > a:nth-child(1)") else None,
            'publisher_url': soup.select_one("div.dev_row:nth-child(4) > div:nth-child(2) > a:nth-child(1)").attrs["href"]
                if soup.select_one("div.dev_row:nth-child(4) > div:nth-child(2) > a:nth-child(1)") else None,
            'tags': [tag.text.strip() for tag in soup.select("a.app_tag")]
                if soup.select("a.app_tag") else None,
            # 'content_video': [el.attrs["src"] for el in soup.select_one("#highlight_player_area").findChildren("video", recursive=True)],
            # 'content_image': [el.attrs["src"] for el in soup.select_one("#highlight_player_area").findChildren("img", recursive=True)[1:]],
            'discount_original_price': soup.select_one("div.discount_block:nth-child(1) > div:nth-child(2) > div:nth-child(1)").text
                if soup.select_one("div.discount_block:nth-child(1) > div:nth-child(2) > div:nth-child(1)") else None,   
            'discount_final_price': soup.select_one("div.discount_block:nth-child(1) > div:nth-child(2) > div:nth-child(2)").text
                if soup.select_one("div.discount_block:nth-child(1) > div:nth-child(2) > div:nth-child(2)") else None,
            'discount': soup.select_one("div.discount_block:nth-child(1) > div:nth-child(1)").text
                if soup.select_one("div.discount_block:nth-child(1) > div:nth-child(1)") else None,
            'price': soup.select_one("div.game_purchase_action_bg:nth-child(1) > div:nth-child(1)").text.strip()
                if soup.select_one("div.game_purchase_action_bg:nth-child(1) > div:nth-child(1)") else None,
            'game_content': get_game_content(soup.select_one(".gameDlcBlocks"))
                if soup.select_one(".gameDlcBlocks") else None,
            # 'lang': get_langs(),
            'name': soup.select_one("#appHubAppName").text,
            'genre': soup.select_one("#genresAndManufacturer > span:nth-child(4) > a:nth-child(1)").text,
            'website': get_web(),
            'metacritic_score': soup.select_one(".score").text.strip()
                if soup.select_one(".score") else None,
            'metacritic_url': soup.select_one("#game_area_metalink > a:nth-child(1)").attrs['href']
                if soup.select_one("#game_area_metalink > a:nth-child(1)") else None,
        }
        
        yield item

    
    def get_input_file_ids(self) -> list[int]:
        """Get the list of game IDs written in self.input_file.

        Returns:
            list[int]: Contains all game ids.
        """
        if not hasattr(self, 'input_file'):
            self.logger.warning("No input file given, unable to crawl games IDs")
            return []
        
        with open(self.input_file, 'r') as input_file:
            self.logger.info(f"Getting IDs from {self.input_file}")
            
            return eval(input_file.read())

    @staticmethod
    def get_url(game_id:int) -> str:
        return f"https://store.steampowered.com/app/{game_id}"
    
