import os
import requests
from telebot import types
from telebot import TeleBot
from radiojavanapi import Client
from moviepy.editor import VideoFileClip
from tqdm import tqdm

bot = TeleBot('YOUR_BOT_TOKEN')
channel_username = "@YOUR_CHANNEL_USERNAME"
bot_username = "YOUR_BOTUSERNAME"
FILE_SIZE_LIMIT = 1 * 1024 * 1024 * 1024  # 1 GB

def is_valid_url(url):
    return url.startswith('https://play.radiojavan.com/')

def check_channel_membership(user_id):
    chat_member = bot.get_chat_member(channel_username, user_id)
    return chat_member.status in ["member", "administrator", "creator"]

def verify_commands(message):
    user_id = message.from_user.id
    if not check_channel_membership(user_id):
        channel_username_cleaned = channel_username.lstrip('@')
        keyboard = types.InlineKeyboardMarkup()
        
        url_button = types.InlineKeyboardButton(text="🔗 عضویت در کانال", url=f"https://t.me/{channel_username_cleaned}")
        keyboard.add(url_button)

        url_button2 = types.InlineKeyboardButton(text="عضو شدم ✅", url=f"https://t.me/{bot_username}?start=welcome")
        keyboard.add(url_button2)

        bot.reply_to(message, f"▫️شما در کانال اسپانسر عضو نیستید\nعضو شوید و سپس /start را بفرستید", reply_markup=keyboard)
        return "Nist"

@bot.message_handler(commands=['start', 'help'])
def handle_start(message):
    try:
        if verify_commands(message) == "Nist":
            return
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        button_song = types.KeyboardButton('🎵 دانلود آهنگ')
        button_podcast = types.KeyboardButton('🎙 دانلود پادکست')
        button_video = types.KeyboardButton('🎬 دانلود ویدیو')
        keyboard.add(button_song, button_podcast, button_video)
        bot.send_message(message.chat.id, f"سلام به ربات خوش اومدی!\n\nلطفا لینک رسانه‌ای که می‌خواهید دانلود کنید را بفرستید.", reply_markup=keyboard)
    except Exception as e:
        bot.reply_to(message, f"Error: {str(e)}")

def download_file(url, file_path):
    response = requests.get(url, stream=True)
    if response.status_code != 200:
        raise Exception(f"Failed to download file: HTTP {response.status_code}")
    
    total_size = int(response.headers.get('content-length', 0))
    if total_size > FILE_SIZE_LIMIT:  # 1 GB limit
        raise Exception("File is too large to download")

    with open(file_path, 'wb') as file, tqdm(
        desc=file_path,
        total=total_size,
        unit='B',
        unit_scale=True,
        unit_divisor=1024,
    ) as bar:
        for data in response.iter_content(chunk_size=8192):
            size = file.write(data)
            bar.update(size)

def handle_media_link(message, media_type):
    try:
        if verify_commands(message) == "Nist":
            return
        
        media_url = message.text

        if not is_valid_url(media_url):
            bot.reply_to(message, "URL نامعتبر است")
            return

        download_message = bot.send_message(message.chat.id, "⏳ دانلود در حال انجام است...")

        client = Client()
        if media_type == "song":
            media = client.get_song_by_url(media_url)
        elif media_type == "podcast":
            media = client.get_podcast_by_url(media_url)
        elif media_type == "video":
            media = client.get_video_by_url(media_url)
        else:
            bot.reply_to(message, "نوع رسانه نامعتبر است")
            return

        photo_file_path = f"{media.title}_photo.jpg"
        download_file(media.photo, photo_file_path)

        with open(photo_file_path, "rb") as file:
            bot.send_photo(message.chat.id, file)

        if media_type == "video":
            media_file_path = f"{media.title}_video.mp4"
            download_file(media.lq_link, media_file_path)
            target_size_bytes = 45 * 1024 * 1024

            while os.path.getsize(media_file_path) > target_size_bytes:
                compressed_file_path = f"{media.title}_compressed_video.mp4"

                video_clip = VideoFileClip(media_file_path)
                video_clip_resized = video_clip.resize(width=640, height=480)
                video_clip_resized.write_videofile(compressed_file_path, codec="libx264", audio_codec="aac")

                os.remove(media_file_path)
                media_file_path = compressed_file_path

            with open(media_file_path, "rb") as file:
                bot.send_video(message.chat.id, file, caption=f"Title: {media.title}\nPower By : {channel_username}")

            os.remove(media_file_path)
        else:
            media_file_path = f"{media.title}.mp3"
            download_file(media.hq_link, media_file_path)

            with open(media_file_path, "rb") as file:
                bot.send_audio(message.chat.id, file, caption=f"Title: {media.title}\nPower By : {channel_username}")

            os.remove(media_file_path)

        os.remove(photo_file_path)
        bot.delete_message(message.chat.id, download_message.message_id)
        bot.send_message(message.chat.id, "<b>✅ دانلود به پایان رسید</b>", parse_mode="HTML")
    except Exception as e:
        bot.reply_to(message, f"Error: {str(e)}")

@bot.message_handler(func=lambda message: message.text.startswith("https://play.radiojavan.com/song"))
def handle_song_link(message):
    handle_media_link(message, "song")

@bot.message_handler(func=lambda message: message.text.startswith("https://play.radiojavan.com/podcast"))
def handle_podcast_link(message):
    handle_media_link(message, "podcast")

@bot.message_handler(func=lambda message: message.text.startswith("https://play.radiojavan.com/video"))
def handle_video_link(message):
    handle_media_link(message, "video")

bot.polling()
