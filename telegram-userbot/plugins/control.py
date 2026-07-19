"""Boshqaruv paneli — barcha rejimlarni bitta joydan yoqib/o'chirish.

Buyruqlar:
  .bot            — panel: qaysi rejim yoqilganini ko'rsatadi
  .bot on         — ishchi rejim: avto-javob + avto-o'qish YOQILADI
  .bot off        — hamma rejim O'CHADI
  .bot autoreply  — avto-javobni yoqib/o'chiradi (toggle)
  .bot autoread   — avto-o'qishni yoqib/o'chiradi
  .bot autoai     — yarim-avtomatik taklifni yoqib/o'chiradi
"""
from . import _state as state
from . import autoai, autoread, autoreply
from ._helpers import command, register_all

# nom -> (modul, ko'rinadigan nom)
FEATURES = {
    "autoreply": (autoreply, "🤖 Avto-javob"),
    "autoread": (autoread, "👁 Avto-o'qish"),
    "autoai": (autoai, "📝 Yarim-avto taklif"),
}


def _set(name, value):
    mod, _ = FEATURES[name]
    mod.STATE["enabled"] = value
    state.set(name, value)
    # autoai o'chganda kutayotgan takliflarni tozalaymiz
    if name == "autoai" and not value:
        getattr(mod, "PENDING", {}).clear()


def _panel():
    lines = ["**🎛 Boshqaruv paneli**\n"]
    for name, (mod, label) in FEATURES.items():
        on = mod.STATE.get("enabled")
        lines.append(f"{'🟢' if on else '⚪️'} {label} — `{name}`")
    lines.append("\n`.bot on` — ishchi rejim  |  `.bot off` — hammasi o‘chadi")
    lines.append("`.bot <nom>` — bittasini yoqib/o‘chirish")
    return "\n".join(lines)


@command("bot", "Boshqaruv paneli — rejimlarni yoqib/o'chirish (.bot on/off)")
async def bot_cmd(event):
    arg = event.pattern_match.group(1).strip().lower()
    if arg == "on":
        _set("autoreply", True)
        _set("autoread", True)
        await event.edit("🟢 **Ishchi rejim YOQILDI** (avto-javob + avto-o'qish)\n\n" + _panel())
    elif arg == "off":
        for name in FEATURES:
            _set(name, False)
        await event.edit("⛔ **Hamma rejim O'CHIRILDI**\n\n" + _panel())
    elif arg in FEATURES:
        _, label = FEATURES[arg]
        new_value = not FEATURES[arg][0].STATE.get("enabled")
        _set(arg, new_value)
        holat = "🟢 yoqildi" if new_value else "⚪️ o‘chirildi"
        await event.edit(f"{label}: {holat}\n\n" + _panel())
    else:
        await event.edit(_panel())


def register(client):
    register_all(client, __import__(__name__, fromlist=["_"]))
