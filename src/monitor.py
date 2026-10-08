from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field

from common import MessageStats
from message_record_service import MessageRecordService
from producer import Producer


class ProduceRequest(BaseModel):
    num_messages: int = Field(default=1000, gt=0, le=100_000)


class ProduceResponse(BaseModel):
    num_messages: int


@asynccontextmanager
async def lifespan(app: FastAPI):
    record_service = MessageRecordService()
    await record_service.open()
    app.state.record_service = record_service

    # Async-native producer (aiokafka), reused across every /produce call
    # instead of reconnecting per request. Sender's consumer side stays on
    # kafka-python (sync, offloaded to a thread) — only the producer needed
    # to be async here, so this intentionally mixes two Kafka client
    # libraries rather than migrating the consumer side too.
    producer = Producer()
    await producer.start()
    app.state.producer = producer

    yield

    await record_service.close()
    await app.state.producer.stop()


app = FastAPI(lifespan=lifespan)


@app.get("/stats", response_model=MessageStats)
async def get_stats(request: Request) -> MessageStats:
    return await request.app.state.record_service.get_stats()


@app.post("/produce", response_model=ProduceResponse)
async def produce_messages(request: Request, body: ProduceRequest) -> ProduceResponse:
    """Kick off a new batch of random SMS messages for the senders to consume."""
    try:
        await request.app.state.producer.run(body.num_messages)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"failed to produce messages: {exc}") from exc
    return ProduceResponse(num_messages=body.num_messages)
