# invite_from_group.py
import asyncio
import json
import random
import time
from pathlib import Path

from telethon import TelegramClient, errors
from telethon.tl.functions.channels import InviteToChannelRequest

# ---------------------- CONFIG ----------------------
API_ID = 26531485
API_HASH = "7ae9b39f4acdc709219b8ef1f073d067"
PHONE = "+918074526151"

SOURCE_GROUP = '@telugusubforsubtelugusub4subtelu'
DESTINATION_CHAT = '@DiscountDiveX'
MAX_INVITES_PER_RUN = 3
MIN_SLEEP_BETWEEN_INVITES = 10
MAX_SLEEP_BETWEEN_INVITES = 25
DATA_FILE = 'invited_users.json'
# ----------------------------------------------------

async def load_invited(path: Path):
    if path.exists():
        try:
            return set(json.loads(path.read_text()))
        except Exception:
            return set()
    return set()

async def save_invited(path: Path, invited_set):
    path.write_text(json.dumps(list(invited_set), indent=2))

async def main():
    client = TelegramClient('session_' + PHONE, API_ID, API_HASH)
    await client.connect()
    if not await client.is_user_authorized():
        await client.send_code_request(PHONE)
        try:
            await client.sign_in(PHONE, input('Enter the code: '))
        except errors.SessionPasswordNeededError:
            pw = input('Two-step password: ')
            await client.sign_in(password=pw)

    # Resolve entities
    try:
        src = await client.get_entity(SOURCE_GROUP)
    except Exception as e:
        print(f"❌ Could not resolve source group '{SOURCE_GROUP}': {e}")
        await client.disconnect()
        return

    try:
        dest = await client.get_entity(DESTINATION_CHAT)
    except Exception as e:
        print(f"❌ Could not resolve destination '{DESTINATION_CHAT}': {e}")
        await client.disconnect()
        return

    data_path = Path(DATA_FILE)
    invited = await load_invited(data_path)

    # Collect eligible members from source group
    members = []
    try:
        async for u in client.iter_participants(src):
            if getattr(u, 'bot', False):
                continue
            if u.is_self:
                continue
            uid = getattr(u, 'id', None)
            if uid is None:
                continue
            if uid in invited:
                continue
            members.append(u)
    except Exception as e:
        print(f"❌ Error while fetching participants: {e}")
        await client.disconnect()
        return

    if not members:
        print("ℹ️ No eligible members found to invite.")
        await client.disconnect()
        return

    to_invite = random.sample(members, min(MAX_INVITES_PER_RUN, len(members)))
    print(f"🔢 Will attempt to invite {len(to_invite)} users.")

    for user in to_invite:
        uid = user.id
        username_or_name = getattr(user, 'username', None) or f"{user.first_name or ''} {user.last_name or ''}".strip()
        try:
            print(f"➤ Inviting {username_or_name} (id={uid})...")
            await client(InviteToChannelRequest(channel=dest, users=[user]))
            invited.add(uid)
            print(f"✅ Invited {username_or_name}")
        except errors.UserPrivacyRestrictedError:
            print(f"⚠️ Privacy restriction for {uid}")
            invited.add(uid)
        except errors.UserAlreadyParticipantError:
            print(f"ℹ️ {uid} is already in destination. Marking as invited.")
            invited.add(uid)
        except errors.FloodWaitError as fw:
            print(f"⛔ Flood wait: {fw.seconds} seconds. Exiting to be safe.")
            await save_invited(data_path, invited)
            await client.disconnect()
            return
        except Exception as e:
            print(f"❌ Failed to invite {uid}: {type(e).__name__}: {e}")

        s = random.randint(MIN_SLEEP_BETWEEN_INVITES, MAX_SLEEP_BETWEEN_INVITES)
        print(f"⏱ Sleeping {s} seconds before next invite...")
        time.sleep(s)

    await save_invited(data_path, invited)
    print("💾 Saved invited user list.")
    await client.disconnect()
    print("✅ Done for this run.")

if __name__ == "__main__":
    asyncio.run(main())
