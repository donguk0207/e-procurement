import datetime
import requests
import smtplib
from email.mime.text import MIMEText
import slack_sdk
from slack_sdk import WebClient

base_url = 'http://apis.data.go.kr/1230000/BidPublicInfoService04/'

urls = {
    'getBidPblancListInfoServcPPSSrch01': '[용역]입찰공고',
    #'getBidPblancListInfoCnstwkPPSSrch01': '[공사]입찰공고',
    #'getBidPblancListInfoThngPPSSrch01': '[물품]입찰공고', #물품입찰공고 임시삭제
    #'getBidPblancListInfoFrgcptPPSSrch01': '[외자]입찰공고', #외자입찰공고 임시삭제
    #'getBidPblancListInfoEtcPPSSrch01': '[기타]입찰공고'
}
search_keywords = ['정보보안', '정보보호', '모의해킹', '취약점', 'ISM']
all_results = set()

emailID = 'shds.apt@gmail.com'
emailPW = '*'

slack_token = '*'
client = WebClient(token=slack_token)

keyword_channel_mapping = {
    '정보보안': 'C063DLXJC68',
    '정보보호': 'C063B7SFHPU',
    '모의해킹': 'C063Q261LF3',
    '취약점': 'C063DS1H3FE',
    'ISM': 'C0640EYFH1N'
}

def sendGmail(subject, text, dstEmailAddr):
    s = smtplib.SMTP('smtp.gmail.com', 587)
    s.starttls()

    s.login(emailID, emailPW)

    msg = MIMEText(text)
    msg['Subject'] = subject
    msg['From'] = emailID
    msg['To'] = ",".join(dstEmailAddr)

    s.sendmail(emailID, dstEmailAddr, msg.as_string())

    s.quit()

def format_price(amount):
    amount = int(amount.replace(',', ''))

    if amount >= 10**8:  # 1억 이상
        korean = f'{amount // 10**8:,.0f} 억원'
    elif amount >= 10**4:  # 1만 이상
        korean = f'{amount // 10**4:,.0f} 만원'
    else:
        korean = f'{amount:,.0f} 원'

    return korean

all_results_text = ""
all_keyword_results = {}
now = datetime.datetime.now()
days_ago = now - datetime.timedelta(days=10)
formatted_date = days_ago.strftime('%Y%m%d')

for keyword in search_keywords:
    keyword_results = ""

    for url, description in urls.items():
        print(f"★★★{description} 정보★★★")
        full_url = f'{base_url}{url}'
        params ={
            'serviceKey' : '*',
            'numOfRows' : '100',
            'pageNo' : '1',
            'inqryDiv' : '1',
            'inqryBgnDt' : formatted_date + '0000',
            'inqryEndDt' : '202312302359',
            'bidNtceNm' : keyword,
            'type' : 'json'
            }

        response = requests.get(full_url, params=params)
        data = response.json()

        try:
            items = data["response"]["body"]["items"]
            items.sort(key=lambda x: x['bidNtceDt'], reverse=True)
        except KeyError:
            print("★★★" + f"{description} 없음" + "★★★")
            continue

        for item in items:
            asignBdgtAmt = item.get('asignBdgtAmt', '-')
            presmptPrce = item.get('presmptPrce', '-')

            asignBdgtAmt_korean = ""  # 초기화 추가
            presmptPrce_korean = ""  # 초기화 추가

            if asignBdgtAmt and asignBdgtAmt != '-':
                asignBdgtAmt = f'{int(asignBdgtAmt):,}'
                asignBdgtAmt_korean = format_price(asignBdgtAmt)
            if presmptPrce and presmptPrce != '-':
                presmptPrce = f'{int(presmptPrce):,}'
                presmptPrce_korean = format_price(presmptPrce)

            bidNtceNo = item.get('bidNtceNo', '-')
            if bidNtceNo not in all_results:
                result_text = ""
                #result_text += f"Search Keyword: {keyword}\n"
                result_text += f"[★공고명]:    {item.get('bidNtceNm', '-')}\n"
                result_text += f"[공고번호]:    {item.get('bidNtceNo', '-')}\n"
                result_text += f"[등록일시]:    {item.get('bidNtceDt', '-')}\n"
                result_text += f"[공고기관]:    {item.get('ntceInsttNm', '-')}\n"
                result_text += f"[입찰방식]:    {item.get('bidMethdNm', '-')}\n"
                result_text += f"[계약방법]:    {item.get('cntrctCnclsMthdNm', '-')}\n"
                result_text += f"[입찰개시]:    {item.get('bidBeginDt', '-')}\n"
                result_text += f"[입찰마감]:    {item.get('bidClseDt', '-')}\n"
                result_text += f"[개찰일시]:    {item.get('opengDt', '-')}\n"
                result_text += f"[예가방법]:    {item.get('prearngPrceDcsnMthdNm', '-')}\n"
                result_text += f"[사업금액]:    {asignBdgtAmt}원 ({asignBdgtAmt_korean})\n"
                result_text += f"[추정가격]:    {presmptPrce}원 ({presmptPrce_korean})\n"
                result_text += f"[용역구분]:    {item.get('srvceDivNm', '-')}\n"
                result_text += f"[낙찰방식]:    {item.get('sucsfbidMthdNm', '-')}\n"
                result_text += f"[물품목록]:    {item.get('purchsObjPrdctList', '-')}\n"
                result_text += f"[상세링크]:    {item.get('bidNtceDtlUrl', '-')}\n"
                result_text += "=" * 40 + "\n"
                result_text += "\n"

                all_results.add(bidNtceNo)
                print(result_text)
                keyword_results += result_text

    all_keyword_results[keyword] = keyword_results

now = datetime.datetime.now()
formatted_date = now.strftime('%Y년 %m월 %d일 %A')

for keyword, results in all_keyword_results.items():
    subject = f"◈{formatted_date} 입찰 공고 결과 - {keyword}"
    sendGmail(subject, results, ['donguk0207@gmail.com'])

    channel = keyword_channel_mapping.get(keyword)
    if channel:
        response = client.chat_postMessage(channel=channel, text=f"◈{formatted_date} 입찰 공고 결과 - {keyword}\n{results}")
        print(response)
    else:
        print(f"No channel mapping found for keyword: {keyword}")
