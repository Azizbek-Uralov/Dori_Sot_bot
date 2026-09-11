import bcrypt

MAX_PASSWORD_BYTES = 72


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    encoded = password.encode("utf-8")
    if len(encoded) > MAX_PASSWORD_BYTES:
        # bcrypt raises ValueError above this length instead of just rejecting
        # the password, so an over-long login attempt must be filtered out
        # here rather than reaching checkpw — otherwise it 500s instead of
        # failing like any other wrong password.
        return False
    return bcrypt.checkpw(encoded, password_hash.encode("utf-8"))
