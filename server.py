# ============================================================
#   FOULD STORES v17.0 — API + BOT + BAN SYSTEM
#   Dev: MTGXZz TEAM  •  Equipe: FOULD STORES
# ============================================================

import os, json, secrets, string, re, threading, socket
from datetime import datetime, timedelta, timezone
from flask import Flask, request, jsonify
import discord
from discord.ext import commands
from dotenv import load_dotenv

# Carrega .env
load_dotenv()

# ============================================================
#   CONFIGURAÇÕES (via .env)
# ============================================================

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
if not BOT_TOKEN:
    raise SystemExit("[ERRO] BOT_TOKEN nao definido no .env")

_admins_raw = os.getenv("ADMIN_IDS", "")
ADMIN_IDS = {int(x.strip()) for x in _admins_raw.split(",") if x.strip().isdigit()}

API_PORT = int(os.getenv("API_PORT", "5023"))
DB_FILE  = os.getenv("DB_FILE", "fould.json")


# ============================================================
#   HELPERS DE TEMPO
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


# ============================================================
#   BANCO DE DADOS
# ============================================================

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
            "vpn_required": "VPN ÍNDIA OBRIGATÓRIA",
            "discord_link": "https://discord.gg/fould",
            "default_max_devices": 1,
        },
        "features": {
            "aimbot_esp_lock": {"name": "Aimbot+ESP+Lock ALL", "icon": "A",
                "category": "aimbot", "locked": True, "order": 1,
                "type": "toggle", "special": True},
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
    for k, v in db["keys"].items():
        if "devices" not in v: v["devices"] = []
        if "max_devices" not in v:
            v["max_devices"] = db["config"].get("default_max_devices", 1)
        if "permanent" not in v: v["permanent"] = False
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


# ============================================================
#   BANS
# ============================================================

def add_ban(target, tipo, motivo="Banido"):
    db = load_db()
    db["bans"][target.upper()] = {
        "tipo": tipo, "motivo": motivo, "data": iso_now()
    }
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
        b = bans[hwid.upper()]
        return True, b.get("motivo", "Banido"), "HWID"
    if ip and ip.upper() in bans:
        b = bans[ip.upper()]
        return True, b.get("motivo", "Banido"), "IP"
    if key and key.upper() in bans:
        b = bans[key.upper()]
        return True, b.get("motivo", "Banido"), "KEY"
    return False, "", ""


def add_log(hwid, ip, key):
    db = load_db()
    entry = {
        "hwid": hwid.upper() if hwid else "",
        "ip": ip.upper() if ip else "",
        "key": key.upper() if key else "",
        "data": iso_now()
    }
    db.setdefault("logs", []).append(entry)
    if len(db["logs"]) > 500:
        db["logs"] = db["logs"][-500:]
    save_db(db)


# ============================================================
#   ADMINS
# ============================================================

def is_admin(did):
    return did in ADMIN_IDS or did in load_db()["admins"]

def add_admin(did):
    db = load_db()
    if did not in db["admins"]: db["admins"].append(did); save_db(db)

def list_admins(): return list(ADMIN_IDS) + load_db()["admins"]


# ============================================================
#   PARSE DE TEMPO
# ============================================================

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
    for k, v in fixes.items(): text = text.replace(k, v)
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
    y, s = divmod(s, 31536000); mo, s = divmod(s, 2592000)
    d, s = divmod(s, 86400); h, s = divmod(s, 3600); m, s = divmod(s, 60)
    p = []
    if y: p.append(f"{y}ano" + ("s" if y > 1 else ""))
    if mo: p.append(f"{mo}mes" + ("es" if mo > 1 else ""))
    if d: p.append(f"{d}d")
    if h: p.append(f"{h}h")
    if m: p.append(f"{m}m")
    if s and not p: p.append(f"{s}s")
    return " ".join(p)


# ============================================================
#   KEYS
# ============================================================

def gen_key(name):
    a = string.ascii_uppercase + string.digits
    r = "".join(secrets.choice(a) for _ in range(16))
    return f"{name.upper()}-{r[:4]}-{r[4:8]}-{r[8:12]}-{r[12:16]}"


def create_key(name, dur, max_devices=1, permanent=False):
    db = load_db()
    key = gen_key(name)
    db["keys"][key] = {
        "name": name,
        "created_at": iso_now(),
        "expires_at": iso_future(dur) if not permanent else "PERMANENTE",
        "permanent": permanent,
        "active": True, "uses": 0, "last_used": None,
        "max_devices": max_devices, "devices": []
    }
    save_db(db); return key


def validate_key(key, hwid="", ip=""):
    banido, motivo, tipo = check_ban(hwid, ip, key)
    if banido:
        return {
            "valid": False, "banned": True,
            "reason": f"Voce foi banido ({tipo})",
            "message": motivo, "ban_type": tipo
        }

    db = load_db()
    k = db["keys"].get(key)
    if not k:
        add_log(hwid, ip, key)
        return {"valid": False, "reason": "Key nao encontrada"}
    if not k["active"]:
        return {"valid": False, "reason": "Key desativada"}

    is_perm = k.get("permanent", False) or k.get("expires_at") == "PERMANENTE"

    if not is_perm:
        exp = parse_iso(k["expires_at"])
        if now_utc() > exp:
            c = get_config()
            return {
                "valid": False, "reason": "Key expirada",
                "expired": True,
                "expired_at": date_str(k["expires_at"]),
                "discord_link": c.get("discord_link", "https://discord.gg/fould"),
                "message": "Sua key expirou! Renove com a FOULD STORES"
            }

    hwid = hwid.strip().upper()
    if hwid:
        devices = k.get("devices", [])
        max_dev = k.get("max_devices", 1)
        if hwid not in devices:
            if len(devices) >= max_dev:
                add_log(hwid, ip, key)
                return {"valid": False,
                        "reason": f"Limite de {max_dev} dispositivo(s) atingido"}
            devices.append(hwid); k["devices"] = devices

    add_log(hwid, ip, key)

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
    return {
        "valid": True, "name": k["name"],
        "permanent": is_perm,
        "time_left": left_str,
        "seconds_left": left_sec,
        "created_at": date_str(k["created_at"]),
        "expires_at": "NUNCA" if is_perm else date_str(k["expires_at"]),
        "max_devices": k.get("max_devices", 1),
        "devices_used": len(k.get("devices", [])),
        "discord_link": c.get("discord_link", "https://discord.gg/fould")
    }


# ============================================================
#   FLASK API
# ============================================================

app = Flask(__name__)


@app.route("/")
def home():
    return jsonify({"app": "FOULD STORES", "dev": "MTGXZz TEAM", "version": "17.0"})


@app.route("/status")
def status():
    c = get_config()
    return jsonify({
        "maintenance": c["maintenance"],
        "message": c["message"],
        "watermark": c.get("watermark", "By MTGXZz TEAM"),
        "vpn_required": c.get("vpn_required", "VPN ÍNDIA OBRIGATÓRIA"),
        "discord_link": c.get("discord_link", "https://discord.gg/fould"),
        "features": get_features()
    })


@app.route("/validate", methods=["POST"])
def api_validate():
    data = request.json or {}
    key = data.get("key", "").strip().upper()
    hwid = data.get("hwid", "").strip()
    ip = request.headers.get("X-Forwarded-For", request.remote_addr or "")
    ip = ip.split(",")[0].strip()
    c = get_config()
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
    except:
        return "127.0.0.1"


def run_flask():
    app.run(host="0.0.0.0", port=API_PORT, debug=False, use_reloader=False)


# ============================================================
#   DISCORD BOT
# ============================================================

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)


def is_adm(did): return is_admin(did)


# ---------- MODALS / VIEWS ----------

class CreateKeyModal(discord.ui.Modal, title="Criar Nova Key"):
    nome = discord.ui.TextInput(label="Nome da Key", placeholder="fould...", max_length=30)
    tempo = discord.ui.TextInput(label="Tempo (1d, 2h, 1mes, 1ano)", placeholder="30d", max_length=40)
    limite = discord.ui.TextInput(label="Limite de dispositivos", placeholder="1", required=False, max_length=3)

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
        key = create_key(str(self.nome), secs, lim)
        emb = discord.Embed(title="KEY CRIADA", color=0x4ADE80)
        emb.add_field(name="Key", value=f"```{key}```", inline=False)
        emb.add_field(name="Nome", value=str(self.nome), inline=True)
        emb.add_field(name="Duracao", value=human(secs), inline=True)
        emb.add_field(name="Dispositivos", value=str(lim), inline=True)
        if warn: emb.set_footer(text=warn)
        await itx.response.send_message(embed=emb, ephemeral=True)


class LockFeatureSelect(discord.ui.Select):
    def __init__(self):
        feats = get_features(); opts = []
        for fid, f in list(feats.items())[:25]:
            locked = f.get("locked", False)
            opts.append(discord.SelectOption(
                label=f.get("name", fid), value=fid,
                description=("BLOQUEADA" if locked else "ATIVA")))
        if not opts:
            opts = [discord.SelectOption(label="(nenhuma)", value="__none__")]
        super().__init__(placeholder="Selecione o que fica ATIVO",
                         min_values=0, max_values=min(len(opts), 25), options=opts)

    async def callback(self, itx):
        if not is_adm(itx.user.id):
            await itx.response.send_message("Sem permissao.", ephemeral=True); return
        for fid in get_features().keys(): set_feature_lock(fid, True)
        for fid in self.values:
            if fid != "__none__": set_feature_lock(fid, False)
        ativas = [get_features()[f]["name"] for f in self.values if f != "__none__"] or ["Nenhuma"]
        await itx.response.send_message(f"Ativas: **{', '.join(ativas)}**", ephemeral=True)


class LockFeatureView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=180)
        self.add_item(LockFeatureSelect())


class PainelView(discord.ui.View):
    def __init__(self): super().__init__(timeout=300)

    @discord.ui.button(label="Criar Key", style=discord.ButtonStyle.success)
    async def b1(self, itx, b):
        if not is_adm(itx.user.id):
            await itx.response.send_message("Sem perm.", ephemeral=True); return
        await itx.response.send_modal(CreateKeyModal())

    @discord.ui.button(label="Keys Ativas", style=discord.ButtonStyle.primary)
    async def b2(self, itx, b):
        if not is_adm(itx.user.id):
            await itx.response.send_message("Sem perm.", ephemeral=True); return
        db = load_db(); txt = ""
        for k, v in db["keys"].items():
            if v.get("permanent", False):
                if v["active"]:
                    dev = f"{len(v.get('devices',[]))}/{v.get('max_devices',1)}"
                    txt += f"`{k}` - **{v['name']}** - PERM - [dev {dev}]\n"
            else:
                left = int((parse_iso(v["expires_at"]) - now_utc()).total_seconds())
                if v["active"] and left > 0:
                    dev = f"{len(v.get('devices',[]))}/{v.get('max_devices',1)}"
                    txt += f"`{k}` - **{v['name']}** - {human(left)} - [dev {dev}]\n"
        emb = discord.Embed(title="KEYS ATIVAS",
                            description=txt[:4000] if txt else "Nenhuma", color=0x4ADE80)
        await itx.response.send_message(embed=emb, ephemeral=True)

    @discord.ui.button(label="Manutencao", style=discord.ButtonStyle.secondary)
    async def b4(self, itx, b):
        if not is_adm(itx.user.id):
            await itx.response.send_message("Sem perm.", ephemeral=True); return
        await itx.response.send_message("Selecione o que fica ATIVO:",
                                        view=LockFeatureView(), ephemeral=True)

    @discord.ui.button(label="Bans", style=discord.ButtonStyle.danger)
    async def b5(self, itx, b):
        if not is_adm(itx.user.id):
            await itx.response.send_message("Sem perm.", ephemeral=True); return
        db = load_db(); bans = db.get("bans", {})
        txt = ""
        for t, info in bans.items():
            txt += f"`{t[:30]}` - [{info.get('tipo','?')}] - {info.get('motivo','—')}\n"
        emb = discord.Embed(title=f"BANS ({len(bans)})",
            description=txt[:4000] if txt else "Nenhum banimento", color=0xF87171)
        await itx.response.send_message(embed=emb, ephemeral=True)

    @discord.ui.button(label="Logs", style=discord.ButtonStyle.secondary)
    async def b6(self, itx, b):
        if not is_adm(itx.user.id):
            await itx.response.send_message("Sem perm.", ephemeral=True); return
        db = load_db(); logs = db.get("logs", [])
        txt = ""
        for l in reversed(logs[-20:]):
            txt += f"`{l.get('hwid','')[:12]}` | {l.get('ip','')} | {l.get('key','')[:20]}\n"
        emb = discord.Embed(title=f"ULTIMOS LOGS ({len(logs)} totais)",
            description=txt[:4000] if txt else "Nenhum log", color=0x2B2B33)
        await itx.response.send_message(embed=emb, ephemeral=True)


# ---------- EVENTOS ----------

@bot.event
async def on_ready():
    try:
        synced = await bot.tree.sync()
        print(f"Slash sincronizados: {len(synced)}")
    except Exception as e:
        print("Erro:", e)
    print(f"BOT: {bot.user}")
    print(f"API: http://{get_local_ip()}:{API_PORT}")


# ---------- COMANDOS ----------

@bot.tree.command(name="painel", description="Painel ADM")
async def s1(itx):
    if not is_adm(itx.user.id):
        await itx.response.send_message("Sem permissao.", ephemeral=True); return
    c = get_config(); feats = get_features(); db = load_db()
    ativas = [f["name"] for f in feats.values() if not f.get("locked")]
    emb = discord.Embed(title="PAINEL ADM - FOULD STORES v17.0",
        description="Dev: **MTGXZz TEAM** - Equipe: **FOULD STORES**", color=0x2B2B33)
    emb.add_field(name="Status",
        value="MANUTENCAO" if c["maintenance"] else "ONLINE", inline=True)
    emb.add_field(name="Keys", value=str(len(db["keys"])), inline=True)
    emb.add_field(name="Bans", value=str(len(db.get("bans", {}))), inline=True)
    emb.add_field(name="Logs", value=str(len(db.get("logs", []))), inline=True)
    emb.add_field(name="ATIVAS", value=", ".join(ativas) if ativas else "Nenhuma", inline=False)
    emb.set_footer(text=f"API: http://{get_local_ip()}:{API_PORT}")
    await itx.response.send_message(embed=emb, view=PainelView(), ephemeral=True)


@bot.tree.command(name="banir", description="Bane um usuário por HWID/IP/Key")
async def s_ban(itx, tipo: str, valor: str, motivo: str = "Banido pelo ADM"):
    if not is_adm(itx.user.id):
        await itx.response.send_message("Sem permissao.", ephemeral=True); return
    t = tipo.lower()
    if t not in ("hwid", "ip", "key"):
        await itx.response.send_message("Tipo deve ser: hwid, ip ou key", ephemeral=True); return
    add_ban(valor, t.upper(), motivo)
    await itx.response.send_message(
        f"BANIDO `{valor[:30]}` ({t.upper()})\nMotivo: {motivo}", ephemeral=True)


@bot.tree.command(name="desbanir", description="Remove ban")
async def s_unban(itx, valor: str):
    if not is_adm(itx.user.id):
        await itx.response.send_message("Sem permissao.", ephemeral=True); return
    if remove_ban(valor):
        await itx.response.send_message(f"Desbanido `{valor[:30]}`", ephemeral=True)
    else:
        await itx.response.send_message("Nao achei esse ban.", ephemeral=True)


@bot.tree.command(name="bans", description="Lista bans")
async def s_bans(itx):
    if not is_adm(itx.user.id):
        await itx.response.send_message("Sem permissao.", ephemeral=True); return
    db = load_db(); bans = db.get("bans", {})
    txt = ""
    for t, info in bans.items():
        txt += f"`{t[:30]}` - [{info.get('tipo','?')}] - {info.get('motivo','—')}\n"
    emb = discord.Embed(title=f"BANS ({len(bans)})",
        description=txt[:4000] if txt else "Nenhum", color=0xF87171)
    await itx.response.send_message(embed=emb, ephemeral=True)


@bot.tree.command(name="logs", description="Últimos logs de uso")
async def s_logs(itx):
    if not is_adm(itx.user.id):
        await itx.response.send_message("Sem permissao.", ephemeral=True); return
    db = load_db(); logs = db.get("logs", [])
    txt = ""
    for l in reversed(logs[-25:]):
        txt += f"`{l.get('hwid','')[:12]}` | {l.get('ip','')} | {l.get('key','')[:20]}\n"
    emb = discord.Embed(title=f"LOGS ({len(logs)})",
        description=txt[:4000] if txt else "Nenhum", color=0x2B2B33)
    await itx.response.send_message(embed=emb, ephemeral=True)


@bot.tree.command(name="criarkey", description="Cria key com tempo")
async def s2(itx, nome: str, tempo: str, limite: int = 1):
    if not is_adm(itx.user.id):
        await itx.response.send_message("Sem permissao.", ephemeral=True); return
    secs, warn = parse_time(tempo)
    if secs is None:
        await itx.response.send_message(warn, ephemeral=True); return
    if limite < 1: limite = 1
    key = create_key(nome, secs, limite)
    emb = discord.Embed(title="KEY CRIADA", color=0x4ADE80)
    emb.add_field(name="Key", value=f"```{key}```", inline=False)
    emb.add_field(name="Nome", value=nome, inline=True)
    emb.add_field(name="Duracao", value=human(secs), inline=True)
    emb.add_field(name="Dispositivos", value=str(limite), inline=True)
    await itx.response.send_message(embed=emb, ephemeral=True)


@bot.tree.command(name="criarkeyperm", description="Cria key PERMANENTE")
async def s_perm(itx, nome: str, limite: int = 1):
    if not is_adm(itx.user.id):
        await itx.response.send_message("Sem permissao.", ephemeral=True); return
    if limite < 1: limite = 1
    key = create_key(nome, 0, limite, permanent=True)
    emb = discord.Embed(title="KEY PERMANENTE CRIADA", color=0xFFD700)
    emb.add_field(name="Key", value=f"```{key}```", inline=False)
    emb.add_field(name="Nome", value=nome, inline=True)
    emb.add_field(name="Duracao", value="NUNCA EXPIRA", inline=True)
    emb.add_field(name="Dispositivos", value=str(limite), inline=True)
    await itx.response.send_message(embed=emb, ephemeral=True)


@bot.tree.command(name="manutencao", description="Ativa/desativa manutenção")
async def s_manut(itx, estado: str, motivo: str = "Sistema em manutenção"):
    if not is_adm(itx.user.id):
        await itx.response.send_message("Sem permissao.", ephemeral=True); return
    on = estado.lower() in ("on", "1", "true", "sim", "ativar", "ligar")
    set_config(maintenance=on, message=motivo)
    await itx.response.send_message(
        f"Manutenção: **{'ATIVADA' if on else 'DESATIVADA'}**\nMotivo: `{motivo}`",
        ephemeral=True)


@bot.tree.command(name="link", description="Muda link do Discord")
async def s_link(itx, url: str):
    if not is_adm(itx.user.id):
        await itx.response.send_message("Sem permissao.", ephemeral=True); return
    set_config(discord_link=url)
    await itx.response.send_message(f"Link: `{url}`", ephemeral=True)


@bot.tree.command(name="watermark", description="Muda watermark")
async def s7(itx, texto: str):
    if not is_adm(itx.user.id):
        await itx.response.send_message("Sem permissao.", ephemeral=True); return
    set_config(watermark=texto)
    await itx.response.send_message(f"Watermark: `{texto}`", ephemeral=True)


@bot.tree.command(name="vpnmsg", description="Muda msg VPN")
async def s8(itx, texto: str):
    if not is_adm(itx.user.id):
        await itx.response.send_message("Sem permissao.", ephemeral=True); return
    set_config(vpn_required=texto)
    await itx.response.send_message(f"VPN msg: `{texto}`", ephemeral=True)


@bot.tree.command(name="api", description="URL da API")
async def s11(itx):
    if not is_adm(itx.user.id):
        await itx.response.send_message("Sem permissao.", ephemeral=True); return
    ip = get_local_ip()
    emb = discord.Embed(title="API FOULD STORES", color=0x2B2B33)
    emb.add_field(name="Local", value=f"`http://127.0.0.1:{API_PORT}`", inline=False)
    emb.add_field(name="Rede", value=f"`http://{ip}:{API_PORT}`", inline=False)
    await itx.response.send_message(embed=emb, ephemeral=True)


# ============================================================
#   INICIALIZAÇÃO
# ============================================================

if __name__ == "__main__":
    ip = get_local_ip()
    print("=" * 55)
    print("  FOULD STORES v17.0")
    print("  Dev: MTGXZz TEAM  -  Equipe: FOULD STORES")
    print("=" * 55)
    print(f"  API Local:  http://127.0.0.1:{API_PORT}")
    print(f"  API Rede:   http://{ip}:{API_PORT}")
    print(f"  Banco:      {os.path.abspath(DB_FILE)}")
    print(f"  Admins:     {ADMIN_IDS}")
    print("=" * 55)
    threading.Thread(target=run_flask, daemon=True).start()
    bot.run(BOT_TOKEN)