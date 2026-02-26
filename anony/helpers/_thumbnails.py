import os
import aiohttp
from io import BytesIO
from PIL import (
    Image,
    ImageDraw,
    ImageEnhance,
    ImageFilter,
    ImageFont,
    ImageOps,
)

from anony import config
from anony.helpers import Track


class Thumbnail:
    def __init__(self):
        self.size = (1280, 720)
        self.font_title = ImageFont.truetype(
            "anony/helpers/Raleway-Bold.ttf", 40
        )
        self.font_channel = ImageFont.truetype(
            "anony/helpers/Inter-Light.ttf", 30
        )

    async def fetch_image(self, url: str) -> Image.Image:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    data = await resp.read()
            return Image.open(BytesIO(data)).convert("RGBA")
        except Exception:
            return Image.new("RGBA", self.size, (30, 30, 30, 255))

    def resize_crop(self, img: Image.Image) -> Image.Image:
        img = img.resize(self.size, Image.Resampling.LANCZOS)
        return img

    def rounded_cover(self, image: Image.Image, size=(220, 220)) -> Image.Image:
        image = ImageOps.fit(image, size, Image.Resampling.LANCZOS)
        mask = Image.new("L", size, 0)
        ImageDraw.Draw(mask).rounded_rectangle(
            (0, 0, size[0], size[1]), radius=25, fill=255
        )
        image.putalpha(mask)
        return image

    async def generate(self, song: Track) -> str:
        try:
            output = f"cache/{song.id}.png"
            if os.path.exists(output):
                return output

            # 🔹 Background
            thumb = await self.fetch_image(song.thumbnail)
            bg = self.resize_crop(thumb)
            bg = bg.filter(ImageFilter.GaussianBlur(25))
            bg = ImageEnhance.Brightness(bg).enhance(0.4)

            # 🔹 Dark box overlay
            box = (300, 120, 980, 600)
            region = bg.crop(box)
            dark = ImageEnhance.Brightness(region).enhance(0.5)

            mask = Image.new("L", dark.size, 0)
            ImageDraw.Draw(mask).rounded_rectangle(
                (0, 0, dark.size[0], dark.size[1]),
                radius=25,
                fill=255,
            )

            bg.paste(dark, box, mask)

            # 🔹 Rounded thumbnail cover
            cover = self.rounded_cover(thumb)
            bg.paste(cover, (340, 170), cover)

            draw = ImageDraw.Draw(bg)

            # 🔹 Title
            title = song.title[:35] if song.title else "Unknown"
            draw.text(
                (600, 190),
                title,
                font=self.font_title,
                fill=(255, 255, 255),
            )

            # 🔹 Channel
            channel = song.channel_name[:30] if song.channel_name else "Unknown"
            draw.text(
                (600, 250),
                channel,
                font=self.font_channel,
                fill=(220, 220, 220),
            )

            # 🔹 Duration
            draw.text(
                (600, 300),
                f"Duration: {song.duration}",
                font=self.font_channel,
                fill=(200, 200, 200),
            )

            # 🔹 Save
            bg = ImageEnhance.Contrast(bg).enhance(1.1)
            bg = ImageEnhance.Color(bg).enhance(1.2)

            os.makedirs("cache", exist_ok=True)
            bg.save(output, format="PNG")

            return output

        except Exception:
            return config.DEFAULT_THUMB
