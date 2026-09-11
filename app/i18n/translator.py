from app.constants import Language
from app.i18n import ru, uz

_TABLES: dict[Language, dict[str, str]] = {
    Language.UZ: uz.STRINGS,
    Language.RU: ru.STRINGS,
}


def t(key: str, lang: Language | str | None, **kwargs) -> str:
    if isinstance(lang, str):
        try:
            lang = Language(lang)
        except ValueError:
            lang = Language.UZ
    if lang is None:
        lang = Language.UZ

    table = _TABLES.get(lang, _TABLES[Language.UZ])
    template = table.get(key) or _TABLES[Language.UZ].get(key) or key
    try:
        return template.format(**kwargs)
    except (KeyError, IndexError):
        return template


def localized(obj, field: str, lang: Language | str | None) -> str:
    if isinstance(lang, str):
        try:
            lang = Language(lang)
        except ValueError:
            lang = Language.UZ
    if lang is None:
        lang = Language.UZ
    return getattr(obj, f"{field}_{lang.value}")
