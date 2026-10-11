"""GSTIN generator and validator according to SPEC §5."""

import random
import re

GSTIN_REGEX = re.compile(r"^[0-3][0-9][A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]$")
CHARS = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
CHAR_MAP = {c: i for i, c in enumerate(CHARS)}

STATE_CODES = [f"{i:02d}" for i in range(1, 39)]

CITY_TO_STATE_CODE = {
    "Mumbai": "27",
    "Pune": "27",
    "Bengaluru": "29",
    "Bangalore": "29",
    "Delhi": "07",
    "New Delhi": "07",
    "Gurugram": "06",
    "Gurgaon": "06",
    "Noida": "09",
    "Chennai": "33",
    "Hyderabad": "36",
    "Kolkata": "19",
    "Ahmedabad": "24",
    "Jaipur": "08",
}


def calculate_gstin_checksum(chars_14: str) -> str:
    """Calculate the 15th check character for the given 14-character GSTIN prefix."""
    if len(chars_14) != 14:
        raise ValueError(f"Expected 14 characters, got {len(chars_14)}")
    s = 0
    for i in range(14):
        char = chars_14[i]
        if char not in CHAR_MAP:
            raise ValueError(f"Invalid character in GSTIN prefix: {char}")
        v = CHAR_MAP[char]
        p = v * (1 if i % 2 == 0 else 2)
        s += (p // 36) + (p % 36)
    check_val = (36 - (s % 36)) % 36
    return CHARS[check_val]


def validate_gstin(gstin: str) -> bool:
    """Validate GSTIN format, state code (01-38), and checksum character."""
    if not isinstance(gstin, str):
        return False
    if not GSTIN_REGEX.match(gstin):
        return False
    state_code = int(gstin[:2])
    if not (1 <= state_code <= 38):
        return False
    return gstin[14] == calculate_gstin_checksum(gstin[:14])


def generate_synthetic_gstin(
    state_code: str | None = None,
    city: str | None = None,
    rng: random.Random | None = None,
) -> str:
    """Generate a valid synthetic GSTIN that passes SPEC §5 checksum."""
    r = rng or random.Random()
    if state_code is None:
        if city and city in CITY_TO_STATE_CODE:
            state_code = CITY_TO_STATE_CODE[city]
        else:
            state_code = r.choice(STATE_CODES)

    # PAN format: 5 uppercase letters, 4 digits, 1 uppercase letter
    letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    pan_letters_1 = "".join(r.choices(letters, k=5))
    pan_digits = f"{r.randint(0, 9999):04d}"
    pan_letter_2 = r.choice(letters)
    entity_code = r.choice("123456789" + letters)  # 1-9 or A-Z
    constant_z = "Z"

    prefix = f"{state_code}{pan_letters_1}{pan_digits}{pan_letter_2}{entity_code}{constant_z}"
    checksum = calculate_gstin_checksum(prefix)
    return f"{prefix}{checksum}"
