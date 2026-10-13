from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from jose import JWTError

import traceback


async def global_exception_handler(
    request: Request,
    exc: Exception,
):
    """
    Global application exception handler.
    """

    error_message = str(exc)

    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR

    errors = None

    # Validation errors
    if isinstance(
        exc,
        RequestValidationError,
    ):
        status_code = status.HTTP_422_UNPROCESSABLE_ENTITY

        error_message = "Validation error"

        errors = exc.errors()

    # JWT errors
    elif isinstance(
        exc,
        JWTError,
    ):
        status_code = status.HTTP_401_UNAUTHORIZED

        error_message = "Invalid authentication token"

    # Log error
    print(
        f"❌ Error: {error_message}"
    )

    print(
        traceback.format_exc()
    )

    return JSONResponse(
        status_code=status_code,
        content={
            "success": False,
            "message": error_message,
            "errors": errors,
        },
    )