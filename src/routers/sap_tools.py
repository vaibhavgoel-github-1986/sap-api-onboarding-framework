"""
API routes for SAP technical tools.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional

from ..agents.sap_agent import create_sap_agent
from ..pydantic_models.api_models import QueryResponse
from ..utils.logger import (
    logger,
    log_api_request,
    log_api_response,
    log_error_with_context,
)

router = APIRouter()


@router.get(
    "/tools",
    response_model=QueryResponse,
    summary="SAP AI Agent",
    description="""\
    **Intelligent SAP AI Agent** that handles various SAP query operations using natural language.

    ## Supported Operations:
    - **API Metadata**: Retrieve OData service metadata and structure
    - **Table Schema Retrieval**: Get structure and field information for SAP tables
    - **Source Code Access**: Fetch ABAP objects source code
    - **Service Items Retrieval**: Get subscription items, configuration items, CC config parameters, and material characteristics

    ## Example Queries:
    ```
    "Get table schema for MAKT from D2A system"
    "Show source code for ZCL_JIRA_ISSUES from D2A system"  
    "Get metadata for ZSD_PRODUCTS service, Namespace ZSB_PRODUCTS, System D2A"
    "Get Subscription Items for Subscription ID 12345 from D2A system"
    "Get Configuration Items for Service Order 67890 from Q2A system"
    "Get Material Characteristics for Material E3-COLLAB from RHA system"
    "Get CC Config Params for Item / Product ABC123 from SHA system"
    "Get CC Config Details from D2A System"
    "Get Material Characteristics from DHA System"
    ```

    ## Supported SAP Systems:
    - **D2A**: Development System  
    - **QHA/Q2A**: QA Systems
    - **RHA**: Pre-Production
    - **SHA**: Sandbox

    The agent automatically determines the appropriate SAP service to call based on your request.
    """,
    responses={
        200: {"description": "Successful response with SAP data"},
        400: {"description": "Invalid query or missing parameters"},
        500: {"description": "Internal server error or SAP system unavailable"},
    },
)
async def execute_sap_query(
    user_query: str = Query(
        ...,
        min_length=1,
        max_length=1000,
        description="Natural Language Query Tool for SAP Operations"
    )
) -> QueryResponse:
    """
    Process natural language SAP queries using AI agent.

    Args:
        user_query: Natural language description of the SAP operation to perform

    Returns:
        QueryResponse: Result of the SAP operation

    Raises:
        HTTPException: For validation errors or system failures
    """

    # Input validation
    if not user_query or not user_query.strip():
        raise HTTPException(
            status_code=400, detail="Please provide some input."
        )

    # Log the incoming request
    log_api_request(method="GET", url="/tools", user_query=user_query.strip())

    try:
        logger.info(
            f"Processing SAP query: {user_query[:100]}{'...' if len(user_query) > 100 else ''}"
        )

        # Execute the agent with timeout consideration
        agent = create_sap_agent()
        if not agent:
            raise HTTPException(
                status_code=500,
                detail="Failed to initialize SAP agent. Please try again.",
            )

        result = agent.invoke(
            {"messages": [{"role": "user", "content": user_query.strip()}]}
        )

        # Validate agent response
        if not result or "messages" not in result or not result["messages"]:
            raise HTTPException(
                status_code=500, detail="Agent returned empty or invalid response"
            )

        # Extract the final response
        final_message = result["messages"][-1]
        response_content = (
            final_message.content
            if hasattr(final_message, "content")
            else str(final_message)
        )

        if not response_content:
            raise HTTPException(
                status_code=500, detail="Agent returned empty response content"
            )

        # Log successful response
        log_api_response(
            status_code=200,
            execution_time_ms=0,  # TODO: Add actual timing
            success=True,
        )

        return QueryResponse(success=True, response=response_content, error=None)

    except HTTPException:
        # Re-raise HTTP exceptions (already handled)
        raise
    except ValueError as e:
        error_msg = f"Invalid input or configuration: {str(e)}"
        logger.error(error_msg)
        log_error_with_context(error_msg, {"user_query": user_query})
        raise HTTPException(status_code=400, detail=error_msg)
    except ConnectionError as e:
        error_msg = f"SAP system connection failed: {str(e)}"
        logger.error(error_msg)
        log_error_with_context(error_msg, {"user_query": user_query})
        raise HTTPException(
            status_code=502, detail="SAP system temporarily unavailable"
        )
    except TimeoutError as e:
        error_msg = f"Request timeout: {str(e)}"
        logger.error(error_msg)
        log_error_with_context(error_msg, {"user_query": user_query})
        raise HTTPException(
            status_code=504, detail="Request timeout - SAP system is slow"
        )
    except Exception as e:
        error_msg = f"Unexpected error processing query: {str(e)}"
        logger.error(error_msg)
        log_error_with_context(
            error_msg, {"user_query": user_query, "error_type": type(e).__name__}
        )

        # Log failed response
        log_api_response(status_code=500, execution_time_ms=0, success=False)

        # Don't expose internal errors to client
        raise HTTPException(
            status_code=500,
            detail="Internal server error occurred. Please try again or contact support.",
        )
