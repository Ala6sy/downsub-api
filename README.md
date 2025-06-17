# downsub-api

🎯 Extract YouTube subtitles via API using `youtube_transcript_api` and return clean subtitle lines as JSON.

## 📦 How to Use

- Send a POST request to the `/` endpoint with this JSON body:

```json
{
  "video_id": "YOUR_VIDEO_ID"
}
