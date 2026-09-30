"""Shared harness for the Jev experiments: client, timing, cost, printing."""

from __future__ import annotations

import asyncio
import time
from collections.abc import Mapping, Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any

from dotenv import load_dotenv
from typesafe_sdk import (
    AsyncTypeSafeClient,
    ChoiceAnswer,
    NoulAnswer,
    ScoreAnswer,
    SystemOneResponse,
    TypeSafeClient,
)

# https://docs.typesafe.ai/models — $42 per billion input tokens, output free.
USD_PER_INPUT_TOKEN = 42 / 1_000_000_000

_client: TypeSafeClient | None = None


def client() -> TypeSafeClient:
    global _client
    if _client is None:
        load_dotenv()
        _client = TypeSafeClient()
    return _client


@dataclass
class Timed:
    response: SystemOneResponse
    ms: float

    @property
    def answers(self) -> dict[str, Any]:
        return self.response.answers

    @property
    def input_tokens(self) -> int:
        return self.response.usage.input_tokens or 0

    @property
    def usd(self) -> float:
        return self.input_tokens * USD_PER_INPUT_TOKEN

    def __getitem__(self, key: str) -> Any:
        return self.response.answers[key]


def ask(state: Any, questions: Mapping[str, Any], **kwargs: Any) -> Timed:
    start = time.perf_counter()
    response = client().system_one(state, questions, **kwargs)
    return Timed(response, (time.perf_counter() - start) * 1000)


def ask_batch(
    calls: Sequence[tuple[Any, Mapping[str, Any]]], concurrency: int = 8
) -> list[Timed]:
    """Run (state, questions) pairs concurrently."""

    async def run() -> list[Timed]:
        load_dotenv()
        limit = asyncio.Semaphore(concurrency)
        async with AsyncTypeSafeClient() as api:

            async def one(state: Any, questions: Mapping[str, Any]) -> Timed:
                async with limit:
                    start = time.perf_counter()
                    response = await api.system_one(state, questions)
                    return Timed(response, (time.perf_counter() - start) * 1000)

            return await asyncio.gather(*(one(s, q) for s, q in calls))

    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(run())
    # Already inside a running loop (Jupyter, IPython): run on a worker thread.
    with ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(asyncio.run, run()).result()


def ask_many(
    states: Sequence[Any], questions: Mapping[str, Any], concurrency: int = 8
) -> list[Timed]:
    """Same questions over many states, run concurrently."""
    return ask_batch([(s, questions) for s in states], concurrency)


def describe(answer: Any) -> str:
    """One-line human summary of any answer type."""
    if isinstance(answer, NoulAnswer):
        return f"noul={answer.noul:.3f}"
    if isinstance(answer, ChoiceAnswer):
        return f"choice={answer.choice!r} conf={answer.confidence:.3f}"
    if isinstance(answer, ScoreAnswer):
        top = max(answer.probabilities, key=answer.probabilities.get)
        return f"score={answer.score:.2f} (top level {top}) conf={answer.confidence:.3f}"
    return repr(answer)


def value_of(answer: Any) -> Any:
    """The decision itself, stripped of metadata."""
    if isinstance(answer, NoulAnswer):
        return answer.noul
    if isinstance(answer, ChoiceAnswer):
        return answer.choice
    if isinstance(answer, ScoreAnswer):
        return answer.score
    raise TypeError(f"unknown answer type: {type(answer)}")


def confidence_of(answer: Any) -> float:
    """Noul has no confidence field; distance from 0.5 is the equivalent signal."""
    if isinstance(answer, NoulAnswer):
        return abs(answer.noul - 0.5) * 2
    return answer.confidence


def header(title: str) -> None:
    print(f"\n\033[1m{title}\033[0m\n" + "-" * len(title))


def footer(t: Timed) -> None:
    print(f"\n  {t.ms:.0f} ms | {t.input_tokens} input tokens | ${t.usd:.8f}")


def bar(fraction: float, width: int = 24) -> str:
    filled = round(fraction * width)
    return "█" * filled + "·" * (width - filled)
