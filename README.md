# JevTest

Four small examples against [TypeSafe AI](https://typesafe.ai)'s **Jev** (`jev-1.13.0`),
a "System One" model that returns typed decisions with calibrated probabilities
instead of text.

Every example is set in the inbox of **Crust Issues**, a fictional pizza shop.

| Primitive | Ask | Returns |
|---|---|---|
| `Noul` | a yes/no proposition | `noul`: P(yes), 0 to 1. The number *is* the confidence |
| `Choice` | pick one of N options | `choice`, `probabilities`, `confidence` |
| `Score` | position on an ordered scale | `score` (expected value), `probabilities`, `confidence` |

## Setup

```bash
cp .env.example .env   # add TYPESAFE_API_KEY (and ANTHROPIC_API_KEY for example 4)
uv sync
uv run run.py          # all four
uv run run.py 3        # just example 3
```

## The examples

| # | The point | File |
|---|---|---|
| 1 | **Three primitives.** A cold margherita, surprise pineapple and a driver who ate a slice: one call returns a yes/no, a pick-one and a scale | `experiments/e1_primitives.py` |
| 2 | **Questions are nearly free.** Ask 1 question about a review, then 32: same wait, almost the same bill | `experiments/e2_fanout.py` |
| 3 | **Can you act on the confidence?** 17 inbox messages. One ask decides the route (auto, suggest, human); then each message is checked against my label and re-asked 34 times to see if the answer holds | `experiments/e3_confidence.py` |
| 4 | **Jev + an LLM.** Jev decides which document and which tool the LLM gets. The LLM writes the reply | `experiments/e4_jev_plus_llm.py` |

## What to look for

1. The raw JSON. There is no text to parse, just typed values.
2. The `ms` column stays flat as questions go from 1 to 32. Tokens grow, but slowly.
3. Whether the `auto` rows are both right (✓) and stable (100%), and whether the ✗
   marks and the flips sit in `suggest` and `human`. Then the last chart: do the
   probabilities from a single ask predict how the answer splits across 34 asks?
   Note that consistent is not the same as correct: an answer can hold 34 times and
   still disagree with my label.
4. The Garden Party question. The menu says "pesto"; only the allergen sheet says the
   pesto has walnuts. Jev's `allergy` flag is what puts that sheet in front of the LLM.
   When Jev is unsure what the customer wants, the LLM gets no tools and asks a question.
   Scale note: with 4 documents and 2 tools you could send everything; read it as a
   stand-in for 400 and 40. At this size routing buys safety, not tokens.

## Aside: Jev for judgement, Python for dates

From the original experiments (`archive/`): Jev passed 25 of 26 hard probes, including
counting and multi-hop reasoning. The one miss: an invoice issued 2026-08-09, net 45,
checked on 2026-09-22, is due *tomorrow*. Jev said "overdue" at 0.84. Extract the dates
with Jev; compare them in Python.

## Findings (run of 2026-09-30, raw output in `run_output.txt`)

### 1. Three primitives
Driver misbehaved: **0.96**. Wants: **refund** (1.00). Anger: **1.74 of 3**, between
"mildly" and "properly" annoyed, with confidence 0.63. The Score picked up the mixed
message ("Honestly I'm a little impressed. I still want my money back") instead of
forcing it into one box. 482 input tokens, $0.00002, 384 ms.

### 2. Questions are nearly free
| questions | ms (median) | input tokens | cost |
|---|---|---|---|
| 1 | 254 | 327 | $0.0000137 |
| 4 | 242 | 360 | $0.0000151 |
| 16 | 224 | 516 | $0.0000217 |
| 32 | 247 | 724 | $0.0000304 |

32x the questions: same wait, 2.2x the cost (about 13 tokens per extra question).
And it got the silly ones right: "mentions safety equipment" 0.98 (the fire
extinguisher), "uses a nickname they were called" 0.87 ("chief"), "mentions a pet" 1.00.

### 3. Can you act on the confidence?
Raw output in `run_output_confidence.txt`. 17 messages, 578 calls, $0.009.

| route | messages | right | answer held across 34 asks |
|---|---|---|---|
| auto (>= 0.99) | 6 | **6/6** | **100%** |
| suggest (0.80-0.99) | 5 | 4/5 | 100% |
| human (< 0.80) | 6 | 3/6 | 93% |

- **Above 0.80, 10 of 11 were right and none moved.** Every one of 374 re-asks gave
  the same answer as the first ask.
- **Both flips were in the human bucket, both under 0.55 confidence.** Nothing
  confident ever changed its mind.
- **The probabilities predicted the flip.** "If the driver is late again tonight, do I
  get my money back?": one ask said delivery 0.65, billing 0.35. Across 34 asks it
  picked delivery 74%, billing 26%.
- **Steady is not the same as right.** "40 minutes late and it's the wrong one" held
  delivery 34 out of 34 at 0.86; I'd labelled it kitchen. "Charged for extra cheese and
  there's no cheese" held kitchen 34 out of 34 at 0.54; I'd labelled it billing. Low
  confidence doesn't mean "this will flip"; it means "reasonable people could disagree".
- **The misses share a pattern.** Three of the four are about money (two refund
  requests and a disputed charge) but also mention a driver or the food. My house rule
  is "money goes to billing first"; Jev followed the topic instead. If a rule like that matters, write it into the option
  descriptions; Jev can't know a rule you haven't told it.

### 4. Jev + an LLM
| message | Jev picked | LLM got | LLM did |
|---|---|---|---|
| "Where is my pizza?? ... eating the box" | where_is_my_order (1.00), upset | 1 of 4 docs, 1 of 2 tools | apologised, called `track_order("4417")` |
| "Does the Garden Party have nuts?" | menu_question (1.00), allergy **0.99** | menu **+ allergen sheet** | "Yes... the pesto is made with walnuts" |
| "Order #5120 ... basically a lasagne" | refund (1.00), upset | 1 of 4 docs, 1 of 2 tools | apologised, called `issue_refund("#5120", ...)` |
| "Something's not right with my order" | other (**0.66**) | nothing, no tools | asked one clarifying question |

Jev: about 230 ms and $0.000018 per message. Claude Sonnet 5: about 2 s and $0.002.
The router costs roughly 1/100th of the call it routes.

One thing to fix in real code: the LLM passed `"4417"` to one tool and `"#5120"` to
the other. Normalise tool arguments in Python rather than trusting their format.

The original nine experiments and their findings (calibration, jaggedness, criteria
design and the rest) are kept in `archive/`.
