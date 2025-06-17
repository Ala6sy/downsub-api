import os
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound

# إعداد Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds_json = os.getenv("CREDS_JSON")

if not creds_json:
    raise Exception("❌ متغير البيئة CREDS_JSON غير موجود!")

creds_data = json.loads(creds_json)
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_data, scope)
client = gspread.authorize(creds)
sheet = client.open("DownSub Captions").sheet1

# قراءة الرابط من الخلية A2
video_url = sheet.acell("A2").value.strip()
if "watch?v=" not in video_url:
    sheet.update_cell(2, 2, "❌ رابط YouTube غير صحيح")
    exit()

video_id = video_url.split("watch?v=")[-1].split("&")[0]

# سحب الترجمة
try:
    transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=['ar', 'en'])
except TranscriptsDisabled:
    sheet.update_cell(2, 2, "❌ الترجمة معطلة في هذا الفيديو")
    exit()
except NoTranscriptFound:
    sheet.update_cell(2, 2, "❌ لا توجد ترجمة متاحة لهذا الفيديو")
    exit()
except Exception as e:
    sheet.update_cell(2, 2, f"❌ خطأ: {str(e)}")
    exit()

# كتابة الترجمة في العمود B
sheet.batch_clear(["B2:B"])
for i, item in enumerate(transcript):
    line = item.get("text", "").strip()
    if line:
        sheet.update_cell(i + 2, 2, line)

sheet.update_cell(2, 2, f"✅ تم استخراج {len(transcript)} سطر ترجمة")
