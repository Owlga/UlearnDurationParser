import re
from dataclasses import dataclass
from typing import Any

import requests
import yt_dlp

from constants import BASE_API_URL, BASE_YT_URL, REQUEST_TIMEOUT


class YTDLPLogger:
    """убираем весь вывод ютуб-парсера"""

    def debug(self, msg: str) -> None:
        pass

    def warning(self, msg: str) -> None:
        pass

    def error(self, msg: str) -> None:
        pass


class DurationParser:
    """Парсер для длительности видео"""

    _ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'skip_download': True,
        'logger': YTDLPLogger(),
    }

    @staticmethod
    def get_video_duration(video_url: str) -> int:
        """Длительность видео по URL, поддерживает и YT, и VK"""
        try:
            with yt_dlp.YoutubeDL(DurationParser._ydl_opts) as ydl:
                info = ydl.extract_info(video_url, download=False)
                if not info:
                    return 0
                duration = info.get('duration')
                return int(duration) if duration else 0
        except yt_dlp.utils.DownloadError as e:
            print(f"Не удалось получить длительность {video_url}: {e}")
            return 0


class UrlBuilder:
    """Методы для собирания URL для видео в YT и VK"""

    _yt_regex: re.Pattern[str] = re.compile(r'[0-9A-Za-z_-]{11}')
    _yt_regex_full: re.Pattern[str] = re.compile(r'(?:v=|/|embed/)([0-9A-Za-z_-]{11})')

    @staticmethod
    def clean_yt_id(raw_string: str | None) -> str | None:
        """Достаём регуляркой id из ссылки"""
        if not isinstance(raw_string, str) or not raw_string:
            return None
        if UrlBuilder._yt_regex.fullmatch(raw_string):
            return raw_string
        match = UrlBuilder._yt_regex_full.search(raw_string)
        return match.group(1) if match else None

    @staticmethod
    def create_yt_url(video_id: str | None) -> str | None:
        """Собираем URL для YT"""
        clean_id = UrlBuilder.clean_yt_id(video_id)
        return f"{BASE_YT_URL.rstrip('/')}{clean_id}" if clean_id else None

    @staticmethod
    def create_vk_url(vk_id: str | None, vk_oid: str | None, vk_hash: str | None) -> str | None:
        """Собираем URL для Vk"""
        if vk_id is None or vk_oid is None:
            return None

        url = f'https://vk.com/video{vk_oid}_{vk_id}'
        if vk_hash:
            url += f'?hash={vk_hash}'
        return url


@dataclass(frozen=True)
class Block:
    """Один блок слайда. Нас интересуют только видео-поля."""

    video_id: str | None
    vk_id: str | None
    vk_oid: str | None
    vk_hash: str | None

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> Block:
        return cls(
            video_id=raw.get("videoId"),
            vk_id=raw.get("vkId"),
            vk_oid=raw.get("vkOid"),
            vk_hash=raw.get("vkHash"),
        )

    @property
    def has_video(self) -> bool:
        return bool(self.video_id or self.vk_id)


class VideoInfo:
    """Класс для информации про одно видео"""

    def __init__(self, block: Block) -> None:
        self._yt_url = UrlBuilder.create_yt_url(block.video_id)
        self._vk_url = UrlBuilder.create_vk_url(
            block.vk_id,
            block.vk_oid,
            block.vk_hash,
        )

    @property
    def yt_url(self) -> str | None:
        return self._yt_url

    @property
    def vk_url(self) -> str | None:
        return self._vk_url

    def get_duration(self) -> int:
        """Длительность видео"""
        if self._yt_url:
            duration = DurationParser.get_video_duration(self._yt_url)
            if duration:
                return duration

        if self._vk_url:
            return DurationParser.get_video_duration(self._vk_url)

        return 0


def get_slide_duration_from_blocks(blocks: list[Block]) -> int:
    """Суммарная длительность видео по блокам слайда. Без сети."""
    return sum(VideoInfo(block).get_duration() for block in blocks if block.has_video)


def get_slide_duration_by_api_url(api_url: str) -> int:
    """Суммарная длительность видео на слайде."""
    try:
        response = requests.get(BASE_API_URL + api_url, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as e:
        print(f"Ошибка при запросе {api_url}: {e}")
        return 0
    except ValueError as e:
        print(f"Некорректные данные от {api_url}: {e}")
        return 0
    if not isinstance(data, dict):
        print(f"Неожиданный ответ API {api_url}: {type(data)}")
        return 0

    raw_blocks = data.get("blocks") or []
    blocks = [Block.from_dict(b) for b in raw_blocks if isinstance(b, dict)]
    return get_slide_duration_from_blocks(blocks)
