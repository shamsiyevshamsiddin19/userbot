"""Guruh / kanal / bot xabarlarini avtomatik va qo'lda o'qish.

Yoqilganda (.autoread on):
  1) Yangi kelgan guruh/kanal/bot xabari darhol o'qilgan bo'ladi.
  2) Har necha daqiqada BARCHA guruh/kanal/bot chatlari qayta tekshirilib,
     o'qilmaganlari o'qilgan qilinadi (doimiy toza turadi).
Shaxsiy (tirik odam) xabarlariga tegilmaydi.

Buyruqlar:
  .autoread on | off | status
  .readall       — barcha guruh + kanal + bot chatlarini o'qiydi
  .readgroups    — faqat guruhlarni o'qiydi
  .readchannels  — faqat kanallarni o'qiydi
  .readbots      — faqat bot chatlarini o'qiydi
"""
import asyncio

from telethon import events

from . import _state as state
from ._helpers import command, register_all

STATE = {"enabled": state.get("autoread", False)}

SWEEP_INTERVAL = 180   # har necha soniyada hammasini qayta tekshirish (3 daqiqa)
FIRST_SWEEP_DELAY = 15  # ishga tushgach birinchi tekshiruvgacha


async def _sweep(client, kinds) -> int:
    """kinds ichidagi turlar bo'yicha o'qilmagan chatlarni o'qilgan qiladi.

    kinds: {"group", "channel", "bot"} to'plamining bo'lagi.
    """
    count = 0
    async for dialog in client.iter_dialogs():
        try:
            if not dialog.unread_count:
                continue
            is_bot = dialog.is_user and getattr(dialog.entity, "bot", False)
            # Kanal = faqat broadcast (superguruh "group" ga kiradi)
            is_channel = dialog.is_channel and not dialog.is_group
            match = (
                ("group" in kinds and dialog.is_group)
                or ("channel" in kinds and is_channel)
                or ("bot" in kinds and is_bot)
            )
            if match:
                await client.send_read_acknowledge(dialog.id)
                count += 1
        except Exception:  # noqa: BLE001
            pass
    return count


ALL_KINDS = {"group", "channel", "bot"}


async def _sweeper(client):
    """Doimiy fon vazifasi: vaqti-vaqti bilan hammasini o'qib turadi."""
    await asyncio.sleep(FIRST_SWEEP_DELAY)
    while True:
        if STATE["enabled"]:
            try:
                n = await _sweep(client, ALL_KINDS)
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
            "Guruh, kanal va botlar avtomatik o'qiladi. Shaxsiylarga tegilmaydi."
        )
    elif arg == "off":
        STATE["enabled"] = False
        state.set("autoread", False)
        await event.edit("Avto-o'qish **O'CHIRILDI**.")
    else:
        holat = "YOQILGAN 👁" if STATE["enabled"] else "O'CHIRILGAN ⛔"
        await event.edit(
            f"ℹ️ Avto-o'qish (doimiy): {holat}\n"
            f"Qo'lda: `.readall` `.readgroups` `.readchannels` `.readbots`"
        )


@command("readall", "Barcha guruh/kanal/bot chatlarini o'qiydi")
async def readall_cmd(event):
    await event.edit("👁 O'qilmoqda...")
    n = await _sweep(event.client, ALL_KINDS)
    await event.edit(f"✅ {n} ta guruh/kanal/bot chati o'qildi.")


@command("readgroups", "Faqat guruhlarni o'qiydi")
async def readgroups_cmd(event):
    await event.edit("👥 Guruhlar o'qilmoqda...")
    n = await _sweep(event.client, {"group"})
    await event.edit(f"✅ {n} ta guruh o'qildi.")


@command("readchannels", "Faqat kanallarni o'qiydi")
async def readchannels_cmd(event):
    await event.edit("📢 Kanallar o'qilmoqda...")
    n = await _sweep(event.client, {"channel"})
    await event.edit(f"✅ {n} ta kanal o'qildi.")


@command("readbots", "Faqat bot chatlarini o'qiydi")
async def readbots_cmd(event):
    await event.edit("🤖 Botlar o'qilmoqda...")
    n = await _sweep(event.client, {"bot"})
    await event.edit(f"✅ {n} ta bot chati o'qildi.")


def register(client):
    register_all(client, __import__(__name__, fromlist=["_"]))
    client.add_event_handler(_on_incoming, events.NewMessage(incoming=True))
    asyncio.create_task(_sweeper(client))
