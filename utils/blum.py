import random
from utils.core import logger
from pyrogram import Client
from pyrogram.raw.functions.messages import RequestWebView
import asyncio
from urllib.parse import unquote
from data import config
import aiohttp
from aiohttp_proxy import ProxyConnector
from better_proxy import Proxy
from pyrogram.errors import Unauthorized, UserDeactivated, AuthKeyUnregistered
from .headers import headers

# Заголовки HTTP-запросов
headers = {
    'Accept': '*/*',
    'Accept-Language': 'ru,en;q=0.9,en-GB;q=0.8,en-US;q=0.7',
    'Connection': 'keep-alive',
    'Origin': 'https://game-domain.blum',
    'Referer': 'https://game-domain.blum/',
    'Sec-Fetch-Dest': 'empty',
    'Sec-Fetch-Mode': 'cors',
    'Sec-Fetch-Site': 'same-site',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36 Edg/123.0.0.0',
    'sec-ch-ua': '"Microsoft Edge";v="123", "Not:A-Brand";v="8", "Chromium";v="123", "Microsoft Edge WebView2";v="123"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
}

# Класс для работы с клиентом Pyrogram
class Start:
    def __init__(self, tg_client: Client):
        self.session_name = tg_client.name
        self.tg_client = tg_client
        self.session = aiohttp.ClientSession(headers=headers, trust_env=True)
        
    async def check_proxy(self, http_client: aiohttp.ClientSession, proxy: Proxy) -> None:
        try:
            response = await http_client.get(url='https://httpbin.org/ip', timeout=aiohttp.ClientTimeout(5))
            ip = (await response.json()).get('origin')
            logger.info(f"{self.session_name} | Proxy IP: {ip}")
        except Exception as e:
            logger.error(f"Ошибка при проверке прокси: {e}")

    async def main(self, proxy: str | None):
        await self.tg_client.start()  # Начинаем сессию клиента перед использованием
        if config.USE_PROXY:
            proxy_conn = ProxyConnector().from_url(proxy) if proxy else None
        else:
            proxy_conn = None
        async with aiohttp.ClientSession(headers=headers, connector=proxy_conn) as http_client:
            if proxy and config.USE_PROXY:
                await self.check_proxy(http_client=http_client, proxy=proxy)

            while True:
                try:
                    await asyncio.sleep(random.uniform(6, 10))  # Случайная задержка от 6  до 10 секунд
                    await self.login(http_client=http_client, proxy=proxy)

                    while True:
                        try:
                            await self.login(http_client=http_client, proxy=proxy)
                            await asyncio.sleep(random.uniform(10, 20))
                            timestamp, start_time, end_time = await self.balance(http_client=http_client)

                            if start_time is None and end_time is None:
                                await asyncio.sleep(random.uniform(6, 10))  # Случайная задержка от 6  до 10 секунд перед началом фарма
                                await self.start(http_client=http_client)
                                logger.info(f"Поток {self} | Начало фарма!")

                            elif start_time is not None and end_time is not None and timestamp >= end_time:
                                timestamp, balance = await self.claim(http_client=http_client)
                                logger.success(f"Поток {self} | Получена награда! Также заклеймилась награда за друзей! Баланс: {balance}")
                                await asyncio.sleep(random.uniform(6, 10))  # Случайная задержка от 6  до 10 секунд  перед клеймом награды


                            else:
                                logger.info(f"Поток {self} | Спим {end_time - timestamp} секунд!")
                                await asyncio.sleep(end_time - timestamp)

                            await asyncio.sleep(1)
                        except Exception as e:
                            logger.error(f"Поток {self} | Ошибка: {e}")
                except Exception as e:
                    logger.error(f"Ошибка: {e}")

    async def get_tg_web_data(self, proxy: str | None) -> str:
        if proxy:
            proxy = Proxy.from_str(proxy)
            proxy_dict = dict(
                scheme=proxy.protocol,
                hostname=proxy.host,
                port=proxy.port,
                username=proxy.login,
                password=proxy.password
            )
        else:
            proxy_dict = None

        self.tg_client.proxy = proxy_dict

        web_view = await self.tg_client.invoke(RequestWebView(
            peer=await self.tg_client.resolve_peer('BlumCryptoBot'),
            bot=await self.tg_client.resolve_peer('BlumCryptoBot'),
            platform='android',
            from_bot_menu=False,
            url='https://telegram.blum.codes/'
        ))

        auth_url = web_view.url
        return unquote(string=unquote(string=auth_url.split('tgWebAppData=')[1].split('&tgWebAppVersion')[0]))

    async def claim(self, http_client: aiohttp.ClientSession):
        resp = await http_client.post("https://game-domain.blum.codes/api/v1/farming/claim")
        resp_json = await resp.json()
        resp2 = await http_client.post("https://gateway.blum.codes/v1/friends/claim")
        return int(resp_json.get("timestamp")/1000), resp_json.get("availableBalance")


    async def start(self, http_client: aiohttp.ClientSession):
        resp = await http_client.post("https://game-domain.blum.codes/api/v1/farming/start")

    async def balance(self, http_client: aiohttp.ClientSession):
        resp = await http_client.get("https://game-domain.blum.codes/api/v1/user/balance")
        resp_json = await resp.json()

        timestamp = resp_json.get("timestamp")
        if resp_json.get("farming"):
            start_time = resp_json.get("farming").get("startTime")
            end_time = resp_json.get("farming").get("endTime")

            return int(timestamp/1000), int(start_time/1000), int(end_time/1000)
        return int(timestamp/1000), None, None

    async def login(self, http_client: aiohttp.ClientSession, proxy: str | None):
        json_data = {"query": await self.get_tg_web_data(proxy)}

        resp = await http_client.post("https://gateway.blum.codes/v1/auth/provider/PROVIDER_TELEGRAM_MINI_APP", json=json_data)
        http_client.headers['Authorization'] = "Bearer " + (await resp.json()).get("token").get("access")

async def run_claimer(tg_client: Client, proxy: str | None):
    await Start(tg_client=tg_client).main(proxy=proxy)

async def run_claimer_multiple_accounts(proxy: str | None):
    tasks = []
    for api_id, api_hash in zip(config.API_IDS, config.API_HASHES):
        tg_client = Client(
            f"{config.WORKDIR}/session_{api_id}",
            api_id=api_id,
            api_hash=api_hash
        )
        tasks.append(run_claimer(tg_client, proxy))
    
    await asyncio.gather(*tasks)


    await run_claimer_multiple_accounts(proxy)
