import asyncio, logging, os, time
from contextlib import asynccontextmanager
from collections import defaultdict, deque
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from alerts import emit
from demo_data import EVAL_TICKETS, burst_messages
from impact import estimate
from spike import detect, normalize_theme
from triage import DailyQuotaExhausted, available_model, classify, configure_limiter, make_client

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
load_dotenv()
tickets=[]; spikes=[]; alerts=[]; critical_alerted={}; last_eval=None; tasks=set(); client=None; model_in_use=""
progress={"task":None,"done":0,"total":0,"status":"idle","eta_seconds":0,"wait_seconds":0}
batch_running=False

def config():
    key=os.environ.get("GEMINI_API_KEY", "")
    if not key or key == "PASTE_YOUR_GEMINI_API_KEY_HERE": raise RuntimeError("GEMINI_API_KEY is missing or is still a placeholder.")
    return {"key":key,"model":os.environ.get("GEMINI_MODEL","gemini-3.1-flash-lite"),"rpm":int(os.environ.get("GEMINI_RPM_LIMIT","15")),"daily":int(os.environ.get("GEMINI_DAILY_LIMIT","500")),"sample":int(os.environ.get("EVAL_SAMPLE_SIZE","50")),"threshold":int(os.environ.get("SPIKE_THRESHOLD","8")),"window":int(os.environ.get("SPIKE_WINDOW_SECONDS","600")),"manual_minutes":float(os.environ.get("MANUAL_MINUTES_PER_TICKET","4")),"webhook":os.environ.get("SLACK_WEBHOOK_URL","")}

@asynccontextmanager
async def lifespan(app):
    global client, model_in_use
    settings=config(); client=make_client(settings["key"]); configure_limiter(settings["rpm"], settings["daily"])
    model_in_use=available_model(client, settings["model"]); print(f"QZero Gemini model in use: {model_in_use}")
    yield
    if client: await client.aio.aclose()
app=FastAPI(title="QZero", lifespan=lifespan)
class TicketInput(BaseModel): text:str=Field(min_length=3,max_length=10000)
def add_task(coro):
    task=asyncio.create_task(coro); tasks.add(task); task.add_done_callback(tasks.discard)
def update_eta(): progress["eta_seconds"]=round(max(0,progress["total"]-progress["done"])*4.2/10)*10
def waiting(seconds):
    progress.update(status="rate_limit_wait",wait_seconds=round(seconds)); update_eta()
def running(): progress.update(status="running",wait_seconds=0); update_eta()
async def finish(status="done"):
    global batch_running
    progress.update(status=status,wait_seconds=0,eta_seconds=0); batch_running=False
    await asyncio.sleep(10)
    if progress["status"]==status: progress.update(task=None,done=0,total=0,status="idle",eta_seconds=0,wait_seconds=0)
async def refresh_spikes():
    global spikes
    settings=config(); spikes,new=detect(tickets,spikes,settings["threshold"],settings["window"],time.time())
    for spike in new: await emit(alerts,"spike",f"Spike detected: {spike['count']} tickets about {spike['theme']}",settings["webhook"])
async def classify_ticket(ticket, track=False):
    try:
        result=await classify(client,model_in_use,ticket["text"],waiting if track else None)
        ticket.update(result.model_dump(),classified_at=time.time(),status="triaged")
        theme=normalize_theme(ticket["theme"]); settings=config()
        if ticket["urgency"]=="critical" and time.time()-critical_alerted.get(theme,0)>=600:
            critical_alerted[theme]=time.time(); await emit(alerts,"critical",f"Critical ticket: {ticket['summary']} ({theme})",settings["webhook"])
        await refresh_spikes(); return result
    except DailyQuotaExhausted:
        ticket["status"]="quota_exhausted"; raise
    except Exception as exc:
        logging.exception("Ticket %s failed classification",ticket["id"]); ticket.update(status="failed",error=str(exc)); return None
    finally:
        if track: progress["done"]+=1; running()
def new_ticket(text,source,ticket_id=None):
    ticket={"id":ticket_id or f"live-{len(tickets)+1}","text":text,"source":source,"received_at":time.time(),"status":"pending"}; tickets.append(ticket); return ticket
def sample_eval(size):
    if size>=len(EVAL_TICKETS): return EVAL_TICKETS
    groups=defaultdict(deque)
    for row in EVAL_TICKETS: groups[row[1]].append(row)
    chosen=[]
    while len(chosen)<size and groups:
        for category in list(groups):
            if len(chosen)>=size: break
            if groups[category]: chosen.append(groups[category].popleft())
            if not groups[category]: del groups[category]
    return chosen
def score(results, elapsed):
    category_correct=urgency_correct=exact=0; per_category={}; mismatches=[]
    for ticket_id,cat,urgency,text,prediction in results:
        bucket=per_category.setdefault(cat,{"count":0,"correct":0}); bucket["count"]+=1
        category_ok,urgency_ok=prediction.category==cat,prediction.urgency==urgency
        category_correct+=category_ok; urgency_correct+=urgency_ok; exact+=category_ok and urgency_ok
        if category_ok: bucket["correct"]+=1
        if not(category_ok and urgency_ok): mismatches.append({"id":ticket_id,"expected":{"category":cat,"urgency":urgency},"predicted":{"category":prediction.category,"urgency":prediction.urgency},"text":text})
    for b in per_category.values(): b["accuracy"]=round(b["correct"]/b["count"],3)
    total=len(results) or 1
    return {"category_accuracy":round(category_correct/total,3),"urgency_accuracy":round(urgency_correct/total,3),"exact_match":round(exact/total,3),"per_category":per_category,"mismatches":mismatches,"total_time_seconds":round(elapsed,2),"model":model_in_use,"completed":len(results)}
@app.get("/")
async def index(): return FileResponse("static/index.html")
@app.get("/api/state")
async def state():
    rank={"critical":0,"high":1,"medium":2,"low":3}; queue=sorted(tickets,key=lambda t:(rank.get(t.get("urgency"),4),t["received_at"]))
    return {"queue":queue,"spikes":spikes,"alerts":list(reversed(alerts)),"kpis":estimate(tickets,spikes,config()["manual_minutes"]),"last_eval":last_eval,"model":model_in_use,"progress":progress}
@app.post("/api/tickets")
async def submit_ticket(body:TicketInput):
    ticket=new_ticket(body.text,"manual"); add_task(classify_ticket(ticket)); return {"id":ticket["id"],"status":"pending"}
@app.post("/api/demo/burst")
async def demo_burst():
    global batch_running
    if batch_running: raise HTTPException(409,"An eval or burst is already running")
    batch_running=True; messages=burst_messages(15); progress.update(task="burst",done=0,total=len(messages),status="running",wait_seconds=0); update_eta()
    async def run():
        stopped=False
        for text in messages:
            ticket=new_ticket(text,"demo_burst")
            try: await classify_ticket(ticket,True)
            except DailyQuotaExhausted: stopped=True; break
            await asyncio.sleep(.3)
        if stopped:
            for text in messages[progress["done"]:]: new_ticket(text,"demo_burst")["status"]="quota_exhausted"
        await finish("stopped_daily_quota" if stopped else "done")
    add_task(run()); return {"status":"started","count":len(messages)}
@app.post("/api/eval")
async def run_eval():
    global batch_running,last_eval
    if batch_running: raise HTTPException(409,"An eval or burst is already running")
    rows=sample_eval(config()["sample"]); batch_running=True; progress.update(task="eval",done=0,total=len(rows),status="running",wait_seconds=0); update_eta()
    async def run():
        global last_eval
        started=time.perf_counter(); results=[]; stopped=False
        for ticket_id,cat,urgency,text in rows:
            temp={"id":f"eval-{ticket_id}","text":text,"received_at":time.time(),"status":"pending"}
            try:
                prediction=await classify_ticket(temp,True)
                if prediction: results.append((ticket_id,cat,urgency,text,prediction))
            except DailyQuotaExhausted: stopped=True; break
        last_eval=score(results,time.perf_counter()-started); last_eval["stopped_daily_quota"]=stopped
        await finish("stopped_daily_quota" if stopped else "done")
    add_task(run()); return {"status":"started","count":len(rows)}
@app.get("/api/eval")
async def get_eval(): return last_eval or {}
@app.post("/api/reset")
async def reset():
    tickets.clear(); spikes.clear(); alerts.clear(); critical_alerted.clear(); return {"status":"reset"}
