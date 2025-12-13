import json
import random
import os

FILE = "./presents.json"
PRESENTS_NUM = 50
CODE_LENGTH = 6

# Znaky pro generování ID (malá písmena a čísla, bez matoucích znaků jako o/0, l/1/i)
ZNAKY = "abcdefghjkmnpqrstuvwxyz23456789"

def vygeneruj_kod(delka):
    return "".join(random.choices(ZNAKY, k=delka))

def main():
    data = {}
    
    print(f"Generating {PRESENTS_NUM} presents to file '{FILE}'...")

    while len(data) < PRESENTS_NUM:
        code = vygeneruj_kod(CODE_LENGTH)

        if code in data:
            continue

        data[code] = {
            "recipients": [],       # fill in names (["Father"])
            "senders": [],          # fill who is it from (např. ["John"])
            "note": "",             # A note ("Love you")
            "status": "locked",     # default status
            "question_categories": [] # optional category selection
        }

    with open(FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print("Done! Data saved.")

if __name__ == "__main__":
    main()