import os
from io import BytesIO

import httpx
from PIL import (
    Image,
    ImageDraw,
    ImageEnhance,
    ImageFilter,
    ImageFont,
    ImageOps,
)

from anony import logger, config
from anony.helpers import Track


# =======================
# Fonts
# =======================

def load_fonts():
    try:
        return {
            "title": ImageFont.truetype(
                "anony/helpers/Raleway-Bold.ttf", 36
            ),
            "artist": ImageFont.truetype(
                "anony/helpers/Inter-Light.ttf", 26
            ),
            "small": ImageFont.truetype(
                "anony/helpers/Inter-Light.ttf", 22
            ),
        }
    except Exception as e:
        logger.warning("Font load failed: %s", e)
        return {
            "title": ImageFont.load_default(),
            "artist": ImageFont.load_default(),
            "small": ImageFont.load_default(),
        }


FONTS = load_fonts()


# =======================
# Fetch Thumbnail
# =======================

async def fetch_image(url: str) -> Image.Image:
    async with httpx.AsyncClient() as client:
        try:
            r = await client.get(url, timeout=6)
            r.raise_for_status()
            img = Image.open(BytesIO(r.content)).convert("RGBA")
            return ImageOps.fit(img, (1280, 720), Image.Resampling.LANCZOS)
        except Exception as e:
            logger.warning("Thumbnail fetch error: %s", e)
            return Image.new("RGBA", (1280, 720), (30, 30, 30, 255))


# =======================
# Main Thumbnail Class
# =======================

class Thumbnail:
    async def generate(self, song: Track) -> str:
        try:
            os.makedirs("cache", exist_ok=True)
            save_path = f"cache/{song.id}.png"

            if os.path.exists(save_path):
                return save_path

            # ===== Background =====
            thumb = await fetch_image(song.thumbnail)
            bg = thumb.filter(ImageFilter.GaussianBlur(40))
            bg = ImageEnhance.Brightness(bg).enhance(0.6)

            width, height = 1280, 720

            # ===== Glass Panel =====
            panel_w, panel_h = 900, 460
            panel_x = (width - panel_w) // 2
            panel_y = (height - panel_h) // 2

            glass = bg.crop(
                (panel_x, panel_y, panel_x + panel_w, panel_y + panel_h)
            )
            glass = glass.filter(ImageFilter.GaussianBlur(20))

            overlay = Image.new(
                "RGBA", (panel_w, panel_h), (25, 25, 45, 170)
            )

            mask = Image.new("L", (panel_w, panel_h), 0)
            ImageDraw.Draw(mask).rounded_rectangle(
                (0, 0, panel_w, panel_h), radius=40, fill=255
            )

            glass = Image.alpha_composite(glass.convert("RGBA"), overlay)
            glass.putalpha(mask)

            bg.paste(glass, (panel_x, panel_y), glass)

            draw = ImageDraw.Draw(bg)

            # ===== Album Cover =====
            cover = ImageOps.fit(
                thumb, (220, 220), Image.Resampling.LANCZOS
            )

            cover_mask = Image.new("L", (220, 220), 0)
            ImageDraw.Draw(cover_mask).rounded_rectangle(
                (0, 0, 220, 220), radius=25, fill=255
            )

            cover.putalpha(cover_mask)
            bg.paste(cover, (panel_x + 70, panel_y + 110), cover)

            # ===== Title =====
            title = (song.title or "Unknown")[:32]
            draw.text(
                (panel_x + 340, panel_y + 120),
                title,
                fill="white",
                font=FONTS["title"],
            )

            # ===== Artist =====
            artist = (song.channel_name or "Unknown")[:30]
            draw.text(
                (panel_x + 340, panel_y + 170),
                artist,
                fill=(200, 200, 200),
                font=FONTS["artist"],
            )

            # ===== Progress Bar =====
            bar_x1 = panel_x + 340
            bar_x2 = panel_x + 780
            bar_y = panel_y + 240

            # background line
            draw.line(
                [(bar_x1, bar_y), (bar_x2, bar_y)],
                fill=(140, 140, 140),
                width=6,
            )

            # fake progress
            progress = bar_x1 + 180
            draw.line(
                [(bar_x1, bar_y), (progress, bar_y)],
                fill="white",
                width=6,
            )

            # time text
            draw.text(
                (bar_x1, bar_y - 30),
                "0:24",
                fill="white",
                font=FONTS["small"],
            )

            draw.text(
                (bar_x2 - 40, bar_y - 30),
                song.duration or "--:--",
                fill="white",
                font=FONTS["small"],
            )

            # ===== Controls (Drawn manually) =====
            controls_text = "⏮      ⏯      ⏭"
            draw.text(
                (panel_x + 420, panel_y + 300),
                controls_text,
                fill="white",
                font=FONTS["title"],
            )

            # Save
            bg.save(save_path, "PNG", quality=95)
            return save_path

        except Exception as e:
            logger.warning("Thumbnail generation failed: %s", e)
            return config.DEFAULT_THUMB
