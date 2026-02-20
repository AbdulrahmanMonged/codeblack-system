"""ASGI entrypoint for the CodeBlack backend."""

from backend.app import create_app

app = create_app()

