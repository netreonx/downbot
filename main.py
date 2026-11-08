import os
import subprocess
import json
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import yt_dlp

TOKEN = "9020707414:AAGRs1D744vwMyCeQLS0TbRzZMJxcZ5wKeU"
bot = telebot.TeleBot(TOKEN)

# Kullanıcı linklerini geçici olarak tutmak için sözlük
user_urls = {}

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Selam! OK.ru veya VK linki at, çözünürlük seçmeni sağlayayım. Büyük dosyaları otomatik parçalara bölüp göndereyim.")

@bot.message_handler(func=lambda message: True)
def handle_link(message):
    url = message.text.strip()
    if not ("ok.ru" in url or "vk.com" in url or "vk.video" in url):
        bot.reply_to(message, "Lütfen geçerli bir OK.ru veya VK video linki at!")
        return

    msg = bot.reply_to(message, "⏳ Video analiz ediliyor, çözünürlükler hazırlanıyor...")
    
    try:
        # Kullanıcının linkini hafızaya al
        user_urls[message.from_user.id] = url

        # Çözünürlük seçim butonları
        markup = InlineKeyboardMarkup()
        markup.row_width = 2
        
        buttons = [
            InlineKeyboardButton("🔥 1080p", callback_data="dl_1080"),
            InlineKeyboardButton("⚡ 720p", callback_data="dl_720"),
            InlineKeyboardButton("📱 480p", callback_data="dl_480"),
            InlineKeyboardButton("🚀 En İyi Kalite", callback_data="dl_best")
        ]
        markup.add(*buttons)
        
        bot.edit_message_text("🎥 Lütfen indirmek istediğin çözünürlüğü seç:", 
                              chat_id=message.chat.id, 
                              message_id=msg.message_id, 
                              reply_markup=markup)
    except Exception as e:
        bot.edit_message_text(f"❌ Hata: {str(e)}", chat_id=message.chat.id, message_id=msg.message_id)

@bot.callback_query_handler(func=lambda call: call.data.startswith('dl_'))
def callback_resolution(call):
    user_id = call.from_user.id
    if user_id not in user_urls:
        bot.answer_callback_query(call.id, "Zaman aşımı! Lütfen tekrar link at.")
        return

    url = user_urls[user_id]
    res = call.data.split('_')[1]
    
    bot.answer_callback_query(call.id, f"{res} kalitesi seçildi, indiriliyor...")
    bot.edit_message_text(f"⏳ Seçilen kalite ({res}) indiriliyor, lütfen bekle...", 
                          chat_id=call.message.chat.id, 
                          message_id=call.message.message_id)

    # yt-dlp format ayarı
    if res == "best":
        ydl_format = 'best'
    else:
        ydl_format = f'bestvideo[height<={res}]+bestaudio/best[height<={res}]/best'

    ydl_opts = {
        'format': ydl_format,
        'outtmpl': f'video_{user_id}.%(ext)s',
    }

    filename = None
    downloaded_files = []
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)

        if not filename or not os.path.exists(filename):
            raise Exception("Video dosyası indirilemedi.")

        # Boyut kontrolü (2GB sınırına takılmamak için 1900 MB sınır alıyoruz)
        file_size_mb = os.path.getsize(filename) / (1024 * 1024)
        max_part_size = 1900 # MB

        if file_size_mb > max_part_size:
            bot.edit_message_text(f"📦 Dosya büyük ({file_size_mb:.1f}MB). Parçalara bölünüyor...", 
                                  chat_id=call.message.chat.id, 
                                  message_id=call.message.message_id)
            downloaded_files = split_video(filename, max_part_size)
        else:
            downloaded_files = [filename]

        bot.edit_message_text(f"📤 Toplam {len(downloaded_files)} parça Telegram'a yükleniyor...", 
                              chat_id=call.message.chat.id, 
                              message_id=call.message.message_id)

        for i, part_file in enumerate(downloaded_files):
            with open(part_file, 'rb') as f:
                bot.send_video(call.message.chat.id, f, caption=f"Part {i+1}/{len(downloaded_files)} ({res})", timeout=300)

        bot.delete_message(call.message.chat.id, call.message.message_id)

    except Exception as e:
        bot.edit_message_text(f"❌ İşlem sırasında hata oluştu: {str(e)}", chat_id=call.message.chat.id, message_id=call.message.message_id)
    
    finally:
        # Geçici dosyaları temizle
        if filename and os.path.exists(filename):
            os.remove(filename)
        for f in downloaded_files:
            if f != filename and os.path.exists(f):
                os.remove(f)

def get_video_duration(filename):
    cmd = ['ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_format', filename]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    data = json.loads(result.stdout)
    return float(data['format']['duration'])

def split_video(filename, max_size_mb=1900):
    file_size_mb = os.path.getsize(filename) / (1024 * 1024)
    duration = get_video_duration(filename)
    
    parts_count = int(file_size_mb // max_size_mb) + 1
    part_duration = duration / parts_count
    
    output_files = []
    base, ext = os.path.splitext(filename)
    
    for i in range(parts_count):
        start_time = i * part_duration
        part_filename = f"{base}_part{i+1}{ext}"
        
        cmd = [
            'ffmpeg', '-y', '-ss', str(start_time), '-i', filename,
            '-t', str(part_duration), '-c', 'copy', part_filename
        ]
        subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output_files.append(part_filename)
        
    return output_files

print("Bot çalışıyor (Çözünürlük ve Bölme Modu Aktif)...")
bot.infinity_polling()
