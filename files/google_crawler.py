# Import dependencies
from bs4 import BeautifulSoup
import requests
from urllib.parse import quote
from pprint import pprint


class GoogleSpider(object):
    def __init__(self):
        """Crawl Google search results

        This class is used to crawl Google's search results using requests and BeautifulSoup.
        """
        super().__init__()
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.14; rv:79.0) Gecko/20100101 Firefox/79.0',
            'Host': 'www.google.com',
            'Referer': 'https://www.google.com/'
        }

    def __get_source(self, url: str) -> requests.Response:
        """Get the web page's source code

        Args:
            url (str): The URL to crawl

        Returns:
            requests.Response: The response from URL
        """
        return requests.get(url, headers=self.headers)

    def search(self, query: str) -> list:
        """Search Google

        Args:
            query (str): The query to search for

        Returns:
            list: The search results
        """
        # Get response
        response = self.__get_source('https://www.google.com/search?q=%s' % quote(query))
        print(response.text)
        # Initialize BeautifulSoup
        soup = BeautifulSoup(response.text, 'html.parser')
        # Get the result containers
        result_containers = soup.findAll('body link')
        # Final results list
        results = []
        # Loop through every container
        for container in result_containers:
            # Result title
            title = container.text
            # Result URL
            # url = container.find('a')['href']
            # # Result description
            # des = container.find('span', class_='st').text
            results.append({
                'title': title,
                # 'url': url,
                # 'des': des
            })
        return results


if __name__ == '__main__':
    pprint(GoogleSpider().search(input('Search for what? ')))