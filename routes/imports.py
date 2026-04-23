"""Import endpoints for external data sources."""

import logging
from fastapi import APIRouter, File, Query, UploadFile
from db.client import get_beurer_supabase
from models import ServiceCaseImportResult
from services.service_case_importer import import_service_cases

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/import/service-cases",
    response_model=ServiceCaseImportResult,
    summary="Import Salesforce service case CSV or HTML-XLS file",
)
async def upload_service_cases(
    file: UploadFile = File(...),
    client_id: str = Query("beurer", description="Client identifier"),
):
    """Upload and import a Salesforce service case export file.

    Accepts CSV (semicolon or comma delimited) or HTML-table-as-XLS format.
    Deduplicates by case_id — existing cases are skipped.
    """
    try:
        contents = await file.read()
        db_client = get_beurer_supabase()
        result = import_service_cases(
            file_bytes=contents,
            filename=file.filename or "upload.csv",
            client_id=client_id,
            db_client=db_client,
        )
        return ServiceCaseImportResult(**result)
    except Exception as e:
        logger.exception(f"Service case import failed: {e}")
        raise
