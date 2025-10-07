import os
import re
import json
import sys
from typing import List, Literal, Dict, Set, Tuple
from pydantic import BaseModel, Field
from google import genai
from google.genai import types

API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    print("Missing GEMINI_API_KEY environment variable", file=sys.stderr)
    sys.exit(1)
client = genai.Client(api_key=API_KEY)

LEVELS = list("ABCDEFGH")
WORD_BANK: Dict[str, Set[str]] = {
    "A": {"boy", "girl", "dog", "cat", "see", "run", "happy", "today"},
    "B": {"boy", "girl", "dog", "cat", "see", "run", "happy", "today", "school", "friend"},
    "C": {"boy", "girl", "dog", "cat", "see", "run", "happy", "today", "school", "friend", "house", "play"},
    "D": {"boy", "girl", "dog", "cat", "see", "run", "happy", "today", "school", "friend", "house", "play", "yesterday", "park"},
    "E": {"boy", "girl", "dog", "cat", "see", "run", "happy", "today", "school", "friend", "house", "play", "yesterday", "park", "finish", "want"},
    "F": {"boy", "girl", "dog", "cat", "see", "run", "happy", "today", "school", "friend", "house", "play", "yesterday", "park", "finish", "want", "ask", "help"},
    "G": {"boy", "girl", "dog", "cat", "see", "run", "happy", "today", "school", "friend", "house", "play", "yesterday", "park", "finish", "want", "ask", "help", "because"},
    "H": {"boy", "girl", "dog", "cat", "see", "run", "happy", "today", "school", "friend", "house", "play", "yesterday", "park", "finish", "want", "ask", "help", "because", "before", "after"},
}

LEVEL_POLICY = {
    "A": {"max_tokens": 40, "max_sentences": 3},
    "B": {"max_tokens": 50, "max_sentences": 4},
    "C": {"max_tokens": 60, "max_sentences": 5},
    "D": {"max_tokens": 70, "max_sentences": 5},
    "E": {"max_tokens": 80, "max_sentences": 6},
    "F": {"max_tokens": 90, "max_sentences": 6},
    "G": {"max_tokens": 100, "max_sentences": 7},
    "H": {"max_tokens": 110, "max_sentences": 7},
}

LevelEnum = Literal["A", "B", "C", "D", "E", "F", "G", "H"]

class StoryPlan(BaseModel):
    level: LevelEnum = Field(..., description="Difficulty level A–H")
    used_words: List[str] = Field(..., description="Unique lowercase words used in order of first appearance")
    story_text: str = Field(..., description="Short story text in ASL style using only words from the allowed bank")
    sentences: List[str] | None = None

# Tokenization helpers
TOKEN_RE = re.compile(r"[A-Za-z']+")

def normalize_word(w: str) -> str:
    return w.lower()

def tokenize_text(text: str) -> List[str]:
    return [normalize_word(m.group(0)) for m in TOKEN_RE.finditer(text)]

def split_sentences(text: str) -> List[str]:
    parts = re.split(r"[.!?]+\s*", text.strip())
    return [p for p in parts if p]

# Validator enforcing closed vocabulary and difficulty caps
def validate_story(plan: StoryPlan) -> Tuple[bool, List[str], StoryPlan]:
    errors: List[str] = []
    level = plan.level
    allowed = WORD_BANK[level]

    for w in plan.used_words:
        if normalize_word(w) not in allowed:
            errors.append(f"Out-of-bank used_words item: {w}")

    # story_text tokens must all be in bank
    toks = tokenize_text(plan.story_text)
    for t in toks:
        if t not in allowed:
            errors.append(f"OOV token in story_text: {t}")

    # Difficulty caps
    policy = LEVEL_POLICY[level]
    if len(toks) > policy["max_tokens"]:
        errors.append(f"Too many tokens: {len(toks)} > {policy['max_tokens']}")
    sents = split_sentences(plan.story_text)
    if len(sents) > policy["max_sentences"]:
        errors.append(f"Too many sentences: {len(sents)} > {policy['max_sentences']}")

    # Ensure used_words reflects unique tokens in first-appearance order
    uniq = []
    seen = set()
    for t in toks:
        if t not in seen:
            uniq.append(t)
            seen.add(t)
    if [normalize_word(w) for w in plan.used_words] != uniq:
        errors.append("used_words does not match unique token order from story_text")

    # Populate sentences if missing
    if not plan.sentences:
        plan.sentences = sents

    return (len(errors) == 0, errors, plan)

# 7) Prompt templates
SYSTEM_RULES = """You generate short stories in ASL-style grammar.
Constraints:
- Only use words from the allowed word bank for the selected level.
- Keep ASL style: topic/comment ordering, early time markers, minimal function words.
- Do not use words outside the bank. Avoid punctuation-heavy English phrasing.
- Keep it simple and concise appropriate for the level.
Output JSON only, matching the schema.
"""

ASL_HINTS = "ASL style: TOPIC first if present; TIME marker early; minimal function words; simple clauses."

def build_user_instructions(topic: str, level: str, allowed_words: Set[str]) -> str:
    bullets = "\n".join(sorted(allowed_words))
    return f"""Task: Write a short ASL-style story about: "{topic}".

Difficulty level: {level}
Allowed word bank (lowercase only; use ONLY these words):
{bullets}

Return valid JSON with fields:
- level (one of A-H)
- used_words (unique lowercase words in the story, in first-appearance order)
- story_text (the story text, ASL style, only bank words)

Keep within difficulty caps and keep it engaging and clear."""

# Generation with structured output + retry loop
def generate_story(topic: str, level: str, max_retries: int = 3, model: str = "gemini-2.0-flash") -> Tuple[StoryPlan, int]:
    if level not in LEVELS:
        raise ValueError("Invalid level; must be A–H")
    allowed = WORD_BANK[level]

    base_prompt = SYSTEM_RULES + "\n" + ASL_HINTS + "\n\n" + build_user_instructions(topic, level, allowed)

    config = types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=StoryPlan,
    )

    attempt = 0
    tighten_msgs: List[str] = []
    last_errors: List[str] = []

    while attempt < max_retries:
        attempt += 1
        prompt = base_prompt if not tighten_msgs else base_prompt + "\n\n" + "\n".join(tighten_msgs)

        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config=config,
        )

        try:
            plan: StoryPlan = response.parsed
        except Exception:
            last_errors = ["Schema parse error: returned output was not valid JSON per schema"]
            tighten_msgs.append("Previous output violated the JSON schema. Return strict JSON only matching fields: level, used_words, story_text.")
            continue

        ok, errors, plan = validate_story(plan)
        if ok:
            return plan, attempt

        last_errors = errors
        tighten_msgs.append(
            "Previous output violated constraints:\n- "
            + "\n- ".join(errors)
            + "\nRegenerate strictly: use ONLY allowed words; stay under token/sentence caps; keep ASL style."
        )

    raise RuntimeError("Failed to generate a valid story after retries: " + "; ".join(last_errors))

# 9) CLI example
if __name__ == "__main__":
    # Example topic assembled from in-bank words; change as needed
    topic = input("Enter your story Topic: ").strip()
    #topic = "Suzie likes school"
    level = input("Enter text difficulty: ")
    #level = "A"

    if len(level) != 1 or level not in LEVELS:
        print("Bad Level input")
        exit(0)

    plan, attempts = generate_story(topic, level)
    print(json.dumps(plan.model_dump(), indent=2))
    print(f"Attempts: {attempts}")
