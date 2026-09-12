from app.constants import Language
from app.i18n.translator import t
from app.models.user import User
from bot.handlers.checkout import _full_name_prompt


def test_full_name_prompt_is_plain_for_first_time_user():
    user = User(telegram_id=1, full_name=None)

    prompt = _full_name_prompt(Language.UZ, user)

    assert prompt == t("checkout.ask_full_name", Language.UZ)
    assert "Alisher" not in prompt


def test_full_name_prompt_reminds_returning_user_of_their_previous_name_uz():
    user = User(telegram_id=2, full_name="Alisher Karimov")

    prompt = _full_name_prompt(Language.UZ, user)

    assert prompt == t("checkout.ask_full_name_previous", Language.UZ, name="Alisher Karimov")
    assert "Alisher Karimov" in prompt
    # Must not read like a static "e.g." example — it's the user's own
    # previously entered name, not a generic sample.
    assert "masalan" not in prompt.lower()


def test_full_name_prompt_reminds_returning_user_of_their_previous_name_ru():
    user = User(telegram_id=3, full_name="Алишер Каримов")

    prompt = _full_name_prompt(Language.RU, user)

    assert prompt == t("checkout.ask_full_name_previous", Language.RU, name="Алишер Каримов")
    assert "Алишер Каримов" in prompt
    assert "например" not in prompt.lower()
