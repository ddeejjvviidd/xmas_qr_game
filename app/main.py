import os
import json
import random
import shutil
from datetime import datetime

from fastapi import FastAPI, Request, Body, Form, HTTPException, Depends, APIRouter
from fastapi.responses import HTMLResponse, RedirectResponse
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

REPEAT_QUESTIONS = False
TROLL_MODE = True
CHECK_MODE = True

CHARS = "abcdefghjkmnpqrstuvwxyz23456789"
ADMIN_SECRET = "passwd123"


async def verify_admin(request: Request):
    auth_cookie = request.cookies.get("admin_access")
    if auth_cookie != "allowed":
        raise HTTPException(status_code=403, detail="Denied.")
    return True

app_admin = APIRouter(
    dependencies=[Depends(verify_admin)]
)


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

    if not REPEAT_QUESTIONS:
        print(f'- Filtering out answered questions from total of: {len(questions)}')
        original_questions = questions.copy()
        questions = [q for q in questions if not q.get("answered", False)]
        if len(questions) == 0:
            print(f'- all questions answered, keeping original list.')
            questions = original_questions
        else:
            print(f'- Questions after filtering answered: {len(questions)}')

    if len(categories) > 0:
        print(f'- given categories\': {categories}')
        filtered_questions = [
            q for q in questions
            if any(cat in q.get("category", []) for cat in categories)
        ]
        if not filtered_questions:
            print(f'- No questions found for the given categories.')
        else:
            print(f'- Questions after filtering by categories: {len(filtered_questions)}')
            print("RETURN Random choice from specific categories.")
            return random.choice(filtered_questions)
    
    print(f'RETURN Random choice from {len(questions)}')
    return random.choice(questions)
  
def save_presents(presents):
    print("FUNC: save_presents")

    BACKUP_FILE = DATA_PRESENTS + ".bak"
    shutil.copyfile(DATA_PRESENTS, BACKUP_FILE)
    print(f'- Backup created: {BACKUP_FILE}')
    
    try:
        print(f'- Trying to save presents to {DATA_PRESENTS}')
        with open(DATA_PRESENTS, "w", encoding="utf-8") as f:
            json.dump(presents, f, indent=2, ensure_ascii=False)
        print(f'RETURN Presents saved successfully.')
    except Exception as e:
        shutil.copyfile(BACKUP_FILE, DATA_PRESENTS)
        print("ERROR Error saving presents, restored from backup.")
        raise e

def save_questions(questions):
    print("FUNC: save_questions")

    BACKUP_FILE = DATA_QUESTIONS + ".bak"
    shutil.copyfile(DATA_QUESTIONS, BACKUP_FILE)
    print(f'- Backup created: {BACKUP_FILE}')
    
    try:
        print(f'- Trying to save questions to {DATA_QUESTIONS}')
        with open(DATA_QUESTIONS, "w", encoding="utf-8") as f:
            json.dump(questions, f, indent=2, ensure_ascii=False)
        print(f'RETURN Questions saved successfully.')
    except Exception as e:
        shutil.copyfile(BACKUP_FILE, DATA_QUESTIONS)
        print("ERROR Error saving questions, restored from backup.")
        raise e

def calculate_stats(current_present, all_presents):
    print("FUNC: calculate_stats")
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
    print(f'RETURN present stats: {stats}')
    
    return stats
    
def calculate_global_stats(all_presents):
    print("FUNC: calculate_global_stats")
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

    print(f'RETURN global stats: {stats_list}')
    
    return stats_list

def reset_questions_answered():
    print(f'FUNC: reset_questions_answered')
    questions = load_questions()
    changed = False
    for q in questions:
        if q.get("answered", False):
            print(f'- Resetting question ID {q["id"]} answered status.')
            q["answered"] = False
            changed = True
    
    if changed:
        save_questions(questions)
        print(f'RETURN Questions reset completed.')
    else:
        print(f'RETURN No questions needed resetting.')

def reset_presents_locks():
    print(f'FUNC: reset_presents_locks')
    presents = load_presents()
    changed = False
    for p_id in presents:
        if presents[p_id].get("status") != "locked":
            print(f'- Locking present ID {p_id}.')
            presents[p_id]["status"] = "locked"
            changed = True
    
    if changed:
        save_presents(presents)
        print(f'RETURN Presents lock reset completed.')
    else:
        print(f'RETURN No presents needed locking.')

def generate_unique_code(existing_codes):
    print(f'FUNC: generate_unique_code')
    while True:
        code = "".join(random.choices(CHARS, k=6))
        if code not in existing_codes:
            print(f'RETURN Generated unique code: {code}')
            return code

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

    auth_cookie = request.cookies.get("admin_access")
    is_admin = (auth_cookie == "allowed")

    if(TROLL_MODE and not is_admin):
        return RedirectResponse(url=f"https://www.youtube.com/watch?v=xvFZjo5PgG0", status_code=303)
    
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

    # increment scanned_times
    current_present["scanned_times"] = current_present.get("scanned_times", 0) + 1
    save_presents(presents)

    if(CHECK_MODE and is_admin):
        return RedirectResponse(url=f'/control_page?present_id={id}#inspector-form')

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

@app.get("/overview")
async def overview_endpoint(request: Request):
    presents = load_presents()
    
    stats = calculate_global_stats(presents)
    
    return templates.TemplateResponse("overview.html", {
        "request": request,
        "stats": stats
    })

@app_admin.get("/control_page")
async def control_page_endpoint(request: Request, present_id: str = None):
    presents = load_presents()
    stats = calculate_global_stats(presents)
    
    return templates.TemplateResponse("control_page.html", {
        "request": request,
        "stats": stats,
        "present_id": present_id,
        "troll_mode": TROLL_MODE,
        "check_mode": CHECK_MODE
    })

@app_admin.get("/getPresentData/{present_id}")
async def get_present_data_endpoint(present_id: str):
    presents = load_presents()
    
    if present_id in presents:
        return {
            "found": True, 
            "data": presents[present_id]
        }
    else:
        return {
            "found": False,
            "message": f"Present '{present_id}' not found."
        }
    
@app_admin.get("/add_present")
async def add_present_page(request: Request):
    return templates.TemplateResponse("add_present.html", {
        "request": request
    })

@app_admin.get("/add_question")
async def add_question_page(request: Request):
    return templates.TemplateResponse("add_question.html", {
        "request": request
    })

@app.get("/login")
async def admin_login(k: str = None):
    if k is not None and k == ADMIN_SECRET:
        response = RedirectResponse(url="/control_page")
        response.set_cookie(
            key="admin_access", 
            value="allowed", 
            max_age=60*60*6, # 6 hours
            httponly=True
        ) 
        return response
    else:
        return HTMLResponse("<h1>Wrong pass</h1>", status_code=401)

@app.get("/logout")
async def admin_logout():
    response = HTMLResponse(content="<h1>Logged out</h1>")
    response.delete_cookie(key="admin_access")
    return response

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
        if not REPEAT_QUESTIONS:
            print("Marking question as answered")
            question["answered"] = True
            save_questions(questions)
        if present_id in presents:
            presents[present_id]["status"] = "unlocked"
            #presents[present_id]["scanned_times"] = presents[present_id].get("scanned_times", 0) + 1
            save_presents(presents)
        return {"success": True, "message": "Dárek je odemčen."}
    else:
        return {"success": False, "message": "Zkus to znovu."}
    
@app_admin.post("/control/reset_locks")
async def control_reset_locks(request: Request):
    reset_presents_locks()
    return {"success": True, "message": "All presents locked."}

@app_admin.post("/control/reset_questions")
async def control_reset_questions(request: Request):
    reset_questions_answered()
    return {"success": True, "message": "All questions reset."}

@app_admin.post("/control/reset_game")
async def control_reset_game(request: Request):
    reset_presents_locks()
    reset_questions_answered()
    return {"success": True, "message": "Complete game reset performed."}

@app_admin.post("/add_present")
async def add_present_submit(
    request: Request,
    recipients: str = Form(""),
    senders: str = Form(""),
    note: str = Form(""),
    hidden_note: str = Form(""),
    question_categories: str = Form("")
):
    presents = load_presents()
    
    new_code = generate_unique_code(presents.keys())
    
    recipients_list = [r.strip() for r in recipients.split(',') if r.strip()]
    senders_list = [s.strip() for s in senders.split(',') if s.strip()]
    categories_list = [c.strip() for c in question_categories.split(',') if c.strip()]
    
    new_present_data = {
        "recipients": recipients_list,
        "senders": senders_list,
        "note": note.strip(),
        "hidden_note": hidden_note.strip(),
        "status": "locked", 
        "created_at": datetime.utcnow().isoformat(),
        "question_categories": categories_list,
        "scanned_times": 0,
        "qr_printed": False
    }
    
    presents[new_code] = new_present_data
    save_presents(presents)
    
    print(f"Created new present: {new_code}")
    
    return RedirectResponse(url="/control_page", status_code=303)

@app_admin.post("/add_question")
async def add_question_submit(
    request: Request,
    title: str = Form(...),
    categories: str = Form(""),
    correct_index: int = Form(...),
    # Musíme explicitně definovat všech 6 inputů, protože přichází jako jednotlivá pole
    option_0: str = Form(""),
    option_1: str = Form(""),
    option_2: str = Form(""),
    option_3: str = Form(""),
    option_4: str = Form(""),
    option_5: str = Form("")
):
    questions = load_questions()
    
    if questions:
        new_id = max(q["id"] for q in questions) + 1
    else:
        new_id = 0
        
    categories_list = [c.strip() for c in categories.split(',') if c.strip()]
    
    raw_options = [option_0, option_1, option_2, option_3, option_4, option_5]
    
    final_options = []
    final_correct_index = 0
    
    if not raw_options[correct_index].strip():
        # Fallback/Error handling: if user selected an empty field as correct
        # This is a basic error handling, simply redirecting back would be better in production
        print("ERROR: Selected correct option is empty.")
        return RedirectResponse(url="/add_question", status_code=303)

    current_new_index = 0
    for i, opt in enumerate(raw_options):
        cleaned_opt = opt.strip()
        if cleaned_opt:
            final_options.append(cleaned_opt)
            if i == correct_index:
                final_correct_index = current_new_index
            current_new_index += 1
            
    # Basic validation requiring at least 2 options
    if len(final_options) < 2:
        print("ERROR: Less than 2 options provided.")
        return RedirectResponse(url="/add_question", status_code=303)

    new_question_data = {
        "id": new_id,
        "title": title.strip(),
        "options": final_options,
        "correct_option": final_correct_index,
        "category": categories_list,
        "answered": False
    }
    
    # SAVE
    questions.append(new_question_data)
    save_questions(questions)
    
    print(f"Created new question ID: {new_id}")
    
    return RedirectResponse(url="/control_page", status_code=303)

@app_admin.post("/control/toggle_troll")
async def toggle_troll_endpoint():
    global TROLL_MODE
    TROLL_MODE = not TROLL_MODE
    return {"status": "success", "new_state": TROLL_MODE}

@app_admin.post("/control/toggle_check")
async def toggle_check_endpoint():
    global CHECK_MODE
    CHECK_MODE = not CHECK_MODE
    return {"status": "success", "new_state": CHECK_MODE}

app.include_router(app_admin)