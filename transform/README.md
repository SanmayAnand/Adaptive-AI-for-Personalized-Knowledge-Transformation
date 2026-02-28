# Transform — AI Text Rewriting
### Person C works in this folder

---

## Your job in one sentence
Write one Python function: `rewrite(text, level)` that takes clean text + a user level and returns a rewritten version using AWS Bedrock (Claude AI).

## Who calls your function
`main_handler.py` (Person A's file) calls it like this:
```python
rewritten = transform.rewrite(text, 'beginner')   # or 'intermediate' or 'expert'
```
You return a rewritten string. Person A handles the rest.

---

## Setup on your laptop

```
pip install boto3
aws configure    ← run this with the keys Person A sent you
```

---

## How to test your code locally

```python
from transform import rewrite

sample = """
Photosynthesis is the process by which plants use sunlight, water, and CO2 to
produce glucose and oxygen. It occurs in the chloroplasts. The light-dependent
reactions produce ATP and NADPH. The Calvin cycle uses these to fix CO2.
"""

print("--- BEGINNER ---")
print(rewrite(sample, 'beginner'))

print("--- EXPERT ---")
print(rewrite(sample, 'expert'))
```

What good output looks like:
- **Beginner**: longer than input, plain language, "Think of it like:" analogies
- **Intermediate**: similar length to input, technical terms kept
- **Expert**: 40–60% shorter than input, dense, no basic explanations

---

## The most important part: the prompts
The 3 prompts in `PROMPTS` dict are what make this product special. Spend the most time here.
After writing them, test all 3 on the same paragraph and compare the outputs visually.

---

## When you're done
Send `transform.py` to Person A. They put it alongside `main_handler.py` and deploy together.
**The function name must stay exactly `rewrite(text, level)` — Person A imports it by that name.**
