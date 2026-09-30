"""Example 3 — Can you act on the confidence?

Jev gives every answer a confidence. This example checks the two things you'd
want that number to tell you, on the Crust Issues inbox:

  1. Is the answer right?       Compare it with the team I'd have picked.
  2. Will the answer hold?      Ask again 34 times: the identical question 10
                                times, then the four teams in all 24 orders.

The confidence from a single ask decides where the message goes:

    >= 0.99   auto      nobody looks at it
    >= 0.80   suggest   a human confirms
    <  0.80   human     a human decides

If the confidence means anything, the auto rows should be right *and* stable,
and the mistakes and flips should sit lower down.

Note: `confidence` is Jev's own measure of how sure it is. It is not the same
number as the top option's probability, so the two can differ.
"""

import itertools
from collections import Counter

from typesafe_sdk import Choice

from jevtest.lab import ask_batch, bar, header

AUTO = 0.99
SUGGEST = 0.80
REPEATS = 10

TEAMS = {
    "kitchen": "Food quality, wrong or missing items, ingredients",
    "delivery": "Late, lost or mishandled deliveries, drivers",
    "billing": "Charges, refunds, vouchers and payments",
    "other": "Jobs, press, compliments, anything else",
}

# (message, the team I'd pick first). Refund requests go to billing.
INBOX = [
    # --- clear-cut ---
    ("My pizza has no cheese on it. Not less cheese. None.", "kitchen"),
    ("I ordered a Hawaiian and got a pepperoni. I'm not complaining, just confused.", "kitchen"),
    ("Your driver has driven past my house four times. I'm waving. He's waving back.", "delivery"),
    ("The app says delivered. It was not delivered. Unless the pizza is invisible.", "delivery"),
    ("I was charged twice for one pizza.", "billing"),
    ("The voucher code SLICE10 doesn't work at checkout.", "billing"),
    ("Are you hiring? I have strong opinions about crust.", "other"),
    ("Best pizza in town. That's it, that's the message.", "other"),
    # --- messy: two problems, or a problem plus a request ---
    ("The driver dropped my pizza and it's now a calzone. Refund please.", "billing"),
    ("Pizza was 40 minutes late and it's the wrong one.", "kitchen"),
    ("You forgot the garlic bread. Can you send it or do I get money back?", "kitchen"),
    ("Can I pay the driver in cash?", "billing"),
    ("Your pizza gave my whole office food poisoning.", "kitchen"),
    ("Love the food, but why am I paying a delivery fee for pickup?", "billing"),
    ("I was charged for extra cheese and there's no cheese on it.", "billing"),
    ("The driver was rude and the pizza was stone cold.", "delivery"),
    ("If the driver is late again tonight, do I get my money back?", "billing"),
]


def question(order=TEAMS):
    return {"team": Choice(instructions="Which team should pick this up first",
                           criteria={k: TEAMS[k] for k in order})}


def route(confidence: float) -> str:
    if confidence >= AUTO:
        return "auto"
    if confidence >= SUGGEST:
        return "suggest"
    return "human"


def main() -> None:
    header("Example 3 — Confidence: right, and will it hold?")

    orders = list(itertools.permutations(TEAMS))
    per_message = REPEATS + len(orders)
    calls = [(msg, question()) for msg, _ in INBOX for _ in range(REPEATS)]
    calls += [(msg, question(o)) for msg, _ in INBOX for o in orders]
    results = ask_batch(calls)

    rows = []
    for i, (message, expected) in enumerate(INBOX):
        repeats = results[i * REPEATS:(i + 1) * REPEATS]
        start = len(INBOX) * REPEATS + i * len(orders)
        answers = [r["team"] for r in repeats + results[start:start + len(orders)]]

        first = answers[0]  # a single ask: this is all you'd normally see
        picks = Counter(a.choice for a in answers)
        held = picks[first.choice] / per_message
        rows.append({
            "message": message, "first": first, "picks": picks, "held": held,
            "route": route(first.confidence), "right": first.choice == expected,
        })

    rows.sort(key=lambda r: -r["first"].confidence)

    print(f"\n  {'route':<8} {'answer':<9} {'conf':>4}  right  "
          f"{'held across ' + str(per_message) + ' asks':<26} message")
    for r in rows:
        first = r["first"]
        right = "\033[32m ✓ \033[0m" if r["right"] else "\033[31m ✗ \033[0m"
        colour = "\033[32m" if r["held"] == 1 else "\033[31m"
        others = ", ".join(f"{t} x{n}" for t, n in r["picks"].most_common() if t != first.choice)
        print(f"  {r['route']:<8} {first.choice:<9} {first.confidence:.2f}   {right}  "
              f"{colour}{bar(r['held'], 12)} {r['held']:>4.0%}\033[0m  {r['message'][:46]}"
              + (f"\n  {'':<37}(also {others})" if others else ""))

    print(f"\n  {'bucket':<8} {'messages':>8}  {'right':>6}  {'answer held':>11}")
    for bucket in ("auto", "suggest", "human"):
        group = [r for r in rows if r["route"] == bucket]
        if group:
            right = sum(r["right"] for r in group)
            held = sum(r["held"] for r in group) / len(group)
            print(f"  {bucket:<8} {len(group):>8}  {right:>3}/{len(group):<2}  {held:>11.0%}")

    # The probabilities from ONE ask also predict where a shaky answer will flip to.
    shakiest = min(rows, key=lambda r: (r["held"], r["first"].confidence))
    first, picks = shakiest["first"], shakiest["picks"]
    print(f"\n  Shakiest: \"{shakiest['message']}\"")
    print("    probabilities from one ask     share of all asks picking it")
    for team, p in sorted(first.probabilities.items(), key=lambda kv: -kv[1]):
        share = picks[team] / per_message
        print(f"    {team:<9} {bar(p, 12)} {p:.2f}    {bar(share, 12)} {share:.0%}")

    print(f"\n  {len(results)} calls, ${sum(r.usd for r in results):.6f}")


if __name__ == "__main__":
    main()
