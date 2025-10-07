# generator.py

import os
import re
from typing import List, Literal, Tuple
from pydantic import BaseModel, Field
from google import genai
from google.genai import types

from prompts import SYSTEM_RULES, ASL_HINTS, build_user_instructions
from wordBank import LEVELS, WORD_BANK, LEVEL_POLICY, LevelEnum

class StoryPlan(BaseModel):
    level: LevelEnum = Field(..., description="Difficulty level A–H")
    used_words: List[str] = Field(..., description="Unique lowercase words used in order of first appearance")
    story_text: str = Field(..., description="Short story text in ASL style using only words from the allowed bank")
    sentences: List[str] | None = None

# Tokenization and sentence helpers
TOKEN_RE = re.compile(r"[A-Za-z']+")

def normalize_word(w: str) -> str:
    return w.lower()

def tokenize_text(text: str) -> List[str]:
    return [normalize_word(m.group(0)) for m in TOKEN_RE.finditer(text)]

def split_sentences(text: str) -> List[str]:
    parts = re.split(r"[.!?]+\s*", text.strip())
    return [p for p in parts if p]

def validate_story(plan: StoryPlan) -> Tuple[bool, List[str], StoryPlan]:
    errors: List[str] = []
    level = plan.level
    allowed = WORD_BANK[level]

    for w in plan.used_words:
        if normalize_word(w) not in allowed:
            errors.append(f"Out-of-bank used_words item: {w}")

    # tokens must all be in bank
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

_client: genai.Client | None = None

def get_client() -> genai.Client:
    global _client
    if _client is None:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("Missing GEMINI_API_KEY environment variable")
        _client = genai.Client(api_key=api_key)
    return _client

# output + retry loop
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

    client = get_client()

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
