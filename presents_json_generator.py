import json
import random
import os

FILE = "./presents.json"
PRESENTS_NUM = 5
CODE_LENGTH = 6

CHARS = "abcdefghjkmnpqrstuvwxyz23456789"

def generate_code(length):
    return "".join(random.choices(CHARS, k=length))

def main():
    data = {}
    
    print(f"Generating {PRESENTS_NUM} presents to file '{FILE}'...")

    while len(data) < PRESENTS_NUM:
        code = generate_code(CODE_LENGTH)

        if code in data:
            continue

        data[code] = {
            "recipients": [],       # fill in names (["Father"])
            "senders": [],          # fill who is it from (např. ["John"])
            "note": "",             # A note ("Love you")
            "hidden_note": "",
            "status": "locked",     # default status
            "question_categories": [], # optional category selection
            "scanned_times": 0
        }

    with open(FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print("Done! Data saved.")

if __name__ == "__main__":
    main()