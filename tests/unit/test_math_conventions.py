from signaltutor.math.conventions import DEFAULT_CONVENTION, MATH_CONVENTION_VERSION


def test_default_ctft_pair_uses_angular_frequency_convention() -> None:
    assert "2\\pi" in DEFAULT_CONVENTION.ctft_inverse
    assert "e^{-j\\omega t}" in DEFAULT_CONVENTION.ctft_forward
    assert MATH_CONVENTION_VERSION == "v1"
