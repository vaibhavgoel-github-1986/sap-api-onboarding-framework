"""
SAP Source Code Tool - Get ABAP objects source code
"""

from ..pydantic_models.sap_tech import SAPServiceConfig
from .base_sap_tool import BaseSAPTool


class GetServItemsTool(BaseSAPTool):
    """
    Tool for retrieving SAP BRIM service items information including CC Config params, Material Characteristics,
    and other related details.
    """

    name: str = "get_serv_items"
    #     return_direct: bool = True
    description: str = """

    Tool to provide comprehensive access to subscription orders, customer/custom information, 
    configuration parameters, material characteristics, and related data.

    ## Core Responsibilities
    - **Subscription Lifecycle**: Details, activation status, contract periods, start/end dates
    - **Customer/Custom Data**: Header and item-level customer information (billing, shipping, payment)
    - **Configuration Parameters**: CC configuration settings and values
    - **Material Characteristics**: Product specifications and attributes
    - **Appointments**: Contract start/end dates, service appointments, term dates
    - **Pricing**: Adjustments, credits, and pricing information
    - **Smart Accounts**: Virtual account and smart account details

    Use this SAP API details:
    - service_name="ZSD_SERVICE_API",
    - service_namespace="ZSB_SERVICE_API",
    - entity_name=[Depends on the user query], 
    - odata_version="v4",
    - http_method="GET"
    
    Entities Available:
        - `ServiceItems`: Main subscription item details
        - `ConfigParams`: Configuration parameters for CC
        - `MaterialCharac`: Material characteristics for products
        - `HeadCust`: Header-level customer/custom data
        - `ItemCust`: Item-level customer/custom data
        - `PriceAdj`: Pricing adjustments and credits
        - `Appointments`: Service and contract appointment dates
        - `CCParams`: List of available CC configuration parameters
        - `MaterialParams`: List of available material characteristic names
                
    ## Query Strategy Guidelines

    ### Default Behavior for General Subscription Queries
    For any general subscription request (e.g., "get details for subscription X"), ALWAYS apply these performance-optimized defaults:

    ```python
    query_parameters = {
        "filter": "SubscriptionReferenceId eq '[SUBSCRIPTION_ID]' and ObjectType eq 'BUS2000266'",
        "select": "ObjectId,SubscriptionReferenceId,WebOrderId,OrderedProductName,ActivationStatus,ContractTimeSliceStatus"    
    }
    ```

    ### Specific Configuration Parameter Queries
    When users ask for specific configuration parameters, DO NOT use general defaults. Instead, create targeted filters:

    ```python
    # Example: Bill immediate configuration
    query_parameters = {
        "filter": "SubscriptionReferenceId eq '[SUB_ID]' and ItemLevel eq 'Minor'",
        "select": "SubscriptionReferenceId,WebOrderId,OrderedProductName,ActivationStatus,ItemLevel", 
        "expand": "_ConfigParams($filter=ConfigName eq 'CIS_CC_BILLIMMEDIATE' and ConfigValue ne '' and ConfigValue ne 'NA')"
    }
    ```

    ### Dynamic Parameter Discovery
    Before processing configuration or characteristic queries:

    1. **Fetch CC Parameters**: Query CCParams entity to get available configuration parameter names
    2. **Fetch Material Parameters**: Query MaterialParams entity for material characteristic names
    3. **Map User Intent**: Match user's natural language request to exact parameter names
    4. **Generate Targeted Query**: Create specific filters using discovered parameter names

    This ensures you always use current, accurate parameter names rather than hardcoded values.

    ### Exceptions to Default Behavior
    Do NOT use defaults when:
    - User explicitly requests specific fields/columns
    - User asks for "all configurations" or "all characteristics"
    - User queries specific entities (HeadCust, ItemCust, PriceAdj) directly
    - User provides explicit $select or $expand requirements
    - User asks for specific configuration parameters by name

    ### Specific Entity Queries
    You can use direct entities as well for focused queries:
    - `HeadCust`, `ItemCust` (customer/custom data)
    - `ConfigParams`, `MaterialCharac` (config parameters/ material characteristics)
    - `PriceAdj` (pricing adjustments)
    - `Appointments` (dates and scheduling)

    ## Query Rules
    - Always filter out empty values: `ConfigValue ne ''`, `CharacValue ne ''`
    
    ## Few Examples for Query Parameters:
    ### Get items with appointment information
    ```python
        query_parameters={
                "filter": "ActivationStatus eq 'E'",
                "expand": "_Appoint",
                "select": "SubsRefId,Product,ActivationStatus,_Appoint"
        }
    ```

    ### Search by Multiple Criteria
    ```python
        query_parameters={
                "filter": "ActivationStatus eq 'E' and ItemCreatedAt ge 2024-01-01T00:00:00Z and ItemCreatedAt le 2024-12-31T23:59:59Z",
                "orderby": "ItemCreatedAt desc",
                "top": "100"
        }
    ```

    ### Get specific configuration parameter (Bill Immediate for Minor items)
    ```python
        query_parameters={
                "filter": "SubscriptionReferenceId eq 'INTJPKS800205' and ItemLevel eq 'Minor'",
                "select": "SubscriptionReferenceId,WebOrderId,OrderedProductName,ActivationStatus,ItemLevel",
                "expand": "_ConfigParams($filter=ConfigName eq 'CIS_CC_BILLIMMEDIATE' and ConfigValue ne '' and ConfigValue ne 'NA')"
        }
    ```

    ### Get multiple specific configurations
    ```python
        query_parameters={
                "filter": "SubscriptionReferenceId eq 'SUB123456'",
                "select": "SubscriptionReferenceId,WebOrderId,OrderedProductName,ActivationStatus",
                "expand": "_ConfigParams($filter=(ConfigName eq 'CIS_CC_BILL_MODEL' or ConfigName eq 'CIS_CC_BILLIMMEDIATE' or ConfigName eq 'CIS_CC_BASE_START_DATE') and ConfigValue ne '' and ConfigValue ne 'NA')"
        }
    ```

    ### Filter and Select Specific Fields from Child Entities
    ```python
            query_parameters={
                "filter": "SubscriptionReferenceId eq 'SUB12345' and ItemLevel eq 'Minor'",
                "select": "SubscriptionReferenceId,WebOrderId,OrderedProductName,ActivationStatus,ItemLevel",
                "expand": "ConfigParams($select=ConfigName,ConfigValue;$filter=ConfigName eq 'CIS_CC_BILLIMMEDIATE' and ConfigValue ne '' and ConfigValue ne 'NA')"
        }
    ```

    ## Value Examples:
    - **ObjectType** (Subscription Type):
            - BUS2000116	Service Order/Quotation
            - BUS2000265	Subscription Order
            - BUS2000266	Subscription Contract
            
    - **ActivationStatus**:
            - A	Not Active
            - B	Contract Accepted
            - C	In Activation
            - D	Activation Failed
            - E	Technically Active
            
    - **ContractTimeSliceStatus**:
            - N	Not Active
            - Y	Last Contract Time Slice

    - **ActionType**:
            - MANUAL RENEWAL
            - CANCEL
            - MODIFY
            - NEW
            - DELETE
            - NOCHANGE
            - REPLACE
            - ADD
            - CHANGE
            - NOCHANGE

    - **ItemLevel**:
            - Minor
            - BILLING SKU
            - Major
            - Bundle
    """

    def get_service_config(self, **kwargs) -> SAPServiceConfig:
        """
        Return the SAP service configuration for this tool.
        """
        return SAPServiceConfig(
            service_name="ZSD_SERVICE_API",
            service_namespace="ZSB_SERVICE_API",
            entity_name="ServiceItems",
            odata_version="v4",
            http_method="GET",
        )


get_serv_items = GetServItemsTool()
