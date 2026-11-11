import copy

from fastapi import FastAPI, HTTPException, Request

app = FastAPI()

INITIAL = {
    "abc1": {"sys_id": "abc1", "number": "CHG0030412",
             "short_description": "Neue Filiale br05 anbinden",
             "state": "scheduled", "work_notes": []},
    "abc2": {"sys_id": "abc2", "number": "CHG0030413",
             "short_description": "Firewall-Regel ändern",
             "state": "new", "work_notes": []},
}
CHANGES = copy.deepcopy(INITIAL)


@app.get("/api/now/table/change_request")
def list_changes(sysparm_query: str = ""):
    feld, _, wert = sysparm_query.partition("=")
    treffer = [c for c in CHANGES.values() if c.get(feld) == wert]
    return {"result": treffer}


@app.post("/api/now/table/change_request", status_code=201)
async def create_change(request: Request):
    body = await request.json()
    n = len(CHANGES) + 1
    ticket = {"sys_id": f"abc{n}", "number": f"CHG{30411 + n:07d}",
              "short_description": body.get("short_description", ""),
              "description": body.get("description", ""),
              "state": body.get("state", "new"), "work_notes": []}
    CHANGES[ticket["sys_id"]] = ticket
    return {"result": ticket}


@app.patch("/api/now/table/change_request/{sys_id}")
async def update_change(sys_id: str, request: Request):
    body = await request.json()
    if sys_id not in CHANGES:
        raise HTTPException(status_code=404)      # 1. unbekanntes Ticket

    ticket = CHANGES[sys_id]

    if "state" in body:                           # 2. Status setzen
        ticket["state"] = body["state"]                    # Wert aus body

    if "work_notes" in body:                      # 3. Notiz anhängen
        ticket["work_notes"].append(body["work_notes"])                                       # TODO: an ticket["work_notes"] anhängen

    return {"result": ticket}