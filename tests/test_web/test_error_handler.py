# US3 (feature 006): the FastAPI global exception handler must return a real 500 Response,
# not an HTTPException instance (which would itself raise). R-PROC-3 reproduces FR-008.
import pytest
from unittest.mock import MagicMock, patch
from starlette.responses import Response, JSONResponse
from web.main import global_exception_handler


@pytest.mark.asyncio
async def test_global_exception_handler_returns_500_response():
    req = MagicMock()
    exc = RuntimeError("boom")
    with patch("web.main.logger") as mock_logger:
        resp = await global_exception_handler(req, exc)

    # Must be a proper Response (JSONResponse), never an HTTPException instance
    assert isinstance(resp, Response)
    assert isinstance(resp, JSONResponse)
    assert resp.status_code == 500
    # Exception must be logged with traceback
    mock_logger.error.assert_called_once()
    _, kwargs = mock_logger.error.call_args
    assert kwargs.get("exc_info") is True
