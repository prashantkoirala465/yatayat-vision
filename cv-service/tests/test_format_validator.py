from app.plates.format_validator import is_plausible_plate_number


def test_accepts_plausible_devanagari_number():
    assert is_plausible_plate_number("७४५३")


def test_accepts_short_numbers():
    assert is_plausible_plate_number("२२")


def test_rejects_trailing_noise():
    # a real OCR output seen in practice - one character off from a real
    # plate number, and correctly rejected rather than silently accepted
    assert not is_plausible_plate_number("७४५३]")


def test_rejects_latin_digits():
    assert not is_plausible_plate_number("2290")


def test_rejects_empty_string():
    assert not is_plausible_plate_number("")
    assert not is_plausible_plate_number("   ")


def test_rejects_too_long():
    assert not is_plausible_plate_number("१२३४५")
