from pydantic import BaseModel, Field, RootModel, field_validator
from typing import List, Optional
from enum import Enum
from datetime import datetime

class ExchangeEnum(str, Enum):
    binance = "binance"
    coinbase = "coinbase"
    kraken = "kraken"

class JobStatusEnum(str, Enum):
    pending = "pending"
    processing = "processing"
    done = "done"
    error = "error"

class JobRequestBody(BaseModel):
    exchange: ExchangeEnum
    year: int = Field(..., description="Tax year (cannot be in the future).")
    account_holder: str = Field(..., description="Account holder email.")
    uid: str = Field(..., description="Account holder subscription / user Id.")
    api_key: str = Field(..., description="Exchange API Key.")
    api_secret: str = Field(..., description="Exchange API Secret.")
    fiat: str = Field(..., description="Native fiat currency for this account holder.")
    # status: Optional[JobStatusEnum] = JobStatusEnum.pending

    @field_validator('year')
    @classmethod
    def validate_year(cls, v: int) -> int:
        """Validate that the year is not in the future."""
        current_year = datetime.now().year
        if v > current_year:
            raise ValueError(f"Year {v} cannot be in the future (current year is {current_year}).")
        return v

class JobResponseBody(BaseModel):
    job_id: str = Field(..., description="UUID that identifies the job in the system")

class DocumentInfo(BaseModel):
    document_id: str = Field(..., description="UUID that identifies the document in the system")
    document_type: str = Field(..., description="Type of document")

class JobListItem(BaseModel):
    job_id: str
    exchange: ExchangeEnum
    year: int
    fiat: str
    status: JobStatusEnum
    documents: List[DocumentInfo] = []

class JobsResponseBody(RootModel):
    root: List[JobListItem]

class InternalJob(BaseModel):
    job_id: str
    exchange: ExchangeEnum
    year: int = Field(..., description="Tax year (cannot be in the future).")
    account_holder: str
    uid: str
    api_key: str
    api_secret: str
    fiat: str

    @field_validator('year')
    @classmethod
    def validate_year(cls, v: int) -> int:
        """Validate that the year is not in the future."""
        current_year = datetime.now().year
        if v > current_year:
            raise ValueError(f"Year {v} cannot be in the future (current year is {current_year}).")
        return v
