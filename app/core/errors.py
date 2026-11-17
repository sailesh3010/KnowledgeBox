from typing import Any, Optional
from fastapi import HTTPException, status
from fastapi.responses import JSONResponse


class AppError(Exception):
    """Base application exception with standardized code and status."""

    def __init__(
        self,
        message: str,
        code: str = "INTERNAL_ERROR",
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: Optional[Any] = None,
    ):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details

    def to_dict(self) -> dict:
        result = {
            "code": self.code,
            "message": self.message,
        }
        if self.details is not None:
            result["details"] = self.details
        return {"error": result}


class ValidationError(AppError):
    def __init__(self, message: str, details: Optional[Any] = None):
        super().__init__(
            message=message,
            code="VALIDATION_ERROR",
            status_code=status.HTTP_400_BAD_REQUEST,
            details=details,
        )


class ItemNotFoundError(AppError):
    def __init__(self, item_id: str):
        super().__init__(
            message=f"Item with ID '{item_id}' was not found.",
            code="ITEM_NOT_FOUND",
            status_code=status.HTTP_404_NOT_FOUND,
            details={"item_id": item_id},
        )


class ScraperError(AppError):
    def __init__(self, message: str, details: Optional[Any] = None):
        super().__init__(
            message=message,
            code="SCRAPER_FAILED",
            status_code=status.HTTP_502_BAD_GATEWAY,
            details=details,
        )


class ProviderError(AppError):
    def __init__(self, message: str, details: Optional[Any] = None):
        super().__init__(
            message=message,
            code="AI_PROVIDER_ERROR",
            status_code=status.HTTP_502_BAD_GATEWAY,
            details=details,
        )


def error_response(app_error: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=app_error.status_code,
        content=app_error.to_dict(),
    )
