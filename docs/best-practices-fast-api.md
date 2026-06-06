# FastAPI Best Practices Guide

## Async & Performance

* **Never use `async def` for blocking operations**

  * Use `def` for synchronous database calls, file I/O, blocking HTTP requests, or `time.sleep()`.
  * Blocking code inside `async def` can freeze request handling. 

* **Prefer async-compatible libraries**

  * Use `asyncio.sleep()` instead of `time.sleep()`.
  * Use `httpx.AsyncClient` instead of `requests`.
  * Use async database drivers (e.g., Motor for MongoDB). 

* **Avoid heavy computation inside endpoints**

  * Don't process large images, videos, or run expensive ML workloads directly in API routes.
  * Use dedicated inference services (e.g., Triton, TorchServe) or queue/worker architectures (e.g., RabbitMQ + Celery). 

## Dependencies

* **Apply the same async rules to dependencies**

  * Use `def` for blocking work.
  * Use `async def` only for non-blocking async operations.
  * Keep dependencies lightweight and focused. 

* **Use dependencies for database-based validation**

  * Move ownership checks, authorization lookups, and similar DB-driven validation into reusable dependencies.
  * Benefit from dependency reuse and FastAPI's per-request dependency caching. 

## Background Processing

* **Don't make users wait unnecessarily**

  * Use `BackgroundTasks` for lightweight, non-critical work such as:

    * Sending emails
    * Audit logging
    * Notifications
  * For guaranteed delivery, retries, or long-running jobs, use a message queue and worker system instead.

## API Design & Validation

* **Disable Swagger/ReDoc in private production APIs**

  * Set `docs_url=None`, `redoc_url=None`, and `openapi_url=None` when documentation should not be publicly exposed. 

* **Create a custom Pydantic base model**

  * Centralize configuration such as:

    * `camelCase` ↔ `snake_case` aliases
    * `datetime` serialization
    * `Decimal` encoding
    * MongoDB `ObjectId` conversion
  * Improves consistency and maintainability. 

* **Let FastAPI build response models**

  * If `response_model` is defined, return dictionaries or data structures directly.
  * Avoid manually constructing response model objects unless necessary. 

* **Put validation in Pydantic models**

  * Avoid scattered validation logic inside endpoints.
  * Use model fields, validators, and custom validation methods.
  * Keeps OpenAPI documentation accurate and error handling consistent. 

## Database Management

* **Use connection pools**

  * Never create a new database connection per request.
  * Manage connections through dependency injection.

* **Prefer storing pools in `app.state`**

  * Initialize pools during application startup.
  * Retrieve connections through dependencies.
  * Makes cleanup and multi-database management easier. 

## Application Lifecycle

* **Use the Lifespan API**

  * Prefer FastAPI's lifespan context over `@app.on_event("startup")` and `@app.on_event("shutdown")`.
  * Keep startup and shutdown logic together.
  * Ensures proper cleanup when initialization fails. 

## Configuration & Security

* **Never hardcode secrets**

  * Store credentials, API keys, and tokens in environment variables.
  * Add `.env` to `.gitignore`.
  * Maintain a `.env.example` template.

* **Centralize configuration**

  * Use a settings class (e.g., Pydantic `BaseSettings` or Dynaconf).
  * Validate configuration at startup.
  * Avoid accessing `os.environ` throughout the codebase.

## Logging & Observability

* **Use structured logging**

  * Replace `print()` statements with:

    * Python `logging`
    * Loguru
    * Structlog
  * Support log levels (`DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`).

* **Add contextual information**

  * Include request IDs, user IDs (when appropriate), timestamps, and other trace data.
  * Never log sensitive information.

* **Centralize logs**

  * Aggregate logs into a centralized platform (e.g., Elasticsearch stack) for monitoring and analysis.

## Deployment

* **Use production-grade deployment settings**

  * Development: Uvicorn is sufficient.
  * Production: Run Uvicorn behind Gunicorn using `UvicornWorker`. 

* **Install `uvloop`**

  * FastAPI can automatically use it for improved event-loop performance. 

* **Tune worker count**

  * Common starting point:

    * `(CPU cores × 2) + 1`
  * Benchmark and adjust based on workload. 

* **Containerize for scalability**

  * Package applications with Docker to simplify deployment and scaling. 

### Quick Checklist

* ✅ Use async only with non-blocking code
* ✅ Keep endpoints thin and I/O-focused
* ✅ Offload heavy work to workers/services
* ✅ Validate with Pydantic, not route logic
* ✅ Reuse dependencies for DB validation
* ✅ Use connection pooling
* ✅ Manage resources with Lifespan
* ✅ Store secrets in environment variables
* ✅ Use structured logging with context
* ✅ Deploy with Gunicorn + UvicornWorker + uvloop
* ✅ Containerize for production scaling
