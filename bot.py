#!/usr/bin/env python3
"""
Bot de Indexa Capital -> Telegram (solo lectura).

Proyecto independiente, no afiliado a Indexa Capital.

En cada ejecución:
  1. Lee tus cuentas activas de Indexa y su índice de rentabilidad
     (time-weighted: no le afectan tus aportaciones ni retiradas).
  2. Avisa cuando la caída desde el máximo cruza un nuevo umbral
     (por defecto 10, 15, 20, 25 y 30 %). Cuando la cartera se recupera,
     avisa una vez y vuelve a armar los avisos.
  3. Avisa cuando Indexa invierte una aportación (fondos, participaciones,
     precio y efectivo pendiente), y de ventas o rebalanceos.
  4. Una vez al mes (desde el día 3) manda un resumen de la cartera.

Configuración (secrets / variables del repositorio en GitHub):
  INDEXA_TOKEN         secret · token de la API de Indexa
  TELEGRAM_BOT_TOKEN   secret · token del bot (de @BotFather)
  TELEGRAM_CHAT_ID     opcional · si no se pone, se detecta solo
  UMBRALES_CAIDA       variable opcional · "10,15,20,25,30"
  RECUPERACION         variable opcional · "5"
  DIA_RESUMEN          variable opcional · "3"
  AVISO_OPERACIONES    variable opcional · "no" para desactivar el aviso de compras

Uso:
  python bot.py              ejecución diaria
  python bot.py --test       prueba: mensaje de confirmación + resumen
  python bot.py --summary    manda el resumen ahora
  python bot.py --dry-run    imprime los mensajes en vez de enviarlos
  python bot.py --debug      estructura de la respuesta de la API (sin importes)
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import requests

API = "https://api.indexacapital.com"
TG = "https://api.telegram.org/bot{token}/{method}"
TZ = ZoneInfo("Europe/Madrid")
STATE_FILE = Path(__file__).with_name("state.json")
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
         "agosto", "septiembre", "octubre", "noviembre", "diciembre"]


# ------------------------------------------------------- avisos y errores


def summary(text: str) -> None:
    """Escribe en el resumen de la ejecución de GitHub (se ve sin abrir logs)."""
    print(text)
    path = os.environ.get("GITHUB_STEP_SUMMARY")
    if path:
        with open(path, "a", encoding="utf-8") as f:
            f.write(text + "\n\n")


class BotError(Exception):
    """Error con explicación para el usuario."""


def env(name: str, default: str = "") -> str:
    return (os.environ.get(name) or default).strip()


def eur(x: float) -> str:
    s = f"{x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{s} €"


def pct(x: float) -> str:
    return f"{x * 100:+.2f}".replace(".", ",") + " %"


def load_state() -> dict:
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_state(state: dict) -> None:
    STATE_FILE.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n",
                          encoding="utf-8")


# ---------------------------------------------------------------- Telegram


class Telegram:
    def __init__(self, token: str, dry: bool = False):
        self.token, self.dry, self.chat_id = token, dry, None

    def call(self, method: str, **payload) -> dict:
        try:
            r = requests.post(TG.format(token=self.token, method=method),
                              json=payload, timeout=30)
        except requests.RequestException as e:
            raise BotError(f"No se pudo conectar con Telegram ({e}). "
                           "Vuelve a probar en unos minutos.")
        data = r.json() if r.headers.get("content-type", "").startswith(
            "application/json") else {}
        if r.status_code in (401, 404):
            raise BotError(
                "**El token del bot de Telegram no es válido.** Revisa el secret "
                "`TELEGRAM_BOT_TOKEN`: debe ser el texto completo que te dio "
                "@BotFather (con el formato `123456789:AA...`), sin espacios.")
        if not data.get("ok"):
            desc = data.get("description", f"HTTP {r.status_code}")
            if "chat not found" in desc or "bot was blocked" in desc:
                raise BotError(
                    "**Telegram no deja escribirte.** Abre tu bot en Telegram y "
                    "pulsa **Iniciar** (o escríbele «hola»). Si lo bloqueaste, "
                    "desbloquéalo. Después vuelve a ejecutar la prueba.")
            raise BotError(f"Telegram devolvió un error: {desc}")
        return data

    def find_private_chat(self) -> int | None:
        """Chat privado más reciente que ha escrito al bot (últimas 24 h)."""
        updates = self.call("getUpdates").get("result", [])
        for u in reversed(updates):
            msg = u.get("message") or u.get("edited_message") or {}
            chat = msg.get("chat") or (u.get("my_chat_member") or {}).get("chat") or {}
            if chat.get("type") == "private":
                return chat["id"]
        return None

    def send(self, text: str) -> None:
        if self.dry:
            print("-" * 40 + "\n" + text)
            return
        self.call("sendMessage", chat_id=self.chat_id, text=text,
                  parse_mode="HTML", disable_web_page_preview=True)


def resolve_chat(tg: Telegram, state: dict, required: bool) -> bool:
    """Secret > guardado en state.json > detectado en Telegram."""
    tg.chat_id = env("TELEGRAM_CHAT_ID") or state.get("telegram_chat_id")
    if tg.chat_id or tg.dry:
        return True
    found = tg.find_private_chat()
    if found is None:
        if required:
            raise BotError(
                "**Todavía no encuentro tu chat de Telegram.** Abre tu bot en "
                "Telegram, pulsa **Iniciar** (o escríbele «hola») y vuelve a "
                "ejecutar la prueba en menos de 24 horas.")
        return False
    tg.chat_id = found
    state["telegram_chat_id"] = found
    return True


# -------------------------------------------------------------- Indexa API


class Indexa:
    def __init__(self, token: str):
        self.s = requests.Session()
        self.s.headers.update({"X-AUTH-TOKEN": token, "Accept": "application/json"})

    def get(self, path: str) -> dict:
        try:
            r = self.s.get(API + path, timeout=30)
        except requests.RequestException as e:
            raise BotError(f"No se pudo conectar con Indexa ({e}). "
                           "Suele ser temporal; se reintentará en la próxima ejecución.")
        if r.status_code in (401, 403):
            raise BotError(
                "**Indexa no acepta tu token.** Puede que lo copiaras incompleto o "
                "que lo hayas regenerado. Entra en Indexa → Configuración de "
                "usuario → Aplicaciones → Generar token, y pega el nuevo en el "
                "secret `INDEXA_TOKEN`.")
        if r.status_code >= 500:
            raise BotError(f"Indexa no responde ahora mismo (HTTP {r.status_code}). "
                           "Se reintentará en la próxima ejecución.")
        r.raise_for_status()
        return r.json()

    def accounts(self) -> tuple[list[str], list[str]]:
        me = self.get("/users/me")
        accs = me.get("accounts", []) or []
        active = [a["account_number"] for a in accs if a.get("status") == "active"]
        others = [a.get("status", "?") for a in accs if a.get("status") != "active"]
        return active, others

    def performance(self, account: str) -> dict:
        return self.get(f"/accounts/{account}/performance")


# ---------------------------------------------------------------- métricas


def series(d: dict | None) -> list[tuple[date, float]]:
    out = []
    for k, v in (d or {}).items():
        try:
            out.append((date.fromisoformat(str(k)[:10]), float(v)))
        except (TypeError, ValueError):
            continue
    return sorted(out)


def value_at(s: list[tuple[date, float]], day: date) -> float | None:
    val = None
    for d, v in s:
        if d > day:
            break
        val = v
    return val


def metrics(perf: dict, today: date) -> dict | None:
    ret = perf.get("return") or {}
    idx = series(ret.get("index"))
    if len(idx) < 2:
        return None

    vals = [v for _, v in idx]
    peak_i = max(range(len(vals)), key=vals.__getitem__)
    last_d, last_v = idx[-1]

    end_prev = date.fromordinal(today.replace(day=1).toordinal() - 1)
    end_prev2 = date.fromordinal(end_prev.replace(day=1).toordinal() - 1)

    def ratio(a, b):
        va, vb = value_at(idx, a), value_at(idx, b)
        if va is None:
            va = idx[0][1]
        return None if vb is None else vb / va - 1

    total = ret.get("total_amount")
    if total is None:
        ta = series(ret.get("total_amounts"))
        total = ta[-1][1] if ta else None

    return {
        "last_date": last_d,
        "drawdown": last_v / vals[peak_i] - 1,
        "peak_date": idx[peak_i][0],
        "prev_month": ratio(end_prev2, end_prev),
        "prev_month_label": f"{MESES[end_prev.month - 1]} {end_prev.year}",
        "ytd": ratio(date(today.year - 1, 12, 31), last_d),
        "total": total,
        "investment": ret.get("investment"),
        "pl": ret.get("pl"),
        "time_return": ret.get("time_return"),
        "time_return_annual": ret.get("time_return_annual"),
    }


# ------------------------------------------------- operaciones con fondos

# Códigos de operación de /instrument-transactions (según clientes open source)
BUY_CODES = {20, 67, 300, 302, 1371}     # suscripción, por traspaso, plan, switch
SELL_CODES = {21, 72, 304, 1372}         # reembolso, por traspaso, plan, switch
TX_HORIZON_DAYS = 90     # operaciones más antiguas no pueden ser "nuevas"
TX_FIRST_RUN_DAYS = 7    # en la primera ejecución solo se avisa de lo reciente


def num(x: float, decimals: int = 2) -> str:
    s = f"{x:,.{decimals}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return s


def tx_date(t: dict) -> date | None:
    try:
        return date.fromisoformat(str(t.get("date"))[:10])
    except ValueError:
        return None


def tx_key(t: dict) -> str:
    inst = t.get("instrument") or {}
    return "|".join(str(x) for x in (t.get("date"), t.get("value_date"),
                                     t.get("operation_code"), inst.get("identifier"),
                                     t.get("titles"), t.get("amount")))


def fetch_transactions(indexa, account: str) -> list[dict] | None:
    try:
        raw = indexa.get(f"/accounts/{account}/instrument-transactions")
    except requests.HTTPError:
        return None  # no disponible: no tocar el estado
    if isinstance(raw, dict):
        raw = raw.get("transactions") or raw.get("data") or []
    return [t for t in raw if isinstance(t, dict)]


def new_transactions(txs: list[dict], st: dict, today: date) -> list[dict]:
    """Operaciones cerradas que no se habían visto. Actualiza st['tx_seen']."""
    horizon = date.fromordinal(today.toordinal() - TX_HORIZON_DAYS)
    recent = {}
    for t in txs:
        d = tx_date(t)
        if d is None or d < horizon or t.get("status", "closed") != "closed":
            continue
        recent[tx_key(t)] = t

    if "tx_seen" not in st:  # primera vez: solo lo de los últimos días
        first = date.fromordinal(today.toordinal() - TX_FIRST_RUN_DAYS)
        new = [t for t in recent.values() if tx_date(t) >= first]
    else:
        seen = set(st["tx_seen"])
        new = [t for k, t in recent.items() if k not in seen]
    st["tx_seen"] = sorted(recent)
    return new


def group_by_day(txs: list[dict]) -> list[list[dict]]:
    groups: dict[str, list[dict]] = {}
    for t in txs:
        groups.setdefault(str(t.get("value_date") or t.get("date"))[:10], []).append(t)
    return [groups[k] for k in sorted(groups)]


def latest_group(txs: list[dict]) -> list[dict]:
    closed = [t for t in txs if t.get("status", "closed") == "closed" and tx_date(t)]
    if not closed:
        return []
    last = max(str(t.get("value_date") or t.get("date"))[:10] for t in closed)
    return [t for t in closed if str(t.get("value_date") or t.get("date"))[:10] == last]


def tx_line(t: dict) -> str:
    name = (t.get("instrument") or {}).get("name") or "Fondo"
    amount = abs(float(t.get("amount") or 0))
    line = f"• {name}: <b>{eur(amount)}</b>"
    titles, price = t.get("titles"), t.get("price")
    if titles and price:
        line += f"\n   {num(abs(float(titles)), 4)} participaciones a {num(float(price), 4)} €"
    return line


def msg_operations(acc: str, group: list[dict], cash: float | None,
                   preview: bool = False) -> str | None:
    codes = lambda t: int(t.get("operation_code") or 0)
    buys = [t for t in group if codes(t) in BUY_CODES]
    sells = [t for t in group if codes(t) in SELL_CODES]
    if not buys and not sells:
        return None

    day = str(group[0].get("value_date") or group[0].get("date"))[:10]
    try:
        day = date.fromisoformat(day).strftime("%d/%m/%Y")
    except ValueError:
        pass
    pre = "🔎 <i>Vista previa de tu última operación</i>\n\n" if preview else ""
    total = lambda ts: sum(abs(float(t.get("amount") or 0)) for t in ts)

    if buys and sells:
        lines = [f"{pre}🔄 <b>Indexa ha rebalanceado tu cartera</b> ({short(acc)})", "",
                 "Vendido:"] + [tx_line(t) for t in sells] + ["", "Comprado:"] + \
                [tx_line(t) for t in buys] + ["", f"Precio del {day}. Es automático: "
                                              "no tienes que hacer nada."]
        return "\n".join(lines)

    if sells:
        lines = [f"{pre}💸 <b>Venta de participaciones</b> ({short(acc)})", ""] + \
                [tx_line(t) for t in sells] + \
                ["", f"Total: <b>{eur(total(sells))}</b> · precio del {day}"]
        return "\n".join(lines)

    lines = [f"{pre}✅ <b>Aportación invertida</b> ({short(acc)})", ""] + \
            [tx_line(t) for t in buys] + \
            ["", f"Total invertido: <b>{eur(total(buys))}</b>", f"Precio del {day}"]
    if cash is not None and cash >= 1:
        lines.append(f"\nEfectivo pendiente de invertir: {eur(cash)}. Indexa lo "
                     "invertirá cuando pueda comprar al menos 100 € en cada fondo.")
    return "\n".join(lines)


def pending_cash(indexa, account: str) -> float | None:
    try:
        p = indexa.get(f"/accounts/{account}/portfolio")
    except requests.HTTPError:
        return None
    cash = (p.get("portfolio") or {}).get("cash_amount")
    if cash is None:
        cash = ((p.get("cash_accounts") or [{}])[0] or {}).get("amount")
    try:
        return float(cash) if cash is not None else None
    except (TypeError, ValueError):
        return None


def operation_messages(indexa, acc: str, st: dict, today: date,
                       preview: bool = False) -> list[str]:
    txs = fetch_transactions(indexa, acc)
    if txs is None:
        return []
    fresh = new_transactions(txs, st, today)
    groups = group_by_day(fresh)
    if preview and not groups:
        last = latest_group(txs)
        groups = [last] if last else []
    msgs, cash = [], None
    for i, g in enumerate(groups):
        is_last = i == len(groups) - 1
        has_buy = any(int(t.get("operation_code") or 0) in BUY_CODES for t in g)
        if is_last and has_buy and cash is None:
            cash = pending_cash(indexa, acc)
        m = msg_operations(acc, g, cash if is_last else None,
                           preview=preview and not fresh)
        if m:
            msgs.append(m)
    return msgs


# ---------------------------------------------------------------- mensajes


def short(acc: str) -> str:
    return f"cuenta …{acc[-3:]}"


def msg_alert(acc: str, m: dict, tier: int) -> str:
    return (f"⚠️ <b>Indexa: caída de más del {tier} %</b> ({short(acc)})\n\n"
            f"Caída desde el máximo: <b>{pct(m['drawdown'])}</b>\n"
            f"Máximo: {m['peak_date']:%d/%m/%Y} · Último dato: {m['last_date']:%d/%m/%Y}\n"
            + (f"Valor actual: {eur(m['total'])}\n" if m["total"] is not None else "")
            + "\nTu aportación periódica no cambia. Este aviso es solo por si "
              "quieres hacer una aportación extra.")


def msg_recovered(acc: str, m: dict) -> str:
    return (f"✅ <b>Indexa: cartera recuperada</b> ({short(acc)})\n"
            f"Caída desde el máximo: {pct(m['drawdown'])}. Avisos rearmados.")


def msg_summary(acc: str, m: dict) -> str:
    lines = [f"📊 <b>Resumen Indexa · {m['prev_month_label']}</b> ({short(acc)})", ""]
    if m["total"] is not None:
        lines.append(f"Valor: <b>{eur(m['total'])}</b>")
    if m["investment"] is not None:
        lines.append(f"Aportado neto: {eur(m['investment'])}")
    if m["pl"] is not None:
        lines.append(f"Ganancia/pérdida: {eur(m['pl'])}")
    lines.append("")
    if m["prev_month"] is not None:
        lines.append(f"Rentabilidad {m['prev_month_label']}: {pct(m['prev_month'])}")
    if m["ytd"] is not None:
        lines.append(f"Rentabilidad en el año: {pct(m['ytd'])}")
    if m["time_return"] is not None:
        tra = (f" ({pct(m['time_return_annual'])} anual)"
               if m["time_return_annual"] is not None else "")
        lines.append(f"Rentabilidad total: {pct(m['time_return'])}{tra}")
    lines.append(f"Caída desde el máximo: {pct(m['drawdown'])}")
    lines.append(f"\n<i>Datos a {m['last_date']:%d/%m/%Y}</i>")
    return "\n".join(lines)


# -------------------------------------------------------------------- main


def debug_shape(x, depth=0, max_depth=3):
    pad = "  " * depth
    if isinstance(x, dict):
        keys = list(x)
        if keys and all(len(str(k)) >= 10 and str(k)[4] == "-" for k in keys[:3]):
            print(f"{pad}<serie de {len(keys)} fechas: {keys[0]} .. {keys[-1]}>")
            return
        for k in keys:
            print(f"{pad}{k}: {type(x[k]).__name__}")
            if depth < max_depth:
                debug_shape(x[k], depth + 1, max_depth)
    elif isinstance(x, list) and x and depth < max_depth:
        print(f"{pad}[{len(x)} elementos]")
        debug_shape(x[0], depth + 1, max_depth)


def parse_config() -> tuple[list[int], float, int]:
    try:
        tiers = sorted({int(t) for t in env("UMBRALES_CAIDA", "10,15,20,25,30")
                        .replace(" ", "").split(",") if t})
        recovery = float(env("RECUPERACION", "5").replace(",", ".")) / 100
        day = int(env("DIA_RESUMEN", "3"))
        assert tiers and all(0 < t < 100 for t in tiers) and 1 <= day <= 28
    except (ValueError, AssertionError):
        raise BotError(
            "**Alguna variable de configuración tiene un formato incorrecto.** "
            "`UMBRALES_CAIDA` debe ser algo como `10,15,20`, `RECUPERACION` un "
            "número como `5` y `DIA_RESUMEN` un día entre 1 y 28. Si no quieres "
            "cambiarlas, borra esas variables y se usarán los valores por defecto.")
    return tiers, recovery, day


def run(a) -> None:
    scheduled = not (a.test or a.summary or a.dry_run or a.debug)

    indexa_token = env("INDEXA_TOKEN")
    tg_token = env("TELEGRAM_BOT_TOKEN")
    missing = [n for n, v in (("TELEGRAM_BOT_TOKEN", tg_token),
                              ("INDEXA_TOKEN", indexa_token)) if not v]
    if a.dry_run or a.debug:
        missing = [m for m in missing if m != "TELEGRAM_BOT_TOKEN"]
    if missing:
        msg = ("**Falta configurar:** " + ", ".join(f"`{m}`" for m in missing) +
               ". Añádelo en Settings → Secrets and variables → Actions → "
               "New repository secret (paso 5 de la guía).")
        if scheduled:  # aún configurando: no marcar error cada día
            summary("ℹ️ " + msg)
            return
        raise BotError(msg)

    tiers, recovery, summary_day = parse_config()
    indexa = Indexa(indexa_token)

    if a.debug:
        accounts, _ = indexa.accounts()
        print(f"Cuentas activas: {len(accounts)}")
        for acc in accounts:
            print(f"\n/accounts/{short(acc)}/performance:")
            debug_shape(indexa.performance(acc))
            print(f"\n/accounts/{short(acc)}/instrument-transactions:")
            debug_shape(fetch_transactions(indexa, acc) or [])
        return

    state = load_state()
    tg = Telegram(tg_token, a.dry_run)
    if not resolve_chat(tg, state, required=not scheduled):
        summary("ℹ️ Aún no conozco tu chat de Telegram. Escribe «hola» a tu bot "
                "y ejecuta la prueba (paso 6 de la guía).")
        return
    a._tg = tg  # para poder avisar de errores por Telegram
    if not a.dry_run:
        save_state(state)  # guarda el chat aunque luego falle Indexa

    now = datetime.now(TZ).date()
    month_key = f"{now:%Y-%m}"
    acc_state = state.setdefault("accounts", {})
    send_summary = a.test or a.summary or (
        now.day >= summary_day and state.get("last_summary") != month_key)

    accounts, other_statuses = indexa.accounts()
    if a.test:
        tg.send("🤖 <b>Bot de Indexa conectado correctamente.</b>\n"
                "Te avisaré si tu cartera cae con fuerza y te mandaré un resumen "
                "cada mes.")
    if not accounts:
        text = ("Tu cuenta de Indexa todavía no está activa. Es normal si aún "
                "no has hecho tu primera aportación: en cuanto Indexa invierta "
                "tu dinero, el bot empezará a vigilarla solo.")
        if a.test:
            tg.send(text)
        summary(f"ℹ️ {text} (estados: {', '.join(other_statuses) or 'ninguna cuenta'})")
        if not a.dry_run:
            save_state(state)
        return

    ops_on = env("AVISO_OPERACIONES", "si").lower() not in ("no", "false", "0")
    sent = 0
    for acc in accounts:
        st = acc_state.setdefault(acc, {"alert_tier": 0})
        if ops_on:
            for msg in operation_messages(indexa, acc, st, now, preview=a.test):
                tg.send(msg)
                sent += 1

        m = metrics(indexa.performance(acc), now)
        if m is None:
            text = (f"{short(acc)}: todavía no hay datos de rentabilidad. "
                    "Aparecerán unos días después de tu primera inversión.")
            if a.test:
                tg.send(text)
            summary("ℹ️ " + text)
            continue

        hit = max([t for t in tiers if m["drawdown"] <= -t / 100], default=0)

        if hit > st["alert_tier"]:
            tg.send(msg_alert(acc, m, hit))
            st["alert_tier"] = hit
            sent += 1
        elif st["alert_tier"] > 0 and m["drawdown"] > -recovery:
            tg.send(msg_recovered(acc, m))
            st["alert_tier"] = 0
            sent += 1

        if send_summary:
            tg.send(msg_summary(acc, m))
            sent += 1

    if send_summary and scheduled:
        state["last_summary"] = month_key
    if not a.dry_run:
        save_state(state)
    summary(f"✅ Todo correcto · {len(accounts)} cuenta(s) revisada(s) · "
            f"{sent} mensaje(s) enviado(s)")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--test", action="store_true")
    ap.add_argument("--summary", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--debug", action="store_true")
    a = ap.parse_args()
    a._tg = None
    try:
        run(a)
    except BotError as e:
        summary(f"❌ {e}")
        tg = a._tg
        if tg is not None and tg.chat_id and not tg.dry:
            try:  # avisar también por Telegram si es posible
                tg.send("❌ <b>El bot de Indexa tiene un problema</b>\n\n" +
                        str(e).replace("**", "").replace("`", ""))
            except BotError:
                pass
        sys.exit(1)


if __name__ == "__main__":
    main()
