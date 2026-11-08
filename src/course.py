from dataclasses import dataclass
from typing import Any

import requests

from constants import BASE_API_URL, REQUEST_TIMEOUT


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
            slides=tuple(Slide.from_dict(s) for s in raw.get("slides", [])),
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
            units=tuple(Unit.from_dict(u) for u in raw.get("units", [])),
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
        self._courses_cache: list[CourseSummary] | None = None
        self._course_cache: dict[str, Course] = {}

    def _get_json(self, path: str) -> dict[str, Any]:
        response = self._session.get(f"{self._base_url}{path}", timeout=self._timeout)
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, dict):
            raise ValueError(f"Неожиданный ответ API {path}: {type(data)}")
        return data

    def get_courses_list(self) -> list[CourseSummary]:
        if self._courses_cache is None:
            data = self._get_json("/courses")
            self._courses_cache = [CourseSummary.from_dict(course) for course in data.get("courses", [])]
        return self._courses_cache

    def get_course(self, course_id: str, api_url: str | None = None) -> Course:
        if course_id not in self._course_cache:
            path = api_url or f"/courses/{course_id}"
            data = self._get_json(path)
            self._course_cache[course_id] = Course.from_dict(data)
        return self._course_cache[course_id]

    def get_course_by_index(self, index: int) -> Course:
        courses = self.get_courses_list()
        if not 0 <= index < len(courses):
            raise IndexError(f"Курс с индексом {index} не найден (всего {len(courses)})")
        summary = courses[index]
        return self.get_course(summary.id, summary.api_url)
