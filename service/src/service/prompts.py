from typing import Set

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
    user_instructions = f'''
    Task: Write a short ASL-style story about: "{topic}".
    Difficulty level: {level}
    Allowed word bank (lowercase only; use ONLY these words):
    {bullets}

    Return valid JSON with fields:
    - level (one of A-H)
    - used_words (unique lowercase words in the story, in first-appearance order)
    - story_text (the story text, ASL style, only bank words)

    Keep within difficulty caps and keep it engaging and clear.
    '''

    return user_instructions