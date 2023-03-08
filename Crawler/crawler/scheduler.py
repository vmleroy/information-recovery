from urllib import robotparser
from urllib.parse import ParseResult

from util.threads import synchronized
from time import sleep
from collections import OrderedDict
from .domain import Domain


class Scheduler:
    # tempo (em segundos) entre as requisições
    TIME_LIMIT_BETWEEN_REQUESTS = 20

    def __init__(self, usr_agent: str, page_limit: int, depth_limit: int, arr_urls_seeds):
        """
        :param usr_agent: Nome do `User agent`. Usualmente, é o nome do navegador, em nosso caso,  será o nome do coletor (usualmente, terminado em `bot`)
        :param page_limit: Número de páginas a serem coletadas
        :param depth_limit: Profundidade máxima a ser coletada
        :param arr_urls_seeds: ?

        Demais atributos:
        - `page_count`: Quantidade de página já coletada
        - `dic_url_per_domain`: Fila de URLs por domínio (explicado anteriormente)
        - `set_discovered_urls`: Conjunto de URLs descobertas, ou seja, que foi extraída em algum HTML e já adicionadas na fila - mesmo se já ela foi retirada da fila. A URL armazenada deve ser uma string.
        - `dic_robots_per_domain`: Dicionário armazenando, para cada domínio, o objeto representando as regras obtidas no `robots.txt`
        """
        self.usr_agent = usr_agent
        self.page_limit = page_limit
        self.depth_limit = depth_limit
        self.page_count = 0

        self.dic_url_per_domain = OrderedDict()
        self.set_discovered_urls = set()
        self.dic_robots_per_domain = {}

    @synchronized
    def count_fetched_page(self) -> None:
        """
        Contabiliza o número de paginas já coletadas
        """
        self.page_count += 1

    def has_finished_crawl(self) -> bool:
        """
        :return: True se finalizou a coleta. False caso contrário.
        """
        return self.page_count >= self.page_limit

    @synchronized
    def can_add_page(self, obj_url: ParseResult, depth: int) -> bool:
        """
        :return: True caso a profundidade for menor que a maxima e a url não foi descoberta ainda. False caso contrário.
        """
        domain = Domain(obj_url.hostname, self.TIME_LIMIT_BETWEEN_REQUESTS)
        value = self.dic_url_per_domain.get(domain)
        if value is not None:
            if (obj_url, depth) in value:
                return False
        return depth < self.depth_limit

    @synchronized
    def add_new_page(self, obj_url: ParseResult, depth: int) -> bool:
        """
        Adiciona uma nova página
        :param obj_url: Objeto da classe ParseResult com a URL a ser adicionada
        :param depth: Profundidade na qual foi coletada essa URL
        :return: True caso a página foi adicionada. False caso contrário
        """
        # https://docs.python.org/3/library/urllib.parse.html
        if not self.can_add_page(obj_url, depth):
            return False
        domain = Domain(obj_url.hostname, self.TIME_LIMIT_BETWEEN_REQUESTS)
        if not (domain in self.dic_url_per_domain):
            self.dic_url_per_domain[domain] = [(obj_url, depth)]
        else:
            self.dic_url_per_domain[domain].append((obj_url, depth))
        self.set_discovered_urls.add(obj_url.geturl())
        return True

    @synchronized
    def get_next_url(self) -> tuple:
        """
        Obtém uma nova URL por meio da fila. Essa URL é removida da fila.
        Logo após, caso o servidor não tenha mais URLs, o mesmo também é removido.
        """
        for domain in self.dic_url_per_domain.keys():
            if domain.is_accessible():
                if len(self.dic_url_per_domain[domain]) > 0:
                    domain.accessed_now()
                    url = self.dic_url_per_domain[domain].pop(0)
                    return url
        sleep(self.TIME_LIMIT_BETWEEN_REQUESTS)           
        return None, None

    def can_fetch_page(self, obj_url: ParseResult) -> bool:
        """
        Verifica, por meio do robots.txt se uma determinada URL pode ser coletada
        """
        domain = Domain(obj_url.hostname, self.TIME_LIMIT_BETWEEN_REQUESTS)
        url = obj_url.geturl()
        url_robots = obj_url.scheme + "://" + obj_url.hostname + "/robots.txt"
        if domain in self.dic_robots_per_domain:
            rp_exist_domain = self.dic_robots_per_domain[domain]
            return self.__check_can_fetch_page(rp_exist_domain, url)      
        rp = robotparser.RobotFileParser()
        rp.set_url(url_robots)
        rp.read()
        self.dic_robots_per_domain[domain] = rp
        return self.__check_can_fetch_page(rp, url) 
    
    def __check_can_fetch_page(self, robot: robotparser.RobotFileParser, url: str) -> bool:
        """
        Verifica se uma determinada URL pode ser coletada
        """
        robot_str = str(robot)
        if not (robot_str and robot_str.strip()):
            return True
        return robot.can_fetch(self.usr_agent, url)
