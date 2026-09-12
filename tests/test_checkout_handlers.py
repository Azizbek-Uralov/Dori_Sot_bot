from app.constants import Language
from app.i18n import ru, uz
from app.i18n.translator import t
from bot.handlers.checkout import _full_name_prompt


def test_full_name_prompt_is_the_static_example_uz():
    prompt = _full_name_prompt(Language.UZ)

    assert prompt == t("checkout.ask_full_name", Language.UZ)
    assert "Alisher Karimov" in prompt


def test_full_name_prompt_is_the_static_example_ru():
    prompt = _full_name_prompt(Language.RU)

    assert prompt == t("checkout.ask_full_name", Language.RU)
    assert "Алишер Каримов" in prompt


def test_full_name_prompt_does_not_depend_on_any_saved_user_name():
    # The prompt takes only a language now — there is no way to pass a
    # user's saved full_name into it, so it can never be echoed back.
    import inspect

    params = list(inspect.signature(_full_name_prompt).parameters)
    assert params == ["lang"]


def test_ask_full_name_previous_key_removed():
    # The "remind returning users of their last name" feature was reverted;
    # its dedicated string must not linger unused in either language table.
    assert "checkout.ask_full_name_previous" not in uz.STRINGS
    assert "checkout.ask_full_name_previous" not in ru.STRINGS
