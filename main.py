from flask import Flask, request, jsonify
import time
import os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

app = Flask(__name__)

@app.route("/", methods=["POST"])
def download_subtitles():
    video_url = request.json.get("url", "").strip()
    if not video_url.startswith("http"):
        return jsonify({"error": "❌ رابط YouTube غير صالح"}), 400

    try:
        options = Options()
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_experimental_option("prefs", {
            "download.prompt_for_download": False,
            "safebrowsing.enabled": True
        })

        driver = webdriver.Chrome(options=options)
        wait = WebDriverWait(driver, 90)

        # افتح DownSub
        downsub_url = f"https://downsub.com/?url={video_url}"
        driver.get(downsub_url)

        # ابحث عن زر SRT / TXT / RAW
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
                found = True
                break
            except Exception:
                continue

        if not found:
            driver.quit()
            return jsonify({"error": "❌ لم يتم العثور على زر الترجمة"}), 404

        time.sleep(5)  # انتظر تنزيل الملف

        # ابحث عن آخر ملف SRT
        files = [f for f in os.listdir("/tmp") if f.endswith(".srt")]
        if not files:
            driver.quit()
            return jsonify({"error": "❌ لم يتم العثور على ملف الترجمة"}), 404

        files.sort(key=lambda x: os.path.getmtime(os.path.join("/tmp", x)), reverse=True)
        latest_file = os.path.join("/tmp", files[0])

        with open(latest_file, "r", encoding="utf-8") as f:
            content = f.read()

        lines = []
        for block in content.split("\n\n"):
            parts = block.strip().split("\n")
            for line in parts:
                if "-->" not in line and not line.isdigit() and line.strip():
                    lines.append(line.strip())

        driver.quit()
        return jsonify({"lines": lines[:1000]})  # أرجع 1000 سطر كحد أقصى
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# لتشغيل التطبيق عند تنفيذ `gunicorn main:app`
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
