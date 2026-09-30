"""Example 1 — The three primitives.

One angry customer. One call. Three kinds of answer:

    Noul   -> a yes/no, as a probability          "Did the driver misbehave?"   0.97
    Choice -> one option from a list you define   "What do they want?"          refund
    Score  -> a position on a scale you define    "How angry are they?"         2.4 / 3

No prose to parse. Every answer is a typed value your code can use directly.
"""

import json

from typesafe_sdk import Choice, Noul, Score

from jevtest.lab import ask, footer, header

MESSAGE = """
Hi Crust Issues. I ordered a large margherita two hours ago. It arrived cold,
somehow with pineapple on it, and the driver ate a slice in front of me.
Honestly I'm a little impressed. I still want my money back though.
"""

QUESTIONS = {
    # Noul: a yes/no proposition. The number IS the confidence.
    "driver_misbehaved": Noul(instructions="The delivery driver did something wrong"),
    # Choice: pick exactly one of the options you give it.
    "wants": Choice(
        instructions="What does the customer want us to do",
        criteria={
            "refund": "Give them their money back",
            "remake": "Send a fresh pizza",
            "just_venting": "Nothing; they only want to be heard",
            "praise": "Nothing; they are happy",
        },
    ),
    # Score: where the message sits on an ordered scale you define.
    "anger": Score(
        instructions="How angry is the customer",
        criteria=[
            "Happy",
            "Mildly annoyed",
            "Properly annoyed",
            "Furious; writing a one-star review as we speak",
        ],
    ),
}


def main() -> None:
    header("Example 1 — Noul, Choice and Score in one call")

    result = ask(MESSAGE, QUESTIONS)

    noul = result["driver_misbehaved"]
    print(f"\n  Noul    driver_misbehaved  -> {noul.noul:.2f}")

    choice = result["wants"]
    print(f"  Choice  wants              -> {choice.choice!r}  (confidence {choice.confidence:.2f})")
    for option, p in sorted(choice.probabilities.items(), key=lambda kv: -kv[1]):
        print(f"            {option:<14} {p:.2f}")

    score = result["anger"]
    print(f"  Score   anger              -> {score.score:.2f} on a 0-3 scale  "
          f"(confidence {score.confidence:.2f})")

    footer(result)

    print("\n  Raw response:")
    print(json.dumps(result.response.raw_http_response.json(), indent=2))


if __name__ == "__main__":
    main()
