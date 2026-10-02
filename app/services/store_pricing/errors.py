"""Narx hisoblash xatolari.

Noto‘g‘ri so‘rov 500 qaytarmaydi. Kodlar API javobida ochiq ko‘rinadi.
"""


class PricingError(Exception):
    def __init__(self, code: str, message: str, status_code: int) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


def invalid(message: str) -> PricingError:
    return PricingError("INVALID_INPUT", message, 422)


def not_configured(message: str) -> PricingError:
    return PricingError("PRICE_NOT_CONFIGURED", message, 409)


def conflict(message: str) -> PricingError:
    return PricingError("CONFLICTING_RULES", message, 409)
