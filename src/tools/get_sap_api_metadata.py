import sys, os
from typing import Literal, Optional
from dotenv import load_dotenv
from fastapi import HTTPException

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, project_root)
from src.utils.sap_common import handle_sap_exceptions
from src.models.sap_tech import (
    MetadataResponse,
) 
from src.utils.sap_api_client import (
    SAPApiClient,
    SAPServerException,
)
from src.utils.logger import logger

# Load environment variables
load_dotenv()
 
@handle_sap_exceptions("fetching OData service metadata")
def get_service_metadata(
    service_name: str,
    system_id: str,
    service_namespace: Optional[str] = None,
    odata_version: Literal["v2", "v4"] = "v4",
    client_id: Optional[int] = None,
    username: Optional[str] = None,
    password: Optional[str] = None,
) -> MetadataResponse:
    """
    Get OData service metadata from SAP system

    Args:
        service_name: SAP OData service name (required)
        service_namespace: Service namespace (optional, defaults to service_name)
        odata_version: OData version - v2 or v4 (optional, defaults to v4)
        system_id: SAP system ID (optional, uses config default)

    Returns:
        MetadataResponse: Parsed metadata information
    """

    if not system_id:
        raise HTTPException(status_code=400, detail="Please provide SAP system ID")

    if not service_name:
        raise HTTPException(status_code=400, detail="Service name is required")

    # Validate odata_version
    if odata_version not in ["v2", "v4"]:
        raise HTTPException(
            status_code=400, detail="OData version must be 'v2' or 'v4'"
        )

    # Use service_name as namespace if not provided
    if not service_namespace:
        service_namespace = service_name

    # Initialize SAP API client
    client = SAPApiClient(
        client_id=client_id,
        system_id=system_id,
        username=username,
        password=password,
        service_name=service_name,
        service_namespace=service_namespace,
        odata_version=odata_version
    )

    logger.info(
        f"Initialized SAP client for system: {system_id}, service: {service_name} -> {service_namespace}, version: {odata_version}"
    )

    try:
        # Get the raw metadata XML using the client's get_raw_metadata method
        metadata_xml = client.get_raw_metadata()

        logger.info(
            f"Retrieved metadata XML for service {service_name}, size: {len(metadata_xml)} characters"
        )

        if not metadata_xml or len(metadata_xml) < 100:
            return MetadataResponse(
                service_name=service_name,
                service_namespace=service_namespace,
                odata_version=odata_version,
                metadata_xml="",
                entity_count=0,
                message="No metadata found or metadata response is too small"
            )

        # Count entity types in the XML for summary info
        import xml.etree.ElementTree as ET

        try:
            root = ET.fromstring(metadata_xml)
            entity_count = 0

            if odata_version == "v4":
                namespace = {"edm": "http://docs.oasis-open.org/odata/ns/edm"}
                entity_types = root.findall(".//edm:EntityType", namespace)
                entity_count = len(entity_types)
            else:
                namespace = {
                    "edmx": "http://schemas.microsoft.com/ado/2007/06/edmx",
                    "edm": "http://schemas.microsoft.com/ado/2008/09/edm",
                }
                schema_elements = root.findall(".//edm:Schema", namespace)
                for schema in schema_elements:
                    entity_types = schema.findall("edm:EntityType", namespace)
                    entity_count += len(entity_types)

        except Exception as parse_error:
            logger.warning(f"Could not parse XML for entity count: {parse_error}")
            entity_count = 0

        return MetadataResponse(
            service_name=service_name,
            service_namespace=service_namespace,
            odata_version=odata_version,
            metadata_xml=metadata_xml,
            entity_count=entity_count,
            message=f"Successfully retrieved metadata for {service_name} with {entity_count} entities"
        ) # pyright: ignore[reportCallIssue]

    except SAPServerException as e:
        logger.error(
            f"SAP Server Error - Status: {e.status_code}, Detail: {e.error_detail}"
        )
        logger.error(f"Full exception message: {e.message}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error calling SAP API: {type(e).__name__}: {e}")
        raise
