import logging
import random
import string
from io import BytesIO
from datetime import datetime, timedelta

from PIL import Image, ImageDraw, ImageFont
from captcha.image import ImageCaptcha

logger = logging.getLogger(__name__)

CHALLENGE_TTL_MINUTES = 10

class Challenge:
    def __init__(self, guild_id: int, user_id: int, answer: str, image_bytes: bytes, expires_at: datetime, attempts_left: int = 5, kind: str = "text"):
        self.guild_id = guild_id
        self.user_id = user_id
        self.answer = answer
        self.image_bytes = image_bytes
        self.expires_at = expires_at
        self.attempts_left = attempts_left
        self.kind = kind

    def is_expired(self) -> bool:
        return datetime.utcnow() > self.expires_at

# {(guild_id, user_id): Challenge}
challenges = {}

def _render_text_to_image(text: str):
    width, height = 420, 140
    bg_color = (255, 255, 255)
    text_color = (30, 30, 30)
    image = Image.new("RGB", (width, height), bg_color)
    draw = ImageDraw.Draw(image)

    font = None
    for candidate in ["arial.ttf", "Arial.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]:
        try:
            font = ImageFont.truetype(candidate, 48)
            break
        except Exception:
            continue
    if font is None:
        font = ImageFont.load_default()

    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    x = (width - tw) // 2
    y = (height - th) // 2
    draw.text((x, y), text, fill=text_color, font=font)

    bio = BytesIO()
    image.save(bio, format="PNG")
    return bio.getvalue()

def _generate_text_captcha():
    length = random.choice([5, 6])
    text = "".join(random.choices(string.ascii_uppercase + string.digits, k=length))
    gen = ImageCaptcha(width=280, height=100)
    image = gen.generate_image(text)
    bio = BytesIO()
    image.save(bio, format="PNG")
    return text, bio.getvalue()

def _generate_math_captcha():
    ops = ["+", "-", "*"]
    terms = [random.randint(2, 15)]
    expr_parts = [str(terms[0])]
    for _ in range(random.choice([1, 2])):  # 2 or 3 terms
        op = random.choice(ops)
        n = random.randint(2, 15)
        expr_parts.append(op)
        expr_parts.append(str(n))
    expr = " ".join(expr_parts)
    try:
        result = eval(expr, {"__builtins__": {}})
    except Exception:
        result = 0
    img_bytes = _render_text_to_image(expr)
    return str(int(result)), img_bytes

def make_new_challenge(guild_id: int, user_id: int) -> Challenge:
    if random.random() < 0.5:
        ans, img_bytes = _generate_text_captcha()
        kind = "text"
    else:
        ans, img_bytes = _generate_math_captcha()
        kind = "math"
    expires_at = datetime.utcnow() + timedelta(minutes=CHALLENGE_TTL_MINUTES)
    ch = Challenge(guild_id, user_id, ans, img_bytes, expires_at, attempts_left=5, kind=kind)
    logger.info("Created %s challenge for guild=%s user=%s (expires in %s min)", kind, guild_id, user_id, CHALLENGE_TTL_MINUTES)
    return ch

def get_or_create_active_challenge(guild_id: int, user_id: int) -> Challenge:
    key = (guild_id, user_id)
    ch = challenges.get(key)
    if ch is None or ch.is_expired() or ch.attempts_left <= 0:
        ch = make_new_challenge(guild_id, user_id)
        challenges[key] = ch
    return ch

def clear_challenge(guild_id: int, user_id: int):
    if (guild_id, user_id) in challenges:
        logger.info("Cleared challenge for guild=%s user=%s", guild_id, user_id)
    challenges.pop((guild_id, user_id), None)