from fastapi import FastAPI

from source.api import create_app


def create_api(container) -> FastAPI:
    """Create FastAPI app for the Mini App backend."""
    return create_app(container)
