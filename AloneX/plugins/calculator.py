import ast
import math
import operator
import re

from pyrogram import filters, enums, errors
from pyrogram.enums import ButtonStyle
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from AloneX import pbot as app, prefix_cmds, font

__module__ = "𝐂ᴀʟᴄᴜʟᴀᴛᴏʀ🧮"

__help__ = """
**Calculator🧮**

**Description:**
Perform calculations directly using the bot. Basic and scientific mode (angles are in degrees).

**Commands:**
❂ `/calc` or `/calculator` – Open interactive calculator

**Scientific mode:** sin, cos, tan, log, ln, √, x², π, e, n!
"""

MAX_LEN = 80            # longest expression that can be typed
MAX_STATES = 500        # open calculators kept in memory
calc_states = {}


# ── safe evaluator (NO eval: callback data can be forged by modified Telegram clients) ──
def _pow(a, b):
    if a == 0 and b < 0:
        raise ZeroDivisionError
    r = a ** b                      # floats only: a huge power raises OverflowError instead of hanging
    if isinstance(r, complex):
        raise ValueError("complex result")
    return r


def _fact(x):
    if x < 0 or x != int(x) or x > 170:
        raise ValueError("bad factorial")
    return float(math.factorial(int(x)))


def _tan(x):
    if x % 180 == 90:
        raise ValueError("tan undefined")
    return math.tan(math.radians(x))


_BIN = {
    ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
    ast.Div: operator.truediv, ast.Mod: operator.mod, ast.FloorDiv: operator.floordiv,
}
_FUNC = {
    "sin": lambda x: math.sin(math.radians(x)),
    "cos": lambda x: math.cos(math.radians(x)),
    "tan": _tan,
    "log": math.log10,
    "ln": math.log,
    "sqrt": math.sqrt,
    "abs": abs,
    "fact": _fact,
}
_CONST = {"pi": math.pi, "e": math.e}


def _eval(node):
    if isinstance(node, ast.Expression):
        return _eval(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
        return float(node.value)
    if isinstance(node, ast.Name) and node.id in _CONST:
        return _CONST[node.id]
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
        v = _eval(node.operand)
        return v if isinstance(node.op, ast.UAdd) else -v
    if isinstance(node, ast.BinOp):
        left, right = _eval(node.left), _eval(node.right)
        if isinstance(node.op, ast.Pow):
            return _pow(left, right)
        op = _BIN.get(type(node.op))
        if op:
            return op(left, right)
    if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in _FUNC
            and len(node.args) == 1 and not node.keywords):
        return _FUNC[node.func.id](_eval(node.args[0]))
    raise ValueError("unsupported expression")


def _prepare(text: str) -> str:
    t = text.replace("×", "*").replace("÷", "/").replace("^", "**").replace("π", "pi").replace("√", "sqrt")
    t = re.sub(r"(?<=[\d)])(?=[a-z(])", "*", t)        # 2(3)  2sin(30)  (1+2)(3+4)  2pi
    t = re.sub(r"(?<=\))(?=\d)", "*", t)               # (1+2)3
    t = re.sub(r"(?<=\bpi)(?=[\d(a-z])", "*", t)       # pi2  pi(2)
    t = re.sub(r"(?<=\be)(?=[\d(a-z])", "*", t)        # e2   e(2)
    return t


def _fmt(x: float) -> str:
    if math.isnan(x) or math.isinf(x):
        raise OverflowError
    if abs(x) < 1e-12:
        x = 0.0
    if x.is_integer() and abs(x) < 1e15:
        return str(int(x))
    return f"{x:.10g}"


def calcExpression(text: str):
    """Returns (result, error). Exactly one of them is None."""
    if not text.strip():
        return "0", None
    try:
        tree = ast.parse(_prepare(text), mode="eval")
        return _fmt(_eval(tree)), None
    except ZeroDivisionError:
        return None, "Cannot divide by zero"
    except OverflowError:
        return None, "Number too large"
    except (ValueError, SyntaxError, TypeError, RecursionError, MemoryError):
        return None, "Invalid expression"


# ── keyboards ────────────────────────────────────────────────────────────────
# callback code -> text that is added to the expression
INSERT = {
    "sin": "sin(", "cos": "cos(", "tan": "tan(", "log": "log(", "ln": "ln(",
    "rt": "√(", "sq": "^2", "pi": "π", "e": "e", "fa": "fact(",
}
OPERATORS = set("+-*/") | {"sq"}                      # keep working on the last result
CONTROL = {"D", "A", "=", "C", "S", "B"}
ALLOWED = set("0123456789.()+-*/") | set(INSERT) | CONTROL


def _b(label, uid, code, style):
    return InlineKeyboardButton(label, callback_data=f"c|{uid}|{code}", style=style)


def _pad(uid):
    P, S, D = ButtonStyle.PRIMARY, ButtonStyle.SUCCESS, ButtonStyle.DANGER
    return [
        [_b("7", uid, "7", P), _b("8", uid, "8", P), _b("9", uid, "9", P), _b("÷", uid, "/", S), _b(font("DEL"), uid, "D", D)],
        [_b("4", uid, "4", P), _b("5", uid, "5", P), _b("6", uid, "6", P), _b("×", uid, "*", S), _b(font("AC"), uid, "A", D)],
        [_b("1", uid, "1", P), _b("2", uid, "2", P), _b("3", uid, "3", P), _b("-", uid, "-", S), _b("(", uid, "(", S)],
        [_b("0", uid, "0", P), _b(".", uid, ".", P), _b("=", uid, "=", S), _b("+", uid, "+", S), _b(")", uid, ")", S)],
    ]


def calc_btn(uid):
    P, D = ButtonStyle.PRIMARY, ButtonStyle.DANGER
    rows = _pad(uid) + [[
        _b(font("🧮 Scientific"), uid, "S", P),
        _b(font("❌ Close"), uid, "C", D),
    ]]
    return InlineKeyboardMarkup(rows)


def sci_btn(uid):
    P, S, D = ButtonStyle.PRIMARY, ButtonStyle.SUCCESS, ButtonStyle.DANGER
    rows = [
        [_b("sin", uid, "sin", S), _b("cos", uid, "cos", S), _b("tan", uid, "tan", S), _b("log", uid, "log", S), _b("ln", uid, "ln", S)],
        [_b("√", uid, "rt", S), _b("x²", uid, "sq", S), _b("π", uid, "pi", S), _b("e", uid, "e", S), _b("n!", uid, "fa", S)],
    ] + _pad(uid) + [[
        _b(font("🧮 Basic"), uid, "B", P),
        _b(font("❌ Close"), uid, "C", D),
    ]]
    return InlineKeyboardMarkup(rows)


def _show(text: str) -> str:
    shown = (text or "0").replace("*", "×").replace("/", "÷")
    return f"`{shown}`"


def _remember(key):
    if key not in calc_states and len(calc_states) >= MAX_STATES:
        calc_states.pop(next(iter(calc_states)))      # forget the oldest calculator
    return calc_states.setdefault(key, {"text": "", "mode": "basic", "done": False})


# ── handlers ─────────────────────────────────────────────────────────────────
@app.on_message(filters.command(["calc", "calculate", "calculator"], prefix_cmds) & ~filters.forwarded, group=25)
async def calculate_handler(client, message):
    if not message.from_user:
        return
    uid = message.from_user.id
    sent = await message.reply_text(
        _show(""),
        reply_markup=calc_btn(uid),
        parse_mode=enums.ParseMode.MARKDOWN,
        quote=True,
    )
    calc_states.pop(f"{uid}:{sent.chat.id}:{sent.id}", None)
    _remember(f"{uid}:{sent.chat.id}:{sent.id}")


@app.on_callback_query(filters.regex(r"^c\|"))
async def calc_cb(client, query):
    try:
        parts = query.data.split("|")
        uid = int(parts[1])
        data = parts[2]

        if query.from_user.id != uid:
            return await query.answer(font("⚠️ This is not your calculator!"), show_alert=True)
        if data not in ALLOWED or not query.message:
            return await query.answer()

        key = f"{uid}:{query.message.chat.id}:{query.message.id}"
        if data == "C":
            calc_states.pop(key, None)
            await query.message.delete()
            return await query.answer()

        state = _remember(key)
        text = state["text"]

        if data == "S":
            state["mode"] = "scientific"
        elif data == "B":
            state["mode"] = "basic"
        elif data == "A":
            text, state["done"] = "", False
        elif data == "D":
            text, state["done"] = text[:-1], False
        elif data == "=":
            result, err = calcExpression(text)
            if err:
                return await query.answer(f"⚠️ {err}", show_alert=False)
            text, state["done"] = ("" if result == "0" and not text else result), True
        else:
            if state["done"] and (data not in OPERATORS or re.search(r"\d[eE][+-]?\d", text)):
                text = ""                              # a new number starts a new calculation
            state["done"] = False
            add = INSERT.get(data, data)
            if len(text) + len(add) > MAX_LEN:
                return await query.answer(font("⚠️ Too long!"), show_alert=False)
            text += add

        state["text"] = text
        markup = sci_btn(uid) if state["mode"] == "scientific" else calc_btn(uid)
        try:
            await query.message.edit_text(_show(text), reply_markup=markup, parse_mode=enums.ParseMode.MARKDOWN)
        except errors.MessageNotModified:
            pass
        await query.answer()

    except Exception:
        try:
            await query.answer(font("Error!"), show_alert=False)
        except Exception:
            pass
