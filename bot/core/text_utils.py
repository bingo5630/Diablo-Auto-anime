# text_utils.py
from calendar import month_name
from datetime import datetime
from random import choice
from asyncio import sleep as asleep
from .database import db
from aiohttp import ClientSession
import xml.etree.ElementTree as ET
from anitopy import parse
from bot.core.bot_instance import bot, ani_cache
from config import Var, LOGS
from .ffencoder import ffargs
from .func_utils import handle_logs
from .reporter import rep
import os
from aiofiles.os import path as aiopath
import html  # for escaping captions

CAPTION_FORMAT = """
CAPTION_FORMAT = """
<b>➥ {title} </b>
╭━━━━━━━━━━━━━━━━━━━━━━━
<b>➣ Season: {anime_season}</b>
<b>➣ Episodes: {ep_no}</b>
<b>➣ Total Episode: {t_eps}</b>
<b>➣ Audio: Japanese [English Sub]</b>
<b>➣ Quality: Multi Quality</b>
╰━━━━━━━━━━━━━━━━━━━━━━━
<b>➥ Powered By: @Anime_Mines</b> """

GENRES_EMOJI = {
    "Action": "👊", "Adventure": choice(['🪂', '🧗‍♀️', '🗺️']), "Comedy": "🤣",
    "Drama": "🎭", "Ecchi": choice(['💋', '🥵']), "Fantasy": choice(['🧞', '🧙‍♂️', '🐉', '🌗']),
    "Hentai": "🔞", "Horror": "☠️", "Mahou Shoujo": "☯️", "Mecha": "🤖", "Mystery": "🔮",
    "Psychological": "♟️", "Romance": "💞", "Sci-Fi": "🛸", "Slice of Life": choice(['☘️', '🍁']),
    "Sports": "⚽️", "Supernatural": "🫧", "Thriller": choice(['🥶', '🔪', '🤯']),
    "Isekai": choice(['🌌', '🌀', '🧙']), "Historical": "🏯", "Music": "🎶", "Martial Arts": "🥋",
    "School": "🏫", "Military": "🎖️", "Demons": "😈", "Vampire": "🧛‍♂️", "Space": "🚀",
    "Game": "🎮", "Crime": "🚓", "Parody": "😂", "Detective": "🕵️‍♂️", "Tragedy": "💔",
    "Yaoi": "👨‍❤️‍👨", "Yuri": "👩‍❤️‍👩", "Kids": "🧒", "Harem": "👸", "Music & Idol": "🎤",
    "Post-Apocalyptic": "☢️", "Cyberpunk": "💽", "Samurai": "🗡️", "Time Travel": "⏳"
}

GENRE_NORMALIZATION = {
    "Action & Adventure": "Action",
    "Romantic Comedy": "Comedy",
    "Shounen": "Action",
    "Shoujo": "Romance",
    "Seinen": "Drama",
    "Josei": "Drama",
    "Slice-of-Life": "Slice of Life",
    "Magical Girl": "Mahou Shoujo",
    "Science Fiction": "Sci-Fi",
    "Psychological Thriller": "Psychological",
    "Suspense": "Thriller",
    "Martial-Arts": "Martial Arts",
    "Fantasy Adventure": "Fantasy",
    "Post Apocalypse": "Post-Apocalyptic",
    "Cyber Punk": "Cyberpunk",
    "Historical Drama": "Historical",
    "Romance Comedy": "Romance",
    "Action Comedy": "Action",
    "Super Power": "Supernatural",
    "Game Based": "Game",
    "Music Idol": "Music & Idol",
    "Sports Drama": "Sports",
    "Military Sci-Fi": "Military",
    "Time-Travel": "Time Travel",
    "Detective Mystery": "Detective"
}

ANIME_GRAPHQL_QUERY = """
query ($id: Int, $search: String, $seasonYear: Int) {
  Media(id: $id, type: ANIME, format_not_in: [MOVIE, MUSIC, MANGA, NOVEL, ONE_SHOT], search: $search, seasonYear: $seasonYear) {
    id
    idMal
    title {
      romaji
      english
      native
    }
    type
    format
    status(version: 2)
    description(asHtml: false)
    startDate {
      year
      month
      day
    }
    endDate {
      year
      month
      day
    }
    season
    seasonYear
    episodes
    duration
    chapters
    volumes
    countryOfOrigin
    source
    hashtag
    trailer {
      id
      site
      thumbnail
    }
    updatedAt
    coverImage {
      large
    }
    bannerImage
    genres
    synonyms
    averageScore
    meanScore
    popularity
    trending
    favourites
    studios {
      nodes {
        name
        siteUrl
      }
    }
    isAdult
    nextAiringEpisode {
      airingAt
      timeUntilAiring
      episode
    }
    airingSchedule {
      edges {
        node {
          airingAt
          timeUntilAiring
          episode
        }
      }
    }
    externalLinks {
      url
      site
    }
    siteUrl
  }
}
"""

def normalize_genres(genres: list) -> list:
    normalized = []
    for genre in genres or []:
        genre_key = GENRE_NORMALIZATION.get(genre, genre)
        if genre_key in GENRES_EMOJI:
            normalized.append(genre_key)
    return normalized

class AniLister:
    def __init__(self, anime_name: str, year: int) -> None:
        self.__api = "https://graphql.anilist.co"
        self.__ani_name = anime_name
        self.__ani_year = year
        self.__vars = {'search': self.__ani_name, 'seasonYear': self.__ani_year}

    def __update_vars(self, year: bool = True) -> None:
        if year:
            self.__ani_year -= 1
            self.__vars['seasonYear'] = self.__ani_year
        else:
            self.__vars = {'search': self.__ani_name}

    async def post_data(self):
        async with ClientSession() as sess:
            async with sess.post(self.__api, json={'query': ANIME_GRAPHQL_QUERY, 'variables': self.__vars}) as resp:
                # return status, json body, headers
                return (resp.status, await resp.json(), resp.headers)

    async def get_anidata(self):
        cache_key = f"{self.__ani_name}:{self.__ani_year}"
        if cache_key in ani_cache:
            return ani_cache[cache_key]

        res_code, resp_json, res_heads = await self.post_data()
        # Sometimes AniList returns 404 for specific season/year combos; retry with older year
        while res_code == 404 and self.__ani_year > 2020:
            self.__update_vars()
            await rep.report(f"AniList Query Name: {self.__ani_name}, Retrying with {self.__ani_year}", "warning", log=False)
            res_code, resp_json, res_heads = await self.post_data()

        # final attempt without year constraint
        if res_code == 404:
            self.__update_vars(year=False)
            res_code, resp_json, res_heads = await self.post_data()

        if res_code == 200:
            data = resp_json.get('data', {}).get('Media', {}) or {}
            ani_cache[cache_key] = data
            return data
        elif res_code == 429:
            retry_after = int(res_heads.get('Retry-After', 10))
            await asleep(retry_after * 1.5)
            return await self.get_anidata()
        elif res_code in [500, 501, 502]:
            await asleep(5)
            return await self.get_anidata()

        await rep.report(f"AniList API Error: {res_code}", "error", log=False)
        return {}

    @handle_logs
    async def _parse_anilist_data(self, data):
        # Accept both wrapped (`{'data': {'Media': {...}}}`) and raw media dict
        if not data:
            return {}
        anime = data.get("data", {}).get("Media") if isinstance(data, dict) and data.get("data") else data.get("Media") if isinstance(data, dict) and data.get("Media") else data
        if not anime:
            return {}
        genres = normalize_genres(anime.get("genres", []))
        return {
            "id": anime.get("id"),
            "idMal": anime.get("idMal"),
            "title": anime.get("title", {}),
            "status": anime.get("status", "").replace("_", " ").title(),
            "description": anime.get("description"),
            "startDate": anime.get("startDate", {}),
            "endDate": anime.get("endDate", {}),
            "episodes": anime.get("episodes"),
            "genres": genres,
            "averageScore": anime.get("averageScore"),
            "coverImage": anime.get("coverImage", {})
        }

    @handle_logs
    async def get_anilist_id(self, mal_id: int = None, name: str = None, year: int = None):
        # This method isn't used above but kept for convenience elsewhere
        if mal_id:
            variables = {'idMal': mal_id}
        else:
            variables = {'search': name, 'seasonYear': year} if year else {'search': name}

        # update self.__vars temporarily for the request
        prev_vars = self.__vars.copy()
        try:
            self.__vars = variables
            res_code, resp_json, res_heads = await self.post_data()
        finally:
            self.__vars = prev_vars

        if res_code == 200 and resp_json.get('data', {}).get('Media'):
            return resp_json['data']['Media']['id']
        elif res_code == 429:
            f_timer = int(res_heads.get('Retry-After', 10))
            await rep.report(f"AniList ID Fetch Rate Limit: Sleeping for {f_timer}s", "error")
            await asleep(f_timer)
            return await self.get_anilist_id(mal_id, name, year)
        await rep.report(f"Failed to fetch AniList ID for {name or mal_id}", "error")
        return None


class TextEditor:
    def __init__(self, name):
        self.__name = name
        self.adata = {}
        self.pdata = parse(name)
        self.anilister = AniLister(self.__name, datetime.now().year)

    async def load_anilist(self):
        cache_names = set()
        # try combinations: title only / title+year / title+season / title+season+year
        for no_s, no_y in [(False, False), (False, True), (True, False), (True, True)]:
            ani_name = await self.parse_name(no_s, no_y)
            if not ani_name or ani_name in cache_names:
                continue
            cache_names.add(ani_name)
            # set anilister search and fetch
            self.anilister._AniLister__ani_name = ani_name
            self.anilister._AniLister__vars['search'] = ani_name
            self.adata = await self.anilister.get_anidata()
            if self.adata:
                break

    @handle_logs
    async def parse_name(self, no_s=False, no_y=False):
        anime_name = self.pdata.get("anime_title") or self.__name
        anime_season = self.pdata.get("anime_season")
        anime_year = self.pdata.get("anime_year")
        if anime_name:
            pname = anime_name
            if not no_s and self.pdata.get("episode_number") and anime_season:
                pname += f" {anime_season}"
            if not no_y and anime_year:
                pname += f" {anime_year}"
            return pname
        return anime_name

    @handle_logs
    async def get_poster(self):
        anime_id = self.adata.get("id")

        # 1. Channel-specific poster from DB (setchannel)
        if anime_id:
            channel_poster = await db.get_custom_poster(anime_id)
            if channel_poster and await aiopath.exists(channel_poster):
                return channel_poster

        # 2. Custom poster from DB (setposter) - this might be a Telegram file_id
        anime_name_from_pdata = (self.pdata or {}).get("anime_title")
        if anime_name_from_pdata:
            custom_poster = await db.get_anime_poster(anime_name_from_pdata)
            if custom_poster:
                return custom_poster

        # 3. Special case banner
        if Var.ANIME in self.__name:
            return Var.CUSTOM_BANNER

        # 4. AniList fallback
        if anime_id and str(anime_id).isdigit():
            return f"https://img.anili.st/media/{anime_id}"

        # 5. Final fallback image
        return "https://envs.sh/YsH.jpg"

    @handle_logs
    async def get_upname(self, qual=""):
        anime_name = self.pdata.get("anime_title")
        ff = ffargs.get(qual, "")
        codec = 'HEVC' if 'libx265' in ff else 'AV1' if 'libaom-av1' in ff else ''
        lang = 'SUB' if 'sub' in self.__name.lower() else 'Sub'
        ani_s = self.pdata.get('anime_season', '01')
        anime_season = str(ani_s[-1]) if isinstance(ani_s, list) else str(ani_s)
        if anime_name and self.pdata.get("episode_number"):
            titles = self.adata.get('title', {})
            english = titles.get('english') or titles.get('romaji') or titles.get('native') or anime_name
            ep_part = 'E'+str(self.pdata.get('episode_number')) if self.pdata.get('episode_number') else ''
            qual_part = f"[{qual}p]" if qual else ''
            codec_part = f"[{codec.upper()}] " if codec else ''
            lang_part = f"[{lang}]"
            filename = f"[S{anime_season}-{ep_part}] {english} {qual_part} {codec_part}{lang_part} {Var.BRAND_UNAME}.mkv"
            return " ".join(filename.split())  # clean extra spaces
        return None

    @handle_logs
    async def get_caption(self):
        # Start / End dates
        sd = self.adata.get('startDate', {}) or {}
        try:
            month_idx = int(sd.get('month')) if sd.get('month') else None
            startdate = (
                f"{month_name[month_idx]} {sd['day']}, {sd['year']}"
                if sd.get('day') and sd.get('year') and month_idx
                else "N/A"
            )
        except (ValueError, TypeError, IndexError):
            startdate = "N/A"

        ed = self.adata.get('endDate', {}) or {}
        try:
            month_idx = int(ed.get('month')) if ed.get('month') else None
            enddate = (
                f"{month_name[month_idx]} {ed['day']}, {ed['year']}"
                if ed.get('day') and ed.get('year') and month_idx
                else "N/A"
            )
        except (ValueError, TypeError, IndexError):
            enddate = "N/A"

        titles = self.adata.get("title", {}) or {}
        raw_title = titles.get('english') or titles.get('romaji') or titles.get('native') or "Unknown Title"

        # Prepare plot/description and trim safely
        raw_desc = self.adata.get("description") or "No description available."
        desc = raw_desc.strip()
        # AniList may include HTML entities; we keep them but escape before sending
        if len(desc) > 350:
            desc = desc[:350].rsplit(" ", 1)[0] + "..."

        # Genres to emoji+hashtag string
        genres_list = self.adata.get('genres') or []
        # if normalize wasn't run, normalize here
        genres_list = normalize_genres(genres_list) if genres_list and not all(g in GENRES_EMOJI for g in genres_list) else genres_list
        if genres_list:
            genres_str = ", ".join(f"{GENRES_EMOJI.get(g, '')} #{g.replace(' ', '_').replace('-', '_')}" for g in genres_list)
            genres_str = genres_str or "N/A"
        else:
            genres_str = "N/A"

        # Season parsing from parsed data
        ani_s = self.pdata.get('anime_season', '01')
        anime_season = str(ani_s[-1]) if isinstance(ani_s, list) else str(ani_s)

        # average score formatting
        avg_score_val = self.adata.get('averageScore')
        avg_score = f"{avg_score_val}%" if avg_score_val is not None else "N/A"
        status = self.adata.get("status") or "N/A"
        total_eps = self.adata.get("episodes") or "N/A"
        ep_no = self.pdata.get("episode_number") or "N/A"

        # HTML-escape all dynamic fields to keep Telegram parse_mode=HTML safe
        safe = lambda s: html.escape(str(s)) if s is not None else "N/A"

        caption = CAPTION_FORMAT.format(
            title=safe(raw_title),
            anime_season=safe(anime_season),
            ep_no=safe(ep_no),
            t_eps=safe(total_eps),
            status=safe(status),
            avg_score=safe(avg_score),
            genres=safe(genres_str),
            plot=safe(desc),
            cred=safe(Var.BRAND_UNAME),
        ).strip()

        return caption
        
