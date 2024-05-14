import random
import os
import glob
import argparse
import asyncio
from itertools import cycle

from pyrogram import Client
from better_proxy import Proxy

import data.config
from utils.core import logger
from utils.blum import run_claimer
from utils.core import create_sessions

start_text = """
Mallin Makin BLUM Software
https://t.me/mallinmakin
Select an action:

    1. Create session
    2. Run claimer
"""

# Функция для обработки действий
async def process() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('-a', '--action', type=int, help='Action to perform')

    logger.info(f"Detected {len(get_session_names())} sessions | {len(get_proxies())} proxies")

    action = parser.parse_args().action

    if not action:
        print(start_text)

        while True:
            action = input("> ")

            if not action.isdigit():
                logger.warning("Action must be number")
            elif action not in ['1', '2']:
                logger.warning("Action must be 1 or 2")
            else:
                action = int(action)
                break

    if action == 1:
        await create_sessions()
    elif action == 2:
        tg_clients = await get_tg_clients()

        await run_tasks(tg_clients=tg_clients)

# Функция для выполнения задач
async def run_tasks(tg_clients: list[Client]):
    proxies = get_proxies()
    proxies_cycle = cycle(proxies) if proxies else None
    tasks = [asyncio.create_task(run_claimer(tg_client=tg_client, proxy=next(proxies_cycle) if proxies_cycle else None))
             for tg_client in tg_clients]

    await asyncio.gather(*tasks)


def get_session_names() -> list[str]:
    session_names = glob.glob('sessions/*.session')
    session_names = [os.path.splitext(os.path.basename(file))[0] for file in session_names]

    return session_names


def get_proxies() -> list[Proxy]:
    if data.config.USE_PROXY:
        with open(file='proxies.txt', encoding='utf-8-sig') as file:
            proxies = [Proxy.from_str(proxy=row.strip()).as_url for row in file]
        return proxies
    else:
        return []


async def get_tg_clients() -> list[Client]:
    session_names = get_session_names()

    if not session_names:
        raise FileNotFoundError("Not found session files")

    if not data.config.API_IDS or not data.config.API_HASHES:
        raise ValueError("API_IDS and API_HASHES not found in the config file.")

    tg_clients = [Client(
        name=session_name,
        api_id=api_id,
        api_hash=api_hash,
        workdir='sessions/',
    ) for session_name, api_id, api_hash in zip(session_names, data.config.API_IDS, data.config.API_HASHES)]

    return tg_clients


if __name__ == '__main__':
    asyncio.get_event_loop().run_until_complete(process())
