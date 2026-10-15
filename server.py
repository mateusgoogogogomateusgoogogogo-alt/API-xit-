# ============================================================
#   FOULD STORES v27.0 — API ANTI-SLEEP
#   Dev: MTGXZz TEAM  •  Equipe: FOULD STORES
# ============================================================

import os, json, secrets, string, re, threading, socket, time
from datetime import datetime, timedelta, timezone
from flask import Flask, request, jsonify
import discord
from discord.ext import commands

# ============================================================
#   CONFIG — LÊ DAS VARIÁVEIS DE AMBIENTE
# ============================================================
BOT_TOKEN = os.environ.get("BOT_TOKEN", "").strip()

ADMIN_IDS = set()
_admins_str = os.environ.get("ADMIN_IDS", "")
if _admins_str:
    for _id in re.split(r"[,\s]+", _admins_str.strip()):
        try: ADMIN_IDS.add(int(_id))
        except: pass
if not ADMIN_IDS:
    ADMIN_IDS = {1426663384614699223}

API_PORT = int(os.environ.get("PORT", os.environ.get("API_PORT", "5023")))
DB_FILE  = os.environ.get("DB_FILE", "fould.json")

APP_VERSION_CODE  = 27
APP_VERSION_NAME  = "27.0"
APP_DOWNLOAD_URL  = os.environ.get("APP_DOWNLOAD_URL", "https://discord.gg/fould")
PUBLIC_API_URL    = os.environ.get("PUBLIC_API_URL", "").strip()

# ⏱ CONFIG ANTI-SLEEP
KEEPALIVE_INTERVAL = 300        # 5 min
FIRST_PING_DELAY   = 30         # Primeiro ping em 30s
MAX_PING_FAILURES  = 5          # Depois de 5 falhas, continua tentando

print("=" * 60)
print("  🔧 FOULD STORES v27.0 — ANTI-SLEEP")
print("=" * 60)
print(f"  BOT_TOKEN:      {'✅' if BOT_TOKEN else '❌ VAZIO'}")
print(f"  ADMIN_IDS:      {ADMIN_IDS}")
print(f"  API_PORT:       {API_PORT}")
print(f"  DB_FILE:        {DB_FILE}")
print(f"  PUBLIC_API_URL: {PUBLIC_API_URL or '(auto-detect)'}")
print(f"  Keepalive:      {KEEPALIVE_INTERVAL}s")
print("=" * 60)


# ============================================================
#   UTILS
# ============================================================
def now_utc(): return datetime.now(timezone.utc)
def iso_now(): return now_utc().isoformat()
def iso_future(sec): return (now_utc() + timedelta(seconds=sec)).isoformat()
def parse_iso(s):
    d = datetime.fromisoformat(s)
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
def date_str(s):
    try: return parse_iso(s).strftime("%d/%m/%Y %H:%M")
    except: return "—"


def default_db():
    return {
        "keys": {},
        "admins": [],
        "bans": {},
        "logs": [],
        "config": {
            "maintenance": False,
            "message": "Sistema online",
            "watermark": "By MTGXZz TEAM",
            "discord_link": "https://discord.gg/fould",
            "default_max_devices": 1,
            "min_version": APP_VERSION_CODE,
            "version_name": APP_VERSION_NAME,
            "download_url": APP_DOWNLOAD_URL,
            "api_url": PUBLIC_API_URL,
            "auto_ping": True,
        },
        "features": {
            "aimbot_esp_lock": {"name": "Aimbot+ESP+Lock ALL", "icon": "A",
                "category": "aimbot", "locked": True, "order": 1, "type": "toggle"},
            "speed_hack": {"name": "Speed Hack", "icon": "S", "category": "diversos", "locked": False, "order": 2, "type": "toggle"},
            "wall_hack": {"name": "Wall Hack", "icon": "W", "category": "visuais", "locked": False, "order": 3, "type": "toggle"},
            "radar_hack": {"name": "Radar Hack", "icon": "R", "category": "visuais", "locked": False, "order": 4, "type": "toggle"},
            "infinite_ammo": {"name": "Infinite Ammo", "icon": "I", "category": "diversos", "locked": False, "order": 5, "type": "toggle"},
            "no_recoil": {"name": "No Recoil", "icon": "N", "category": "diversos", "locked": False, "order": 6, "type": "toggle"},
            "fast_cross": {"name": "Fast Crosshair", "icon": "F", "category": "visuais", "locked": False, "order": 7, "type": "toggle"},
            "ignore_death": {"name": "Ignore Death", "icon": "D", "category": "visuais", "locked": False, "order": 8, "type": "toggle"},
            "freeze_all": {"name": "Congelar Todos", "icon": "❄", "category": "fake", "locked": True, "order": 1, "type": "toggle"},
            "freeze_self": {"name": "Congelar Você", "icon": "❄", "category": "fake", "locked": True, "order": 2, "type": "toggle"},
            "ghost_mode": {"name": "Modo Fantasma", "icon": "👻", "category": "fake", "locked": True, "order": 3, "type": "toggle"},
            "invisible_mode": {"name": "Invisível", "icon": "◌", "category": "fake", "locked": True, "order": 4, "type": "toggle"},
            "fake_lag_1": {"name": "Fake Lag Leve", "icon": "◐", "category": "fake", "locked": True, "order": 5, "type": "toggle"},
            "fake_lag_2": {"name": "Fake Lag Médio", "icon": "◑", "category": "fake", "locked": True, "order": 6, "type": "toggle"},
            "fake_lag_3": {"name": "Fake Lag Extremo", "icon": "◒", "category": "fake", "locked": True, "order": 7, "type": "toggle"},
        }
    }


def load_db():
    if not os.path.exists(DB_FILE):
        d = default_db(); save_db(d); return d
    with open(DB_FILE, "r", encoding="utf-8") as f: db = json.load(f)
    if "features" not in db: db["features"] = default_db()["features"]
    if "config" not in db: db["config"] = default_db()["config"]
    if "bans" not in db: db["bans"] = {}
    if "logs" not in db: db["logs"] = []
    if "admins" not in db: db["admins"] = []
    for k, v in db["keys"].items():
        if "devices" not in v: v["devices"] = []
        if "max_devices" not in v: v["max_devices"] = 1
        if "permanent" not in v: v["permanent"] = False
        if "paused" not in v: v["paused"] = False
        if "start_on_first_use" not in v: v["start_on_first_use"] = False
        if "activated" not in v: v["activated"] = True
    return db

def save_db(d):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(d, f, indent=2, ensure_ascii=False)

def get_config(): return load_db()["config"]
def set_config(**kw):
    db = load_db(); db["config"].update(kw); save_db(db)
def get_features(): return load_db()["features"]
def set_feature_lock(fid, locked):
    db = load_db()
    if fid in db["features"]:
        db["features"][fid]["locked"] = locked; save_db(db); return True
    return False


def is_admin(did):
    return did in ADMIN_IDS or did in load_db()["admins"]
def add_admin(did):
    db = load_db()
    if did not in db["admins"]: db["admins"].append(did); save_db(db)
def remove_admin(did):
    db = load_db()
    if did in db["admins"]: db["admins"].remove(did); save_db(db)
def list_admins(): return list(ADMIN_IDS) + load_db()["admins"]


def add_ban(target, tipo, motivo="Banido"):
    db = load_db()
    db["bans"][target.upper()] = {"tipo": tipo, "motivo": motivo, "data": iso_now()}
    save_db(db)

def remove_ban(target):
    db = load_db()
    if target.upper() in db["bans"]:
        del db["bans"][target.upper()]; save_db(db); return True
    return False

def check_ban(hwid="", ip="", key=""):
    db = load_db()
    bans = db.get("bans", {})
    if hwid and hwid.upper() in bans:
        b = bans[hwid.upper()]; return True, b.get("motivo", "Banido"), "HWID"
    if ip and ip.upper() in bans:
        b = bans[ip.upper()]; return True, b.get("motivo", "Banido"), "IP"
    if key and key.upper() in bans:
        b = bans[key.upper()]; return True, b.get("motivo", "Banido"), "KEY"
    return False, "", ""

def add_log(hwid, ip, key, action="use"):
    db = load_db()
    db.setdefault("logs", []).append({
        "hwid": hwid.upper() if hwid else "",
        "ip": ip.upper() if ip else "",
        "key": key.upper() if key else "",
        "action": action, "data": iso_now()
    })
    if len(db["logs"]) > 500: db["logs"] = db["logs"][-500:]
    save_db(db)


UNITS = {"s":1,"seg":1,"segundo":1,"m":60,"min":60,"minuto":60,
         "h":3600,"hora":3600,"d":86400,"dia":86400,
         "sem":604800,"semana":604800,"me":2592000,"mes":2592000,
         "a":31536000,"ano":31536000}

def parse_time(text):
    if not text: return (None, "Use: 1d, 2h, 30m, 1mes, 1ano")
    original = text
    text = text.lower().strip().replace(",", " ")
    fixes = {"ds":"d","dias":"d","dia":"d","hr":"h","hrs":"h","horas":"h",
             "hora":"h","mins":"m","minutos":"m","minuto":"m","meses":"me",
             "mes":"me","mês":"me","anos":"a","ano":"a","semana":"sem","semanas":"sem"}
    for k,v in fixes.items(): text = text.replace(k,v)
    text = re.sub(r"(\d+)\s+([a-z]+)", r"\1\2", text)
    tokens = re.findall(r"(\d+)([a-z]+)", text)
    if not tokens:
        m = re.match(r"^\d+$", original.strip())
        if m: return (int(original.strip())*86400, "Interpretei como DIAS")
        return (None, f"Nao entendi '{original}'")
    total = 0
    for num, unit in tokens:
        secs = None
        for key, val in UNITS.items():
            if unit.startswith(key) or unit.rstrip("s") == key:
                secs = val; break
        if not secs: return (None, f"Unidade: '{unit}'")
        total += int(num)*secs
    warn = None
    if total <= 0: return (None, "Precisa ser >0")
    if total < 60: warn = f"Tempo curto ({total}s)"
    return (total, warn)

def human(s):
    if s <= 0: return "Expirada"
    y,s = divmod(s, 31536000); mo,s = divmod(s, 2592000)
    d,s = divmod(s, 86400); h,s = divmod(s, 3600); m,s = divmod(s, 60)
    p = []
    if y: p.append(f"{y}ano" + ("s" if y>1 else ""))
    if mo: p.append(f"{mo}mes" + ("es" if mo>1 else ""))
    if d: p.append(f"{d}d")
    if h: p.append(f"{h}h")
    if m: p.append(f"{m}m")
    if s and not p: p.append(f"{s}s")
    return " ".join(p)


def gen_key(name):
    a = string.ascii_uppercase + string.digits
    r = "".join(secrets.choice(a) for _ in range(16))
    return f"{name.upper()}-{r[:4]}-{r[4:8]}-{r[8:12]}-{r[12:16]}"

def create_key(name, dur, max_devices=1, permanent=False, start_on_first_use=False):
    db = load_db()
    key = gen_key(name)
    now = now_utc()
    if start_on_first_use and not permanent:
        db["keys"][key] = {
            "name": name, "created_at": now.isoformat(),
            "expires_at": "AGUARDANDO_ATIVACAO",
            "duration_seconds": dur, "permanent": False,
            "active": True, "paused": False,
            "start_on_first_use": True, "activated": False,
            "uses": 0, "last_used": None,
            "max_devices": max_devices, "devices": []
        }
    else:
        db["keys"][key] = {
            "name": name, "created_at": now.isoformat(),
            "expires_at": iso_future(dur) if not permanent else "PERMANENTE",
            "duration_seconds": dur, "permanent": permanent,
            "active": True, "paused": False,
            "start_on_first_use": False, "activated": True,
            "uses": 0, "last_used": None,
            "max_devices": max_devices, "devices": []
        }
    save_db(db); return key


def validate_key(key, hwid="", ip=""):
    banido, motivo, tipo = check_ban(hwid, ip, key)
    if banido:
        return {"valid": False, "banned": True,
                "reason": f"Voce foi banido ({tipo})",
                "message": motivo, "ban_type": tipo}
    db = load_db()
    k = db["keys"].get(key)
    if not k:
        add_log(hwid, ip, key, "invalid")
        return {"valid": False, "reason": "Key nao encontrada"}
    if not k["active"]: return {"valid": False, "reason": "Key desativada"}
    if k.get("paused", False):
        return {"valid": False, "reason": "Key pausada pelo ADM"}

    if k.get("start_on_first_use", False) and not k.get("activated", False):
        dur = k.get("duration_seconds", 0)
        k["expires_at"] = iso_future(dur)
        k["activated"] = True
        k["activated_at"] = iso_now()
        save_db(db)
        print(f"🔓 Key ativada: {key[:20]}...")

    is_perm = k.get("permanent", False) or k.get("expires_at") == "PERMANENTE"

    if not is_perm:
        exp = parse_iso(k["expires_at"])
        if now_utc() > exp:
            c = get_config()
            return {"valid": False, "reason": "Key expirada",
                    "expired": True,
                    "expired_at": date_str(k["expires_at"]),
                    "discord_link": c.get("discord_link", "https://discord.gg/fould"),
                    "message": "Sua key expirou! Renove com a FOULD STORES"}

    hwid = hwid.strip().upper()
    if hwid:
        devices = k.get("devices", [])
        max_dev = k.get("max_devices", 1)
        if hwid not in devices:
            if len(devices) >= max_dev:
                add_log(hwid, ip, key, "device_limit")
                return {"valid": False,
                        "reason": f"Limite de {max_dev} dispositivo(s) atingido"}
            devices.append(hwid); k["devices"] = devices

    add_log(hwid, ip, key, "use")

    if is_perm:
        left_str = "PERMANENTE"; left_sec = 0
    else:
        exp = parse_iso(k["expires_at"])
        left_sec = int((exp - now_utc()).total_seconds())
        left_str = human(left_sec)

    k["last_used"] = iso_now()
    k["uses"] = k.get("uses", 0) + 1
    save_db(db)
    c = get_config()
    return {"valid": True, "name": k["name"], "permanent": is_perm,
            "time_left": left_str, "seconds_left": left_sec,
            "created_at": date_str(k["created_at"]),
            "expires_at": "NUNCA" if is_perm else date_str(k["expires_at"]),
            "max_devices": k.get("max_devices", 1),
            "devices_used": len(k.get("devices", [])),
            "discord_link": c.get("discord_link", "https://discord.gg/fould")}


# ============================================================
#   🌐 KEEP-ALIVE — SISTEMA ANTI-SLEEP
# ============================================================
_keepalive_stats = {
    "total_pings": 0,
    "success": 0,
    "failed": 0,
    "last_ping": None,
    "last_status": None,
    "started_at": iso_now()
}


def _get_ping_url():
    """Detecta a URL pra pingar."""
    # 1. Tenta da config do banco
    try:
        cfg = get_config()
        url = cfg.get("api_url", "").strip()
        if url: return f"{url.rstrip('/')}/keepalive"
    except: pass
    
    # 2. Tenta variável de ambiente
    if PUBLIC_API_URL:
        return f"{PUBLIC_API_URL.rstrip('/')}/keepalive"
    
    # 3. Tenta detectar pelo Render (via env)
    render_url = os.environ.get("RENDER_EXTERNAL_URL", "").strip()
    if render_url:
        return f"{render_url.rstrip('/')}/keepalive"
    
    # 4. Fallback: ping local
    return f"http://127.0.0.1:{API_PORT}/keepalive"


def _do_ping():
    """Faz o ping e atualiza stats."""
    import urllib.request
    
    url = _get_ping_url()
    _keepalive_stats["total_pings"] += 1
    _keepalive_stats["last_ping"] = iso_now()
    
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "FouldKeepAlive/1.0"}
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            _keepalive_stats["success"] += 1
            _keepalive_stats["last_status"] = resp.status
            return True
    except Exception as e:
        _keepalive_stats["failed"] += 1
        _keepalive_stats["last_status"] = f"erro: {str(e)[:50]}"
        return False


def keepalive_loop():
    """
    Loop principal do keep-alive.
    Pings a cada KEEPALIVE_INTERVAL segundos (5 min).
    """
    print(f"💓 Keep-alive iniciado (intervalo: {KEEPALIVE_INTERVAL}s)")
    
    # Espera um pouco antes do primeiro ping
    time.sleep(FIRST_PING_DELAY)
    
    while True:
        try:
            # Verifica se auto_ping tá ativado
            try:
                cfg = get_config()
                if not cfg.get("auto_ping", True):
                    print("💤 Auto-ping desativado, aguardando...")
                    time.sleep(60)
                    continue
            except: pass
            
            # Faz o ping
            ok = _do_ping()
            url = _get_ping_url()
            
            if ok:
                print(f"💓 Ping #{_keepalive_stats['total_pings']} OK → {url}")
            else:
                print(f"⚠️ Ping #{_keepalive_stats['total_pings']} FALHOU → {url}")
                # Se falhou, tenta de novo em 30s
                time.sleep(30)
                _do_ping()
            
            # Aguarda o próximo ciclo
            time.sleep(KEEPALIVE_INTERVAL)
            
        except Exception as e:
            print(f"❌ Erro no keep-alive: {e}")
            time.sleep(60)


# ============================================================
#   FLASK APP
# ============================================================
app = Flask(__name__)


@app.route("/")
def home():
    return jsonify({
        "app": "FOULD STORES",
        "dev": "MTGXZz TEAM",
        "version": "27.0",
        "status": "online",
        "uptime_since": _keepalive_stats["started_at"]
    })


@app.route("/status")
def status():
    c = get_config()
    return jsonify({
        "maintenance": c["maintenance"],
        "message": c["message"],
        "watermark": c.get("watermark", "By MTGXZz TEAM"),
        "discord_link": c.get("discord_link", "https://discord.gg/fould"),
        "min_version": c.get("min_version", APP_VERSION_CODE),
        "version_name": c.get("version_name", APP_VERSION_NAME),
        "download_url": c.get("download_url", APP_DOWNLOAD_URL),
        "features": get_features(),
        "uptime": iso_now()
    })


@app.route("/ping")
def ping():
    """Endpoint simples pra health check."""
    return jsonify({"ok": True, "time": iso_now()})


@app.route("/keepalive")
def keepalive():
    """
    Endpoint especial do anti-sleep.
    Retorna informações do keep-alive.
    """
    _keepalive_stats["total_pings"] += 0  # não conta o próprio request
    return jsonify({
        "ok": True,
        "message": "Keep-alive ativo",
        "time": iso_now(),
        "stats": _keepalive_stats,
        "ping_url": _get_ping_url()
    })


@app.route("/keepalive/stats")
def keepalive_stats():
    """Stats detalhados do keep-alive."""
    return jsonify({
        **_keepalive_stats,
        "interval": KEEPALIVE_INTERVAL,
        "ping_url": _get_ping_url(),
        "server_time": iso_now()
    })


@app.route("/validate", methods=["POST"])
def api_validate():
    data = request.json or {}
    key = data.get("key", "").strip().upper()
    hwid = data.get("hwid", "").strip()
    app_ver = data.get("app_version", 0)
    ip = request.headers.get("X-Forwarded-For", request.remote_addr or "")
    ip = ip.split(",")[0].strip()
    c = get_config()
    min_ver = c.get("min_version", APP_VERSION_CODE)
    if app_ver < min_ver:
        return jsonify({
            "valid": False, "needs_update": True,
            "message": f"Atualize o app para v{APP_VERSION_NAME}",
            "download_url": c.get("download_url", APP_DOWNLOAD_URL),
            "current_version": app_ver, "min_version": min_ver
        })
    if c["maintenance"]:
        return jsonify({
            "valid": False, "reason": "Sistema em manutencao",
            "maintenance": True, "message": c["message"]
        }), 503
    return jsonify(validate_key(key, hwid, ip))


def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80)); ip = s.getsockname()[0]; s.close()
        return ip
    except: return "127.0.0.1"


# ============================================================
#   BOT DISCORD
# ============================================================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

def is_adm(did): return is_admin(did)


class CreateKeyModal(discord.ui.Modal, title="🔑 Criar Nova Key"):
    nome = discord.ui.TextInput(label="Nome da Key", placeholder="fould...", max_length=30)
    tempo = discord.ui.TextInput(label="Tempo", placeholder="30d", max_length=40)
    limite = discord.ui.TextInput(label="Dispositivos", placeholder="1", required=False, max_length=3)

    async def on_submit(self, itx):
        if not is_adm(itx.user.id):
            await itx.response.send_message("Sem permissao.", ephemeral=True); return
        secs, warn = parse_time(str(self.tempo))
        if secs is None:
            await itx.response.send_message(warn, ephemeral=True); return
        try:
            lim = int(str(self.limite) or "1")
            if lim < 1: lim = 1
        except: lim = 1
        key = create_key(str(self.nome), secs, lim, start_on_first_use=True)
        emb = discord.Embed(title="✅ KEY CRIADA", color=0x4ADE80)
        emb.add_field(name="Key", value=f"```{key}```", inline=False)
        emb.add_field(name="Nome", value=str(self.nome), inline=True)
        emb.add_field(name="Duração", value=human(secs) + " (após ativar)", inline=True)
        emb.add_field(name="Dispositivos", value=str(lim), inline=True)
        await itx.response.send_message(embed=emb, ephemeral=True)


class CreatePermKeyModal(discord.ui.Modal, title="♾️ Criar Key PERMANENTE"):
    nome = discord.ui.TextInput(label="Nome da Key", max_length=30)
    limite = discord.ui.TextInput(label="Dispositivos", placeholder="1", required=False, max_length=3)

    async def on_submit(self, itx):
        if not is_adm(itx.user.id):
            await itx.response.send_message("Sem permissao.", ephemeral=True); return
        try:
            lim = int(str(self.limite) or "1")
            if lim < 1: lim = 1
        except: lim = 1
        key = create_key(str(self.nome), 0, lim, permanent=True)
        emb = discord.Embed(title="♾️ KEY PERMANENTE", color=0xFFD700)
        emb.add_field(name="Key", value=f"```{key}```", inline=False)
        emb.add_field(name="Nome", value=str(self.nome), inline=True)
        emb.add_field(name="Dispositivos", value=str(lim), inline=True)
        await itx.response.send_message(embed=emb, ephemeral=True)


class BanUserModal(discord.ui.Modal, title="🚫 Banir Usuário"):
    valor = discord.ui.TextInput(label="Valor (HWID/IP/Key)", max_length=200)
    motivo = discord.ui.TextInput(label="Motivo", required=False, max_length=100)

    async def on_submit(self, itx):
        if not is_adm(itx.user.id):
            await itx.response.send_message("Sem permissao.", ephemeral=True); return
        v = str(self.valor).strip()
        m = str(self.motivo or "Banido pelo ADM").strip()
        tipo = "HWID"
        if v.count(".") == 3 and all(p.isdigit() for p in v.split(".")): tipo = "IP"
        elif v.startswith("FOULD-"): tipo = "KEY"
        add_ban(v, tipo, m)
        await itx.response.send_message(
            f"🚫 BANIDO `{v[:30]}` ({tipo})\n{m}", ephemeral=True)


class SetVersionModal(discord.ui.Modal, title="⬆️ Versão Mínima"):
    code = discord.ui.TextInput(label="Versão (código)", placeholder="27", max_length=4)
    nome = discord.ui.TextInput(label="Nome da versão", placeholder="27.0", max_length=10)
    url = discord.ui.TextInput(label="URL download", required=False, max_length=200)

    async def on_submit(self, itx):
        if not is_adm(itx.user.id):
            await itx.response.send_message("Sem permissao.", ephemeral=True); return
        try: c = int(str(self.code))
        except:
            await itx.response.send_message("Código inválido.", ephemeral=True); return
        set_config(min_version=c, version_name=str(self.nome),
                   download_url=str(self.url or APP_DOWNLOAD_URL))
        await itx.response.send_message(f"✅ v{self.nome} (code {c})", ephemeral=True)


class SetConfigModal(discord.ui.Modal, title="⚙️ Configurar"):
    api_url = discord.ui.TextInput(label="URL pública da API", required=False, max_length=200)
    watermark = discord.ui.TextInput(label="Watermark", required=False, max_length=50)
    discord_link = discord.ui.TextInput(label="Link do Discord", required=False, max_length=200)

    async def on_submit(self, itx):
        if not is_adm(itx.user.id):
            await itx.response.send_message("Sem permissao.", ephemeral=True); return
        kw = {}
        if str(self.api_url): kw["api_url"] = str(self.api_url).strip()
        if str(self.watermark): kw["watermark"] = str(self.watermark).strip()
        if str(self.discord_link): kw["discord_link"] = str(self.discord_link).strip()
        if kw: set_config(**kw)
        await itx.response.send_message("✅ Salvo!", ephemeral=True)


class MaintenanceModal(discord.ui.Modal, title="🔧 Manutenção"):
    msg = discord.ui.TextInput(label="Motivo", max_length=100)

    async def on_submit(self, itx):
        if not is_adm(itx.user.id):
            await itx.response.send_message("Sem permissao.", ephemeral=True); return
        set_config(maintenance=True, message=str(self.msg))
        await itx.response.send_message(f"🔴 Manutenção ATIVADA\n{self.msg}", ephemeral=True)


class AddAdminModal(discord.ui.Modal, title="👑 Adicionar Admin"):
    uid = discord.ui.TextInput(label="ID do Discord", max_length=30)

    async def on_submit(self, itx):
        if itx.user.id not in ADMIN_IDS:
            await itx.response.send_message("Só MASTER.", ephemeral=True); return
        try: uid = int(str(self.uid))
        except:
            await itx.response.send_message("ID inválido.", ephemeral=True); return
        add_admin(uid)
        await itx.response.send_message(f"✅ <@{uid}> virou ADMIN!", ephemeral=True)


class RemoveAdminModal(discord.ui.Modal, title="🚫 Remover Admin"):
    uid = discord.ui.TextInput(label="ID do Discord", max_length=30)

    async def on_submit(self, itx):
        if itx.user.id not in ADMIN_IDS:
            await itx.response.send_message("Só MASTER.", ephemeral=True); return
        try: uid = int(str(self.uid))
        except:
            await itx.response.send_message("ID inválido.", ephemeral=True); return
        remove_admin(uid)
        await itx.response.send_message(f"✅ <@{uid}> removido.", ephemeral=True)


class LockFeatureSelect(discord.ui.Select):
    def __init__(self):
        feats = get_features(); opts = []
        for fid, f in list(feats.items())[:25]:
            locked = f.get("locked", False)
            opts.append(discord.SelectOption(
                label=f.get("name", fid), value=fid,
                description=("🔴 BLOQUEADA" if locked else "🟢 ATIVA"),
                emoji="🔧" if locked else "✅"))
        if not opts:
            opts = [discord.SelectOption(label="(nenhuma)", value="__none__")]
        super().__init__(placeholder="Marque ATIVO...",
                         min_values=0, max_values=min(len(opts), 25), options=opts)
    async def callback(self, itx):
        if not is_adm(itx.user.id):
            await itx.response.send_message("Sem perm.", ephemeral=True); return
        for fid in get_features().keys(): set_feature_lock(fid, True)
        for fid in self.values:
            if fid != "__none__": set_feature_lock(fid, False)
        ativas = [get_features()[f]["name"] for f in self.values if f != "__none__"] or ["Nenhuma"]
        await itx.response.send_message(f"✅ {', '.join(ativas)}", ephemeral=True)


class LockFeatureView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=180)
        self.add_item(LockFeatureSelect())


class ManageKeySelect(discord.ui.Select):
    def __init__(self, action="pause"):
        self.action = action
        feats = load_db()["keys"]
        opts = []
        for k, v in list(feats.items())[:25]:
            nome = v.get("name", "?")
            status = "🟢"
            if v.get("paused", False): status = "⏸"
            elif not v.get("activated", True): status = "⏳"
            opts.append(discord.SelectOption(
                label=f"{status} {k[:40]}", value=k,
                description=f"nome: {nome}"))
        if not opts:
            opts = [discord.SelectOption(label="(nenhuma)", value="__none__")]
        super().__init__(placeholder=f"Key pra {action}",
                         min_values=1, max_values=1, options=opts)
    async def callback(self, itx):
        if not is_adm(itx.user.id):
            await itx.response.send_message("Sem perm.", ephemeral=True); return
        key = self.values[0]
        if key == "__none__":
            await itx.response.send_message("Nenhuma.", ephemeral=True); return
        db = load_db()
        k = db["keys"].get(key)
        if not k:
            await itx.response.send_message("Não encontrada.", ephemeral=True); return
        if self.action == "pause":
            k["paused"] = True; save_db(db)
            await itx.response.send_message(f"⏸ Pausada", ephemeral=True)
        elif self.action == "unpause":
            k["paused"] = False; save_db(db)
            await itx.response.send_message(f"▶ Ativada", ephemeral=True)
        elif self.action == "activate":
            if k.get("activated", False):
                await itx.response.send_message("Já ativada.", ephemeral=True); return
            dur = k.get("duration_seconds", 0)
            k["expires_at"] = iso_future(dur)
            k["activated"] = True
            k["activated_at"] = iso_now()
            save_db(db)
            await itx.response.send_message(f"🔓 Ativada ({human(dur)})", ephemeral=True)
        elif self.action == "delete":
            del db["keys"][key]; save_db(db)
            await itx.response.send_message(f"🗑 Deletada", ephemeral=True)
        elif self.action == "info":
            info = validate_key(key, "", "")
            emb = discord.Embed(title=f"Info", color=0x2B2B33)
            for kk, vv in info.items():
                emb.add_field(name=kk, value=str(vv)[:100], inline=True)
            await itx.response.send_message(embed=emb, ephemeral=True)


class ManageKeyView(discord.ui.View):
    def __init__(self, action):
        super().__init__(timeout=180)
        self.add_item(ManageKeySelect(action))


class BanSelect(discord.ui.Select):
    def __init__(self):
        bans = load_db().get("bans", {})
        opts = []
        for b, info in list(bans.items())[:25]:
            opts.append(discord.SelectOption(
                label=f"{b[:40]}", value=b,
                description=f"[{info.get('tipo','?')}] {info.get('motivo','—')[:40]}"))
        if not opts:
            opts = [discord.SelectOption(label="(nenhum)", value="__none__")]
        super().__init__(placeholder="Ban pra remover",
                         min_values=1, max_values=1, options=opts)
    async def callback(self, itx):
        if not is_adm(itx.user.id):
            await itx.response.send_message("Sem perm.", ephemeral=True); return
        v = self.values[0]
        if v == "__none__":
            await itx.response.send_message("Nenhum.", ephemeral=True); return
        remove_ban(v)
        await itx.response.send_message(f"✅ Desbanido", ephemeral=True)


class BanView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=180)
        self.add_item(BanSelect())


class PainelView(discord.ui.View):
    def __init__(self): super().__init__(timeout=600)

    @discord.ui.button(label="Criar Key", style=discord.ButtonStyle.success, row=0)
    async def b1(self, itx, b):
        if not is_adm(itx.user.id):
            await itx.response.send_message("Sem perm.", ephemeral=True); return
        await itx.response.send_modal(CreateKeyModal())

    @discord.ui.button(label="Key PERM", style=discord.ButtonStyle.success, row=0)
    async def b2(self, itx, b):
        if not is_adm(itx.user.id):
            await itx.response.send_message("Sem perm.", ephemeral=True); return
        await itx.response.send_modal(CreatePermKeyModal())

    @discord.ui.button(label="Keys Ativas", style=discord.ButtonStyle.primary, row=0)
    async def b3(self, itx, b):
        if not is_adm(itx.user.id):
            await itx.response.send_message("Sem perm.", ephemeral=True); return
        db = load_db(); txt = ""
        for k, v in db["keys"].items():
            if v.get("paused", False): continue
            if not v.get("activated", True):
                txt += f"⏳ `{k[:30]}` - **{v['name']}**\n"; continue
            if v.get("permanent", False):
                txt += f"♾️ `{k[:30]}` - **{v['name']}**\n"
            else:
                left = int((parse_iso(v["expires_at"]) - now_utc()).total_seconds())
                if v["active"] and left > 0:
                    txt += f"🟢 `{k[:30]}` - **{v['name']}** - {human(left)}\n"
        emb = discord.Embed(title="🔑 ATIVAS",
            description=txt[:4000] if txt else "Nenhuma", color=0x4ADE80)
        await itx.response.send_message(embed=emb, ephemeral=True)

    @discord.ui.button(label="Pausar", style=discord.ButtonStyle.secondary, row=1)
    async def b4(self, itx, b):
        if not is_adm(itx.user.id):
            await itx.response.send_message("Sem perm.", ephemeral=True); return
        await itx.response.send_message("Pausar:", view=ManageKeyView("pause"), ephemeral=True)

    @discord.ui.button(label="Despausar", style=discord.ButtonStyle.secondary, row=1)
    async def b5(self, itx, b):
        if not is_adm(itx.user.id):
            await itx.response.send_message("Sem perm.", ephemeral=True); return
        await itx.response.send_message("Despausar:", view=ManageKeyView("unpause"), ephemeral=True)

    @discord.ui.button(label="Ativar", style=discord.ButtonStyle.secondary, row=1)
    async def b6(self, itx, b):
        if not is_adm(itx.user.id):
            await itx.response.send_message("Sem perm.", ephemeral=True); return
        await itx.response.send_message("Ativar:", view=ManageKeyView("activate"), ephemeral=True)

    @discord.ui.button(label="Deletar", style=discord.ButtonStyle.danger, row=1)
    async def b7(self, itx, b):
        if not is_adm(itx.user.id):
            await itx.response.send_message("Sem perm.", ephemeral=True); return
        await itx.response.send_message("Deletar:", view=ManageKeyView("delete"), ephemeral=True)

    @discord.ui.button(label="Info", style=discord.ButtonStyle.secondary, row=1)
    async def b8(self, itx, b):
        if not is_adm(itx.user.id):
            await itx.response.send_message("Sem perm.", ephemeral=True); return
        await itx.response.send_message("Info:", view=ManageKeyView("info"), ephemeral=True)

    @discord.ui.button(label="Manut. Funções", style=discord.ButtonStyle.primary, row=2)
    async def b9(self, itx, b):
        if not is_adm(itx.user.id):
            await itx.response.send_message("Sem perm.", ephemeral=True); return
        await itx.response.send_message("ATIVO:",
            view=LockFeatureView(), ephemeral=True)

    @discord.ui.button(label="Manut. Geral", style=discord.ButtonStyle.danger, row=2)
    async def b10(self, itx, b):
        if not is_adm(itx.user.id):
            await itx.response.send_message("Sem perm.", ephemeral=True); return
        c = get_config()
        if c["maintenance"]:
            set_config(maintenance=False)
            await itx.response.send_message("🟢 OFF", ephemeral=True)
        else:
            await itx.response.send_modal(MaintenanceModal())

    @discord.ui.button(label="Banir", style=discord.ButtonStyle.danger, row=3)
    async def b11(self, itx, b):
        if not is_adm(itx.user.id):
            await itx.response.send_message("Sem perm.", ephemeral=True); return
        await itx.response.send_modal(BanUserModal())

    @discord.ui.button(label="Ver Bans", style=discord.ButtonStyle.secondary, row=3)
    async def b12(self, itx, b):
        if not is_adm(itx.user.id):
            await itx.response.send_message("Sem perm.", ephemeral=True); return
        db = load_db(); bans = db.get("bans", {})
        txt = ""
        for t, info in list(bans.items())[:25]:
            txt += f"`{t[:30]}` - [{info.get('tipo','?')}]\n"
        emb = discord.Embed(title=f"🚫 BANS ({len(bans)})",
            description=txt[:4000] if txt else "Nenhum", color=0xF87171)
        await itx.response.send_message(embed=emb, ephemeral=True)

    @discord.ui.button(label="Desbanir", style=discord.ButtonStyle.secondary, row=3)
    async def b13(self, itx, b):
        if not is_adm(itx.user.id):
            await itx.response.send_message("Sem perm.", ephemeral=True); return
        await itx.response.send_message("Escolha:",
            view=BanView(), ephemeral=True)

    @discord.ui.button(label="Logs", style=discord.ButtonStyle.secondary, row=4)
    async def b14(self, itx, b):
        if not is_adm(itx.user.id):
            await itx.response.send_message("Sem perm.", ephemeral=True); return
        db = load_db(); logs = db.get("logs", [])
        txt = ""
        for l in reversed(logs[-20:]):
            ac = l.get("action", "use")[:4]
            txt += f"[{ac}] `{l.get('hwid','')[:10]}` | {l.get('ip','')}\n"
        emb = discord.Embed(title=f"📊 LOGS ({len(logs)})",
            description=txt[:4000] if txt else "Nenhum", color=0x2B2B33)
        await itx.response.send_message(embed=emb, ephemeral=True)

    @discord.ui.button(label="Add ADM", style=discord.ButtonStyle.success, row=4)
    async def b15(self, itx, b):
        if itx.user.id not in ADMIN_IDS:
            await itx.response.send_message("Só MASTER.", ephemeral=True); return
        await itx.response.send_modal(AddAdminModal())

    @discord.ui.button(label="Del ADM", style=discord.ButtonStyle.danger, row=4)
    async def b16(self, itx, b):
        if itx.user.id not in ADMIN_IDS:
            await itx.response.send_message("Só MASTER.", ephemeral=True); return
        await itx.response.send_modal(RemoveAdminModal())

    @discord.ui.button(label="Config", style=discord.ButtonStyle.primary, row=5)
    async def b17(self, itx, b):
        if not is_adm(itx.user.id):
            await itx.response.send_message("Sem perm.", ephemeral=True); return
        await itx.response.send_modal(SetConfigModal())

    @discord.ui.button(label="Versão", style=discord.ButtonStyle.primary, row=5)
    async def b18(self, itx, b):
        if not is_adm(itx.user.id):
            await itx.response.send_message("Sem perm.", ephemeral=True); return
        await itx.response.send_modal(SetVersionModal())

    @discord.ui.button(label="💓 Keep-Alive", style=discord.ButtonStyle.secondary, row=5)
    async def b19(self, itx, b):
        if not is_adm(itx.user.id):
            await itx.response.send_message("Sem perm.", ephemeral=True); return
        emb = discord.Embed(title="💓 KEEP-ALIVE STATUS", color=0x4ADE80)
        emb.add_field(name="Total Pings", value=str(_keepalive_stats["total_pings"]), inline=True)
        emb.add_field(name="✅ Sucesso", value=str(_keepalive_stats["success"]), inline=True)
        emb.add_field(name="❌ Falhas", value=str(_keepalive_stats["failed"]), inline=True)
        emb.add_field(name="Último ping", value=_keepalive_stats["last_ping"] or "—", inline=False)
        emb.add_field(name="Último status", value=str(_keepalive_stats["last_status"]), inline=False)
        emb.add_field(name="URL", value=f"`{_get_ping_url()}`", inline=False)
        emb.add_field(name="Intervalo", value=f"{KEEPALIVE_INTERVAL}s", inline=True)
        emb.set_footer(text="Pings automáticos a cada 5 minutos")
        await itx.response.send_message(embed=emb, ephemeral=True)

    @discord.ui.button(label="Status", style=discord.ButtonStyle.secondary, row=5)
    async def b20(self, itx, b):
        if not is_adm(itx.user.id):
            await itx.response.send_message("Sem perm.", ephemeral=True); return
        c = get_config(); db = load_db()
        ip = get_local_ip()
        emb = discord.Embed(title="📊 STATUS", color=0x2B2B33)
        emb.add_field(name="🟢 Online", value="Sim", inline=True)
        emb.add_field(name="🔧 Manut", value="Sim" if c["maintenance"] else "Não", inline=True)
        emb.add_field(name="💓 Keep-Alive",
            value="ON" if c.get("auto_ping", True) else "OFF", inline=True)
        emb.add_field(name="🔑 Keys", value=str(len(db["keys"])), inline=True)
        emb.add_field(name="🚫 Bans", value=str(len(db.get("bans", {}))), inline=True)
        emb.add_field(name="👑 Admins", value=str(len(list_admins())), inline=True)
        emb.add_field(name="🌐 Local", value=f"`http://127.0.0.1:{API_PORT}`", inline=False)
        emb.add_field(name="🌐 Rede", value=f"`http://{ip}:{API_PORT}`", inline=False)
        if c.get("api_url"):
            emb.add_field(name="🌐 Pública", value=f"`{c['api_url']}`", inline=False)
        await itx.response.send_message(embed=emb, ephemeral=True)


@bot.event
async def on_ready():
    try:
        synced = await bot.tree.sync()
        print(f"✅ Slash: {len(synced)}")
    except Exception as e: print(f"❌ Sync: {e}")
    print(f"✅ BOT: {bot.user}")
    print(f"✅ API: http://{get_local_ip()}:{API_PORT}")
    print(f"💓 Keep-Alive: {_get_ping_url()}")


@bot.tree.command(name="painel", description="Painel ADM")
async def cmd_painel(itx):
    if not is_adm(itx.user.id):
        await itx.response.send_message("Sem permissao.", ephemeral=True); return
    c = get_config(); feats = get_features(); db = load_db()
    ativas = [f["name"] for f in feats.values() if not f.get("locked")]
    emb = discord.Embed(
        title="🎮 PAINEL ADM — FOULD STORES v27.0",
        description="Dev: MTGXZz TEAM\nEquipe: FOULD STORES",
        color=0x2B2B33)
    emb.add_field(name="Status",
        value="🔴 Manut" if c["maintenance"] else "🟢 Online", inline=True)
    emb.add_field(name="Keys", value=str(len(db["keys"])), inline=True)
    emb.add_field(name="Bans", value=str(len(db.get("bans", {}))), inline=True)
    emb.add_field(name="💓 Keep-Alive",
        value="✅ ON" if c.get("auto_ping", True) else "❌ OFF", inline=True)
    emb.add_field(name="ATIVAS",
        value=", ".join(ativas[:5]) if ativas else "Nenhuma", inline=False)
    emb.set_footer(text=f"API: http://{get_local_ip()}:{API_PORT}")
    await itx.response.send_message(embed=emb, view=PainelView(), ephemeral=True)


# ============================================================
#   MAIN
# ============================================================
if __name__ == "__main__":
    # 1️⃣ Inicia keep-alive (thread daemon)
    threading.Thread(target=keepalive_loop, daemon=True).start()
    
    # 2️⃣ Inicia Flask em thread daemon
    def run_api():
        app.run(host="0.0.0.0", port=API_PORT, debug=False, use_reloader=False)
    
    threading.Thread(target=run_api, daemon=True).start()
    print(f"🚀 API rodando na porta {API_PORT}")
    
    # 3️⃣ Inicia bot Discord
    if BOT_TOKEN:
        print("🤖 Iniciando bot Discord...")
        bot.run(BOT_TOKEN)
    else:
        print("⚠️ Sem BOT_TOKEN! Rodando só a API...")
        # Mantém a API rodando
        while True: time.sleep(3600)
