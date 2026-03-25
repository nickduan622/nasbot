"""qBittorrent WebUI API client."""

import logging

import aiohttp

import config

log = logging.getLogger(__name__)


class QbitClient:
    def __init__(self):
        self._cookie_jar = aiohttp.CookieJar()
        self._logged_in = False

    async def _session(self) -> aiohttp.ClientSession:
        return aiohttp.ClientSession(cookie_jar=self._cookie_jar)

    async def login(self) -> bool:
        async with await self._session() as session:
            async with session.post(
                f"{config.QBIT_URL}/api/v2/auth/login",
                data={"username": config.QBIT_USER, "password": config.QBIT_PASS},
            ) as resp:
                text = await resp.text()
                self._logged_in = text.strip() == "Ok."
                if not self._logged_in:
                    log.error("qBit login failed: %s", text)
                return self._logged_in

    async def _api(self, method: str, path: str, **kwargs) -> aiohttp.ClientResponse | None:
        if not self._logged_in:
            await self.login()
        async with await self._session() as session:
            async with session.request(method, f"{config.QBIT_URL}{path}", **kwargs) as resp:
                if resp.status == 403:
                    await self.login()
                    async with session.request(method, f"{config.QBIT_URL}{path}", **kwargs) as retry:
                        return retry
                return resp

    async def add_torrent_url(self, url: str, save_path: str, category: str = "seed") -> bool:
        if not self._logged_in:
            await self.login()
        async with await self._session() as session:
            data = aiohttp.FormData()
            data.add_field("urls", url)
            data.add_field("savepath", save_path)
            data.add_field("category", category)
            async with session.post(
                f"{config.QBIT_URL}/api/v2/torrents/add", data=data
            ) as resp:
                ok = resp.status == 200
                if not ok:
                    log.error("qBit add torrent failed: %s", await resp.text())
                return ok

    async def get_torrents(self, category: str | None = None) -> list[dict]:
        if not self._logged_in:
            await self.login()
        params = {}
        if category:
            params["category"] = category
        async with await self._session() as session:
            async with session.get(
                f"{config.QBIT_URL}/api/v2/torrents/info", params=params
            ) as resp:
                if resp.status != 200:
                    return []
                return await resp.json()

    async def get_transfer_info(self) -> dict:
        if not self._logged_in:
            await self.login()
        async with await self._session() as session:
            async with session.get(f"{config.QBIT_URL}/api/v2/transfer/info") as resp:
                if resp.status != 200:
                    return {}
                return await resp.json()

    async def delete_torrent(self, hash_: str, delete_files: bool = True) -> bool:
        if not self._logged_in:
            await self.login()
        async with await self._session() as session:
            data = {
                "hashes": hash_,
                "deleteFiles": str(delete_files).lower(),
            }
            async with session.post(
                f"{config.QBIT_URL}/api/v2/torrents/delete", data=data
            ) as resp:
                return resp.status == 200


qbit = QbitClient()
