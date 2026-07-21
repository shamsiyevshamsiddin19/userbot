"""Shaxsiy chatga javob QORALAMASINI tayyorlab qo'yadi (yubormaydi).

Yoqilganda (.autodraft on) shaxsiy xabar kelsa, Gemini javob matnini o'sha
chatning yozish qatoriga (draft) tayyorlab qo'yadi. Siz o'qib, tahrirlab,
o'zingiz Send bosasiz. Hech narsa avtomatik yuborilmaydi.

Buyruqlar:
  .autodraft on | off | status
"""
import os

from telethon import events
from telethon.tl.functions.messages import SaveDraftRequest

import config

from . import _state as state
from ._helpers import command, register_all
from .ai import ask_gemini

STATE = {"enabled": state.get("autodraft", False)}

HISTORY_LIMIT = 8
_PERSONA_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "persona.txt"
)
_DEFAULT_PERSONA = (
    "Sen foydalanuvchi o'rniga uning shaxsiy suhbatlariga qisqa, tabiiy va muloyim "
    "javob matnini yozadigan yordamchisan. Faqat javob matnini yoz. Xabar qaysi "
    "tilda bo'lsa o'sha tilda javob ber. Aniq narsani (vaqt, pul, va'da) bilmasang "
    "o'ylab topma — 'tez orada aniq javob beraman' deb yoz."
)


def _persona():
    try:
        with open(_PERSONA_FILE, encoding="utf-8") as f:
            txt = f.read().strip()
        if txt:
            return txt
    except Exception:  # noqa: BLE001
        pass
    return _DEFAULT_PERSONA


async def _on_incoming(event):
    if not STATE["enabled"]:
        return
    if not event.is_private or not event.text:
        return
    sender = await event.get_sender()
    if sender is None or getattr(sender, "bot", False):
        return
    if getattr(sender, "id", None) in config.OWN_ACCOUNT_IDS:
        return

    try:
        # Suhbat konteksti bilan tabiiy javob
        history = []
        async for msg in event.client.iter_messages(event.chat_id, limit=HISTORY_LIMIT):
            if msg.text:
                who = "Men" if msg.out else "Suhbatdosh"
                history.append(f"{who}: {msg.text}")
        history.reverse()
        convo = "\n".join(history) if history else f"Suhbatdosh: {event.text}"
        prompt = (
            "Quyida Telegram suhbati (sen 'Men' rolidasan). "
            "Oxirgi xabarga qisqa, tabiiy javob matnini tayyorla:\n\n" + convo
        )
        reply = await ask_gemini(prompt, system=_persona())
        if reply and reply[0] not in "❌⚠️🤔":
            # Javobni chatning yozish qatoriga QORALAMA qilib qo'yamiz (yubormaymiz)
            await event.client(SaveDraftRequest(
                peer=await event.get_input_chat(),
                message=reply[:4096],
                no_webpage=True,
            ))
            print(f"[autodraft] qoralama tayyor: {reply[:50]!r}", flush=True)
    except Exception as e:  # noqa: BLE001
        print(f"[autodraft] xato: {e}", flush=True)


@command("autodraft", "Shaxsiy chatga javob qoralamasini tayyorlaydi (on/off/status)")
async def autodraft_cmd(event):
    arg = event.pattern_match.group(1).strip().lower()
    if arg == "on":
        STATE["enabled"] = True
        state.set("autodraft", True)
        await event.edit(
            "✍️ **Qoralama rejimi YOQILDI**\n"
            "Shaxsiy xabarga javob matni o'sha chatning yozish qatoriga tayyorlab "
            "qo'yiladi. O'qib, tahrirlab, o'zingiz Send bosasiz — avtomat yuborilmaydi."
        )
    elif arg == "off":
        STATE["enabled"] = False
        state.set("autodraft", False)
        await event.edit("✍️ Qoralama rejimi **O'CHIRILDI**.")
    else:
        holat = "YOQILGAN ✍️" if STATE["enabled"] else "O'CHIRILGAN ⛔"
        await event.edit(f"ℹ️ Qoralama rejimi: {holat}\nYoqish: `.autodraft on`")


def register(client):
    register_all(client, __import__(__name__, fromlist=["_"]))
    client.add_event_handler(_on_incoming, events.NewMessage(incoming=True))
