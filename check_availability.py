from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import os
import time
from selenium.webdriver.common.by import By
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import requests

# ── ChromeOptions で「バイナリパス」を指定する例 ───────────────────────────
options = Options()
options.add_argument('--headless')
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')

# 環境変数 CHROME_BINARY が指定されていればそれを使用し、
# なければ従来のパスを利用する
options.binary_location = os.environ.get('CHROME_BINARY', '/usr/bin/chromium-browser')

from selenium.webdriver.chrome.service import Service

# CHROMEDRIVER 環境変数にドライバのパスが指定されている場合はそれを使用する
chromedriver_path = os.environ.get('CHROMEDRIVER')
if chromedriver_path:
    service = Service(chromedriver_path)
    driver = webdriver.Chrome(service=service, options=options)
else:
    driver = webdriver.Chrome(options=options)
driver.implicitly_wait(5)

# 以下は元々のスクレイピングロジックです
driver.get('https://fujisawacity.service-now.com/facilities_reservation?id=facility_search')

# 施設選択画面
driver.find_element(By.CSS_SELECTOR,'#\\30 1_市民センター').click()
driver.find_element(By.CSS_SELECTOR,'#query_string').send_keys("湘南台")
# 検索
driver.find_element(By.CSS_SELECTOR,'#x28aa391893a70a1028bcbba32bba1071 > div.main-container > div.search-area.ng-scope > div.query-area.background-1 > div:nth-child(5) > button').click()
# 室場一覧を開く
driver.find_element(By.CSS_SELECTOR,'#x28aa391893a70a1028bcbba32bba1071 > div.main-container > div.search-result.ng-scope > div > div > details > summary').click()

empties = [[], []]

# 体育館A面
driver.find_element(By.CSS_SELECTOR,'#x28aa391893a70a1028bcbba32bba1071 > div.main-container > div.search-result.ng-scope > div > div > details > div > div:nth-child(6) > p > a:nth-child(2)').click()
driver.switch_to.window(driver.window_handles[0])
# 体育館B面
driver.find_element(By.CSS_SELECTOR,'#x28aa391893a70a1028bcbba32bba1071 > div.main-container > div.search-result.ng-scope > div > div > details > div > div:nth-child(7) > p > a:nth-child(2)').click()

for x in range(2):
    driver.switch_to.window(driver.window_handles[x+1])
    # 今週の処理
    dt = datetime.today().date() - timedelta(days=3)
    day_name = ['(月)', '(火)', '(水)', '(木)', '(金)', '(土)', '(日)']

    for i in range(6):
        yyy = str(int(dt.year)-2000).zfill(3)
        mm = str(dt.month).zfill(2)
        dd = str(dt.day).zfill(2)
        day = day_name[dt.weekday()]
        try:
            if driver.find_element(By.CSS_SELECTOR, f'#\\32 {yyy}-{mm}-{dd}_19\\:00-22\\:00').text == "O":
                empties[x].append(f'{mm}/{dd}{day}')
        except Exception:
            pass
        dt = dt + timedelta(days=1)

    # 翌月以降の処理
    for k in range(4):
        dt2 = datetime.today().date() + relativedelta(months=k)
        yyy = str(int(dt2.year)-2000).zfill(3)
        mm = str(dt2.month).zfill(2)
        for i in range(1,7):
            try:
                driver.find_element(By.CSS_SELECTOR, f'#datepicker > div > table > tbody > tr:nth-child({i}) > td:nth-child(4) > a').click()
                time.sleep(5)
                d = int(driver.find_element(By.CSS_SELECTOR, f'#datepicker > div > table > tbody > tr:nth-child({i}) > td.ui-datepicker-current-day > a').text) - 3
                for j in range(7):
                    dd = str(d + j).zfill(2)
                    day = day_name[(j+6)%7]
                    try:
                        if driver.find_element(By.CSS_SELECTOR, f'#\\32 {yyy}-{mm}-{dd}_19\\:00-22\\:00').text == "O":
                            empties[x].append(f'{mm}/{dd}{day}')
                    except Exception:
                        pass
            except Exception:
                try:
                    if i > 4:
                        driver.find_element(By.CSS_SELECTOR, f'#datepicker > div > table > tbody > tr:nth-child({i}) > td:nth-child(1) > a').click()
                        d = int(driver.find_element(By.CSS_SELECTOR, f'#datepicker > div > table > tbody > tr:nth-child({i}) > td.ui-datepicker-current-day > a').text)
                        for j in range(4):
                            dd = str(d + j).zfill(2)
                            day = day_name[(j+6)%7]
                            try:
                                if driver.find_element(By.CSS_SELECTOR, f'#\\32 {yyy}-{mm}-{dd}_19\\:00-22\\:00').text == "O":
                                    empties[x].append(f'{mm}/{dd}{day}')
                            except Exception:
                                pass
                except Exception:
                    break
        try:
            driver.find_element(By.CSS_SELECTOR, '#datepicker > div > div > a.ui-datepicker-next.ui-corner-all > span').click()
        except Exception:
            break

driver.quit()

# ──（以下は前回比較→Discord 通知ロジック。変更不要）───

discord_webhook_url = os.environ.get("SECRET_DISCORD_WEBHOOK")
if not discord_webhook_url:
    print("ERROR: Discord Webhook URL が設定されていません。")
    exit(1)

message_lines = []
message_lines.append("A面")
message_lines.extend(empties[0])
message_lines.append("")
message_lines.append("B面")
message_lines.extend(empties[1])
new_message = "\n".join(message_lines)

last_message = ""
if os.path.exists("last_message.txt"):
    with open("last_message.txt", "r", encoding="utf-8") as f:
        last_message = f.read()

if new_message != last_message:
    res = requests.post(discord_webhook_url, json={"content": new_message})
    if res.status_code in (200, 204):
        print("Discord 通知を送信しました。")
        with open("last_message.txt", "w", encoding="utf-8") as f:
            f.write(new_message)
    else:
        print(f"Discord 通知に失敗しました: {res.status_code} {res.text}")
else:
    print("前回通知時と差分なし。Discord 送信は行いません。")
