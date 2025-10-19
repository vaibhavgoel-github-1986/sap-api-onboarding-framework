"""
SAP Table Schema Tool - Get table structure and field information
"""

from ..pydantic_models.sap_tech import SAPServiceConfig
from .base_sap_tool import BaseSAPTool


class GetAppLogsTool(BaseSAPTool):
    """
    Tool for retrieving SLG1 Application Logs from SAP System
    """

    name: str = "get_slg1_logs"
    # return_direct: bool = True
    description: str = """
    Get Application SLG1 Logs from SAP for any transaction or object including log messages,
    timestamps, user information, and log levels.
    
    Use this SAP API:
    - service_name="ZSD_APPL_LOG_READ",
    - service_namespace="ZSB_APPL_LOG_READ",
    - entity_name="LogMessages", 
    - odata_version="v4",
    - http_method="GET"

    ## Query Parameters Examples:
    Mostly object is defaulted to "ZCISCO" and sub_object to "*" to get all logs.
    
    ### Get logs for Subs Ref ID or Object ID Sub2011473 for today
    ```python
        query_parameters={
                "filter": "external_number eq 'Sub2011473' and logged_on eq 2025-10-19T00:00:00Z"
        }
    ```
    
    You can play around with other date ranges, log levels, etc. as needed.
    """
    
    def get_service_config(self, **kwargs) -> SAPServiceConfig:
        """
        Return the SAP service configuration for this tool.
        """
        return SAPServiceConfig(
            service_name="ZSD_APPL_LOG_READ",
            service_namespace="ZSB_APPL_LOG_READ",
            entity_name="LogMessages",
            odata_version="v4",
            http_method="GET"
        )   
        
get_slg1_logs = GetAppLogsTool()        
