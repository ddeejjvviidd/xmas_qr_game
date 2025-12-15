import os
import json
import random
import shutil

from fastapi import FastAPI, Request, Body
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles


APP_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(APP_DIR)

TEMPLATES_DIR = os.path.join(APP_DIR, "templates")

DATA_PRESENTS = os.path.join(ROOT_DIR, "presents.json")
DATA_QUESTIONS = os.path.join(ROOT_DIR, "questions.json")


print(f"APP_DIR: {APP_DIR}")
print(f"ROOT_DIR: {ROOT_DIR}")
print(f"TEMPLATES_DIR: {TEMPLATES_DIR}")
print(f"DATA_PRESENTS: {DATA_PRESENTS}")
print(f"DATA_QUESTIONS: {DATA_QUESTIONS}")

app = FastAPI()

app.mount("/static", StaticFiles(directory=os.path.join(APP_DIR, "static")), name="static")
templates = Jinja2Templates(directory=TEMPLATES_DIR)


#===============================================================
#==================         FUNCTIONS         ==================
#===============================================================
def load_presents():
    with open(DATA_PRESENTS, "r", encoding="utf-8") as f:
        presents = json.load(f)
    return presents

def load_questions():
    with open(DATA_QUESTIONS, "r", encoding="utf-8") as f:
        questions = json.load(f)
    return questions

def get_random_question(questions, categories=None):
    print("FUNC: get_random_question")
    print(f'- given categories\': {categories}')

    if categories is None:
        print("RETURN Random choice without filtering")
        return random.choice(questions)
    

    filtered_questions = [
        q for q in questions
        if any(cat in q.get("category", []) for cat in categories)
    ]

    print(f'- Total questions count: {len(questions)}')
    print(f'- Filtered questions count: {len(filtered_questions)}')
    
    if not filtered_questions:
        print("RETURN No questions found for the given categories")
        return random.choice(questions)
    
    print("RETURN Questions filtered by categories")
    return random.choice(filtered_questions)

def save_presents(presents):

    BACKUP_FILE = DATA_PRESENTS + ".bak"
    shutil.copyfile(DATA_PRESENTS, BACKUP_FILE)
    
    try:
        with open(DATA_PRESENTS, "w", encoding="utf-8") as f:
            json.dump(presents, f, indent=2, ensure_ascii=False)
    except Exception as e:
        shutil.copyfile(BACKUP_FILE, DATA_PRESENTS)
        print("Error saving presents, restored from backup.")
        raise e
    finally:
        if os.path.exists(BACKUP_FILE):
            os.remove(BACKUP_FILE)

def calculate_stats(current_present, all_presents):
    """
    Goes through all the presents and counts stats for specified gift recipients.
    Returns a list of dict: [{"name": "Táta", "found": 3, "total": 5}, ...]
    """
    recipients = current_present.get("recipients", [])
    stats = []

    for person in recipients:
        found_count = 0
        total_count = 0

        for p_id, p_data in all_presents.items():
            if person in p_data.get("recipients", []):
                total_count += 1
                if p_data.get("status") == "unlocked":
                    found_count += 1
        
        stats.append({
            "name": person,
            "found": found_count,
            "total": total_count
        })
    
    return stats
    
def calculate_global_stats(all_presents):
    """
    Goes through all the presents and counts stats for unique gift recipients.
    Returns a list of dict: [{"name": "Táta", "found": 5, "total": 10}, ...]
    """
    stats_map = {}

    for p_id, p_data in all_presents.items():
        recipients = p_data.get("recipients", [])
        is_unlocked = p_data.get("status") == "unlocked"

        for person in recipients:
            if person not in stats_map:
                stats_map[person] = {
                    "name": person,
                    "found": 0,
                    "total": 0,
                    "unlocked_ids": [],
                    "locked_ids": []
                }

            stats_map[person]["total"] += 1
            
            if is_unlocked:
                stats_map[person]["found"] += 1
                stats_map[person]["unlocked_ids"].append(p_id)
            else:
                stats_map[person]["locked_ids"].append(p_id)

    stats_list = list(stats_map.values())
    
    # sort by name
    stats_list.sort(key=lambda x: x["name"])
    
    return stats_list

#===============================================================
#==================       GET ENDPOINTS       ==================
#===============================================================
@app.get("/test")
async def test_endpoint(request: Request, id: str = None):
    if id is None:
        return {"message": "No id provided"}
    print(id)
    return {"message": f"Received id: {id}"}


@app.get("/present")
async def present_endpoint(request: Request, id: str = None):
    
    # no ID
    if id is None:
        return templates.TemplateResponse("error.html", {
            "request": request,
            "message": "Neposkytnut kód dárku."
        })
    
    presents = load_presents()

    # invalid ID
    if id not in presents:
        return templates.TemplateResponse("error.html", {
            "request": request,
            "message": "Neexistuje dárek s tímto kódem."
        })
    
    current_present = presents[id]

    # present unlocked
    if current_present["status"] == "unlocked":
        stats_data = calculate_stats(current_present, presents)
        return templates.TemplateResponse("result.html", {
            "request": request,
            "present": current_present,
            "stats": stats_data
        })
    
    questions = load_questions()
    selected_question = get_random_question(questions, current_present.get("question_categories", []))
    
    # question page
    return templates.TemplateResponse("question.html", {
        "request": request,
        "present_id": id,
        "question": selected_question
    })

#===============================================================
#==================       POST ENDPOINTS      ==================
#===============================================================
@app.post("/verify_answer")
async def verify_answer(request: Request):
    # 1. Načteme JSON data z requestu do slovníku
    data = await request.json()
    
    present_id = data.get("present_id")
    question_id = data.get("question_id")
    selected_option_index = data.get("selected_option_index")

    questions = load_questions()
    presents = load_presents()
    
    # searchj for the question by ID
    question = next((q for q in questions if q["id"] == question_id), None)
    
    if not question:
        return {"success": False, "message": "Chyba otázky"}

    # validation
    is_correct = (selected_option_index == question["correct_option"])
    
    if is_correct:
        if present_id in presents:
            presents[present_id]["status"] = "unlocked"
            save_presents(presents)
        return {"success": True, "message": "Správně! Dárek je odemčen."}
    else:
        return {"success": False, "message": "Špatná odpověď, zkus to znovu."}
    
@app.get("/overview")
async def overview_endpoint(request: Request):
    presents = load_presents()
    
    stats = calculate_global_stats(presents)
    
    return templates.TemplateResponse("overview.html", {
        "request": request,
        "stats": stats
    })

@app.get("/debug_overview")
async def debug_overview_endpoint(request: Request):
    presents = load_presents()
    stats = calculate_global_stats(presents)
    
    return templates.TemplateResponse("debug_overview.html", {
        "request": request,
        "stats": stats
    })

