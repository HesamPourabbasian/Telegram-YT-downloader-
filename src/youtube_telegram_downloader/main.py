import os
import tempfile
import asyncio
import logging
import yt_dlp
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Bot token
TOKEN = "7611838639:AAHt8IiHtlF5w9426WLx5vsSNowaO6cITSw"


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle the /start command by sending a welcome message.

    Args:
        update: The incoming update from Telegram.
        context: The context object for the bot.
    """
    logger.info("Received /start command")
    await update.message.reply_text("Hello! Send /download <YouTube URL> to download a video.")


async def download(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle the /download command to download a YouTube video and send it directly through Telegram.

    Args:
        update: The incoming update from Telegram.
        context: The context object for the bot.
    """
    logger.info(f"Received /download command with args: {context.args}")
    if len(context.args) == 0:
        await update.message.reply_text("Please provide a YouTube URL.")
        return

    url = context.args[0]
    chat_id = update.message.chat_id

    # Step 1: Get video info to check size
    ydl_opts_info = {
        'format': 'best[ext=mp4]',  # Best quality MP4 stream
        'quiet': True,
        'cookiesfrombrowser': ('firefox', None, None, None),  # Corrected format for browser cookies
    }
    with yt_dlp.YoutubeDL(ydl_opts_info) as ydl_info:
        try:
            info = ydl_info.extract_info(url, download=False)
            size = info.get('filesize', None)
            if size is None:
                await update.message.reply_text("Unable to determine video size.")
                return
            if size > 50 * 1024 * 1024:  # 50 MB limit
                await update.message.reply_text("Video is too large to send. Maximum size is 50 MB.")
                return

            # Step 2: Create a temporary file for downloading
            with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tmp_file:
                tmp_filename = tmp_file.name
                tmp_file.close()  # Close it since yt-dlp will write to it

            # Step 3: Download the video to the temporary file
            ydl_opts_download = {
                'format': 'best[ext=mp4]',
                'outtmpl': tmp_filename,
                'quiet': True,
                'cookiesfrombrowser': ('firefox', None, None, None),  # Corrected format for browser cookies
            }
            with yt_dlp.YoutubeDL(ydl_opts_download) as ydl_download:
                # Download in a separate thread to avoid blocking the event loop
                loop = asyncio.get_running_loop()
                await loop.run_in_executor(None, ydl_download.download, [url])

            # Step 4: Send the video
            await update.message.reply_text("Starting download...")
            with open(tmp_filename, 'rb') as video_file:
                await context.bot.send_video(chat_id=chat_id, video=video_file, supports_streaming=True)
            await update.message.reply_text("Video sent successfully.")

        except Exception as e:
            logger.error(f"Error during download: {str(e)}")
            await update.message.reply_text(f"Failed to download video: {str(e)}")

        finally:
            # Step 5: Delete the temporary file
            if os.path.exists(tmp_filename):
                os.remove(tmp_filename)


def main() -> None:
    """
    Set up and run the Telegram bot.
    """
    logger.info("Starting bot...")
    application = Application.builder().token(TOKEN).build()

    # Add command handlers
    start_handler = CommandHandler("start", start)
    download_handler = CommandHandler("download", download)

    application.add_handler(start_handler)
    application.add_handler(download_handler)

    # Run the bot
    logger.info("Bot is running and polling for updates.")
    application.run_polling()


if __name__ == "__main__":
    main()