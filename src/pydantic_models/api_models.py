"""
Pydantic models for SAP Wrapper API operations
"""
from pydantic import BaseModel
from typing import Any

class QueryRequest(BaseModel):
    """Input model for user query"""

    user_query: str


class QueryResponse(BaseModel):
    """Output model for agent response"""

    success: bool
    response: Any
    error: str | None = None