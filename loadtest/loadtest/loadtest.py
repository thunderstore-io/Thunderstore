import asyncio
import time
from typing import List, Optional

import aiohttp
from aiohttp import ClientConnectorError, ClientPayloadError, ServerDisconnectedError


class LoadtestSession:
    def __init__(
        self, request_limit: int, host: str, paths: List[str], log_interval: int
    ):
        self.request_limit = request_limit
        self.performed_requests = 0
        self.host = host
        self.paths = paths
        self.history = []
        self.max_history = log_interval
        self.last_log_time = time.time()

    def start(self, workers: int):
        print("Starting load testing with parameters:")
        print(f"  Request limit: {self.request_limit}")
        print(f"  Host: {self.host}")
        print(f"  Paths: {self.paths}")
        print(f"  Client count: {workers}")
        loop = asyncio.get_event_loop()
        self.last_log_time = time.time()
        tasks = asyncio.gather(*[worker(self) for _ in range(workers)])
        loop.run_until_complete(tasks)

    def log_result(
        self, duration: Optional[float], status_code: Optional[int], success: bool
    ):
        self.history.append((duration, status_code, success))
        if len(self.history) >= self.max_history:
            delta_time = time.time() - self.last_log_time
            requests_per_second = len(self.history) / delta_time
            print(f"Last {len(self.history)} requests")
            print("-" * 20)
            average_duration = sum(
                [x[0] for x in self.history if x[0] is not None]
            ) / len(self.history)
            print(f"Average successfull request duration: {average_duration:.2f}ms")
            print(
                f"Status codes received: {set([x[1] for x in self.history if x[1] is not None])}"
            )
            print(f"Requests per second: {requests_per_second:.2f}")
            print(
                f"Dropped requests: {len(self.history) - sum([x[2] for x in self.history])}"
            )
            self.history = []
            self.last_log_time = time.time()
        self.performed_requests += 1

    def get_next_url(self):
        next_path = self.paths[self.performed_requests % len(self.paths)]
        return f"{self.host}{next_path}"

    @property
    def should_continue(self):
        if self.request_limit is None:
            return True
        return self.performed_requests < self.request_limit


async def worker(loadtest: LoadtestSession):
    while loadtest.should_continue:
        async with aiohttp.ClientSession() as session:
            start_time = time.time()
            try:
                async with session.get(loadtest.get_next_url()) as response:
                    await response.read()
                duration = (time.time() - start_time) * 1000
                loadtest.log_result(
                    duration=duration, status_code=response.status, success=True
                )
            except (ClientConnectorError, ServerDisconnectedError, ClientPayloadError):
                loadtest.log_result(duration=None, status_code=None, success=False)


def start_loadtest(
    clients: int, host: str, paths: List[str], limit: Optional[int], log_interval: int
):
    loadtest = LoadtestSession(
        request_limit=limit, host=host, paths=paths, log_interval=log_interval
    )
    loadtest.start(workers=clients)
