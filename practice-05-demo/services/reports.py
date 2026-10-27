import asyncio
import uuid

from fastapi import FastAPI, HTTPException

from services.log import log

app = FastAPI(title="reports")

BUILD_SECONDS = 5
jobs: dict[str, dict] = {}
background: set[asyncio.Task] = set()


async def build_report(job_id: str) -> None:
    jobs[job_id]["status"] = "running"
    log("reports", f"отчёт {job_id}: строю")
    await asyncio.sleep(BUILD_SECONDS)
    jobs[job_id].update(status="done", result_url=f"/reports/{job_id}/file")
    log("reports", f"отчёт {job_id}: готов")


@app.post("/reports/sync")
async def create_report_sync():
    job_id = uuid.uuid4().hex[:6]
    log("reports", f"отчёт {job_id}: строю синхронно, клиент ждёт")
    await asyncio.sleep(BUILD_SECONDS)
    log("reports", f"отчёт {job_id}: готов")
    return {"job_id": job_id, "status": "done"}


@app.post("/reports", status_code=202)
async def create_report():
    job_id = uuid.uuid4().hex[:6]
    jobs[job_id] = {"status": "queued", "result_url": None}
    task = asyncio.create_task(build_report(job_id))
    background.add(task)
    task.add_done_callback(background.discard)
    return {"job_id": job_id, "status_url": f"/reports/{job_id}"}


@app.get("/reports/{job_id}")
async def report_status(job_id: str):
    if job_id not in jobs:
        raise HTTPException(404, "unknown job")
    return {"job_id": job_id, **jobs[job_id]}
