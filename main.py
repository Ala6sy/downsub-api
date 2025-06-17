import os
import json
import time
import gspread
from flask import Flask, request, jsonify
from oauth2client.service_account import ServiceAccountCredentials
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

app = Flask(__name__)

@app.route("/", methods=["POST"])
def handle_request():
    data = request.get_json()
    url = data.get("url", "").strip()

    if not url or not url.startswith("http"):
        return jsonify({"error": "❌ رابط غير صالح"}), 400

    try:
        # إعداد gspread
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_name("creds.json", scope)
        client = gspread.authorize(creds)
        sheet = client.open("DownSub Captions").sheet1

        # مسح العمود B
        sheet.batch_clear(["B2:B"])

        # إعداد selenium
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        prefs = {
            "download.default_directory": "/tmp",
            "download.prompt_for_download": False,
            "safebrowsing.enabled": True
        }
        options.add_experimental_option("prefs", prefs)

        driver = webdriver.Chrome(options=options)
        wait = WebDriverWait(driver, 90)

        driver.get(f"https://downsub.com/?url={url}")

        # الضغط على زر الترجمة
        formats = ['SRT', 'TXT', 'RAW']
        found = False

        for fmt in formats:
            try:
                button = wait.until(
                    EC.visibility_of_element_located((By.XPATH, f"//span[contains(text(),'{fmt}')]/ancestor::button"))
                )
                driver.execute_script("arguments[0].click();", button)
                time.sleep(5)
                found = True
                break
            except:
                continue

        if not found:
            driver.quit()
            sheet.update_cell(2, 2, "❌ لم يتم العثور على زر الترجمة")
            return jsonify({"error": "لم يتم العثور على زر الترجمة"}), 400

        driver.quit()

        # البحث عن آخر ملف تم تحميله
        files = [f for f in os.listdir("/tmp") if f.endswith(".srt")]
        if not files:
            sheet.update_cell(2, 2, "❌ تم الضغط ولكن لم يتم العثور على ملف")
            return jsonify({"error": "لم يتم العثور على الملف"}), 400

        files.sort(key=lambda x: os.path.getmtime(os.path.join("/tmp", x)), reverse=True)
        latest_file = os.path.join("/tmp", files[0])

        # استخراج الأسطر
        with open(latest_file, "r", encoding="utf-8") as f:
            content = f.read()

        lines = []
        for block in content.split("\n\n"):
            parts = block.strip().split("\n")
            for line in parts:
                if "-->" not in line and not line.isdigit() and line.strip():
                    lines.append(line.strip())

        if lines:
            for i, line in enumerate(lines):
                sheet.update_cell(i + 2, 2, line)
            return jsonify({"message": f"✅ تم استخراج {len(lines)} سطر"}), 200
        else:
            sheet.update_cell(2, 2, "⚠️ تم تحميل الملف لكن لم تُستخرج أسطر ترجمة")
            return jsonify({"error": "لم يتم استخراج الأسطر"}), 200

    except Exception as e:
        return jsonify({"error": f"❌ حدث خطأ: {str(e)}"}), 500
