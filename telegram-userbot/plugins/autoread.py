"""Guruh / kanal / bot xabarlarini avtomatik o'qilgan qiladi.

Yoqilganda (.autoread on):
  1) Yangi kelgan guruh/kanal/bot xabari darhol o'qilgan bo'ladi.
  2) Har necha daqiqada BARCHA guruh/kanal/bot chatlari qayta tekshirilib,
     o'qilmaganlari o'qilgan qilinadi (doimiy toza turadi).
Shaxsiy (tirik odam) xabarlariga tegilmaydi — ularni o'zingiz ko'rasiz.

Buyruqlar:
  .autoread on | off | status
  .readall    — hozir mavjud barcha guruh/kanal/bot chatlarini o'qilgan qiladi
"""
import asyncio

from telethon import events

from . import _state as state
from ._helpers import command, register_all

STATE = {"enabled": state.get("autoread", False)}

SWEEP_INTERVAL = 180   # har necha soniyada hammasini qayta tekshirish (3 daqiqa)
FIRST_SWEEP_DELAY = 15  # ishga tushgach birinchi tekshiruvgacha


async def _sweep_once(client) -> int:
    """Barcha guruh/kanal/bot chatlarini o'qilgan qiladi. O'qilgan chat sonini qaytaradi."""
    count = 0
    async for dialog in client.iter_dialogs():
        try:
            if not dialog.unread_count:
                continue
            is_bot = dialog.is_user and getattr(dialog.entity, "bot", False)
            if dialog.is_group or dialog.is_channel or is_bot:
                await client.send_read_acknowledge(dialog.id)
                count += 1
        except Exception:  # noqa: BLE001
            pass
    return count


async def _sweeper(client):
    """Doimiy fon vazifasi: vaqti-vaqti bilan hammasini o'qib turadi."""
    await asyncio.sleep(FIRST_SWEEP_DELAY)
    while True:
        if STATE["enabled"]:
            try:
                n = await _sweep_once(client)
                if n:
                    print(f"[autoread] davriy o'qish: {n} ta chat", flush=True)
            except Exception as e:  # noqa: BLE001
                print(f"[autoread] sweeper xato: {e}", flush=True)
        await asyncio.sleep(SWEEP_INTERVAL)


async def _on_incoming(event):
    if not STATE["enabled"]:
        return
    try:
        target = event.is_group or event.is_channel
        if not target and event.is_private:
            sender = await event.get_sender()
            target = bool(getattr(sender, "bot", False))
        if target:
            await event.mark_read()
    except Exception as e:  # noqa: BLE001
        print(f"[autoread] xato: {e}", flush=True)


@command("autoread", "Guruh/kanal/bot xabarlarini doimo o'qiydi (on/off/status)")
async def autoread_cmd(event):
    arg = event.pattern_match.group(1).strip().lower()
    if arg == "on":
        STATE["enabled"] = True
        state.set("autoread", True)
        await event.edit(
            "👁 **Avto-o'qish YOQILDI (doimiy)**\n"
            "Guruh, kanal va botlar avtomatik o'qiladi — yangi kelganda ham, "
            "har 3 daqiqada qayta ham. Shaxsiy xabarlarga tegilmaydi."
        )
    elif arg == "off":
        STATE["enabled"] = False
        state.set("autoread", False)
        await event.edit("Avto-o'qish **O'CHIRILDI**.")
    else:
        holat = "YOQILGAN 👁" if STATE["enabled"] else "O'CHIRILGAN ⛔"
        await event.edit(
            f"ℹ️ Avto-o'qish (doimiy): {holat}\n"
            f"Tekshiruv oralig'i: {SWEEP_INTERVAL}s\nYoqish: `.autoread on`"
        )


@command("readall", "Barcha guruh/kanal/bot chatlarini hozir o'qilgan qiladi")
async def readall_cmd(event):
    await event.edit("👁 O'qilmoqda...")
    count = await _sweep_once(event.client)
    await event.edit(f"✅ {count} ta guruh/kanal/bot chati o'qildi.")


def register(client):
    register_all(client, __import__(__name__, fromlist=["_"]))
    client.add_event_handler(_on_incoming, events.NewMessage(incoming=True))
    # Doimiy fon-o'qish vazifasini ishga tushiramiz
    asyncio.create_task(_sweeper(client))
