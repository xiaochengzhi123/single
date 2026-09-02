from pydantic import BaseModel

PROMPT_VERSION = "2026-08-v1"
MATH_CONVENTION_VERSION = "v1"
TAXONOMY_VERSION = "v1"


class MathConvention(BaseModel):
    ctft_forward: str
    ctft_inverse: str
    bilateral_laplace: str
    z_transform: str
    heaviside_at_zero: float | None


DEFAULT_CONVENTION = MathConvention(
    ctft_forward=r"X(j\omega)=\int_{-\infty}^{\infty}x(t)e^{-j\omega t}\,dt",
    ctft_inverse=(r"x(t)=\frac{1}{2\pi}\int_{-\infty}^{\infty}X(j\omega)e^{j\omega t}\,d\omega"),
    bilateral_laplace=r"X(s)=\int_{-\infty}^{\infty}x(t)e^{-st}\,dt",
    z_transform=r"X(z)=\sum_{n=-\infty}^{\infty}x[n]z^{-n}",
    heaviside_at_zero=None,
)
