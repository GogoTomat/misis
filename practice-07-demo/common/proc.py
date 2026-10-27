import asyncio
import os
import sys


class Worker:
    def __init__(self, name: str = "worker", **env: str) -> None:
        self.name = name
        self.env = {**os.environ, "PYTHONIOENCODING": "utf-8", "SAGA_WORKER_NAME": name}
        self.env.update({f"SAGA_{k.upper()}": str(v) for k, v in env.items()})
        self.process: asyncio.subprocess.Process | None = None
        self.reader: asyncio.Task | None = None

    async def start(self) -> "Worker":
        self.process = await asyncio.create_subprocess_exec(
            sys.executable, "-m", "saga.worker",
            env=self.env, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT,
        )
        self.reader = asyncio.create_task(self._pipe())
        await asyncio.sleep(0.8)
        return self

    async def _pipe(self) -> None:
        async for line in self.process.stdout:
            print(line.decode("utf-8", "replace").rstrip(), flush=True)

    async def wait(self) -> int:
        code = await self.process.wait()
        await self.reader
        return code

    async def stop(self) -> None:
        if self.process and self.process.returncode is None:
            self.process.terminate()
            await self.process.wait()
        if self.reader:
            await self.reader


async def wait_final(saga_id: str, timeout: float = 30) -> str:
    from common.db import connect

    conn = await connect("orders")
    try:
        for _ in range(int(timeout * 10)):
            state = await conn.fetchval("SELECT state FROM sagas WHERE id = $1", saga_id)
            if state in ("CONFIRMED", "CANCELLED", "NEEDS_ATTENTION"):
                return state
            await asyncio.sleep(0.1)
        return state
    finally:
        await conn.close()
