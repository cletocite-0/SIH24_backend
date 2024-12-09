from fastapi import FastAPI, APIRouter, HTTPException
from typing import Callable
from pymongo import MongoClient
import os

from utils.utils import obtain_mongo_uri


def obtain_active_routes(user_id: str):
    try:
        client = MongoClient(obtain_mongo_uri())
    except Exception as e:
        print("Error in connecting to db: ", e.with_traceback)
        exit(1)

    db = client.get_database("axel_configs")
    collection = db.get_collection("active_routes")
    active_routes = collection.find_one({"user_id": user_id})

    if not active_routes:
        active_routes = {"user_id": user_id, "routes": {}}
        collection.insert_one(active_routes)

    return active_routes, collection


# app is mutable and so changes are reflected in master.py
# optional to return app


def add_route(
    app: FastAPI, path: str, method: Callable, method_name: str, user_id: str
):
    """Add a route dynamically to the FastAPI app."""
    active_routes, collection = obtain_active_routes(user_id)
    if path in active_routes["routes"]:
        raise ValueError(f"Route {path} is already active.")

    # Create a new router for isolation
    router = APIRouter()

    # Add the route to the router
    router.add_api_route(path, method, methods=["POST"], name=method_name)

    # Include the router in the app
    app.include_router(router)

    # Store route info
    active_routes["routes"][path] = method_name
    collection.find_one_and_update(
        {"user_id": user_id},
        {"$set": {"routes": active_routes["routes"]}},
    )


def remove_route(app: FastAPI, path: str, user_id: str):
    """Remove a route dynamically from the FastAPI app."""
    active_routes, collection = obtain_active_routes(user_id)
    if path not in active_routes["routes"]:
        raise ValueError(f"Route {path} is not active.")

    # Get the router associated with the path
    router = active_routes["routes"][path]

    # Remove the router from the app
    app.router.routes = [route for route in app.router.routes if route.path != path]

    # Remove it from the registry
    del active_routes["routes"][path]
    collection.find_one_and_update(
        {"user_id": user_id},
        {"$set": {"routes": active_routes["routes"]}},
    )
