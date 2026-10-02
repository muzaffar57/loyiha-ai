"""Google Sheets o‘qish manbasi.

Yozish chaqiruvi yo‘q: scope faqat spreadsheets.readonly. Kalitlar logga
va istisno matniga tushmaydi. Testlar tarmoq o‘rniga opener uzatadi.
"""
import json
import logging
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable

import jwt

from app.core.config import settings
from app.services.store_sheets.errors import SheetUnavailable, SheetValidationError
from app.services.store_sheets.layout import SHEET_COLUMNS, SHEETS_SCOPE

logger = logging.getLogger(__name__)

TOKEN_URL = "https://oauth2.googleapis.com/token"
_RETRY_STATUSES = {429, 500, 502, 503, 504}
_DELAYS = (0.4, 0.8)
Opener = Callable[[str, str, dict[str, str], bytes | None, float], tuple[int, bytes]]


def urllib_opener(method: str, url: str, headers: dict[str, str], body: bytes | None, timeout: float) -> tuple[int, bytes]:
    request = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read()
    except urllib.error.URLError:
        raise SheetUnavailable() from None


class GoogleSheetSource:
    def __init__(
        self,
        *,
        spreadsheet_id: str | None = None,
        credentials_file: str | None = None,
        opener: Opener = urllib_opener,
        sleeper: Callable[[float], None] = time.sleep,
        timeout: float = 20,
    ) -> None:
        self.spreadsheet_id = spreadsheet_id if spreadsheet_id is not None else settings.STORE_SHEETS_SPREADSHEET_ID
        self.credentials_file = credentials_file if credentials_file is not None else settings.STORE_SHEETS_CREDENTIALS_FILE
        self.opener = opener
        self.sleeper = sleeper
        self.timeout = timeout

    def fetch(self) -> dict[str, list[list[str]]]:
        if not self.spreadsheet_id.strip() or not self.credentials_file.strip():
            raise SheetUnavailable("Google Sheets sozlanmagan.")
        token = self._access_token()
        tables: dict[str, list[list[str]]] = {}
        for name in SHEET_COLUMNS:
            tables[name] = self._read_sheet(name, token)
        return tables

    def _access_token(self) -> str:
        email, private_key = _load_account(self.credentials_file)
        now = int(time.time())
        assertion = jwt.encode(
            {
                "iss": email,
                "scope": SHEETS_SCOPE,
                "aud": TOKEN_URL,
                "iat": now,
                "exp": now + 3600,
            },
            private_key,
            algorithm="RS256",
        )
        if isinstance(assertion, bytes):
            assertion = assertion.decode()
        body = urllib.parse.urlencode(
            {"grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer", "assertion": assertion}
        ).encode()
        status, payload = self._request(
            "POST",
            TOKEN_URL,
            {"Content-Type": "application/x-www-form-urlencoded"},
            body,
        )
        if status != 200:
            raise SheetUnavailable("Google Sheets ruxsati rad etildi.")
        try:
            token = json.loads(payload.decode()).get("access_token")
        except (UnicodeError, json.JSONDecodeError, AttributeError):
            token = None
        if not isinstance(token, str) or not token:
            raise SheetUnavailable("Google Sheets ruxsati rad etildi.")
        return token

    def _read_sheet(self, name: str, token: str) -> list[list[str]]:
        target = urllib.parse.quote(f"{name}!A:ZZ", safe="")
        url = (
            f"https://sheets.googleapis.com/v4/spreadsheets/{urllib.parse.quote(self.spreadsheet_id, safe='')}"
            f"/values/{target}?valueRenderOption=FORMATTED_VALUE&majorDimension=ROWS"
        )
        status, payload = self._request("GET", url, {"Authorization": f"Bearer {token}"}, None)
        if status in {400, 404}:
            raise SheetValidationError([f"{name}: varaq topilmadi."])
        if status != 200:
            raise SheetUnavailable()
        try:
            data = json.loads(payload.decode() or "{}")
        except (UnicodeError, json.JSONDecodeError):
            raise SheetUnavailable() from None
        values = data.get("values") if isinstance(data, dict) else None
        if values is None:
            return []
        if not isinstance(values, list):
            raise SheetValidationError([f"{name}: varaq formati yaroqsiz."])
        table: list[list[str]] = []
        for row in values:
            if not isinstance(row, list):
                raise SheetValidationError([f"{name}: varaq formati yaroqsiz."])
            table.append([_cell_text(cell, name) for cell in row])
        return table

    def _request(self, method: str, url: str, headers: dict[str, str], body: bytes | None) -> tuple[int, bytes]:
        last_status = 0
        for attempt in range(3):
            status, payload = self.opener(method, url, headers, body, self.timeout)
            last_status = status
            if status not in _RETRY_STATUSES:
                return status, payload
            if attempt < 2:
                self.sleeper(_DELAYS[attempt])
        logger.warning("store sheet request failed status=%s", last_status)
        raise SheetUnavailable()


def _load_account(path: str) -> tuple[str, str]:
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, json.JSONDecodeError, UnicodeError):
        raise SheetUnavailable("Google Sheets hisob ma’lumoti topilmadi.") from None
    email = data.get("client_email") if isinstance(data, dict) else None
    key = data.get("private_key") if isinstance(data, dict) else None
    if not isinstance(email, str) or not isinstance(key, str) or "BEGIN PRIVATE KEY" not in key:
        raise SheetUnavailable("Google Sheets hisob ma’lumoti topilmadi.")
    return email, key


def _cell_text(cell: object, sheet: str) -> str:
    if isinstance(cell, str):
        return cell
    if cell is None:
        return ""
    raise SheetValidationError([f"{sheet}: narx kataklari matn bo‘lishi kerak."])
