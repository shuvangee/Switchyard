"""Provider adapter interface.

Every provider — mock or real — implements `Provider.generate()` and
returns a `ProviderResult`. Routing, evaluation, and experiment code call
only this interface, never a vendor SDK directly.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass


class ProviderError(Exception):
    """Raised when a provider fails to produce a response."""


@dataclass(frozen=True)
class ProviderResult:
    text: str
    input_tokens: int | None
    output_tokens: int | None
    latency_ms: float


class Provider(ABC):
    name: str

    @abstractmethod
    def generate(self, model_id: str, prompt: str) -> ProviderResult:
        """Run `prompt` against `model_id` and return the normalized result.

        Raises ProviderError on any failure (timeout, API error, malformed
        response) so callers have one exception type to handle regardless
        of provider.
        """
        raise NotImplementedError
