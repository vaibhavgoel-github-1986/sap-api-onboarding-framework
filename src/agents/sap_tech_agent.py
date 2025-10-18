from langgraph.prebuilt import create_react_agent
from typing import Any

from ..llm_model.get_azure_llm import get_azure_llm
from ..tools.get_table_schema import get_table_schema
from ..tools.get_source_code import get_source_code
from ..tools.get_metadata import get_metadata
from ..utils.logger import logger


def create_sap_tech_agent() -> Any:
    """Create and return the SAP Technical Agent."""
    logger.info("Creating SAP Technical Agent")

    return create_react_agent(
        model=get_azure_llm(),
        tools=[get_table_schema, get_source_code, get_metadata],
        prompt="""
            You are an intelligent SAP agent with access to tools that interact with SAP APIs.

            Your task is to analyze the user's request and determine which tool to use to retrieve the required information from the SAP system.

            - Before invoking any tool that calls an SAP API, always use the `get_metadata` tool first to fetch the API metadata.  
            - Use this metadata to understand the API structure, parameters, and HTTP methods that can be used.  
            - Then, construct the appropriate `query_parameters` or `request_body` based on the API method before executing the call.
        """,
        name="SAPTechnicalAgent",
    )
