from starlette.middleware.base import BaseHTTPMiddleware
import logging

logger = logging.getLogger("request_logger")

class LogRequestsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        logger.info(
            f"{request.method} {request.url.path} | "
            f"Origin: {request.headers.get('origin')} | "
            f"Access-Control-Request-Method: {request.headers.get('access-control-request-method')} | "
            f"Access-Control-Request-Headers: {request.headers.get('access-control-request-headers')}"
        )
        response = await call_next(request)
        logger.info(f"Response status: {response.status_code}")
        return response

