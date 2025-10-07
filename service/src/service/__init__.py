import json

from wordBank import LEVELS, WORD_BANK
from generator import generate_story

def main():
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

if __name__ == "__main__":
    main()