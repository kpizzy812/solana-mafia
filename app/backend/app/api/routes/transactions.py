"""
API routes for transaction processing.
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime
import structlog

from app.services.signature_processor import (
    queue_signature_for_processing,
    get_processing_status,
    get_signature_processor
)

logger = structlog.get_logger(__name__)
router = APIRouter()


class ProcessTransactionRequest(BaseModel):
    """Request to process a transaction signature."""
    signature: str
    user_wallet: Optional[str] = None
    slot_index: Optional[int] = None
    business_level: Optional[int] = None
    context: Optional[Dict[str, Any]] = None  # Additional context data


class ProcessTransactionResponse(BaseModel):
    """Response for transaction processing request."""
    success: bool
    message: str
    signature: str
    queued_at: str
    estimated_processing_time: str = "30-60 seconds"


class TransactionStatusResponse(BaseModel):
    """Response for transaction status check."""
    signature: str
    status: str  # queued, processing, completed, failed
    result: Optional[Dict[str, Any]] = None


@router.post("/process", response_model=ProcessTransactionResponse)
async def process_transaction(request: ProcessTransactionRequest):
    """
    Queue a transaction signature for processing.
    
    This endpoint:
    1. Receives signature from frontend immediately after transaction
    2. Queues it for async processing using proven force_process_transaction logic  
    3. Returns immediately with queued status
    4. Processing happens in background
    5. WebSocket notifications sent when complete
    """
    try:
        logger.info("📥 API: Process transaction request",
                   signature=request.signature,
                   user_wallet=request.user_wallet,
                   slot_index=request.slot_index)
        
        # Validate signature format
        if not request.signature or len(request.signature) < 64:
            raise HTTPException(
                status_code=400,
                detail="Invalid signature format"
            )
        
        # Queue for processing
        success = await queue_signature_for_processing(
            signature=request.signature,
            user_wallet=request.user_wallet,
            slot_index=request.slot_index,
            business_level=request.business_level
        )
        
        if not success:
            raise HTTPException(
                status_code=500,
                detail="Failed to queue transaction for processing"
            )
        
        logger.info("✅ Transaction queued successfully",
                   signature=request.signature)
        
        return ProcessTransactionResponse(
            success=True,
            message="Transaction queued for processing",
            signature=request.signature,
            queued_at=str(datetime.utcnow()),
            estimated_processing_time="30-60 seconds"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("❌ Failed to process transaction request",
                    signature=request.signature,
                    error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@router.get("/status/{signature}", response_model=TransactionStatusResponse)
async def get_transaction_status(signature: str):
    """
    Get processing status for a transaction signature.
    
    Returns:
    - queued: In processing queue
    - processing: Currently being processed  
    - completed: Successfully processed
    - failed: Processing failed
    """
    try:
        logger.info("🔍 API: Get transaction status", signature=signature)
        
        status_info = await get_processing_status(signature)
        
        if not status_info:
            raise HTTPException(
                status_code=404,
                detail="Transaction not found in processing system"
            )
        
        return TransactionStatusResponse(
            signature=signature,
            status=status_info["status"],
            result=status_info.get("result")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("❌ Failed to get transaction status",
                    signature=signature,
                    error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@router.get("/processor/status")
async def get_processor_status():
    """
    Get signature processor status and statistics.
    
    Useful for monitoring and debugging.
    """
    try:
        processor = await get_signature_processor()
        status = processor.get_status()
        
        return {
            "success": True,
            "processor_status": status,
            "message": "Processor is running" if status["running"] else "Processor is stopped"
        }
        
    except Exception as e:
        logger.error("❌ Failed to get processor status", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get processor status: {str(e)}"
        )


@router.post("/processor/restart")
async def restart_processor():
    """
    Restart the signature processor (admin only).
    
    Useful for recovery scenarios.
    """
    try:
        logger.info("🔄 API: Restarting signature processor")
        
        processor = await get_signature_processor()
        await processor.stop()
        await processor.start()
        
        return {
            "success": True,
            "message": "Signature processor restarted successfully"
        }
        
    except Exception as e:
        logger.error("❌ Failed to restart processor", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to restart processor: {str(e)}"
        )