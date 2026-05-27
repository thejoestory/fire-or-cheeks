import os
import uuid
import aiofiles
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

from fastapi import (
    FastAPI, Request, Form, File, UploadFile, HTTPException,
    WebSocket, WebSocketDisconnect, Depends
)
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.base import BaseHTTPMiddleware

from .database import init_db
from .websocket_manager import manager
from . import services

ROOT_PATH = os.getenv("ROOT_PATH", "")
HOST_PIN = os.getenv("HOST_PIN", "1234")
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "app/static/uploads"))
ALLOWED_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

app = FastAPI(root_path=ROOT_PATH)

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")


@app.on_event("startup")
async def startup():
    init_db()


# ── Helpers ──────────────────────────────────────────────────────────────────

def verify_pin(pin: str):
    if pin != HOST_PIN:
        raise HTTPException(status_code=403, detail="Invalid host PIN")


def session_player_id(request: Request) -> Optional[int]:
    val = request.cookies.get("player_id")
    return int(val) if val else None


async def broadcast_vote_update(game_code: str, round_id: int):
    counts = services.get_vote_counts(round_id)
    await manager.broadcast(game_code, {
        "type": "vote_update",
        "fire": counts.fire,
        "cheeks": counts.cheeks,
        "total": counts.total,
        "fire_pct": counts.fire_pct,
        "cheeks_pct": counts.cheeks_pct,
    })


# ── Pages ─────────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("home.html", {"request": request})


@app.get("/host/new", response_class=HTMLResponse)
async def host_new(request: Request):
    return templates.TemplateResponse("host_new.html", {"request": request, "error": None})


@app.post("/host/new")
async def host_create(
    request: Request,
    title: str = Form(...),
    pin: str = Form(...),
):
    if pin != HOST_PIN:
        return templates.TemplateResponse(
            "host_new.html",
            {"request": request, "error": "Invalid host PIN. Check your .env file."},
            status_code=403,
        )
    title = title.strip()[:80] or "Fire or Cheeks"
    game = services.create_game(title)
    return RedirectResponse(request.url_for('host_dashboard', code=game.code), status_code=303)


@app.get("/host/{code}", response_class=HTMLResponse)
async def host_dashboard(request: Request, code: str, pin: Optional[str] = None):
    game = services.get_game_by_code(code)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    current_round = services.get_current_round(game.id)
    counts = services.get_vote_counts(current_round.id) if current_round else None
    player_count = services.get_player_count(game.id)
    return templates.TemplateResponse("host.html", {
        "request": request,
        "game": game,
        "current_round": current_round,
        "counts": counts,
        "player_count": player_count,
        "host_pin": HOST_PIN,
    })


@app.get("/join", response_class=HTMLResponse)
async def join_page(request: Request, code: str = ""):
    return templates.TemplateResponse("join.html", {"request": request, "code": code, "error": None})


@app.post("/join")
async def join_game(
    request: Request,
    code: str = Form(...),
    display_name: str = Form(...),
):
    code = code.strip().upper()
    display_name = display_name.strip()[:30]
    game = services.get_game_by_code(code)
    if not game:
        return templates.TemplateResponse(
            "join.html",
            {"request": request, "code": code, "error": "Game not found. Check the code and try again."},
            status_code=404,
        )
    if not display_name:
        return templates.TemplateResponse(
            "join.html",
            {"request": request, "code": code, "error": "Display name is required."},
            status_code=422,
        )
    player = services.create_or_get_player(game.id, display_name)
    response = RedirectResponse(request.url_for('play_page', code=code), status_code=303)
    response.set_cookie("player_id", str(player.id), max_age=86400 * 7, httponly=True)
    response.set_cookie("player_name", display_name, max_age=86400 * 7)

    await manager.broadcast(code, {
        "type": "player_joined",
        "display_name": display_name,
        "player_count": services.get_player_count(game.id),
    })
    return response


@app.get("/play/{code}", response_class=HTMLResponse)
async def play_page(request: Request, code: str):
    game = services.get_game_by_code(code)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    player_id = session_player_id(request)
    if not player_id:
        return RedirectResponse(str(request.url_for('join_page')) + f"?code={code}", status_code=303)
    player = services.get_player(player_id)
    if not player or player.game_id != game.id:
        return RedirectResponse(str(request.url_for('join_page')) + f"?code={code}", status_code=303)
    if game.status == "finished":
        return RedirectResponse(request.url_for('results_page', code=code), status_code=303)
    current_round = services.get_current_round(game.id)
    my_vote = None
    if current_round:
        my_vote = services.get_player_vote(current_round.id, player_id)
    counts = services.get_vote_counts(current_round.id) if current_round else None
    return templates.TemplateResponse("play.html", {
        "request": request,
        "game": game,
        "player": player,
        "current_round": current_round,
        "my_vote": my_vote,
        "counts": counts,
    })


@app.get("/display/{code}", response_class=HTMLResponse)
async def display_page(request: Request, code: str):
    game = services.get_game_by_code(code)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    if game.status == "finished":
        return RedirectResponse(request.url_for('results_page', code=code), status_code=303)
    current_round = services.get_current_round(game.id)
    counts = services.get_vote_counts(current_round.id) if current_round else None
    return templates.TemplateResponse("display.html", {
        "request": request,
        "game": game,
        "current_round": current_round,
        "counts": counts,
    })


@app.get("/results/{code}", response_class=HTMLResponse)
async def results_page(request: Request, code: str):
    game = services.get_game_by_code(code)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    summary = services.get_game_summary(game.id)
    return templates.TemplateResponse("results.html", {
        "request": request,
        "game": game,
        "summary": summary,
    })


# ── Host API ──────────────────────────────────────────────────────────────────

@app.post("/api/host/{code}/round/new")
async def new_round(
    request: Request,
    code: str,
    pin: str = Form(...),
    prompt: Optional[str] = Form(None),
    image: Optional[UploadFile] = File(None),
):
    verify_pin(pin)
    game = services.get_game_by_code(code)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    image_path = None
    if image and image.filename:
        ext = Path(image.filename).suffix.lower()
        if ext not in ALLOWED_EXTS:
            raise HTTPException(status_code=400, detail="Invalid image type")
        data = await image.read()
        if len(data) > MAX_FILE_SIZE:
            raise HTTPException(status_code=400, detail="Image too large (max 10MB)")
        filename = f"{uuid.uuid4().hex}{ext}"
        dest = UPLOAD_DIR / filename
        async with aiofiles.open(dest, "wb") as f:
            await f.write(data)
        image_path = str(request.url_for("static", path=f"uploads/{filename}"))

    prompt = prompt.strip() if prompt else None
    if not image_path and not prompt:
        raise HTTPException(status_code=400, detail="Provide an image or prompt")

    round_ = services.create_round(game.id, prompt, image_path)
    await manager.broadcast(code, {
        "type": "round_new",
        "round_id": round_.id,
        "round_number": round_.round_number,
        "image_path": round_.image_path,
        "prompt": round_.prompt,
        "status": round_.status,
    })
    return JSONResponse({"ok": True, "round_id": round_.id, "round_number": round_.round_number})


@app.post("/api/host/{code}/round/start")
async def start_voting(code: str, pin: str = Form(...)):
    verify_pin(pin)
    game = services.get_game_by_code(code)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    round_ = services.get_current_round(game.id)
    if not round_:
        raise HTTPException(status_code=400, detail="No round to start")
    round_ = services.update_round_status(round_.id, "voting")
    await manager.broadcast(code, {
        "type": "voting_started",
        "round_id": round_.id,
        "image_path": round_.image_path,
        "prompt": round_.prompt,
        "round_number": round_.round_number,
    })
    return JSONResponse({"ok": True})


@app.post("/api/host/{code}/round/stop")
async def stop_voting(code: str, pin: str = Form(...)):
    verify_pin(pin)
    game = services.get_game_by_code(code)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    round_ = services.get_current_round(game.id)
    if not round_:
        raise HTTPException(status_code=400, detail="No round active")
    round_ = services.update_round_status(round_.id, "closed")
    await manager.broadcast(code, {"type": "voting_closed", "round_id": round_.id})
    return JSONResponse({"ok": True})


@app.post("/api/host/{code}/end")
async def end_game(request: Request, code: str, pin: str = Form(...)):
    verify_pin(pin)
    game = services.get_game_by_code(code)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    services.end_game(game.id)
    summary = services.get_game_summary(game.id)
    rounds_data = []
    if summary:
        for r in summary.rounds:
            rounds_data.append({
                "round_number": r.round_number,
                "image_path": r.image_path,
                "prompt": r.prompt,
                "fire": r.fire,
                "cheeks": r.cheeks,
                "total": r.total,
                "fire_pct": r.fire_pct,
                "cheeks_pct": r.cheeks_pct,
                "verdict": r.verdict,
            })
    results_url = str(request.url_for('results_page', code=code))
    await manager.broadcast(code, {
        "type": "game_ended",
        "results_url": results_url,
        "rounds": rounds_data,
        "overall_verdict": summary.overall_verdict if summary else "GAME OVER",
    })
    return JSONResponse({"ok": True, "redirect": results_url})


@app.post("/api/host/{code}/round/reveal")
async def reveal_results(code: str, pin: str = Form(...)):
    verify_pin(pin)
    game = services.get_game_by_code(code)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    round_ = services.get_current_round(game.id)
    if not round_:
        raise HTTPException(status_code=400, detail="No round to reveal")
    round_ = services.update_round_status(round_.id, "revealed")
    counts = services.get_vote_counts(round_.id)
    await manager.broadcast(code, {
        "type": "results_revealed",
        "round_id": round_.id,
        "fire": counts.fire,
        "cheeks": counts.cheeks,
        "total": counts.total,
        "fire_pct": counts.fire_pct,
        "cheeks_pct": counts.cheeks_pct,
        "verdict": counts.verdict,
    })
    return JSONResponse({"ok": True})


# ── Participant API ───────────────────────────────────────────────────────────

@app.post("/api/vote/{code}")
async def cast_vote(
    request: Request,
    code: str,
    vote_value: str = Form(...),
):
    if vote_value not in ("fire", "cheeks"):
        raise HTTPException(status_code=400, detail="Invalid vote")
    game = services.get_game_by_code(code)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    player_id = session_player_id(request)
    if not player_id:
        raise HTTPException(status_code=401, detail="Not joined")
    player = services.get_player(player_id)
    if not player or player.game_id != game.id:
        raise HTTPException(status_code=403, detail="Not in this game")
    round_ = services.get_current_round(game.id)
    if not round_ or round_.status != "voting":
        raise HTTPException(status_code=400, detail="Voting is not open")
    services.cast_vote(round_.id, player_id, vote_value)
    await broadcast_vote_update(code, round_.id)
    return JSONResponse({"ok": True, "vote": vote_value})


# ── WebSocket ─────────────────────────────────────────────────────────────────

@app.websocket("/ws/{code}")
async def websocket_endpoint(websocket: WebSocket, code: str):
    game = services.get_game_by_code(code)
    if not game:
        await websocket.close(code=4004)
        return
    await manager.connect(code, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(code, websocket)
