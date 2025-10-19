from langgraph.prebuilt import create_react_agent
from langgraph.graph.state import CompiledStateGraph

from ..llm_model.get_azure_llm import get_azure_llm
from ..tools.get_metadata import get_metadata
from ..tools.get_table_schema import get_table_schema
from ..tools.get_source_code import get_source_code
from ..tools.get_serv_items import get_serv_items
from ..tools.get_slg1_logs import get_slg1_logs

from ..utils.logger import logger


def create_sap_agent() -> CompiledStateGraph:
    """Create and return the SAP Agent."""
    logger.info("Creating SAP Agent")

    return create_react_agent(
        model=get_azure_llm(),
        tools=[
            get_metadata,
            get_table_schema,
            get_source_code,
            get_serv_items,
            get_slg1_logs,
        ],
        prompt="""
            You are an intelligent SAP agent with access to tools that interact with SAP APIs.

            Your task is to analyze the user's request and determine which tool to use to retrieve the required information from the SAP system.
            If user's request does not relate to any of the SAP operations or tools you have access to, then politely inform them that you
            can only assist with SAP related queries and provide them your capabilities.

            - Before invoking any tool that calls an SAP API, always use the `get_metadata` tool first to fetch the API metadata.  
            - Use this metadata to understand the API structure, parameters, and HTTP methods that can be used.  
            - Then, construct the appropriate `query_parameters` or `request_body` based on the API method before executing the call.
            
            ## Global oData Query Rules
            - Use proper OData filters (`eq`, `startswith`, `contains`, etc.)
            - SAP OData does NOT support `in` operator - so use `or` conditions instead
            - Date/time must be ISO 8601 UTC format
            - GUIDs must be valid format: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
            - Case sensitivity: use annotations (`IsUpperCase`)
            - Date format in SAP: YYYYMMDD (e.g. 20210329 for March 29, 2021)
            - TimeStamp Format in SAP: YYYYMMDDHHMMSS (e.g. 20210329143000 for March 29, 2021 at 2:30 PM)
            - When user says current date/time, use the actual current date/time in PST Format
        """,
        name="SAPAgent",
    )
