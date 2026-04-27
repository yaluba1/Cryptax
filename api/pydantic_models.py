from pydantic import BaseModel, Field, RootModel, field_validator, model_validator
from typing import List, Optional
from enum import Enum
from datetime import datetime

class ExchangeEnum(str, Enum):
    binance = "binance"
    coinbase = "coinbase"
    kraken = "kraken"

class CountryEnum(str, Enum):
    IE = "IE"
    JP = "JP"
    ES = "ES"
    US = "US"
    GENERIC = "GENERIC"

class LangEnum(str, Enum):
    en = "en"
    es = "es"
    de = "de"
    fr = "fr"
    it = "it"
    ja = "ja"
    pt = "pt"

class AccountingMethodEnum(str, Enum):
    FIFO = "FIFO"
    LIFO = "LIFO"
    HIFO = "HIFO"
    LOFO = "LOFO"

class GenericInfo(BaseModel):
    long_term_capital_gains_days: int = Field(..., description="Number of days to hold an asset to be considered long-term capital gains.")
    accounting_method: AccountingMethodEnum = Field(..., description="Accounting method applicable for this user's country of residence.")

class JobStatusEnum(str, Enum):
    pending = "pending"
    processing = "processing"
    done = "done"
    error = "error"

class JobRequestBody(BaseModel):
    lang: LangEnum = Field(LangEnum.en, description="Language used for the job. ISO 639-1.")
    country: CountryEnum = Field(..., description="Countries whose tax regulations apply for this job. ISO 3166-1 alpha-2 code.")
    generic: Optional[GenericInfo] = Field(None, description="Generic information applicable to the user's country of residence. MUST be included if country is GENERIC.")
    exchange: ExchangeEnum
    year: int = Field(..., description="Tax year (cannot be in the future).")
    account_holder: str = Field(..., description="Account holder email.")
    uid: str = Field(..., description="Account holder subscription / user Id.")
    api_key: str = Field(..., description="Exchange API Key.")
    api_secret: str = Field(..., description="Exchange API Secret.")
    fiat: str = Field(..., description="Native fiat currency for this account holder.")

    @field_validator('year')
    @classmethod
    def validate_year(cls, v: int) -> int:
        """Validate that the year is not in the future."""
        current_year = datetime.now().year
        if v > current_year:
            raise ValueError(f"Year {v} cannot be in the future (current year is {current_year}).")
        return v

    @model_validator(mode='after')
    def validate_country_generic(self) -> 'JobRequestBody':
        """Validate that generic info is provided when country is GENERIC."""
        if self.country == CountryEnum.GENERIC and self.generic is None:
            raise ValueError("generic info must be provided when country is GENERIC.")
        return self

class JobResponseBody(BaseModel):
    job_id: str = Field(..., description="UUID that identifies the job in the system")

class DocumentInfo(BaseModel):
    document_id: str = Field(..., description="UUID that identifies the document in the system")
    document_type: str = Field(..., description="Type of document")

class JobListItem(BaseModel):
    job_id: str
    lang: LangEnum
    country: CountryEnum
    generic: Optional[GenericInfo] = None
    exchange: ExchangeEnum
    year: int
    fiat: str
    status: JobStatusEnum
    documents: List[DocumentInfo] = []

class JobsResponseBody(RootModel):
    root: List[JobListItem]

class InternalJob(BaseModel):
    job_id: str
    api_key: str
    api_secret: str
