import os
from pyrogram import Client, filters
import yt_dlp

API_ID = 36345749  # Kendi API ID'ni yaz
API_HASH = "9ff5973f89cc76e5aa58d50140e4837f"  # Kendi API Hash'ini yaz
BOT_TOKEN = "9020707414:AAGRs1D744vwMyCeQLS0TbRzZMJxcZ5wKeU"  # BotFather'dan aldığın token

app = Client("video_downloader_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

@app.on_message(filters.command("start"))
async def start_command(client, message):
    await message.reply_text("👋 Selam! Botum GitHub & Render üzerinden sorunsuz çalışıyor. Bana bir **VK Video** veya **OK.ru** linki gönder!")

@app.on_message(filters.text & (filters.regex("vk.com") | filters.regex("ok.ru")))
async def download_video(client, message):
    url = message.text.strip()
    status_msg = await message.reply_text("⏳ Video işleniyor, lütfen bekleyin...")
    
    output_template = "downloads/%(id)s.%(ext)s"
    os.makedirs("downloads", exist_ok=True)
    
    ydl_opts = {
        'format': 'bestvideo+bestaudio/best',
        'outtmpl': output_template,
        'merge_output_format': 'mp4',
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            file_path = ydl.prepare_filename(info)
            if not file_path.endswith('.mp4'):
                file_path = os.path.splitext(file_path)[0] + '.mp4'
                
        await status_msg.edit_text("📤 Telegram'a yükleniyor...")
        
        await message.reply_video(
            video=file_path,
            caption=f"✅ Kaynak: {url}",
            supports_streaming=True
        )
        
        await status_msg.delete()
        
    except Exception as e:
        await status_msg.edit_text(f"❌ Bir hata oluştu:\n`{str(e)}`")
        
    finally:
        if 'file_path' in locals() and os.path.exists(file_path):
            os.remove(file_path)

if __name__ == "__main__":
    print("Bot başlatılıyor...")
    app.run()
