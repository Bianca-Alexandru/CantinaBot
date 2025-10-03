import logging
import os
import random

import discord
from discord.ext import commands
import requests
import asyncio
from io import BytesIO
import fitz  # PyMuPDF
import urllib3
from zoneinfo import ZoneInfo

from dataclasses import dataclass
from datetime import datetime, timedelta, date, time
from typing import Callable, List, Optional, Sequence, Tuple

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("cantina_bot")

# Suppress InsecureRequestWarning
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# =====================
# CONFIG
# =====================
TOKEN_ENV_VAR = "DISCORD_BOT_TOKEN"
CHANNEL_ID_ENV_VAR = "DISCORD_CHANNEL_ID"

TOKEN = os.environ.get(TOKEN_ENV_VAR)
if not TOKEN:
    raise RuntimeError(
        "Missing Discord token. Set the DISCORD_BOT_TOKEN environment variable before running the bot."
    )

try:
    CHANNEL_ID = int(os.environ[CHANNEL_ID_ENV_VAR])
except KeyError as exc:
    raise RuntimeError(
        "Missing channel ID. Set the DISCORD_CHANNEL_ID environment variable before running the bot."
    ) from exc
except ValueError as exc:
    raise RuntimeError(
        "Invalid DISCORD_CHANNEL_ID value. It must be an integer."
    ) from exc
ROMANIA_TZ = ZoneInfo("Europe/Bucharest")

RETRY_DELAY = timedelta(minutes=5)
OPEN_TIME = time(hour=11, minute=30)
DEFAULT_CLOSE_TIME = time(hour=14, minute=45)
TITU_CLOSE_TIME = time(hour=18, minute=45)

BASE_PDF_URL = "https://www.uaic.ro/wp-content/uploads"

PRAISE_GIF_URL = "https://tenor.com/view/noni-itayuwuji-phainon-dance-honkaistarrail-phainon-chibi-gif-318861480241854034"
INSULT_GIF_URL = "https://tenor.com/view/phainon-noni-itayuwuji-phainon-honkaistarrail-phainon-chibi-cry-gif-14390704413906512030"
WISE_WORDS_GIF_URL = "https://tenor.com/view/phainon-kitty-cute-dance-cat-gif-7410832384021952970"

PRAISE_RESPONSES = [
    "yayyy thank you >w< :3c",
    "yippiee yippiee yippiee ฅ^•ﻌ•^ฅ",
    "aww you're too nice /ᐠ ˵> ⩊ <˵マ",
    "hehe thamks ≽(•⩊ •マ≼",
]

INSULT_RESPONSES = [
    "sowwyyy /ᐠ ◞ ᆺ ◟マ",
    "oh so that's how it is /ᐠ - ˕ -マ ᶻ 𝗓 𐰁",
    "i'm trying my best /ᐠ ･᷄ ︵ ･᷅マ",
    "i-i'll do better /ᐠ •̥ ﻌ •̥ ᐟマ",
    "FRICK YOU"
]

WISE_SAYINGS = [
    "You cannot change what you refuse to confront.",
    "Sometimes good things fall apart so better things can fall together.",
    "Don’t think of cost.  Think of value.",
    "No matter how many mistakes you make or how slow you progress, you are still way ahead of everyone who isn’t trying.",
    "The only way to do great work is to love what you do.",
    "Success is not final, failure is not fatal: It is the courage to continue that counts.",
    "Making one person smile can change the world – maybe not the whole world, but their world.",
    "The fool doth think he is wise, but the wise man knows himself to be a fool.",
    "Even a broken clock is right twice a day.",
    "A journey of a thousand miles begins with a single step.",
    "Even a humble soup can warm the coldest evening.",
    "A shared meal tastes twice as good.",
    "It is better to remain silent at the risk of being thought a fool, than to talk and remove all doubt of it.",
    "Patience is the secret ingredient in every great stew.",
    "The only true wisdom is in knowing you know nothing.",
    "Count your age by friends, not years. Count your life by smiles, not tears.",
    "May you live every day of your life.",
    "meow meow meow meow",
    "lucky message!",
    "Any fool can know. The point is to understand.",
    "The secret of life, though, is to fall seven times and to get up eight times.",
    "The unexamined life is not worth living.",
    "Yesterday I was clever, so I wanted to change the world. Today I am wise, so I am changing myself",
    "The best way out is always through.",
    "Happiness depends upon ourselves.",
    "We are what we repeatedly do. Excellence, then, is not an act, but a habit.",
    "The mind is everything. What you think you become.",
    "yea!",
    "frick you",
    "Let no man pull you so low as to hate him.",
    "Do what you can, with what you have, where you are.",
    "You miss 100% of the shots you don’t take.",
    "The greatest wealth is to live content with little.",
    "The best way to predict the future is to create it.",
    "please help me theyre keeping me captive in this discord bot /ᐠ •̥ ﻌ •̥ ᐟマ",
    "i am suffering /ᐠ •̥ ﻌ •̥ ᐟマ",
    "The root of suffering is attachment.",
    "Happiness is not something ready made. It comes from your own actions.",
    "In the middle of difficulty lies opportunity.",
    "Life is really simple, but we insist on making it complicated.",
    "The only limit to our realization of tomorrow will be our doubts of today.",
    "Do not dwell in the past, do not dream of the future, concentrate the mind on the present moment.",
    "The best revenge is massive success.",
    "The only thing necessary for the triumph of evil is for good men to do nothing."
    "Early to bed and early to rise makes a man healthy, wealthy, and wise.",
    "An unexamined life is not worth living.",
    "To be yourself in a world that is constantly trying to make you something else is the greatest accomplishment.",
    "If you tell the truth, you don't have to remember anything.",
    "We accept the love we think we deserve.",
    "It is better to be hated for what you are than to be loved for what you are not.",
    "I have not failed. I've just found 10,000 ways that won't work.",
    "Be the change that you wish to see in the world.",
    "In three words I can sum up everything I've learned about life: it goes on.",
    "Live as if you were to die tomorrow. Learn as if you were to live forever.",
    "That which does not kill us makes us stronger.",
    "The journey of a thousand miles begins with one step.",
    "You must be the change you wish to see in the world.",
    "What we think, we become.",
    "All that we are is the result of what we have thought."
]


@dataclass(frozen=True)
class CantinaConfig:
    key: str
    display_name: str
    close_time: time
    url_builder: Callable[[date], Sequence[str]]
    auto_post: bool = False


def build_gaudeamus_url(target_date: date) -> Sequence[str]:
    year = target_date.strftime("%Y")
    month = target_date.strftime("%m")
    new_filename = f"Meniu-site-GAU-{target_date.strftime('%d.%m.%Y')}.pdf"
    legacy_filename = f"GAU-{target_date.strftime('%d-%b-%Y').upper()}.pdf"
    base_path = f"{BASE_PDF_URL}/{year}/{month}"
    return (
        f"{base_path}/{new_filename}",
        f"{base_path}/{legacy_filename}",
    )


def build_titu_url(target_date: date) -> Sequence[str]:
    year = target_date.strftime("%Y")
    month = target_date.strftime("%m")
    month_abbr = target_date.strftime("%b").upper()
    legacy_filename = f"{target_date.day}-{month_abbr}-TM.pdf"
    base_path = f"{BASE_PDF_URL}/{year}/{month}"
    return (
        f"{base_path}/meniu.pdf",
        f"{base_path}/{legacy_filename}",
    )


def build_akademos_url(target_date: date) -> Sequence[str]:
    year = target_date.strftime("%Y")
    month = target_date.strftime("%m")
    new_filename = f"MENIU-AKADEMOS-{target_date.strftime('%d.%m.%Y')}.pdf"
    legacy_filename = f"AK-{target_date.strftime('%d-%b-%Y').upper()}-.pdf"
    base_path = f"{BASE_PDF_URL}/{year}/{month}"
    return (
        f"{base_path}/{new_filename}",
        f"{base_path}/{legacy_filename}",
    )


CANTINAS = {
    "gau": CantinaConfig(
        key="gau",
        display_name="Gaudeamus",
        close_time=DEFAULT_CLOSE_TIME,
        url_builder=build_gaudeamus_url,
        auto_post=True,
    ),
    "titu": CantinaConfig(
        key="titu",
        display_name="Titu Maiorescu",
        close_time=TITU_CLOSE_TIME,
        url_builder=build_titu_url,
    ),
    "aka": CantinaConfig(
        key="aka",
        display_name="Akademos",
        close_time=DEFAULT_CLOSE_TIME,
        url_builder=build_akademos_url,
    ),
}

DEFAULT_CANTINA_KEY = "gau"

# =====================
# BOT SETUP
# =====================
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

pdf_cache: dict[str, List[bytes]] = {}
cache_lock = asyncio.Lock()
auto_schedule_lock = asyncio.Lock()
next_auto_post_at: Optional[datetime] = None
auto_post_task: Optional[asyncio.Task] = None
last_channel_id = CHANNEL_ID
_scheduler_started = False


def make_cache_key(cantina_key: str, target_date: date) -> str:
    return f"{cantina_key}:{target_date:%Y-%m-%d}"


async def get_cached_images(cantina_key: str, target_date: date) -> Optional[List[bytes]]:
    key = make_cache_key(cantina_key, target_date)
    async with cache_lock:
        cached = pdf_cache.get(key)
    if cached is None:
        return None
    return list(cached)


async def store_cached_images(cantina_key: str, target_date: date, image_bytes_list: Sequence[bytes]):
    key = make_cache_key(cantina_key, target_date)
    async with cache_lock:
        pdf_cache[key] = list(image_bytes_list)


async def fetch_and_cache_pdf(
    cantina: CantinaConfig,
    target_date: date,
    retries: int = 3,
    delay: int = 5,
) -> Optional[Tuple[List[bytes], bool]]:
    cached = await get_cached_images(cantina.key, target_date)
    if cached is not None:
        return cached, True

    raw_candidates = cantina.url_builder(target_date)
    if isinstance(raw_candidates, str):
        pdf_urls = [raw_candidates]
    else:
        # Preserve order while removing duplicates and filtering out empty values
        seen_urls = set()
        pdf_urls = []
        for candidate in raw_candidates:
            if not candidate or candidate in seen_urls:
                continue
            pdf_urls.append(candidate)
            seen_urls.add(candidate)

    if not pdf_urls:
        return None

    for attempt in range(1, retries + 1):
        for variant_index, pdf_url in enumerate(pdf_urls, start=1):
            try:
                print(f"📥 Attempt {attempt}.{variant_index} to fetch PDF from {pdf_url}...")
                response = await asyncio.to_thread(requests.get, pdf_url, timeout=60, verify=False)
                response.raise_for_status()

                pdf_document = fitz.open(stream=response.content, filetype="pdf")
                image_bytes_list: List[bytes] = []
                for page_num in range(len(pdf_document)):
                    page = pdf_document.load_page(page_num)
                    pix = page.get_pixmap()
                    image_bytes_list.append(pix.tobytes("png"))

                if not image_bytes_list:
                    print("❌ The PDF was empty or could not be read.")
                    return None

                await store_cached_images(cantina.key, target_date, image_bytes_list)
                print("✅ PDF fetched, converted, and cached.")
                return image_bytes_list, False
            except Exception as e:
                print(f"❌ Attempt {attempt}.{variant_index} failed: {e}")
        if attempt < retries:
            print(f"⏳ Waiting {delay}s before retrying...")
            await asyncio.sleep(delay)
    print("❌ All attempts failed. Could not fetch PDF.")
    return None

# ========== Menu Dispatch ==========
async def resolve_menu_images(
    cantina: CantinaConfig,
    candidate_dates: Sequence[date],
    retries: int = 3,
    delay: int = 5,
) -> Optional[Tuple[date, List[bytes], bool]]:
    seen: set[date] = set()
    for target_date in candidate_dates:
        if not isinstance(target_date, date):
            continue
        if target_date in seen:
            continue
        seen.add(target_date)
        if target_date.weekday() >= 5:
            continue
        result = await fetch_and_cache_pdf(cantina, target_date, retries=retries, delay=delay)
        if result is None:
            continue
        images, from_cache = result
        return target_date, images, from_cache
    return None


async def send_menu(
    cantina: CantinaConfig,
    channel,
    send_message_func,
    candidate_dates: Sequence[date],
    content_builder: Callable[[date, bool], str],
    failure_message: Optional[str] = None,
) -> Tuple[bool, Optional[date]]:
    global last_channel_id

    if not channel:
        print("❌ Channel not found. Check your channel settings.")
        return False, None

    if hasattr(channel, "guild") and channel.guild is not None:
        bot_member = channel.guild.me or channel.guild.get_member(bot.user.id)
        if bot_member is not None:
            perms = channel.permissions_for(bot_member)
            channel_label = getattr(channel, "name", None) or getattr(channel, "id", "unknown")
            print(
                f"ℹ️ Bot perms in #{channel_label}: "
                f"send_messages={perms.send_messages}, attach_files={perms.attach_files}, "
                f"embed_links={perms.embed_links}, send_msgs_in_threads={getattr(perms, 'send_messages_in_threads', True)}"
            )

    resolved = await resolve_menu_images(cantina, candidate_dates)
    if resolved is None:
        if failure_message:
            try:
                await send_message_func(failure_message)
            except discord.Forbidden:
                print("❌ Missing permission to send failure notice in the target channel.")
        return False, None

    actual_date, images, from_cache = resolved
    files = [
        discord.File(BytesIO(img_bytes), filename=f"{cantina.key}-menu-{actual_date:%Y-%m-%d}-page-{idx + 1}.png")
        for idx, img_bytes in enumerate(images)
    ]
    content = content_builder(actual_date, from_cache)

    try:
        await send_message_func(content, files=files)
        channel_id = getattr(channel, "id", None)
        if channel_id and cantina.auto_post:
            last_channel_id = channel_id
        return True, actual_date
    except discord.Forbidden:
        print("❌ Missing permission to post menu in the target channel.")
        return False, None

# ========== Scheduling ==========
def _to_romania(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=ROMANIA_TZ)
    return dt.astimezone(ROMANIA_TZ)


def _format_schedule(dt: Optional[datetime]) -> str:
    if dt is None:
        return "unscheduled"
    romania_dt = _to_romania(dt)
    return romania_dt.strftime("%Y-%m-%d %H:%M %Z")


def _move_to_auto_time(reference: datetime) -> datetime:
    romania_ref = _to_romania(reference)
    return romania_ref.replace(
        hour=OPEN_TIME.hour,
        minute=OPEN_TIME.minute,
        second=0,
        microsecond=0,
    )

def _align_to_weekday(target: datetime) -> datetime:
    target = _to_romania(target)
    while target.weekday() >= 5:  # 5=Saturday, 6=Sunday
        target += timedelta(days=1)
    return target

def get_initial_auto_post_time(reference: datetime | None = None) -> datetime:
    reference = _to_romania(reference) if reference is not None else datetime.now(ROMANIA_TZ)
    target = _move_to_auto_time(reference)
    if target <= reference:
        target = _move_to_auto_time(reference + timedelta(days=1))
    return _align_to_weekday(target)

def get_next_day_auto_post_time(reference: datetime | None = None) -> datetime:
    reference = _to_romania(reference) if reference is not None else datetime.now(ROMANIA_TZ)
    target = _move_to_auto_time(reference + timedelta(days=1))
    return _align_to_weekday(target)

def get_retry_auto_post_time(reference: datetime | None = None) -> datetime:
    reference = _to_romania(reference) if reference is not None else datetime.now(ROMANIA_TZ)
    candidate = reference + RETRY_DELAY
    if candidate.weekday() >= 5:
        return get_next_day_auto_post_time(candidate)
    return candidate

async def set_next_auto_post(target: datetime, reason: str):
    global next_auto_post_at
    target = _to_romania(target)
    async with auto_schedule_lock:
        next_auto_post_at = target
    message = f"{reason} Next auto menu attempt at {target:%Y-%m-%d %H:%M} Romania time."
    logger.info(message)
    print(message)


def build_candidate_dates(today: date, include_today: bool, max_entries: int = 5) -> List[date]:
    dates: List[date] = []
    if include_today and today.weekday() < 5:
        dates.append(today)

    current = today - timedelta(days=1)
    attempts = 0
    total_needed = max_entries + (1 if include_today and today.weekday() < 5 else 0)

    while len(dates) < total_needed and attempts < 21:
        if current.weekday() < 5:
            dates.append(current)
        current -= timedelta(days=1)
        attempts += 1

    if not dates:
        fallback = today
        while fallback.weekday() >= 5:
            fallback -= timedelta(days=1)
        dates.append(fallback)

    return dates


def determine_command_scenario(cantina: CantinaConfig, now: datetime) -> Tuple[str, List[date]]:
    now = _to_romania(now)
    today = now.date()
    weekday = today.weekday()

    if weekday >= 5:
        return "weekend", build_candidate_dates(today, include_today=False)

    current_time = now.time()
    if current_time < OPEN_TIME:
        return "before_open", build_candidate_dates(today, include_today=False)
    if current_time > cantina.close_time:
        return "after_close", build_candidate_dates(today, include_today=True)
    return "open", build_candidate_dates(today, include_today=True)


def format_human_date(target_date: date) -> str:
    return target_date.strftime("%A, %d %B %Y")


def build_menu_message(
    cantina: CantinaConfig,
    scenario: str,
    actual_date: date,
    request_date: date,
    from_cache: bool,
) -> str:
    cache_note = " (from cache)" if from_cache else ""
    actual_str = format_human_date(actual_date)

    if scenario == "weekend":
        return (
            f"{cantina.display_name} is closed during weekends. "
            f"Here’s the most recent menu from {actual_str}{cache_note}:"
        )

    if scenario == "before_open":
        return (
            f"{cantina.display_name} hasn’t opened yet today. "
            f"Here’s the latest available menu from {actual_str}{cache_note}:"
        )

    if scenario == "after_close":
        if actual_date == request_date:
            return (
                f"{cantina.display_name} is closed for today, but here’s today’s menu{cache_note}:"
            )
        return (
            f"{cantina.display_name} is closed for today. "
            f"Here’s the most recent menu from {actual_str}{cache_note}:"
        )

    if scenario == "auto":
        if actual_date == request_date:
            return f"Here’s today’s {cantina.display_name} menu{cache_note}:"
        return (
            f"Here’s the most recent {cantina.display_name} menu from {actual_str}{cache_note}:"
        )

    # default "open"
    if actual_date == request_date:
        return f"Here’s today’s {cantina.display_name} menu{cache_note}:"
    return f"Here’s the most recent {cantina.display_name} menu from {actual_str}{cache_note}:"


async def send_gif_response(
    interaction: discord.Interaction,
    message: str,
    gif_url: str,
    *,
    defer_if_needed: bool = False,
):
    embed = discord.Embed(description=message, color=discord.Color.random())
    embed.set_image(url=gif_url)
    try:
        if defer_if_needed and not interaction.response.is_done():
            await interaction.response.defer()
        if interaction.response.is_done():
            await interaction.followup.send(gif_url, embed=embed)
        else:
            await interaction.response.send_message(gif_url, embed=embed)
    except (discord.HTTPException, discord.InteractionResponded) as exc:
        logger.warning("Falling back to link for GIF %s: %s", gif_url, exc)
        fallback_content = f"{message}\n{gif_url}"
        if interaction.response.is_done():
            await interaction.followup.send(fallback_content)
        else:
            await interaction.response.send_message(fallback_content)

# ========== Auto-post Loop ==========
async def auto_post_loop():
    await bot.wait_until_ready()
    logger.info("Auto-post loop initialised. Current schedule: %s", _format_schedule(next_auto_post_at))
    while not bot.is_closed():
        try:
            async with auto_schedule_lock:
                if next_auto_post_at is None:
                    next_attempt = get_initial_auto_post_time()
                    next_auto_post_at = next_attempt
                else:
                    next_attempt = next_auto_post_at

            now = datetime.now(ROMANIA_TZ)
            next_attempt = _to_romania(next_attempt)
            delay = (next_attempt - now).total_seconds()

            if delay > 0:
                sleep_for = min(delay, 60)
                await asyncio.sleep(sleep_for)
                continue

            logger.info("Triggering scheduled menu fetch for %s", _format_schedule(next_attempt))

            channel = bot.get_channel(last_channel_id) or bot.get_channel(CHANNEL_ID)
            if channel is None and last_channel_id:
                try:
                    channel = await bot.fetch_channel(last_channel_id)
                except Exception as exc:
                    logger.error("Failed to fetch channel %s: %s", last_channel_id, exc)
                    channel = None

            cantina = CANTINAS[DEFAULT_CANTINA_KEY]
            target_date = next_attempt.date()
            candidate_dates = [target_date]

            if channel:
                success, _ = await send_menu(
                    cantina,
                    channel,
                    channel.send,
                    candidate_dates,
                    lambda actual_date, from_cache: build_menu_message(
                        cantina,
                        "auto",
                        actual_date,
                        target_date,
                        from_cache,
                    ),
                    failure_message=(
                        f"❌ Sorry, I couldn't fetch the {cantina.display_name} menu right now. Please try again later."
                    ),
                )
            else:
                success = False
                logger.error("Scheduled post skipped: channel not found (id=%s).", last_channel_id)

            if success:
                await set_next_auto_post(
                    get_next_day_auto_post_time(next_attempt),
                    "✅ Menu posted automatically.",
                )
            else:
                await set_next_auto_post(
                    get_retry_auto_post_time(now),
                    "🔁 Menu unavailable; retry scheduled.",
                )

            await asyncio.sleep(1)
        except asyncio.CancelledError:
            logger.info("Auto-post loop cancelled; exiting.")
            raise
        except Exception:
            logger.exception("Unexpected error inside auto-post loop.")
            await asyncio.sleep(60)


async def handle_menu_interaction(interaction: discord.Interaction, cantina_key: str):
    cantina = CANTINAS[cantina_key]
    now = datetime.now(ROMANIA_TZ)
    scenario, candidate_dates = determine_command_scenario(cantina, now)

    success, posted_date = await send_menu(
        cantina,
        interaction.channel,
        interaction.followup.send,
        candidate_dates,
        lambda actual_date, from_cache: build_menu_message(
            cantina,
            scenario,
            actual_date,
            now.date(),
            from_cache,
        ),
        failure_message=(
            f"❌ Sorry, I couldn't fetch the {cantina.display_name} menu right now. Please try again later."
        ),
    )

    if success and cantina.auto_post and posted_date == now.date():
        await set_next_auto_post(
            get_next_day_auto_post_time(now),
            "✅ Menu posted manually; schedule reset.",
        )

# ========== Bot Events ==========
@bot.event
async def on_ready():
    global auto_post_task, _scheduler_started
    print(f"✅ Logged in as {bot.user}")

    async with auto_schedule_lock:
        needs_initial_schedule = next_auto_post_at is None

    if needs_initial_schedule:
        await set_next_auto_post(get_initial_auto_post_time(), "🕒 Auto menu timer initialised.")

    if not _scheduler_started or auto_post_task is None or auto_post_task.done():
        auto_post_task = bot.loop.create_task(auto_post_loop())
        _scheduler_started = True
        logger.info("Auto-post scheduler task started from on_ready.")
    else:
        logger.info("Auto-post scheduler already running.")

    try:
        synced = await bot.tree.sync()  # sync slash commands
        print(f"✅ Synced {len(synced)} slash commands.")
    except Exception as e:
        print(f"❌ Error syncing commands: {e}")


@bot.event
async def on_resumed():
    logger.info(
        "Gateway session resumed. Next auto menu attempt remains at %s.",
        _format_schedule(next_auto_post_at),
    )

# ========== Prefix Commands ==========
@bot.command()
async def hello(ctx):
    await ctx.send(f"Hello {ctx.author.mention}! 👋")

@bot.command()
async def ping(ctx):
    await ctx.send("Pong!")

# ========== Slash Command ==========
@bot.tree.command(name="hello-world", description="A simple test command.")
async def hello_world(interaction: discord.Interaction):
    await interaction.response.send_message("Hello, world!")

@bot.tree.command(name="insult", description="why would you use this :<")
async def insult(interaction: discord.Interaction):
    message = random.choice(INSULT_RESPONSES)
    await send_gif_response(interaction, message, INSULT_GIF_URL)

@bot.tree.command(name="praise", description="Good job cantina-chan!")
async def praise(interaction: discord.Interaction):
    message = random.choice(PRAISE_RESPONSES)
    await send_gif_response(interaction, message, PRAISE_GIF_URL)


@bot.tree.command(name="wise-words", description="Share a bit of cantina wisdom")
async def wise_words(interaction: discord.Interaction):
    message = random.choice(WISE_SAYINGS)
    await send_gif_response(interaction, message, WISE_WORDS_GIF_URL)

@bot.tree.command(name="meniu", description="Post today’s Gaudeamus menu")
async def meniu(interaction: discord.Interaction):
    await interaction.response.defer()
    await handle_menu_interaction(interaction, "gau")


@bot.tree.command(name="meniu-gau", description="Post today’s Gaudeamus menu")
async def meniu_gau(interaction: discord.Interaction):
    await interaction.response.defer()
    await handle_menu_interaction(interaction, "gau")


@bot.tree.command(name="meniu-titu", description="Post today’s Titu Maiorescu menu")
async def meniu_titu(interaction: discord.Interaction):
    await interaction.response.defer()
    await handle_menu_interaction(interaction, "titu")


@bot.tree.command(name="meniu-aka", description="Post today’s Akademos menu")
async def meniu_aka(interaction: discord.Interaction):
    await interaction.response.defer()
    await handle_menu_interaction(interaction, "aka")

# Run the bot
bot.run(TOKEN)
