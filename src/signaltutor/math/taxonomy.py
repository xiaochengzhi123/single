from __future__ import annotations

TAXONOMY: dict[str, tuple[str, ...]] = {
    "signals": (
        "basic_operations",
        "periodicity",
        "energy_power",
        "even_odd_decomposition",
        "impulse_step",
        "signal_representation",
    ),
    "system_properties": ("linearity", "time_invariance", "causality", "stability", "memory"),
    "lti": ("impulse_response", "convolution", "differential_equation", "difference_equation"),
    "fourier_series": (),
    "fourier_transform": ("ctft", "dtft", "properties", "spectrum", "frequency_response"),
    "sampling": ("ideal_sampling", "nyquist", "aliasing"),
    "laplace": (
        "transform",
        "inverse_transform",
        "roc",
        "system_function",
        "initial_value",
        "final_value",
    ),
    "z_transform": ("transform", "inverse_transform", "roc", "system_function", "pole_zero"),
    "state_space": (),
}


def topic_path(chapter: str, topic: str) -> str:
    if chapter not in TAXONOMY or (TAXONOMY[chapter] and topic not in TAXONOMY[chapter]):
        raise ValueError(f"Unknown taxonomy path: {chapter}/{topic}")
    return f"{chapter}/{topic}" if topic else chapter
