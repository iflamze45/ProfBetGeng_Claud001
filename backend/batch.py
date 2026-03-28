import uuid
import asyncio
from typing import Any
from pydantic import BaseModel, Field, field_validator

from .models import ConvertRequest, ConvertResponse


class BatchConvertRequest(BaseModel):
    tickets: list[ConvertRequest] = Field(..., min_length=1, max_length=10)

    @field_validator("tickets")
    @classmethod
    def no_empty_list(cls, v: list) -> list:
        if not v:
            raise ValueError("tickets list cannot be empty")
        return v


class BatchTicketResult(BaseModel):
    index: int
    status: str  # "success" | "error"
    result: ConvertResponse | None = None
    error: str | None = None


class BatchSummary(BaseModel):
    total: int
    succeeded: int
    failed: int


class BatchConvertResponse(BaseModel):
    batch_id: str
    summary: BatchSummary
    results: list[BatchTicketResult]
