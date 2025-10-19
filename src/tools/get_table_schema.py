"""
SAP Table Schema Tool - Get table structure and field information
"""

from ..pydantic_models.sap_tech import SAPServiceConfig
from .base_sap_tool import BaseSAPTool


class GetTableSchemaTool(BaseSAPTool):
    """
    Tool for retrieving SAP table schema information including field definitions,
    data types, lengths, and constraints.
    """

    name: str = "get_table_schema"
    # return_direct: bool = True
    description: str = """
    Get detailed schema information for any SAP table including field names, data types, 
    lengths, descriptions, and constraints. 
    
    Use this SAP API to fetch the table schema:
    - service_name="ZSD_TABLE_SCHEMA",
    - service_namespace="ZSB_TABLE_SCHEMA",
    - entity_name="TableSchema", 
    - odata_version="v4",
    - http_method="GET"
            
    Use this tool when you need to:
    - Understand the structure of an SAP table
    - Retrieve field definitions and data types
    - Identify available fields within a table
    - Analyze the schema to prepare for data queries
    
    Query Parameters Examples:
    - Get all fields for a table: {"filter": "tableName eq 'MARA'"}
    - Get specific fields: {"filter": "tableName eq 'VBAK' and (fieldName eq 'VBELN' or fieldName eq 'ERDAT')"}
    - Limit results: {"filter": "tableName eq 'KNA1'", "top": "50"}
    - Select specific columns: {"filter": "tableName eq 'MAKT'", "select": "fieldName,dataType,length"}
    """
    
    def get_service_config(self, **kwargs) -> SAPServiceConfig:
        """
        Return the SAP service configuration for this tool.
        """
        return SAPServiceConfig(
            service_name="ZSD_TABLE_SCHEMA",
            service_namespace="ZSB_TABLE_SCHEMA",
            entity_name="TableSchema",
            odata_version="v4",
            http_method="GET"
        )   
        
get_table_schema = GetTableSchemaTool()        
