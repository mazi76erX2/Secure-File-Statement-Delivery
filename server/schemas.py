"""Pydantic schemas for customer statement delivery."""

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator


class CustomerBase(BaseModel):
	full_name: str = Field(min_length=1, max_length=255)
	email: str = Field(min_length=5, max_length=255)


class CustomerCreate(CustomerBase):
	pass


class CustomerResponse(CustomerBase):
	id: int
	created_at: datetime
	updated_at: datetime

	model_config = ConfigDict(from_attributes=True)


class AccountStatementBase(BaseModel):
	customer_id: int = Field(gt=0)
	account_number_last4: str = Field(min_length=4, max_length=4)
	statement_period_start: date
	statement_period_end: date
	file_name: str = Field(min_length=1, max_length=255)
	file_path: str = Field(min_length=1, max_length=1024)
	content_type: str = Field(default="application/pdf", min_length=1, max_length=100)
	file_size_bytes: int = Field(gt=0)
	checksum_sha256: str | None = Field(default=None, min_length=64, max_length=64)

	@model_validator(mode="after")
	def validate_period_range(self) -> "AccountStatementBase":
		if self.statement_period_end < self.statement_period_start:
			raise ValueError("statement_period_end must be on or after statement_period_start")
		return self


class AccountStatementCreate(AccountStatementBase):
	pass


class AccountStatementResponse(AccountStatementBase):
	id: int
	created_at: datetime
	updated_at: datetime

	model_config = ConfigDict(from_attributes=True)


class StatementDownloadLinkCreate(BaseModel):
	expires_in_seconds: int = Field(default=900, ge=60, le=86400)
	max_downloads: int = Field(default=1, ge=1, le=20)


class StatementDownloadLinkResponse(BaseModel):
	id: int
	statement_id: int
	expires_at: datetime
	max_downloads: int
	download_count: int
	last_downloaded_at: datetime | None
	revoked_at: datetime | None
	created_at: datetime
	updated_at: datetime

	model_config = ConfigDict(from_attributes=True)


class StatementDownloadLinkIssued(StatementDownloadLinkResponse):
	token: str
	download_url: str
