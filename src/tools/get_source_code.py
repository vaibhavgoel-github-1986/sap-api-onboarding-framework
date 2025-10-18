"""
SAP Source Code Tool - Get ABAP objects source code
"""

from pydantic_models.sap_tech import SAPServiceConfig
from .base_sap_tool import BaseSAPTool


class GetSourceCodeTool(BaseSAPTool):
    """
    Tool for retrieving SAP source code information including field definitions,
    data types, lengths, and constraints.
    """

    name: str = "get_source_code"
    return_direct: bool = True
    description: str = """
    Get detailed source code information for any SAP object like CLAS, PROG, FUNC, etc., including field names, data types, 
    lengths, descriptions, and constraints. 
    
    Use this SAP API to fetch the source code:
    - service_name="ZSD_SOURCE_CODE",
    - service_namespace="ZSB_SOURCE_CODE",
    - entity_name="SourceCode", 
    - odata_version="v4",
    - http_method="GET"
    
    Try to figure out the object type based on common prefixes:
    - CLAS: Classes (e.g., ZCL_)
    - Interfaces: (e.g., ZIF_)
    - PROG: Programs (e.g., ZR_, ZAB_)
    - FUNC: Function Modules (e.g., ZFM_)
    
    Query Parameters Examples:
    - Get all fields for a source code: {"filter": "obj_name eq 'zcl_jira_utils' and obj_type eq 'CLAS'"}
    """

    def get_service_config(self, **kwargs) -> SAPServiceConfig:
        """
        Return the SAP service configuration for this tool.
        """
        return SAPServiceConfig(
            service_name="ZSD_SOURCE_CODE",
            service_namespace="ZSB_SOURCE_CODE",
            entity_name="SourceCode",
            odata_version="v4",
            http_method="GET"
        )

get_source_code = GetSourceCodeTool()
