"""Example 2 — Ask 1 question or 32: same wait, almost the same bill.

Jev reads the message once and answers every question in the same pass.
So adding questions barely changes the time or the cost. Stop rationing them.
"""

import statistics

from typesafe_sdk import Noul

from jevtest.lab import ask, header

REVIEW = """
Ordered the Vegan Volcano. It was brilliant but so spicy my cat left the room.
Delivery took 55 minutes and the driver called me "chief". Box was soggy.
Would order again, but maybe with a fire extinguisher. 4 stars.
"""

# 32 yes/no questions about one review. Some useful, some silly. That's the point:
# when questions are nearly free, you can afford the silly ones too.
QUESTIONS = [
    "The customer liked the food",
    "The food was too spicy",
    "Delivery was late",
    "The driver was rude",
    "The packaging was damaged or soggy",
    "The customer will order again",
    "The customer wants a refund",
    "The customer mentions a pet",
    "The customer is joking at least once",
    "The review mentions a specific pizza by name",
    "The customer mentions an allergy",
    "The review gives a star rating",
    "The customer is vegan or ordered vegan food",
    "The customer mentions a price",
    "The customer mentions a discount code",
    "The customer mentions time waited",
    "The customer is angry",
    "A manager should read this",
    "This review is safe to feature on our website",
    "The customer mentions pineapple",
    "The customer mentions the temperature of the food",
    "The customer asks a question",
    "The customer mentions a competitor",
    "The review is written in English",
    "The customer mentions safety equipment",
    "The customer says the food was cold",
    "The customer mentions their family",
    "The customer uses a nickname they were called",
    "The review mentions the kitchen staff",
    "The customer praises the driver",
    "The customer threatens to leave a bad review elsewhere",
    "The customer would recommend us",
]

SIZES = [1, 2, 4, 8, 16, 32]
REPEATS = 3


def main() -> None:
    header("Example 2 — Fan-out: more questions, same call")

    print(f"\n  {'questions':>9}  {'ms (median)':>11}  {'input tokens':>12}  {'cost':>12}")
    for n in SIZES:
        questions = {f"q{i}": Noul(instructions=q) for i, q in enumerate(QUESTIONS[:n])}
        runs = [ask(REVIEW, questions) for _ in range(REPEATS)]
        ms = statistics.median(r.ms for r in runs)
        last = runs[-1]
        print(f"  {n:>9}  {ms:>11.0f}  {last.input_tokens:>12}  ${last.usd:>11.8f}")

    print("\n  All 32 answers from the last call:")
    for i, q in enumerate(QUESTIONS):
        print(f"    {last[f'q{i}'].noul:.2f}  {q}")


if __name__ == "__main__":
    main()
