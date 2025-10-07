from typing import Dict, Set, Literal

LEVELS = list("ABCDEFGH")

LevelEnum = Literal["A","B","C","D","E","F","G","H"]

# Example word bank
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
