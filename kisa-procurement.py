from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import re
import datetime
import smtplib
from email.mime.text import MIMEText
import slack_sdk
from slack_sdk import WebClient

# SSL 인증서 검증 경고 무시
import warnings
from urllib3.exceptions import InsecureRequestWarning

warnings.filterwarnings("ignore", category=InsecureRequestWarning)

emailID = 'shds.apt@gmail.com'
emailPW = 'fimtapsmuznaqqrp'

slack_token = 'xoxb-6113261522434-6133696751331-zLY7lIZuX3R1QoPSn01La1w2'
client = WebClient(token=slack_token)

channel_id = 'C062WSL797Z'

# 정보 수집 클래스 정의
class InfoScraper:
    def __init__(self):
        self.options = Options()
        user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36 Edg/112.0.1722.48"
        self.options.add_experimental_option("prefs", {"safebrowsing.enabled": True})
        self.options.add_experimental_option("detach", True)
        self.options.add_argument("--start-maximized")
        self.options.add_argument('user-agent=' + user_agent)
        self.driver = webdriver.Chrome('chromedriver', options=self.options)
        self.wait = WebDriverWait(self.driver, 10)
        self.all_results_text = ""

    def sendSlackMessage(self, subject, results):
        if channel_id:
            response = client.chat_postMessage(channel=channel_id, text=f"{subject}\n{results}")
            print(response)
        else:
            print(f"No channel ID found for keyword")

    def sendGmail(self, subject, text, dstEmailAddr):
        s = smtplib.SMTP('smtp.gmail.com', 587)
        s.starttls()

        s.login(emailID, emailPW)

        msg = MIMEText(text)
        msg['Subject'] = subject
        msg['From'] = emailID
        msg['To'] = ",".join(dstEmailAddr)

        s.sendmail(emailID, dstEmailAddr, msg.as_string())

        s.quit()

    def scrape_info(self, search_word, page):
        url = f"https://www.kisa.or.kr/403?page={page}&searchDiv=10&searchWord={search_word}"
        self.driver.get(url)
        WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, '.sbj')))
        soup = BeautifulSoup(self.driver.page_source, 'html.parser')
        info_list = soup.select('tbody tr')

        now = datetime.datetime.now().date()
        days_ago = now - datetime.timedelta(days=10)
        #formatted_date = days_ago.strftime('%Y%m%d')

        info_data = []

        for info_item in info_list:
            date_element = info_item.select_one('.date')
            if date_element:
                date_str = date_element.text.strip()
                post_date = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
                if post_date >= days_ago:
                    link_element = info_item.select_one('.sbj a')
                    relative_link = link_element['href']
                    absolute_link = 'https://www.kisa.or.kr' + relative_link
                    info_data.append(absolute_link)

        return info_data

    def process_info(self, absolute_link):
        scraper.driver.get(absolute_link)
        page_source = scraper.driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')
        content_element = soup.select_one('.board_detail_contents')
        content_text = content_element.text.strip()

        business_name = None
        budget = None
        period = None

        # 사업명 정보 추출
        business_name_match = re.search(r'사업명\s*:\s*(.*?)\n', content_text)
        if business_name_match:
            business_name = business_name_match.group(1)

        # 예산액 정보 추출
        budget_match = re.search(r'예산액\s*:\s*(.*?)\n', content_text)
        if budget_match:
            budget = budget_match.group(1)
            budget_korea = InfoScraper.format_price(budget)

        # 공개기간 정보 추출
        period_match = re.search(r'공개기간\s*:\s*(.*?)\n', content_text)
        if period_match:
            period = period_match.group(1)

        result_text = ""
        result_text += f"[★공고명] : {business_name}\n"
        result_text += f"[예산금액] : {budget}, ({budget_korea})\n"
        result_text += f"[공개기간] : {period}\n"
        result_text += f"[상세링크] : {absolute_link}\n"
        result_text += "=" * 40 + "\n"
        result_text += "\n"
        print(result_text)
        self.all_results_text += result_text

    def format_price(amount_text):
        amount = re.sub(r'[^0-9,]', '', amount_text)

        if amount:
            amount = int(amount.replace(',', ''))

            if amount >= 10 ** 8:  # 1억 이상
                korean = f'{amount // 10 ** 8:,.0f} 억원'
            elif amount >= 10 ** 4:  # 1만 이상
                korean = f'{amount // 10 ** 4:,.0f} 만원'
            else:
                korean = f'{amount:,.0f} 원'
        else:
            korean = '알 수 없음'

        return korean


if __name__ == "__main__":
    search_word = "사전규격공개"
    page_number = 1

    scraper = InfoScraper()
    info_list = scraper.scrape_info(search_word, page_number)

    for absolute_link in info_list:
        scraper.process_info(absolute_link)

    formatted_date = datetime.datetime.now().strftime('%Y년 %m월 %d일 %A')
    subject = f"◈{formatted_date} KISA 입찰 공고 결과 Trend"
    scraper.sendSlackMessage(subject, scraper.all_results_text)
    scraper.sendGmail(subject, scraper.all_results_text, ['donguk0207@gmail.com'])
