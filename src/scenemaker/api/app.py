"""FastAPI application factory."""

from fastapi import FastAPI

from scenemaker import __version__
from scenemaker.api.routers import auth, files, health, jobs, selfies, templates
from scenemaker.services import Services, build_services


def create_app(services: Services | None = None) -> FastAPI:
    app = FastAPI(title="scenemaker", version=__version__)
    app.state.services = services or build_services()

    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(templates.router)
    app.include_router(selfies.router)
    app.include_router(jobs.router)
    app.include_router(files.router)
    return app
