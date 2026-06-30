"""Backend application package.

Smart Factory Vision Inspection System.

This package follows a Clean Architecture layout:

    api/            -> Presentation layer (FastAPI routers / HTTP endpoints)
    websocket/      -> Realtime push layer (WebSocket connection manager)
    inspection/     -> Vision inspection engine (OpenCV algorithms)
    mqtt/           -> MQTT publisher / subscriber (broker communication)
    tcp/            -> TCP/IP socket server (PLC telemetry)
    database/       -> Database engine, session, base model
    repositories/   -> Data-access layer (CRUD per aggregate)
    services/       -> Application / business logic orchestration
    models/         -> SQLAlchemy ORM entities (persistence models)
    schemas/        -> Pydantic DTOs (request / response validation)
    utils/          -> Cross-cutting helpers (logging, time, image io)
    config/         -> Settings & environment management
"""

__version__ = "0.1.0"
