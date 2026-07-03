"""Tournament host countries for the home-advantage feature (P2).

`host_ioc(tourney_name, year)` returns the host nation's IOC code, or None when the
venue is unknown/neutral. Three resolution layers:

  1. Davis Cup ties ("Davis Cup G1 R1: FRA vs GER") — the first code is the host by
     the ATP file's naming convention (verified against every WG final 1982–2018;
     two source reversals are special-cased). Names containing "Finals" are the
     post-2019 neutral-venue finals weeks (Madrid/Malaga/Seville) and resolve to
     None. Fed Cup / BJK Cup tie names carry NO host information in the WTA file
     (pre-1995 and zone-group weeks are pooled single-venue events; even World
     Group home/away ties are ordered arbitrarily, often winner-first) — all
     resolve to None rather than injecting mislabeled home flags.
  2. Year-dependent events (Olympics, Tour Finals, WTA Finals, ...) — small per-year
     dicts, since these move between countries.
  3. A normalized city/name -> IOC map (exact, then longest-substring for
     sponsor-prefixed variants like "Lexus Nottingham Open").

Unmapped names return None; the feature treats that as neutral (0/0), so the map
only ever needs to be *right*, never complete.
"""

from __future__ import annotations

import re
import unicodedata
from functools import cache

# Sources disagree on a few country codes; normalize both host and player codes
# through this before comparing.
IOC_ALIAS = {"SIN": "SGP"}

_TIE_RE = re.compile(r"\b([A-Z]{3}) vs [A-Z]{3}\b")
_TRAIL_RE = re.compile(r"( (?:\d+k?|#\d+))+$")   # "Adelaide 2", "Hua Hin #2", "... 40K"
# the two Davis Cup finals whose host order the source file reverses
_TIE_HOST_FIX = {"Davis Cup WG F: ARG vs CRO": "CRO",   # 2016, Zagreb
                 "Davis Cup WG F: BEL vs FRA": "FRA"}   # 2017, Lille


def _norm(name: str) -> str:
    s = unicodedata.normalize("NFKD", str(name))
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return _TRAIL_RE.sub("", s).strip()


def _olympics(year: int) -> str | None:
    return {1988: "KOR", 1992: "ESP", 1996: "USA", 2000: "AUS", 2004: "GRE",
            2008: "CHN", 2012: "GBR", 2016: "BRA", 2020: "JPN", 2021: "JPN",
            2024: "FRA", 2028: "USA"}.get(year)


def _atp_finals(year: int) -> str | None:
    if year <= 1995:
        return "GER"          # Frankfurt
    if year <= 1999:
        return "GER"          # Hannover
    return {2000: "POR", 2001: "AUS", 2002: "CHN", 2003: "USA", 2004: "USA"}.get(
        year, "CHN" if year <= 2008 else ("GBR" if year <= 2020 else "ITA"))


def _wta_finals(year: int) -> str | None:
    if year <= 2000:
        return "USA"          # MSG, New York
    return {2001: "GER", 2002: "USA", 2003: "USA", 2004: "USA", 2005: "USA",
            2006: "ESP", 2007: "ESP", 2008: "QAT", 2009: "QAT", 2010: "QAT",
            2011: "TUR", 2012: "TUR", 2013: "TUR", 2014: "SGP", 2015: "SGP",
            2016: "SGP", 2017: "SGP", 2018: "SGP", 2019: "CHN", 2021: "MEX",
            2022: "USA", 2023: "MEX"}.get(year, "KSA" if year >= 2024 else None)


_YEARLY = {
    "olympics": _olympics,
    "tour finals": _atp_finals,
    "atp finals": _atp_finals,
    "atp tour finals": _atp_finals,
    "masters cup": _atp_finals,
    "tennis masters cup": _atp_finals,
    "atp tour world championships": _atp_finals,
    "atp world championships": _atp_finals,
    "atp tour world championship": _atp_finals,
    "wta finals": _wta_finals,
    "wta championships": _wta_finals,
    "wta tour championships": _wta_finals,
    "virginia slims championships": _wta_finals,
    "next gen finals": lambda y: "ITA" if y <= 2022 else "KSA",
    "next gen atp finals": lambda y: "ITA" if y <= 2022 else "KSA",
    "nextgen finals": lambda y: "ITA" if y <= 2022 else "KSA",
    "tournament of champions": lambda y: "INA" if y <= 2011 else "BUL",  # Sofia from 2012
}

_BY_IOC = {
    "AUS": ["australian open", "sydney", "sydney outdoor", "sydney indoor", "brisbane",
            "hobart", "adelaide", "melbourne", "gold coast", "canberra", "hope island",
            "warrnambool", "australia circuit", "murray river open",
            "great ocean road open", "gippsland trophy", "yarra valley classic",
            "phillip island trophy", "grampians trophy", "united cup", "atp cup",
            "sydney olympics"],
    "GBR": ["wimbledon", "queen s club", "queens club", "queens", "eastbourne",
            "birmingham", "nottingham", "manchester", "bournemouth", "brighton",
            "cardiff", "london", "london olympics"],
    "USA": ["us open", "miami", "miami masters", "key biscayne", "indian wells",
            "indian wells masters", "cincinnati", "cincinnati masters", "washington",
            "washington dc", "winston salem", "delray beach", "houston", "newport",
            "atlanta", "memphis", "new haven", "san diego", "san jose", "stanford",
            "dallas", "cleveland", "austin", "new york", "new york open",
            "los angeles", "lexington", "carlsbad", "ponte vedra beach", "charleston",
            "chicago", "indianapolis", "amelia island", "philadelphia", "scottsdale",
            "hilton head", "long island", "manhattan beach", "oklahoma",
            "schenectady", "coral springs", "orlando", "oakland", "boston",
            "boca raton", "las vegas", "tampa", "san francisco", "charlotte",
            "pinehurst", "stratton mountain", "forest hills", "sarasota", "waikoloa",
            "fort worth finals", "atlanta olympics", "palm springs", "san antonio",
            "oahu", "albuquerque", "east hanover"],
    "FRA": ["roland garros", "paris", "paris masters", "marseille", "metz",
            "montpellier", "lyon", "strasbourg", "nice", "limoges", "rouen",
            "toulouse", "bordeaux", "bayonne", "paris olympics"],
    "GER": ["hamburg", "hamburg masters", "halle", "munich", "stuttgart",
            "stuttgart outdoor", "stuttgart indoor", "stuttgart masters", "berlin",
            "cologne", "nurnberg", "nuremberg", "bad homburg", "dusseldorf",
            "filderstadt", "leipzig", "essen", "hanover", "german open",
            "world team cup", "world team championship", "grand slam cup"],
    "ITA": ["rome", "rome masters", "milan", "bologna", "palermo", "florence",
            "genova", "taranto", "bolzano", "parma", "cagliari", "courmayeur",
            "sardinia", "naples", "brescia", "merano"],
    "ESP": ["madrid", "madrid masters", "barcelona", "valencia", "mallorca",
            "marbella", "tenerife", "calvia", "gijon", "zaragoza",
            "barcelona olympics"],
    "SUI": ["basel", "geneva", "gstaad", "zurich", "lugano", "biel", "lausanne",
            "lucerne"],
    "AUT": ["vienna", "kitzbuhel", "linz", "bad gastein", "st poelten",
            "poertschach", "maria lankowitz", "styria"],
    "NED": ["rotterdam", "s hertogenbosch", "rosmalen", "amsterdam", "amersfoort",
            "hilversum"],
    "BEL": ["antwerp", "brussels", "knokke heist", "hasselt", "liege"],
    "SWE": ["stockholm", "stockholm masters", "bastad"],
    "DEN": ["copenhagen"],
    "CZE": ["prague", "ostrava"],
    "SVK": ["bratislava"],
    "FIN": ["helsinki"],
    "POL": ["warsaw", "sopot", "katowice", "gdynia"],
    "RUS": ["moscow", "st petersburg", "kremlin cup"],
    "CRO": ["umag", "zagreb", "bol", "split"],
    "SLO": ["portoroz"],
    "SRB": ["belgrade", "serbia"],
    "BIH": ["banja luka"],
    "HUN": ["budapest"],
    "ROU": ["bucharest", "iasi", "cluj napoca"],
    "BUL": ["sofia"],
    "GRE": ["athens", "athens olympics"],
    "TUR": ["istanbul", "antalya"],
    "POR": ["estoril", "oeiras", "oporto", "figueira da foz"],
    "LUX": ["luxembourg"],
    "MON": ["monte carlo", "monte carlo masters"],
    "SMR": ["san marino"],
    "EST": ["tallinn"],
    "LAT": ["jurmala"],
    "ISR": ["tel aviv"],
    "QAT": ["doha"],
    "UAE": ["dubai", "abu dhabi"],
    "KSA": ["riyadh", "jeddah"],
    "MAR": ["casablanca", "marrakech", "rabat", "fes"],
    "TUN": ["monastir"],
    "RSA": ["johannesburg", "sun city", "durban"],
    "CHN": ["beijing", "shanghai", "shanghai masters", "guangzhou", "shenzhen",
            "wuhan", "tianjin", "chengdu", "nanchang", "zhengzhou", "ningbo",
            "jiujiang", "hangzhou", "zhuhai", "beijing olympics", "shenzhen finals"],
    "HKG": ["hong kong"],
    "TPE": ["taipei", "kaohsiung"],
    "JPN": ["tokyo", "tokyo outdoor", "tokyo indoor", "tokyo japan open",
            "tokyo nichirei", "tokyo pan pacific", "japan open", "japan open tokyo",
            "osaka", "hiroshima", "ibaraki", "kugayama", "tokyo olympics"],
    "KOR": ["seoul"],
    "IND": ["chennai", "pune", "kolkata", "hyderabad", "bangalore", "mumbai",
            "new delhi"],
    "VIE": ["ho chi minh city"],
    "THA": ["pattaya", "bangkok", "hua hin"],
    "MAS": ["kuala lumpur"],
    "SGP": ["singapore"],
    "INA": ["jakarta", "bali", "surabaya"],
    "UZB": ["tashkent"],
    "KAZ": ["astana", "nur sultan", "almaty"],
    "AZE": ["baku"],
    "NZL": ["auckland", "wellington"],
    "MEX": ["acapulco", "monterrey", "guadalajara", "los cabos", "merida", "m rida",
            "mexico city", "mexico circuit", "cabo san lucas", "cancun finals",
            "guadalajara finals"],
    "CAN": ["montreal", "toronto", "quebec city", "granby", "canada masters",
            "canadian open"],
    "COL": ["bogota"],
    "ECU": ["quito"],
    "CHI": ["santiago", "vina del mar"],
    "ARG": ["buenos aires", "cordoba"],
    "BRA": ["sao paulo", "rio de janeiro", "costa do sauipe", "florianopolis",
            "guaruja", "buzios", "rio olympics", "brasilia", "salvador", "maceio",
            "bahia"],
    "URU": ["montevideo"],
    "PUR": ["san juan"],
    "BER": ["bermuda"],
}
CITY_IOC = {name: ioc for ioc, names in _BY_IOC.items() for name in names}
# longest-first so "japan open tokyo" wins over "tokyo" in substring scans
_SUBSTR_KEYS = sorted(CITY_IOC, key=len, reverse=True)

# same name, different city per tour: ATP "Birmingham" (1980/1994) is Birmingham,
# Alabama; the WTA event is Edgbaston, England (the CITY_IOC default)
_PER_TOUR = {("birmingham", "atp"): "USA"}


@cache
def host_ioc(name: str, year: int, tour: str | None = None) -> str | None:
    """Host nation IOC code for a tournament name + year, or None if unknown."""
    if not isinstance(name, str) or not name:
        return None
    m = _TIE_RE.search(name)
    if m:                                    # team tie
        # host-first is only trustworthy in the ATP Davis Cup file; Fed Cup /
        # BJK Cup tie order carries no venue information (see module docstring)
        if not name.startswith("Davis Cup") or "finals" in name.lower():
            return None
        code = _TIE_HOST_FIX.get(name, m.group(1))
        return IOC_ALIAS.get(code, code)
    n = _norm(name)
    hit = _PER_TOUR.get((n, tour))
    if hit is not None:
        return hit
    fn = _YEARLY.get(n)
    if fn is not None:
        return fn(int(year))
    hit = CITY_IOC.get(n)
    if hit is not None:
        return hit
    padded = f" {n} "
    for key in _SUBSTR_KEYS:                 # sponsor-prefixed variants
        if f" {key} " in padded:
            return CITY_IOC[key]
    return None
