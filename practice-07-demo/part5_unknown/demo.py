import asyncio

from common.config import PAYMENTS_URL
from common.log import log, title
from common.orders_api import place
from common.proc import Worker, wait_final
from common.schema import GOOD_CARD
from common.show import history, payments_state, state
from common.stand import client, reset


async def slow_saga(http, **worker_env) -> str:
    await http.post(f"{PAYMENTS_URL}/admin/config", params={"delay": 2.5, "delay_calls": 1})
    worker = await Worker(**worker_env).start()
    order_id, saga_id = await place(http, "book", 1, GOOD_CARD)
    await wait_final(saga_id)
    await state(saga_id, "book")
    log("demo", "ждём, пока провайдер ответит на первый запрос...")
    await asyncio.sleep(2.5)
    await worker.stop()
    await payments_state(saga_id)
    await history(saga_id)
    return saga_id


async def authorize(http, saga_id: str) -> dict:
    response = await http.post(
        f"{PAYMENTS_URL}/authorizations",
        json={"saga_id": saga_id, "card": GOOD_CARD, "amount": 1200},
        headers={"Idempotency-Key": f"{saga_id}:authorize"},
    )
    return response.json()


async def void(http, saga_id: str) -> dict:
    return (await http.post(f"{PAYMENTS_URL}/authorizations/{saga_id}/void")).json()


async def main() -> None:
    async with client() as http:
        await reset()
        title("1. Таймаут на авторизации: повтор с тем же ключом")
        await slow_saga(http)

        title("2. Таймаут на авторизации: повтор с новым ключом")
        await slow_saga(http, new_key_on_retry=1)

        title("3. Компенсация пришла раньше действия — без tombstone")
        await http.post(f"{PAYMENTS_URL}/admin/config", params={"tombstones": False})
        log("demo", f"void   → {await void(http, 's-late-1')}")
        log("demo", f"authorize → {await authorize(http, 's-late-1')}")
        await payments_state("s-late-1")

        title("4. Компенсация пришла раньше действия — с tombstone")
        await http.post(f"{PAYMENTS_URL}/admin/config")
        log("demo", f"void   → {await void(http, 's-late-2')}")
        log("demo", f"authorize → {await authorize(http, 's-late-2')}")
        await payments_state("s-late-2")

        title("5. Компенсация пришла, пока действие ещё выполняется")
        await http.post(f"{PAYMENTS_URL}/admin/config", params={"delay": 1.5, "delay_calls": 1})
        slow = asyncio.create_task(authorize(http, "s-late-3"))
        await asyncio.sleep(0.5)
        log("demo", f"void   → {await void(http, 's-late-3')}")
        log("demo", f"authorize → {await slow}")
        await payments_state("s-late-3")


if __name__ == "__main__":
    asyncio.run(main())
