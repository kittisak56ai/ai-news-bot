import os
import time
import feedparser
import requests
from deep_translator import GoogleTranslator
from transformers import pipeline
from gtts import gTTS
from PIL import Image, ImageDraw, ImageFont

# ===== CONFIG =====
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/..."  # 🔁 เปลี่ยนเป็น Webhook ของคุณ

rss_feeds = {
    "การเมือง": "http://feeds.bbci.co.uk/news/politics/rss.xml",
    "เศรษฐกิจ": "http://feeds.reuters.com/reuters/businessNews",
    "เทคโนโลยี": "http://feeds.bbci.co.uk/news/technology/rss.xml",
    "AI": "https://www.reuters.com/technology/ai/feed",
    "หุ้น": "https://feeds.finance.yahoo.com/rss/2.0/headline?s=^DJI,^GSPC,^IXIC&region=US&lang=en-US",
    "คริปโต": "https://cryptonews.com/news/feed",
    "สงคราม": "http://feeds.bbci.co.uk/news/world/rss.xml",
    "สตาร์ทอัพ": "https://techcrunch.com/startups/feed/",
    "วอร์เรน บัฟเฟตต์": "https://news.google.com/rss/search?q=warren+buffett",
    "ข่าวยา": "https://www.fiercepharma.com/rss.xml"
}

KEYWORDS = [
    "trump", "donald trump", "โดนัลด์ ทรัมป์",
    "elon musk", "อีลอน มัสก์", "มัสก์",
    "warren buffett", "วอร์เรน บัฟเฟตต์", "เบิร์กไชร์",
    "stock", "ตลาดหุ้น", "nasdaq", "dow jones", "s&p", "bond", "interest rate", "yield",
    "crypto", "คริปโต", "บิทคอยน์", "bitcoin", "ethereum", "เหรียญ", "defi",
    "ai", "ปัญญาประดิษฐ์", "openai", "chatgpt", "deeplearning", "machine learning",
    "war", "สงคราม", "ยูเครน", "รัสเซีย", "ไต้หวัน", "จีน", "อิสราเอล", "ฮามาส", "กาซา",
    "pharma", "drug", "ยา", "วัคซีน", "fda", "clinical trial",
    "startup", "venture capital", "series a", "funding", "tech startup"
]

# ===== INITIALIZE =====
sent_links = set()
translator = GoogleTranslator(source='auto', target='th')
summarizer = pipeline("summarization", model="facebook/bart-large-cnn")

# ===== FUNCTIONS =====

def summarize_and_translate(content):
    try:
        summary = summarizer(content, max_length=250, min_length=80, do_sample=False)[0]['summary_text']
        return translator.translate(summary)
    except Exception as e:
        print(f"⚠️ สรุปข่าวล้มเหลว: {e}")
        return translator.translate(content[:300])

def create_voice(text, filename="summary.mp3"):
    try:
        tts = gTTS(text=text, lang="th")
        tts.save(filename)
    except Exception as e:
        print(f"⚠️ ไม่สามารถสร้างไฟล์เสียงได้: {e}")

def create_image(title, summary, filename="news.png"):
    img = Image.new('RGB', (800, 600), color=(255, 255, 240))
    draw = ImageDraw.Draw(img)

    try:
        font_title_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        font_body_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
        font_title = ImageFont.truetype(font_title_path, 28) if os.path.exists(font_title_path) else ImageFont.load_default()
        font_body = ImageFont.truetype(font_body_path, 22) if os.path.exists(font_body_path) else ImageFont.load_default()
    except Exception as e:
        print(f"⚠️ โหลดฟอนต์ไม่สำเร็จ: {e}")
        font_title = ImageFont.load_default()
        font_body = ImageFont.load_default()

    draw.text((40, 40), title, font=font_title, fill=(0, 0, 0))

    max_width = 720
    lines = []
    words = summary.split()
    line = ""
    for word in words:
        test_line = line + word + " "
        bbox = draw.textbbox((0, 0), test_line, font=font_body)
        w = bbox[2] - bbox[0]
        if w <= max_width:
            line = test_line
        else:
            lines.append(line)
            line = word + " "
    lines.append(line)

    y_text = 100
    for l in lines:
        draw.text((40, y_text), l, font=font_body, fill=(50, 50, 50))
        y_text += 30

    img.save(filename)

def send_discord(text):
    try:
        data = {"content": text}
        response = requests.post(DISCORD_WEBHOOK_URL, json=data)
        if response.status_code == 204:
            print("✅ ส่งข้อความ Discord สำเร็จ")
        else:
            print("❌ ส่งข้อความ Discord ล้มเหลว:", response.text)
    except Exception as e:
        print(f"❌ ส่งข้อความ Discord error: {e}")

# ===== MAIN LOOP =====

def run_news_bot_loop(interval_seconds=60):
    print("🚀 เริ่มระบบบอทส่งข่าว Discord")
    while True:
        for cat, url in rss_feeds.items():
            try:
                feed = feedparser.parse(url)
                if not feed.entries:
                    continue

                entry = feed.entries[0]
                link = entry.link

                if link in sent_links:
                    continue

                content = entry.get("summary", entry.get("description", ""))
                title = entry.title
                text_to_check = (title + " " + content).lower()

                if not any(kw in text_to_check for kw in KEYWORDS):
                    continue

                title_th = translator.translate(title)
                summary_th = summarize_and_translate(content)

                full_text = (
                    f"🗂️ หมวด: {cat}\n"
                    f"📰 {title_th}\n\n"
                    f"📄 สรุป:\n{summary_th}\n\n"
                    f"🔗 อ่านต่อ: {link}"
                )

                create_image(title_th, summary_th)
                create_voice(summary_th)
                send_discord(full_text)
                sent_links.add(link)
                print(f"📨 ส่งข่าวใหม่ในหมวด {cat}: {title}")
            except Exception as e:
                print(f"⚠️ พบปัญหาในการประมวลผลหมวด {cat}: {e}")

        time.sleep(interval_seconds)

# ===== START =====

if __name__ == "__main__":
    run_news_bot_loop(interval_seconds=60)
