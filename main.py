import time
import os
import json
import gspread
from io import StringIO
from oauth2client.service_account import ServiceAccountCredentials
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# === 1. إعداد Google Sheets عبر متغير بيئة مشفر مرتين ===
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds_json = os.getenv("CREDS_JSON")

if not creds_json:
    raise Exception("❌ متغير البيئة CREDS_JSON غير موجود!")

# ✅ فك التشفير مرتين
creds_data = json.loads(json.loads(creds_json))
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_data, scope)
client = gspread.authorize(creds)
sheet = client.open("DownSub Captions").sheet1

# === 2. قراءة رابط الفيديو من A2 ===
video_url = sheet.acell("A2").value.strip()
if not video_url or not video_url.startswith("http"):
    sheet.update_cell(2, 2, "❌ لم يتم إدخال رابط YouTube صالح في A2")
    exit()

# === 3. إعداد Selenium وتشغيل Chrome ===
options = Options()
options.add_argument("--disable-gpu")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
# يمكنك إزالة التعليق التالي لتشغيله بدون واجهة (مفيد على سيرفرات بدون واجهة رسومية)
# options.add_argument("--headless")

driver = webdriver.Chrome(options=options)
wait = WebDriverWait(driver, 90)

# === 4. فتح DownSub بالرابط ===
downsub_url = f"https://downsub.com/?url={video_url}"
driver.get(downsub_url)

# === 5. الضغط على زر الترجمة (SRT أو TXT أو RAW) ===
formats = ['SRT', 'TXT', 'RAW']
found = False

for fmt in formats:
    try:
        button = wait.until(
            EC.visibility_of_element_located(
                (By.XPATH, f"//span[contains(text(),'{fmt}')]/ancestor::button")
            )
        )
        driver.execute_script("arguments[0].click();", button)
        print(f"✅ تم العثور على زر: {fmt} وتم الضغط عليه")
        time.sleep(5)
        found = True
        break
    except Exception as e:
        print(f"⚠️ الزر {fmt} لم يظهر: {e}")
        continue

if not found:
    sheet.update_cell(2, 2, "❌ لم يتم العثور على زر الترجمة (SRT, TXT, RAW)")
    driver.quit()
    exit()

driver.quit()

# === 6. تحديد أحدث ملف SRT تم تحميله ===
downloads_folder = os.path.join(os.path.expanduser("~"), "Downloads")
files = [f for f in os.listdir(downloads_folder) if f.endswith(".srt")]
if not files:
    sheet.update_cell(2, 2, "❌ تم تحميل الملف لكن لم يتم العثور عليه")
    exit()

files.sort(key=lambda x: os.path.getmtime(os.path.join(downloads_folder, x)), reverse=True)
latest_file = os.path.join(downloads_folder, files[0])

# === 7. قراءة ملف الترجمة وفصل الأسطر ===
with open(latest_file, "r", encoding="utf-8") as f:
    content = f.read()

lines = []
for block in content.split("\n\n"):
    parts = block.strip().split("\n")
    for line in parts:
        if "-->" not in line and not line.isdigit() and line.strip():
            lines.append(line.strip())

# === 8. كتابة الترجمة في Google Sheets ===
if lines:
    sheet.batch_clear(["B2:B"])
    for i, line in enumerate(lines):
        sheet.update_cell(i + 2, 2, line)
    print(f"✅ تم استخراج {len(lines)} سطر وكتابته في العمود B")
else:
    sheet.update_cell(2, 2, "⚠️ تم تحميل الملف، لكن لم يتم استخراج سطور ترجمة")
