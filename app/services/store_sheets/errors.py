"""Sinxron xatolari. Xabarlarda maxfiy kalit qolmaydi."""
import re

_PEM = re.compile(r"-----BEGIN [^-]+-----.*?-----END [^-]+-----", re.DOTALL)
_SECRET_WORDS = ("private_key", "private_key_id", "client_secret", "access_token", "bearer ", "ya29.")


class SheetSyncError(Exception):
    def __init__(self, code: str, message: str) -> None:
        safe = redact(message)
        super().__init__(safe)
        self.code = code
        self.message = safe


class SheetValidationError(SheetSyncError):
    def __init__(self, errors: list[str]) -> None:
        self.errors = [redact(item) for item in errors[:50]]
        super().__init__("SHEET_VALIDATION_FAILED", "; ".join(self.errors))


class SheetUnavailable(SheetSyncError):
    def __init__(self, message: str = "Google Sheets vaqtincha ishlamayapti.") -> None:
        super().__init__("SHEET_UNAVAILABLE", message)


class SyncBusy(SheetSyncError):
    def __init__(self) -> None:
        super().__init__("SYNC_IN_PROGRESS", "Sinxronlash allaqachon ketmoqda.")


def redact(message: str) -> str:
    text = _PEM.sub("[redacted]", message or "")
    lowered = text.lower()
    if any(word in lowered for word in _SECRET_WORDS):
        return "Google Sheets sinxronlash xatosi."
    return text[:500]
