from urllib.parse import ParseResult
from util.threads import synchronized

@synchronized
def page_to_file(url: ParseResult, base_html: bytes):
    """
    Salva o conteúdo da página em um arquivo
    """
    urlStr = url.geturl()
    urlStr = urlStr[urlStr.find("://") + 3:].replace("/", "#").replace(":", "#").replace("?", "#").replace("&", "#")
    file_path = f'pages/{urlStr}.txt'
    file = open(file_path, 'w')
    file.write(f'URL: {url.geturl()}\n\n')
    file.close()
    file = open(file_path, 'ab')
    file.write(base_html)
    file.close()
    print(f'Arquivo salvo em: {file_path}')