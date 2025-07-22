import discord
import os


class MediaProcessor:
    def __init__(self):
        self.image_extensions = [
            ".jpg",
            ".jpeg",
            ".png",
            ".webp",
            ".bmp",
            ".heic",
            ".heif",
        ]
        self.gif_extensions = [".gif"]
        self.video_extensions = [".mp4", ".webm", ".mov", ".avi", ".mkv", ".flv"]

    async def process_image(self, attachment: discord.Attachment) -> tuple[str, bytes]:
        """Process an image attachment and return its raw bytes."""
        try:
            image_bytes = await attachment.read()
            mime_type = attachment.content_type or "image/jpeg"
            return mime_type, image_bytes
        except Exception as e:
            print(f"Error processing image: {e}")
            return None, None

    async def process_gif(self, attachment: discord.Attachment) -> tuple[str, bytes]:
        """Process a GIF attachment and return its raw bytes."""
        try:
            gif_bytes = await attachment.read()
            mime_type = attachment.content_type or "image/gif"
            return mime_type, gif_bytes
        except Exception as e:
            print(f"Error processing GIF: {e}")
            return None, None

    async def process_video(self, attachment: discord.Attachment) -> tuple[str, bytes]:
        """Process a video attachment and return its raw bytes."""
        try:
            video_bytes = await attachment.read()
            mime_type = attachment.content_type or "video/mp4"
            return mime_type, video_bytes
        except Exception as e:
            print(f"Error processing video: {e}")
            return None, None

    async def process_attachment(self, attachment: discord.Attachment) -> tuple[str, bytes, str]:
        """Process any attachment and return the appropriate image data."""
        if not attachment:
            return None, None, None
        filename = attachment.filename.lower()
        _, ext = os.path.splitext(filename)
        if ext in self.image_extensions:
            mime_type, image_bytes = await self.process_image(attachment)
            return mime_type, image_bytes, "image"
        elif ext in self.gif_extensions:
            mime_type, image_bytes = await self.process_gif(attachment)
            return mime_type, image_bytes, "gif"
        elif ext in self.video_extensions:
            mime_type, image_bytes = await self.process_video(attachment)
            return mime_type, image_bytes, "video"
        else:
            print(f"Unsupported file type: {ext}")
            return None, None, None
