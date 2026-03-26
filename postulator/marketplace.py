_LOCALE_TO_COUNTRY_CODE: dict[str, str] = {
    "de-DE": "DE",
    "en-GB": "UK",
    "fr-FR": "FR",
    "it-IT": "IT",
    "en-CA": "CA_EN",
    "fr-CA": "CA_FR",
    "es-ES": "ES",
    "en-US": "US",
    "en-AU": "AU",
}


def locale_to_country_code(locale: str) -> str:
    try:
        return _LOCALE_TO_COUNTRY_CODE[locale]
    except KeyError:
        raise ValueError(f"Unknown locale: {locale!r}. Known: {list(_LOCALE_TO_COUNTRY_CODE)}")


_MARKETPLACE_TO_TLD: dict[str, str] = {
    "US": "com",
    "GB": "co.uk",
    "FR": "fr",
    "DE": "de",
    "IT": "it",
    "ES": "es",
    "CA": "ca",
    "AU": "com.au",
    "IN": "in",
    "JP": "co.jp",
    "BR": "com.br",
    "MX": "com.mx",
}


def marketplace_to_tld(marketplace: str) -> str:
    try:
        return _MARKETPLACE_TO_TLD[marketplace.upper()]
    except KeyError:
        raise ValueError(f"Unknown marketplace: {marketplace!r}. Known: {list(_MARKETPLACE_TO_TLD)}")
