import asyncio
import aiohttp
import json
import os
from typing import Optional, List, Dict

class ClientAPI:
    def __init__(self, server_url='http://localhost:8080'):
        self.server_url = server_url
        self.session = None
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)

    async def _ensure_session(self):
        if self.session is None or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=10)
            self.session = aiohttp.ClientSession(timeout=timeout)

    async def _request(self, method, endpoint, data=None, params=None):
        await self._ensure_session()
        url = f"{self.server_url}{endpoint}"
        try:
            async with self.session.request(method, url, json=data, params=params) as resp:
                if resp.status == 200:
                    return await resp.json()
                else:
                    error = await resp.text()
                    return {'status': 'error', 'message': error}
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            return {'status': 'error', 'message': f'Connection error: {str(e)}'}

    def register(self, login, password):
        return self._loop.run_until_complete(
            self._request('POST', '/register', data={'login': login, 'password': password})
        )

    def login(self, login, password):
        return self._loop.run_until_complete(
            self._request('POST', '/login', data={'login': login, 'password': password})
        )

    def send_message(self, from_user, to_user, content):
        return self._loop.run_until_complete(
            self._request('POST', '/send', data={'from': from_user, 'to': to_user, 'content': content})
        )

    def get_messages(self, user):
        return self._loop.run_until_complete(
            self._request('GET', '/messages', params={'user': user})
        )

    def get_users(self):
        return self._loop.run_until_complete(
            self._request('GET', '/users')
        )

    def close(self):
        if self.session and not self.session.closed:
            self._loop.run_until_complete(self.session.close())
        self._loop.close()