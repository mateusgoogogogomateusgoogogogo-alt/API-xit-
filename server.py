# ============================================================
#   FOULD STORES v26.1 — API + BOT (Render-Ready)
#   Dev: MTGXZz TEAM  •  Equipe: FOULD STORES
# ============================================================

import os, json, secrets, string, re, threading, socket, time
from datetime import datetime, timedelta, timezone
from flask import Flask, request, jsonify
import discord
from discord.ext import commands

# ============================================================
#   ⚙️ CONFIG — LÊ DAS VARIÁVEIS DE AMBIENTE
# ============================================================
BOT_TOKEN = os.environ.get("BOT_TOKEN", "").strip()

# Lê ADMIN_IDS do ambiente (aceita "123,456" ou "123 456")
ADMIN_IDS = set()
_admins_str = os.environ.get("ADMIN_IDS", "")
if _admins_str:
    for _id in re.split(r"[,\s]+", _admins_str.strip()):
        try:
            ADMIN_IDS.add(int(_id))
        except: pass

# Fallback se não tiver variável
if not ADMIN_IDS:
    ADMIN_IDS = {1426663384614699223}

# Render injeta a porta na env var "PORT"
API_PORT = int(os.environ.get("PORT", os.environ.get("API_PORT", "5023")))
DB_FILE  = os.environ.get("DB_FILE", "fould.json")

APP_VERSION_CODE  = 26
APP_VERSION_NAME  = "26.0"
APP_DOWNLOAD_URL  = os.environ.get("APP_DOWNLOAD_URL", "https://discord.gg/fould")
PUBLIC_API_URL    = os.environ.get("PUBLIC_API_URL", "")
AUTO_PING_INTERVAL = 600

# Debug
print("=" * 55)
print("  🔧 CONFIGURAÇÕES CARREGADAS")
print("=" * 55)
print(f"  BOT_TOKEN:      {'✅ configurado' if BOT_TOKEN else '❌ VAZIO!'}")
print(f"  ADMIN_IDS:      {ADMIN_IDS}")
print(f"  API_PORT:       {API_PORT}")
print(f"  DB_FILE:        {DB_FILE}")
print(f"  PUBLIC_API_URL: {PUBLIC_API_URL or '(vazio)'}")
print("=" * 55)


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
            "download_url": APP_DOWNLOAD_URL,
            "api_url": PUBLIC_API_URL,
            "auto_ping": True,
        },
        "features": {
            "aimbot_esp_lock": {"name": "Aimbot+ESP+Lock ALL", "icon": "A",
                "category": "aimbot", "locked": True, "order": 1, "type": "toggle"},
            "speed_hack": {"name": "Speed Hack", "icon": "S", "category": "diversos",
                "locked": False, "order": 2, "type": "toggle"},
            "wall_hack": {"name": "Wall Hack", "icon": "W", "category": "visuais",
                "locked": False, "order": 3, "type": "toggle"},
            "radar_hack": {"name": "Radar Hack", "icon": "R", "category": "visuais",
                "locked": False, "order": 4, "type": "toggle"},
            "infinite_ammo": {"name": "Infinite Ammo", "icon": "I", "category": "diversos",
                "locked": False, "order": 5, "type": "toggle"},
            "no_recoil": {"name": "No Recoil", "icon": "N", "category": "diversos",
                "locked": False, "order": 6, "type": "toggle"},
            "fast_cross": {"name": "Fast Crosshair", "icon": "F", "category": "visuais",
                "locked": False, "order": 7, "type": "toggle"},
            "ignore_death": {"name": "Ignore Death", "icon": "D", "category": "visuais",
                "locked": False, "order": 8, "type": "toggle"},
            "freeze_all": {"name": "Congelar Todos", "icon": "❄", "category": "fake",
                "locked": True, "order": 1, "type": "toggle"},
            "freeze_self": {"name": "Congelar Você", "icon": "❄", "category": "fake",
                "locked": True, "order": 2, "type": "toggle"},
            "ghost_mode": {"name": "Modo Fantasma", "icon": "👻", "category": "fake",
                "locked": True, "order": 3, "type": "toggle"},
            "invisible_mode": {"name": "Invisível", "icon": "◌", "category": "fake",
                "locked": True, "order": 4, "type": "toggle"},
            "fake_lag_1": {"name": "Fake Lag Leve", "icon": "◐", "category": "fake",
                "locked": True, "order": 5, "type": "toggle"},
            "fake_lag_2": {"name": "Fake Lag Médio", "icon": "◑", "category": "fake",
                "locked": True, "order": 6, "type": "toggle"},
            "fake_lag_3": {"name": "Fake Lag Extremo", "icon": "◒", "category": "fake",
                "locked": True, "order": 7, "type": "toggle"},
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
    if did not in db["admins"]:
        db["admins"].append(did); save_db(db)
def remove_admin(did):
    db = load_db()
    if did in db["admins"]:
        db["admins"].remove(did); save_db(db)
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
            "name": name,
            "created_at": now.isoformat(),
            "expires_at": "AGUARDANDO_ATIVACAO",
            "duration_seconds": dur,
            "permanent": False,
            "active": True, "paused": False,
            "start_on_first_use": True,
            "activated": False,
            "uses": 0, "last_used": None,
            "max_devices": max_devices, "devices": []
        }
    else:
        db["keys"][key] = {
            "name": name,
            "created_at": now.isoformat(),
            "expires_at": iso_future(dur) if not permanent else "PERMANENTE",
            "duration_seconds": dur,
            "permanent": permanent,
            "active": True, "paused": False,
            "start_on_first_use": False,
            "activated": True,
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
        print(f"🔓 Key {key[:20]}... ativada agora!")

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


def auto_ping_loop():
    while True:
        try:
            cfg = get_config()
            if not cfg.get("auto_ping", True):
                time.sleep(60); continue
            url = cfg.get("api_url", "") or PUBLIC_API_URL
            if url:
                ping_url = f"{url.rstrip('/')}/ping"
                try:
                    import urllib.request
                    req = urllib.request.Request(ping_url,
                        headers={"User-Agent": "FouldPing/1.0"})
                    with urllib.request.urlopen(req, timeout=10) as resp:
                        print(f"💓 Auto-ping OK ({resp.status})")
                except Exception as e: print(f"⚠️ Auto-ping: {e}")
            time.sleep(AUTO_PING_INTERVAL)
        except: time.sleep(60)


app = Flask(__name__)

@app.route("/")
def home():
    return jsonify({"app": "FOULD STORES", "dev": "MTGXZz TEAM", "version": "26.1"})

@app.route("/status")
def status():
    c = get_config()
    return jsonify({"maintenance": c["maintenance"], "message": c["message"],
        "watermark": c.get("watermark", "By MTGXZz TEAM"),
        "discord_link": c.get("discord_link", "https://discord.gg/fould"),
        "min_version": c.get("min_version", APP_VERSION_CODE),
        "version_name": c.get("version_name", APP_VERSION_NAME),
        "download_url": c.get("download_url", APP_DOWNLOAD_URL),
        "features": get_features(), "uptime": iso_now()})

@app.route("/ping")
def ping(): return jsonify({"ok": True, "time": iso_now()})

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
        return jsonify({"valid": False, "needs_update": True,
            "message": f"Atualize o app para v{APP_VERSION_NAME}",
            "download_url": c.get("download_url", APP_DOWNLOAD_URL),
            "current_version": app_ver, "min_version": min_ver})
    if c["maintenance"]:
        return jsonify({"valid": False, "reason": "Sistema em manutencao",
            "maintenance": True, "message": c["message"]}), 503
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
    tempo = discord.ui.TextInput(label="Tempo (1d, 2h, 1mes)", placeholder="30d", max_length=40)
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
        emb.set_footer(text="⏱ Tempo só começa quando o usuário ativar")
        await itx.response.send_message(embed=emb, ephemeral=True)


class CreatePermanentKeyModal(discord.ui.Modal, title="♾️ Criar Key PERMANENTE"):
    nome = discord.ui.TextInput(label="Nome da Key", placeholder="fould...", max_length=30)
    limite = discord.ui.TextInput(label="Dispositivos", placeholder="1", required=False, max_length=3)

    async def on_submit(self, itx):
        if not is_adm(itx.user.id):
            await itx.response.send_message("Sem permissao.", ephemeral=True); return
        try:
            lim = int(str(self.limite) or "1")
            if lim < 1: lim = 1
        except: lim = 1
        key = create_key(str(self.nome), 0, lim, permanent=True)
        emb = discord.Embed(title="♾️ KEY PERMANENTE CRIADA", color=0xFFD700)
        emb.add_field(name="Key", value=f"```{key}```", inline=False)
        emb.add_field(name="Nome", value=str(self.nome), inline=True)
        emb.add_field(name="Duração", value="NUNCA EXPIRA", inline=True)
        emb.add_field(name="Dispositivos", value=str(lim), inline=True)
        await itx.response.send_message(embed=emb, ephemeral=True)


class BanUserModal(discord.ui.Modal, title="🚫 Banir Usuário"):
    valor = discord.ui.TextInput(label="Valor (HWID, IP ou Key)", max_length=200)
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
            f"🚫 **BANIDO** `{v[:30]}` ({tipo})\nMotivo: {m}", ephemeral=True)


class SetVersionModal(discord.ui.Modal, title="⬆️ Definir Versão Mínima"):
    code = discord.ui.TextInput(label="Versão (código)", placeholder="26", max_length=4)
    nome = discord.ui.TextInput(label="Nome da versão", placeholder="26.0", max_length=10)
    url = discord.ui.TextInput(label="URL de download", required=False, max_length=200)

    async def on_submit(self, itx):
        if not is_adm(itx.user.id):
            await itx.response.send_message("Sem permissao.", ephemeral=True); return
        try:
            c = int(str(self.code))
        except:
            await itx.response.send_message("Código inválido.", ephemeral=True); return
        set_config(min_version=c, version_name=str(self.nome),
                   download_url=str(self.url or APP_DOWNLOAD_URL))
        await itx.response.send_message(
            f"✅ Versão mínima: **v{self.nome}** (code {c})", ephemeral=True)


class SetConfigModal(discord.ui.Modal, title="⚙️ Configurar API"):
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
        await itx.response.send_message("✅ Configuração salva!", ephemeral=True)


class MaintenanceModal(discord.ui.Modal, title="🔧 Manutenção"):
    msg = discord.ui.TextInput(label="Motivo", placeholder="Sistema em manutenção", max_length=100)

    async def on_submit(self, itx):
        if not is_adm(itx.user.id):
            await itx.response.send_message("Sem permissao.", ephemeral=True); return
        set_config(maintenance=True, message=str(self.msg))
        await itx.response.send_message(
            f"🔴 Manutenção **ATIVADA**\nMotivo: `{self.msg}`", ephemeral=True)


class AddAdminModal(discord.ui.Modal, title="👑 Adicionar Admin"):
    uid = discord.ui.TextInput(label="ID do Discord", placeholder="123456789012345678", max_length=30)

    async def on_submit(self, itx):
        if itx.user.id not in ADMIN_IDS:
            await itx.response.send_message("❌ Só o MASTER.", ephemeral=True); return
        try:
            uid = int(str(self.uid))
        except:
            await itx.response.send_message("ID inválido.", ephemeral=True); return
        add_admin(uid)
        await itx.response.send_message(f"✅ <@{uid}> virou **ADMIN**!", ephemeral=True)


class RemoveAdminModal(discord.ui.Modal, title="🚫 Remover Admin"):
    uid = discord.ui.TextInput(label="ID do Discord", max_length=30)

    async def on_submit(self, itx):
        if itx.user.id not in ADMIN_IDS:
            await itx.response.send_message("❌ Só o MASTER.", ephemeral=True); return
        try:
            uid = int(str(self.uid))
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
        super().__init__(placeholder="Marque o que fica ATIVO...",
                         min_values=0, max_values=min(len(opts), 25), options=opts)
    async def callback(self, itx):
        if not is_adm(itx.user.id):
            await itx.response.send_message("Sem permissao.", ephemeral=True); return
        for fid in get_features().keys(): set_feature_lock(fid, True)
        for fid in self.values:
            if fid != "__none__": set_feature_lock(fid, False)
        ativas = [get_features()[f]["name"] for f in self.values if f != "__none__"] or ["Nenhuma"]
        await itx.response.send_message(f"✅ Ativas: **{', '.join(ativas)}**", ephemeral=True)


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
            opts = [discord.SelectOption(label="(nenhuma key)", value="__none__")]
        super().__init__(placeholder=f"Selecione a key pra {action}",
                         min_values=1, max_values=1, options=opts)
    async def callback(self, itx):
        if not is_adm(itx.user.id):
            await itx.response.send_message("Sem permissao.", ephemeral=True); return
        key = self.values[0]
        if key == "__none__":
            await itx.response.send_message("Nenhuma key.", ephemeral=True); return
        db = load_db()
        k = db["keys"].get(key)
        if not k:
            await itx.response.send_message("Key não encontrada.", ephemeral=True); return
        if self.action == "pause":
            k["paused"] = True; save_db(db)
            await itx.response.send_message(f"⏸ Key `{key[:20]}` **PAUSADA**", ephemeral=True)
        elif self.action == "unpause":
            k["paused"] = False; save_db(db)
            await itx.response.send_message(f"▶ Key `{key[:20]}` **ATIVADA**", ephemeral=True)
        elif self.action == "activate":
            if k.get("activated", False):
                await itx.response.send_message("Key já ativada.", ephemeral=True); return
            dur = k.get("duration_seconds", 0)
            k["expires_at"] = iso_future(dur)
            k["activated"] = True
            k["activated_at"] = iso_now()
            save_db(db)
            await itx.response.send_message(f"🔓 Key `{key[:20]}` **ATIVADA** ({human(dur)})", ephemeral=True)
        elif self.action == "delete":
            del db["keys"][key]; save_db(db)
            await itx.response.send_message(f"🗑 Key `{key[:20]}` **DELETADA**", ephemeral=True)
        elif self.action == "info":
            info = validate_key(key, "", "")
            emb = discord.Embed(title=f"ℹ️ Info: {key[:30]}", color=0x2B2B33)
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
            opts = [discord.SelectOption(label="(nenhum ban)", value="__none__")]
        super().__init__(placeholder="Selecione um ban pra remover",
                         min_values=1, max_values=1, options=opts)
    async def callback(self, itx):
        if not is_adm(itx.user.id):
            await itx.response.send_message("Sem permissao.", ephemeral=True); return
        v = self.values[0]
        if v == "__none__":
            await itx.response.send_message("Nenhum ban.", ephemeral=True); return
        remove_ban(v)
        await itx.response.send_message(f"✅ Desbanido `{v[:30]}`", ephemeral=True)


class BanView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=180)
        self.add_item(BanSelect())


class PainelView(discord.ui.View):
    def __init__(self): super().__init__(timeout=600)

    @discord.ui.button(label="Criar Key", style=discord.ButtonStyle.success, row=0)
    async def b_key(self, itx, b):
        if not is_adm(itx.user.id):
            await itx.response.send_message("Sem perm.", ephemeral=True); return
        await itx.response.send_modal(CreateKeyModal())

    @discord.ui.button(label="Key PERMANENTE", style=discord.ButtonStyle.success, row=0)
    async def b_perm(self, itx, b):
        if not is_adm(itx.user.id):
            await itx.response.send_message("Sem perm.", ephemeral=True); return
        await itx.response.send_modal(CreatePermanentKeyModal())

    @discord.ui.button(label="Keys Ativas", style=discord.ButtonStyle.primary, row=0)
    async def b_ativas(self, itx, b):
        if not is_adm(itx.user.id):
            await itx.response.send_message("Sem perm.", ephemeral=True); return
        db = load_db(); txt = ""
        for k, v in db["keys"].items():
            if v.get("paused", False): continue
            if not v.get("activated", True):
                txt += f"⏳ `{k[:30]}` - **{v['name']}** - AGUARDANDO\n"
                continue
            if v.get("permanent", False):
                if v["active"]:
                    dev = f"{len(v.get('devices',[]))}/{v.get('max_devices',1)}"
                    txt += f"♾️ `{k[:30]}` - **{v['name']}** - PERM - [dev {dev}]\n"
            else:
                left = int((parse_iso(v["expires_at"]) - now_utc()).total_seconds())
                if v["active"] and left > 0:
                    dev = f"{len(v.get('devices',[]))}/{v.get('max_devices',1)}"
                    txt += f"🟢 `{k[:30]}` - **{v['name']}** - {human(left)} - [dev {dev}]\n"
        emb = discord.Embed(title="🔑 KEYS ATIVAS",
                            description=txt[:4000] if txt else "Nenhuma", color=0x4ADE80)
        await itx.response.send_message(embed=emb, ephemeral=True)

    @discord.ui.button(label="Todas as Keys", style=discord.ButtonStyle.secondary, row=0)
    async def b_all_keys(self, itx, b):
        if not is_adm(itx.user.id):
            await itx.response.send_message("Sem perm.", ephemeral=True); return
        db = load_db()
        if not db["keys"]:
            await itx.response.send_message("Nenhuma key.", ephemeral=True); return
        txt = ""
        for k, v in list(db["keys"].items())[:30]:
            st = "🟢"
            if v.get("paused", False): st = "⏸"
            elif not v.get("activated", True): st = "⏳"
            elif v.get("permanent", False): st = "♾️"
            txt += f"{st} `{k[:30]}` - **{v.get('name','?')}**\n"
        emb = discord.Embed(title="📋 TODAS AS KEYS",
                            description=txt[:4000], color=0x2B2B33)
        await itx.response.send_message(embed=emb, ephemeral=True)

    @discord.ui.button(label="Pausar Key", style=discord.ButtonStyle.secondary, row=1)
    async def b_pause(self, itx, b):
        if not is_adm(itx.user.id):
            await itx.response.send_message("Sem perm.", ephemeral=True); return
        await itx.response.send_message("Escolha a key pra pausar:",
                                        view=ManageKeyView("pause"), ephemeral=True)

    @discord.ui.button(label="Despausar", style=discord.ButtonStyle.secondary, row=1)
    async def b_unpause(self, itx, b):
        if not is_adm(itx.user.id):
            await itx.response.send_message("Sem perm.", ephemeral=True); return
        await itx.response.send_message("Escolha a key pra despausar:",
                                        view=ManageKeyView("unpause"), ephemeral=True)

    @discord.ui.button(label="Ativar Manual", style=discord.ButtonStyle.secondary, row=1)
    async def b_activate(self, itx, b):
        if not is_adm(itx.user.id):
            await itx.response.send_message("Sem perm.", ephemeral=True); return
        await itx.response.send_message("Escolha a key pra ativar:",
                                        view=ManageKeyView("activate"), ephemeral=True)

    @discord.ui.button(label="Deletar Key", style=discord.ButtonStyle.danger, row=1)
    async def b_del_key(self, itx, b):
        if not is_adm(itx.user.id):
            await itx.response.send_message("Sem perm.", ephemeral=True); return
        await itx.response.send_message("⚠️ Escolha a key pra **DELETAR**:",
                                        view=ManageKeyView("delete"), ephemeral=True)

    @discord.ui.button(label="Info Key", style=discord.ButtonStyle.secondary, row=1)
    async def b_info_key(self, itx, b):
        if not is_adm(itx.user.id):
            await itx.response.send_message("Sem perm.", ephemeral=True); return
        await itx.response.send_message("Escolha a key pra ver info:",
                                        view=ManageKeyView("info"), ephemeral=True)

    @discord.ui.button(label="Manutenção Funções", style=discord.ButtonStyle.primary, row=2)
    async def b_manut_func(self, itx, b):
        if not is_adm(itx.user.id):
            await itx.response.send_message("Sem perm.", ephemeral=True); return
        await itx.response.send_message(
            "🔧 Marque o que fica **ATIVO** (resto = manutenção):",
            view=LockFeatureView(), ephemeral=True)

    @discord.ui.button(label="Manut. Geral", style=discord.ButtonStyle.danger, row=2)
    async def b_manut_geral(self, itx, b):
        if not is_adm(itx.user.id):
            await itx.response.send_message("Sem perm.", ephemeral=True); return
        c = get_config()
        if c["maintenance"]:
            set_config(maintenance=False)
            await itx.response.send_message("🟢 Manutenção **DESATIVADA**", ephemeral=True)
        else:
            await itx.response.send_modal(MaintenanceModal())

    @discord.ui.button(label="Banir User", style=discord.ButtonStyle.danger, row=3)
    async def b_ban(self, itx, b):
        if not is_adm(itx.user.id):
            await itx.response.send_message("Sem perm.", ephemeral=True); return
        await itx.response.send_modal(BanUserModal())

    @discord.ui.button(label="Ver Bans", style=discord.ButtonStyle.secondary, row=3)
    async def b_view_bans(self, itx, b):
        if not is_adm(itx.user.id):
            await itx.response.send_message("Sem perm.", ephemeral=True); return
        db = load_db(); bans = db.get("bans", {})
        txt = ""
        for t, info in list(bans.items())[:25]:
            txt += f"`{t[:30]}` - [{info.get('tipo','?')}] - {info.get('motivo','—')}\n"
        emb = discord.Embed(title=f"🚫 BANS ({len(bans)})",
            description=txt[:4000] if txt else "Nenhum", color=0xF87171)
        await itx.response.send_message(embed=emb, ephemeral=True)

    @discord.ui.button(label="Desbanir", style=discord.ButtonStyle.secondary, row=3)
    async def b_unban(self, itx, b):
        if not is_adm(itx.user.id):
            await itx.response.send_message("Sem perm.", ephemeral=True); return
        await itx.response.send_message("Escolha o ban pra remover:",
                                        view=BanView(), ephemeral=True)

    @discord.ui.button(label="Ver Logs", style=discord.ButtonStyle.secondary, row=4)
    async def b_logs(self, itx, b):
        if not is_adm(itx.user.id):
            await itx.response.send_message("Sem perm.", ephemeral=True); return
        db = load_db(); logs = db.get("logs", [])
        txt = ""
        for l in reversed(logs[-20:]):
            ac = l.get("action", "use")[:4]
            txt += f"[{ac}] `{l.get('hwid','')[:10]}` | {l.get('ip','')} | {l.get('key','')[:18]}\n"
        emb = discord.Embed(title=f"📊 LOGS ({len(logs)})",
            description=txt[:4000] if txt else "Nenhum", color=0x2B2B33)
        await itx.response.send_message(embed=emb, ephemeral=True)

    @discord.ui.button(label="Adicionar ADM", style=discord.ButtonStyle.success, row=4)
    async def b_addadm(self, itx, b):
        if itx.user.id not in ADMIN_IDS:
            await itx.response.send_message("❌ Só MASTER.", ephemeral=True); return
        await itx.response.send_modal(AddAdminModal())

    @discord.ui.button(label="Remover ADM", style=discord.ButtonStyle.danger, row=4)
    async def b_deladm(self, itx, b):
        if itx.user.id not in ADMIN_IDS:
            await itx.response.send_message("❌ Só MASTER.", ephemeral=True); return
        await itx.response.send_modal(RemoveAdminModal())

    @discord.ui.button(label="Listar ADMs", style=discord.ButtonStyle.secondary, row=4)
    async def b_listadm(self, itx, b):
        if not is_adm(itx.user.id):
            await itx.response.send_message("Sem perm.", ephemeral=True); return
        txt = "**MASTER:**\n"
        for aid in ADMIN_IDS: txt += f"<@{aid}>\n"
        txt += "\n**Secundários:**\n"
        sec = load_db().get("admins", [])
        txt += "\n".join(f"<@{a}>" for a in sec) if sec else "Nenhum"
        await itx.response.send_message(txt, ephemeral=True)

    @discord.ui.button(label="⚙️ Configurar", style=discord.ButtonStyle.primary, row=5)
    async def b_config(self, itx, b):
        if not is_adm(itx.user.id):
            await itx.response.send_message("Sem perm.", ephemeral=True); return
        await itx.response.send_modal(SetConfigModal())

    @discord.ui.button(label="⬆️ Versão", style=discord.ButtonStyle.primary, row=5)
    async def b_version(self, itx, b):
        if not is_adm(itx.user.id):
            await itx.response.send_message("Sem perm.", ephemeral=True); return
        await itx.response.send_modal(SetVersionModal())

    @discord.ui.button(label="💓 Auto-Ping", style=discord.ButtonStyle.secondary, row=5)
    async def b_autoping(self, itx, b):
        if not is_adm(itx.user.id):
            await itx.response.send_message("Sem perm.", ephemeral=True); return
        c = get_config()
        new = not c.get("auto_ping", True)
        set_config(auto_ping=new)
        await itx.response.send_message(
            f"💓 Auto-ping: **{'ATIVADO' if new else 'DESATIVADO'}**", ephemeral=True)

    @discord.ui.button(label="📊 Status", style=discord.ButtonStyle.secondary, row=5)
    async def b_status(self, itx, b):
        if not is_adm(itx.user.id):
            await itx.response.send_message("Sem perm.", ephemeral=True); return
        c = get_config(); db = load_db()
        ip = get_local_ip()
        total_keys = len(db["keys"])
        ativas = 0
        for k, v in db["keys"].items():
            if not v.get("paused", False) and v.get("activated", True):
                if v.get("permanent", False): ativas += 1
                else:
                    try:
                        if int((parse_iso(v["expires_at"]) - now_utc()).total_seconds()) > 0:
                            ativas += 1
                    except: pass
        emb = discord.Embed(title="📊 STATUS DO SERVIDOR", color=0x2B2B33)
        emb.add_field(name="🟢 Online", value="Sim", inline=True)
        emb.add_field(name="🔧 Manutenção",
            value="Sim" if c["maintenance"] else "Não", inline=True)
        emb.add_field(name="💓 Auto-Ping",
            value="ON" if c.get("auto_ping", True) else "OFF", inline=True)
        emb.add_field(name="🔑 Keys", value=f"{ativas}/{total_keys}", inline=True)
        emb.add_field(name="🚫 Bans", value=str(len(db.get("bans", {}))), inline=True)
        emb.add_field(name="👑 Admins", value=str(len(list_admins())), inline=True)
        emb.add_field(name="🌐 Local", value=f"`http://127.0.0.1:{API_PORT}`", inline=False)
        emb.add_field(name="🌐 Rede", value=f"`http://{ip}:{API_PORT}`", inline=False)
        if c.get("api_url"):
            emb.add_field(name="🌐 Pública", value=f"`{c['api_url']}`", inline=False)
        emb.add_field(name="⬆️ Versão Mínima",
            value=f"v{c.get('version_name','?')} (code {c.get('min_version',0)})",
            inline=False)
        await itx.response.send_message(embed=emb, ephemeral=True)


@bot.event
async def on_ready():
    try:
        synced = await bot.tree.sync()
        print(f"✅ Slash sincronizados: {len(synced)}")
    except Exception as e: print("❌ Erro sync:", e)
    print(f"✅ BOT ONLINE: {bot.user}")
    print(f"✅ API: http://{get_local_ip()}:{API_PORT}")


@bot.tree.command(name="painel", description="Painel ADM completo")
async def cmd_painel(itx):
    if not is_adm(itx.user.id):
        await itx.response.send_message("Sem permissao.", ephemeral=True); return
    c = get_config(); feats = get_features(); db = load_db()
    ativas = [f["name"] for f in feats.values() if not f.get("locked")]
    emb = discord.Embed(
        title="🎮 PAINEL ADM — FOULD STORES v26.1",
        description="**Dev:** MTGXZz TEAM\n**Equipe:** FOULD STORES",
        color=0x2B2B33)
    emb.add_field(name="Status",
        value="🔴 Manutenção" if c["maintenance"] else "🟢 Online", inline=True)
    emb.add_field(name="Keys", value=str(len(db["keys"])), inline=True)
    emb.add_field(name="Bans", value=str(len(db.get("bans", {}))), inline=True)
    emb.add_field(name="Auto-Ping",
        value="✅ ON" if c.get("auto_ping", True) else "❌ OFF", inline=True)
    emb.add_field(name="ATIVAS",
        value=", ".join(ativas[:5]) if ativas else "Nenhuma", inline=False)
    emb.set_footer(text=f"API: http://{get_local_ip()}:{API_PORT}")
    await itx.response.send_message(embed=emb, view=PainelView(), ephemeral=True)


# ============================================================
#   MAIN — Render usa gunicorn ou thread do Flask
# ============================================================
def start_api():
    """Roda Flask em thread separada."""
    app.run(host="0.0.0.0", port=API_PORT, debug=False, use_reloader=False)


if __name__ == "__main__":
    # Verifica se tem token
    if not BOT_TOKEN:
        print("❌ BOT_TOKEN NÃO CONFIGURADO! Configura nas variáveis de ambiente.")
        print("⚠️ Rodando SÓ a API...")
        app.run(host="0.0.0.0", port=API_PORT, debug=False, use_reloader=False)
    else:
        # Inicia auto-ping
        threading.Thread(target=auto_ping_loop, daemon=True).start()
        print("💓 Auto-ping iniciado")
        
        # Inicia Flask em thread separada
        threading.Thread(target=start_api, daemon=True).start()
        print(f"🚀 API rodando na porta {API_PORT}")
        
        # Inicia bot
        print("🤖 Iniciando bot Discord...")
        bot.run(BOT_TOKEN)
