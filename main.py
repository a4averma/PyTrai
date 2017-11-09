import requests
from bs4 import BeautifulSoup as bs
import urllib3
from PyPDF2 import PdfFileWriter, PdfFileReader
import json
import pymysql.cursors
from gensim.summarization import keywords
from textteaser import TextTeaser
import re


tt = TextTeaser()
connection = pymysql.connect(host='localhost',
                             user='root',
                             password='',
                             db='compliance',
                             charset='utf8mb4',
                             cursorclass=pymysql.cursors.DictCursor)

def ocr_space_file(filename, overlay=False, api_key='Get your key at http://ocr.space', language='eng'):

    payload = {'isOverlayRequired': overlay,
               'apikey': api_key,
               'language': language,
               }
    with open(filename, 'rb') as f:
        r = requests.post('https://api.ocr.space/parse/image',
                          files={filename: f},
                          data=payload,
                          )
    return r.content.decode()

def get_pdf_content_lines(pdf_file_path):
    with open(pdf_file_path) as f:
        pdf_reader = PdfFileReader(f)
        for page in pdf_reader.pages:
            for line in page.extractText().splitlines():
                yield line

notificationPage = 'http://www.trai.gov.in/notifications/press-release/'

page = requests.get(notificationPage)
writer = PdfFileWriter()

soup = bs(page.content, 'html.parser')
i = 0
news_box = soup.findAll('tr', attrs={'class': 'odd'})
work = ""
summary = ""
for news in news_box:
    for title in news.findAll('td', attrs={'class': 'views-field-title'}):
        title = title.text.strip()
    for work in news.findAll('td', attrs={'class': 'views-field-field-start-date'}):
        work = str(work.text.strip())
    for content in news.findAll('td', attrs={'class': 'views-field-php'}):
        for href in content.findAll('a', href=True):
            urls = str(href['href'])
            http = urllib3.PoolManager()
            r = http.request('GET', urls, preload_content=False)
            with open('pdf'+str(i)+".pdf", 'wb+') as out:
                 while True:
                        data = r.read()
                        if not data:
                            break
                        out.write(data)
            try:
                test_file = ocr_space_file(filename='pdf'+str(i)+".pdf")
                parsed_json = json.loads(test_file)
                data_parsed = parsed_json["ParsedResults"][0]["ParsedText"]
            except:
                data_parsed = "Failed to parse the data. Go to: " + urls
            i += 1
            r.release_conn()
            summary = tt.summarize(title, data_parsed)
            summary = str(summary)
            summary = summary.rstrip()
            summary = summary.replace("'", '')
            summary = summary.replace('[', '')
            summary = summary.replace(']', '')
    try:
        with connection.cursor() as cursor:
            sql = "INSERT INTO `laws` (`has_seen`, `country`, `title`, `law`, `summarize`, `keywords`, `date`) VALUES (%s, %s, %s, %s, %s, %s, %s)"
            cursor.execute(sql, ('0', 'IN', title, data_parsed, summary, str(keywords(data_parsed)).replace("\n", " "), work))
            connection.commit()
    except:
        print("Duplicate data or failed to enter")
connection.close()




