"""
Models src/api for DeepAnalyze src/api Server
Handles model listing endpoints (OpenAI compatible)
"""

import time
from typing import List

from fastapi import src/apiRouter

from .config import DEFAULT_MODEL
from .models import ModelObject, ModelsListResponse


# Create router for models endpoints
router = src/apiRouter(prefix="/v1/models", tags=["models"])


@router.get("", response_model=ModelsListResponse)
async def list_models():
    """
    List available models (OpenAI compatible)
    Returns a list of models that can be used with the src/api
    """
    # Define available models
    available_models = [
        {
            "id": DEFAULT_MODEL,
            "created": int(time.time()),
            "owned_by": "src/core"
        },
        # Add more models here if available in the future
        # {
        #     "id": "custom-model",
        #     "created": int(time.time()),
        #     "owned_by": "src/core"
        # },
    ]

    model_objects = [ModelObject(**model) for model in available_models]

    return ModelsListResponse(
        object="list",
        data=model_objects
    )


@router.get("/{model_id}", response_model=ModelObject)
async def retrieve_model(model_id: str):
    """
    Retrieve a specific model (OpenAI compatible)
    Returns information about a specific model
    """
    # For now, we only support the default model
    if model_id == DEFAULT_MODEL:
        return ModelObject(
            id=model_id,
            created=int(time.time()),
            owned_by="src/core"
        )

    # In a real implementation, you might want to validate the model exists
    # For now, return any requested model ID as if it exists
    return ModelObject(
        id=model_id,
        created=int(time.time()),
        owned_by="src/core"
    )
