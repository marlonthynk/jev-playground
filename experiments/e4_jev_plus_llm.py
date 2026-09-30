"""Example 4 — Jev decides what the LLM needs. The LLM does the talking.

The Crust Issues assistant has 4 documents and 2 tools. Instead of handing the
LLM all of them and hoping it picks well, one Jev call reads the message first:

    need     (Choice)  which job is this?          -> which tool + which document
    allergy  (Noul)    is there an allergy?        -> force-load the allergen sheet
    mood     (Score)   how upset are they?         -> how much to apologise

Then plain Python builds the prompt, and the LLM gets only what it needs.

The allergy case is the one to watch. The menu says the Garden Party has pesto.
Only the allergen sheet says the pesto is made with walnuts. Load the wrong
page and the LLM will cheerfully say "no nuts listed".

And when Jev isn't sure what the customer wants, we take the tools away and
let the LLM ask a question instead of guessing.

A note on scale: with 4 documents and 2 tools you could just send the LLM
everything. Read this as a stand-in for 400 documents and 40 tools. At this
size, what routing buys you is safety (the allergy case), not saved tokens.
"""

import os
import time

from dotenv import load_dotenv
from typesafe_sdk import Choice, Noul, Score

from jevtest.lab import ask, header

load_dotenv()

LLM_MODEL = os.environ.get("LLM_MODEL", "claude-sonnet-5")
LLM_PRICES = {"claude-sonnet-5": (2, 10), "claude-haiku-4-5-20251001": (1, 5)}  # USD / M tokens
SURE_ENOUGH = 0.80

# --- What the assistant could know --------------------------------------------

DOCS = {
    "menu": "MENU. Margherita £9: tomato, mozzarella, basil. Garden Party £11: roasted "
    "peppers, courgette, red onion, pesto, mozzarella. Hawaiian £10: ham, pineapple "
    "(we don't judge). Vegan Volcano £12: vegan cheese, jalapeños, chilli oil.",
    "allergens": "ALLERGEN SHEET. Garden Party: our pesto is made with WALNUTS, so it "
    "contains tree nuts. Vegan Volcano: contains soy. Every base contains gluten. "
    "Our kitchen handles nuts, so we cannot promise any pizza is nut-free.",
    "delivery_policy": "DELIVERY. Deliveries take 30 to 45 minutes. Orders more than 60 "
    "minutes late get a free-pizza voucher. Drivers do not accept cash.",
    "refund_policy": "REFUNDS. Full refund for cold, damaged or wrong orders reported "
    "within 24 hours. A refund needs an order number. Money is back in 3 to 5 days.",
}

# --- What the assistant could do ----------------------------------------------

TOOLS = {
    "track_order": {
        "name": "track_order",
        "description": "Look up the live status and ETA of an order.",
        "input_schema": {
            "type": "object",
            "properties": {"order_id": {"type": "string"}},
            "required": ["order_id"],
        },
    },
    "issue_refund": {
        "name": "issue_refund",
        "description": "Refund an order in full.",
        "input_schema": {
            "type": "object",
            "properties": {"order_id": {"type": "string"}, "reason": {"type": "string"}},
            "required": ["order_id", "reason"],
        },
    },
}

# Each job the customer might want -> (description for Jev, docs to load, tools to offer)
JOBS = {
    "where_is_my_order": ("Asking where their order is or when it arrives",
                          ["delivery_policy"], ["track_order"]),
    "refund": ("Wants money back for a bad, wrong or damaged order",
               ["refund_policy"], ["issue_refund"]),
    "menu_question": ("Asking about food, ingredients or prices", ["menu"], []),
    "other": ("Anything else", [], []),
}

MESSAGES = [
    "Where is my pizza?? Order #4417. It's been 50 minutes and I've started eating the box.",
    "Does the Garden Party have nuts in it? My daughter is allergic.",
    "Order #5120 arrived cold and upside down. It's basically a lasagne now. Money back please.",
    "Hi, something's not right with my order.",
]


# --- Step 1: Jev reads the message ---------------------------------------------


def read_message(message: str):
    return ask(message, {
        "need": Choice(instructions="What does the customer need",
                       criteria={job: about for job, (about, _, _) in JOBS.items()}),
        "allergy": Noul(instructions="The customer mentions a food allergy or intolerance"),
        "mood": Score(instructions="How upset is the customer",
                      criteria=["Happy or neutral", "A bit annoyed", "Very upset"]),
    })


# --- Step 2: plain Python turns Jev's answers into a plan ---------------------


def plan(answers):
    need = answers["need"]
    _, docs, tools = JOBS[need.choice]
    docs, tools, rules = list(docs), list(tools), []

    if answers["allergy"].noul > 0.5:
        docs.append("allergens")
        rules.append("The customer mentioned an allergy. Answer only from the allergen "
                     "sheet. Never guess. If it is not covered, say so.")

    if need.confidence < SURE_ENOUGH:
        tools = []
        rules.append("It is not clear what the customer needs. Ask one short clarifying "
                     "question. Do not take any action.")

    if answers["mood"].score >= 1.5:
        rules.append("The customer is upset. Start with a short, sincere apology.")

    return docs, tools, rules


# --- Step 3: the LLM writes the reply (and maybe calls a tool) ----------------


def reply(message: str, docs: list[str], tools: list[str], rules: list[str]):
    system = "\n\n".join([
        "You are the customer support assistant for Crust Issues, a pizza shop. "
        "Keep replies to two or three sentences.",
        *rules,
        *(DOCS[d] for d in docs),
    ])
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return None, system

    import anthropic

    start = time.perf_counter()
    kwargs = {"tools": [TOOLS[t] for t in tools]} if tools else {}
    response = anthropic.Anthropic().messages.create(
        model=LLM_MODEL, max_tokens=400, system=system,
        messages=[{"role": "user", "content": message}], **kwargs,
    )
    ms = (time.perf_counter() - start) * 1000
    price_in, price_out = LLM_PRICES.get(LLM_MODEL, (0, 0))
    usd = (response.usage.input_tokens * price_in + response.usage.output_tokens * price_out) / 1e6
    return (response, ms, usd), system


def main() -> None:
    header("Example 4 — Jev picks the context and the tool, the LLM talks")

    for message in MESSAGES:
        print(f"\n\033[1m> {message}\033[0m")

        jev = read_message(message)
        need = jev["need"]
        print(f"  Jev   need={need.choice} ({need.confidence:.2f})  "
              f"allergy={jev['allergy'].noul:.2f}  mood={jev['mood'].score:.1f}  "
              f"| {jev.ms:.0f} ms, ${jev.usd:.7f}")

        docs, tools, rules = plan(jev.answers)
        print(f"  Plan  docs {docs or '-'} ({len(docs)} of {len(DOCS)})  "
              f"tools {tools or '-'} ({len(tools)} of {len(TOOLS)})")
        for rule in rules:
            print(f"        rule: {rule[:80]}")

        result, system = reply(message, docs, tools, rules)
        if result is None:
            print("  (no ANTHROPIC_API_KEY in .env: this is the prompt that would be sent)")
            print("    " + system.replace("\n", "\n    "))
            continue

        response, ms, usd = result
        print(f"  LLM   {LLM_MODEL} | {ms:.0f} ms, ${usd:.6f}")
        for block in response.content:
            if block.type == "text":
                print(f"    \"{block.text.strip()}\"")
            elif block.type == "tool_use":
                print(f"    -> calls {block.name}({block.input})")


if __name__ == "__main__":
    main()
