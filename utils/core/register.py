import pyrogram
from loguru import logger
from data import config


async def create_sessions():
    while True:
        session_name = input('\nВведите название сессии (для выхода нажмите Enter): ')
        if not session_name:
            return

        api_index = int(input('Введите индекс API из конфига (0, 1, и т.д.): '))
        api_id = config.API_IDS[api_index]
        api_hash = config.API_HASHES[api_index]

        session = pyrogram.Client(
            api_id=api_id,
            api_hash=api_hash,
            name=session_name,
            workdir=config.WORKDIR,
        )

        async with session:
            user_data = await session.get_me()

        logger.success(f'Успешно добавлена сессия {user_data.username} | {user_data.phone_number}')
