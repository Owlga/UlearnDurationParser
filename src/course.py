from dataclasses import dataclass
from typing import Any

import requests

from constants import BASE_API_URL, REQUEST_TIMEOUT
from video_parser import get_slide_duration_by_api_url


@dataclass(frozen=True)
class CourseSummary:
    id: str
    title: str
    api_url: str

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> CourseSummary:
        return cls(
            id=raw["id"],
            title=raw.get("title", ""),
            api_url=raw.get("apiUrl", ""),
        )


@dataclass(frozen=True)
class Slide:
    id: str
    title: str
    api_url: str
    contains_video: bool

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> Slide:
        return cls(
            id=raw["id"],
            title=raw.get("title", ""),
            api_url=raw.get("apiUrl", ""),
            contains_video=bool(raw.get("containsVideo")),
        )


@dataclass(frozen=True)
class Unit:
    id: str
    title: str
    slides: tuple[Slide, ...]

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> Unit:
        return cls(
            id=raw["id"],
            title=raw.get("title", ""),
            slides=tuple(Slide.from_dict(s) for s in (raw.get("slides") or [])),
        )


@dataclass(frozen=True)
class Course:
    id: str
    title: str
    units: tuple[Unit, ...]

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> Course:
        return cls(
            id=raw["id"],
            title=raw.get("title", ""),
            units=tuple(Unit.from_dict(u) for u in (raw.get("units") or [])),
        )


class CourseRepository:
    def __init__(
        self,
        base_url: str = BASE_API_URL,
        session: requests.Session | None = None,
        timeout: float = REQUEST_TIMEOUT,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._session = session or requests.Session()
        self._timeout = timeout
        self._courses_cache: list[CourseSummary] = []
        self._course_cache: dict[str, Course] = {}

    def _get_json(self, path: str) -> dict[str, Any]:
        response = self._session.get(f"{self._base_url}{path}", timeout=self._timeout)
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, dict):
            raise ValueError(f"Неожиданный ответ API {path}: {type(data)}")
        return data

    def get_courses_list(self) -> list[CourseSummary]:
        if not self._courses_cache:
            data = self._get_json("/courses")
            self._courses_cache = [CourseSummary.from_dict(course) for course in (data.get("courses") or [])]
        return self._courses_cache

    def get_course(self, course_id: str, api_url: str | None = None) -> Course | None:
        if course_id not in self._course_cache:
            path = api_url or f"/courses/{course_id}"
            data = self._get_json(path)
            if data:
                self._course_cache[course_id] = Course.from_dict(data)
        if course_id in self._course_cache:
            return self._course_cache[course_id]
        return None

    def get_course_by_index(self, index: int) -> Course | None:
        courses = self.get_courses_list()
        if not 0 <= index < len(courses):
            raise IndexError(f"Курс с индексом {index} не найден (всего {len(courses)})")
        summary = courses[index]
        return self.get_course(summary.id, summary.api_url)


class CourseDurationService:
    """Длительности видео: по юниту и по всему курсу."""

    def __init__(self, repo: CourseRepository) -> None:
        self._repo = repo

    def get_courses_list(self) -> list[CourseSummary]:
        return self._repo.get_courses_list()

    def get_course_units_list(self, course_index: int) -> list[str]:
        course = self._repo.get_course_by_index(course_index)
        if course is not None:
            return [unit.title for unit in course.units]
        return []

    def get_unit_duration(self, course_index: int, unit_index: int) -> int:
        course = self._repo.get_course_by_index(course_index)
        if course is not None:
            if not 0 <= unit_index < len(course.units):
                raise IndexError(f"Юнит с индексом {unit_index} не найден " f"(всего {len(course.units)})")
            return self._get_unit_duration(course.units[unit_index])
        return 0

    def get_course_duration(self, course_index: int) -> int:
        course = self._repo.get_course_by_index(course_index)
        if course is not None:
            return sum(self._get_unit_duration(unit) for unit in course.units)
        return 0

    @staticmethod
    def _get_unit_duration(unit: Unit) -> int:
        video_slides = [s for s in unit.slides if s.contains_video and s.api_url]
        print(f"\nЮнит: {unit.title} (слайдов с видео: {len(video_slides)})")
        total = 0
        for i, slide in enumerate(video_slides, start=1):
            print(f"  [{i}/{len(video_slides)}] {slide.title} ...", end=" ", flush=True)
            duration = get_slide_duration_by_api_url(slide.api_url)
            print(f"{duration} секунд")
            total += duration
        return total
