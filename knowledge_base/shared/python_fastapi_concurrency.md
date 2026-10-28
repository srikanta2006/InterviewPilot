# Python and FastAPI Concurrency Patterns

## Overview
FastAPI is built on Starlette and Pydantic, providing native asynchronous request handling via Python's `asyncio` framework. Understanding how FastAPI executes route handlers is critical for building high-performance, non-blocking APIs.

## Asynchronous vs Synchronous Route Handlers
In FastAPI:
1. **`async def` Endpoints:** When an endpoint is declared with `async def`, FastAPI executes it directly in the main event loop thread. Any I/O-bound operations within the handler (such as HTTP calls with `httpx` or database queries with `asyncpg`) MUST be awaited asynchronously. If a blocking synchronous function (such as `time.sleep`, synchronous database drivers, or intensive CPU loops) is invoked inside an `async def` endpoint, it blocks the entire event loop, severely degrading API throughput.
2. **Standard `def` Endpoints:** When an endpoint is declared with standard `def`, FastAPI offloads its execution to an external threadpool (using `anyio.to_thread.run_sync`). This prevents blocking operations from starving the main event loop, making standard `def` safer for legacy synchronous libraries.

## Data Validation with Pydantic v2
FastAPI leverages Pydantic v2 for request validation, serialization, and OpenAPI schema generation. Pydantic v2 core logic is compiled in Rust (`pydantic-core`), delivering a 5x to 20x performance improvement over Pydantic v1. Type annotations directly enforce runtime constraints, minimizing boilerplate validation logic.

## Background Tasks and Task Queues
For operations that do not need to block the HTTP response (such as audit logging, sending confirmation emails, or triggering cache invalidations), FastAPI provides `fastapi.BackgroundTasks`. For long-running, CPU-intensive, or mission-critical distributed tasks, an external distributed queue (such as Celery, ARQ, or Redis Streams) with separate worker processes is recommended.

## Database Connection Pooling
High-concurrency FastAPI applications should maintain a persistent connection pool (e.g. SQLAlchemy `create_async_engine` with `AsyncSession`) rather than opening a new socket per request. Connection pools limit open connections to the database while reusing warm sockets across incoming requests.

