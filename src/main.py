import click
import requests

from course import CourseDurationService, CourseRepository


def format_duration(seconds: float) -> str:
    seconds = round(seconds)
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    if m:
        return f"{m}:{s:02d}"
    return f"{s}с"


def get_service() -> CourseDurationService:
    return CourseDurationService(CourseRepository())


@click.group()
def cli() -> None:
    """Утилита для работы с курсами ulearn.me."""


@cli.command("courses")
def list_courses() -> None:
    service = get_service()
    try:
        courses = service.get_courses_list()
    except requests.HTTPError as e:
        raise click.ClickException(f"Ошибка API: {e}")
    except requests.RequestException as e:
        raise click.ClickException(f"Ошибка сети: {e}")
    for i, course in enumerate(courses):
        click.echo(f"[{i}] {course.title}")


@cli.command("units")
@click.argument("course_index", type=int)
def list_units(course_index: int) -> None:
    """Показать юниты курса по индексу COURSE_INDEX."""
    service = get_service()
    try:
        units = service.get_course_units_list(course_index)
    except IndexError as e:
        raise click.ClickException(str(e))
    for i, title in enumerate(units):
        click.echo(f"[{i}] {title}")


@cli.command("unit-duration")
@click.argument("course_index", type=int)
@click.argument("unit_index", type=int)
@click.option(
    '-s',
    '--speed',
    type=click.FloatRange(min=0.01, min_open=True),
    default=1.0,
    help='Скорость воспроизведения (например, 1.5)',
)
def unit_duration(course_index: int, unit_index: int, speed: float) -> None:
    """Длительность юнита UNIT_INDEX курса COURSE_INDEX."""
    service = get_service()
    try:
        seconds = service.get_unit_duration(course_index, unit_index)
    except IndexError as e:
        raise click.ClickException(str(e))
    click.echo(format_duration(seconds / speed))


@cli.command("course-duration")
@click.argument("course_index", type=int)
@click.option(
    '-s',
    '--speed',
    type=click.FloatRange(min=0.01, min_open=True),
    default=1.0,
    show_default=True,
    help='Скорость воспроизведения (например, 1.5)',
)
def course_duration(course_index: int, speed: float) -> None:
    """Длительность всего курса COURSE_INDEX."""
    service = get_service()
    try:
        seconds = service.get_course_duration(course_index)
    except IndexError as e:
        raise click.ClickException(str(e))
    click.echo(format_duration(seconds / speed))


@cli.command("interactive")
@click.option(
    '-s',
    '--speed',
    type=click.FloatRange(min=0.01, min_open=True),
    default=1.0,
    show_default=True,
    help='Скорость воспроизведения по умолчанию (например, 1.5)',
)
def interactive(speed: float) -> None:
    """Интерактивный выбор курса и юнита (кэш живёт весь сеанс)."""
    service = get_service()

    courses = service.get_courses_list()
    for i, c in enumerate(courses):
        click.echo(f"[{i}] {c.title}")

    while True:
        course_index = click.prompt("Курс (Enter — выход)", type=int, default=-1)
        if course_index < 0:
            break

        try:
            units = service.get_course_units_list(course_index)
        except IndexError as e:
            click.echo(f"Ошибка: {e}", err=True)
            continue

        click.echo()
        for i, title in enumerate(units):
            click.echo(f"  [{i}] {title}")

        unit_index = click.prompt("Юнит", type=int)
        try:
            unit_sec = service.get_unit_duration(course_index, unit_index)
        except IndexError as e:
            click.echo(f"Ошибка: {e}", err=True)
            continue

        user_speed = click.prompt(
            "Скорость воспроизведения",
            type=click.FloatRange(min=0.01, min_open=True),
            default=speed,
            show_default=True,
        )

        click.echo(f"Длительность юнита: {format_duration(unit_sec / user_speed)}")

        if click.confirm("Посчитать длительность всего курса?", default=False):
            course_sec = service.get_course_duration(course_index)
            click.echo(f"Длительность курса: {format_duration(course_sec / user_speed)}")

        if not click.confirm("Продолжить?", default=True):
            break


if __name__ == "__main__":
    cli()
