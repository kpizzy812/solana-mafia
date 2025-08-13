"""
Commission Withdrawal Service - Automatically processes referral commission withdrawals using admin private key.
"""

import os
import asyncio
from typing import List, Optional
from datetime import datetime, timedelta

from solana.rpc.async_api import AsyncClient
from solders.transaction import Transaction
from solders.system_program import transfer, TransferParams
from solders.pubkey import Pubkey
from solders.keypair import Keypair
from solders.hash import Hash
from solders.message import Message
from solders.instruction import Instruction
import base58

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.services.referral_service import ReferralService
from app.models.referral import ReferralWithdrawal
from app.core.config import settings

logger = structlog.get_logger(__name__)


class CommissionWithdrawalService:
    """Service for automatically processing referral commission withdrawals."""
    
    def __init__(self):
        self.rpc_url = settings.solana_rpc_url
        self.admin_private_key = settings.admin_private_key
        self.min_withdrawal_amount = 0.001  # Minimum 0.001 SOL
        self.max_batch_size = 10  # Process max 10 withdrawals at once
        
        # Initialize admin keypair
        try:
            # Convert base58 private key to keypair
            private_key_bytes = base58.b58decode(self.admin_private_key)
            self.admin_keypair = Keypair.from_bytes(private_key_bytes)
            
            logger.info(
                "Admin keypair initialized for commission withdrawals",
                admin_pubkey=str(self.admin_keypair.pubkey())
            )
            
        except Exception as e:
            logger.error(
                "Failed to initialize admin keypair", 
                error=str(e)
            )
            raise
    
    async def process_pending_withdrawals(self) -> int:
        """Process all pending commission withdrawals."""
        processed_count = 0
        
        async with get_async_session() as db:
            referral_service = ReferralService(db)
            
            # Get pending withdrawals
            pending_withdrawals = await referral_service.get_pending_withdrawals(
                limit=self.max_batch_size
            )
            
            if not pending_withdrawals:
                logger.debug("No pending withdrawals to process")
                return 0
            
            logger.info(
                f"Processing {len(pending_withdrawals)} pending withdrawals"
            )
            
            # Process each withdrawal
            for withdrawal in pending_withdrawals:
                try:
                    success = await self._process_single_withdrawal(
                        db, referral_service, withdrawal
                    )
                    
                    if success:
                        processed_count += 1
                        # Add small delay between transactions
                        await asyncio.sleep(1)
                    
                except Exception as e:
                    logger.error(
                        "Failed to process withdrawal",
                        withdrawal_id=withdrawal.id,
                        user_id=withdrawal.user_id,
                        amount_sol=withdrawal.amount_sol,
                        error=str(e)
                    )
                    
                    # Mark withdrawal as failed
                    try:
                        await referral_service.fail_sol_withdrawal(
                            withdrawal_id=withdrawal.id,
                            error_message=f"Automatic processing failed: {str(e)}"
                        )
                        await db.commit()
                    except Exception as fail_error:
                        logger.error(
                            "Failed to mark withdrawal as failed",
                            withdrawal_id=withdrawal.id,
                            error=str(fail_error)
                        )
            
            logger.info(
                f"Commission withdrawal processing completed",
                processed=processed_count,
                total=len(pending_withdrawals)
            )
            
        return processed_count
    
    async def _process_single_withdrawal(
        self,
        db: AsyncSession,
        referral_service: ReferralService,
        withdrawal: ReferralWithdrawal
    ) -> bool:
        """Process a single withdrawal transaction."""
        
        # Validate withdrawal amount
        if withdrawal.amount_sol < self.min_withdrawal_amount:
            await referral_service.fail_sol_withdrawal(
                withdrawal_id=withdrawal.id,
                error_message=f"Amount too small (minimum: {self.min_withdrawal_amount} SOL)"
            )
            await db.commit()
            return False
        
        try:
            # Create Solana client
            async with AsyncClient(self.rpc_url) as client:
                
                # Get recipient public key
                try:
                    recipient_pubkey = Pubkey.from_string(withdrawal.user_id)
                except Exception:
                    raise ValueError(f"Invalid recipient wallet address: {withdrawal.user_id}")
                
                # Check admin balance
                admin_balance = await client.get_balance(self.admin_keypair.pubkey())
                admin_balance_sol = admin_balance.value / 1_000_000_000
                
                required_sol = withdrawal.amount_sol + 0.000005  # Add fee buffer
                
                if admin_balance_sol < required_sol:
                    raise ValueError(
                        f"Insufficient admin balance: {admin_balance_sol} SOL, "
                        f"required: {required_sol} SOL"
                    )
                
                # Get recent blockhash
                recent_blockhash = await client.get_latest_blockhash()
                
                # Create transfer instruction
                transfer_instruction = transfer(
                    TransferParams(
                        from_pubkey=self.admin_keypair.pubkey(),
                        to_pubkey=recipient_pubkey,
                        lamports=withdrawal.amount_lamports
                    )
                )
                
                # Create message and transaction
                message = Message.new_with_blockhash(
                    [transfer_instruction],
                    self.admin_keypair.pubkey(),
                    recent_blockhash.value.blockhash
                )
                
                # Create and sign transaction
                transaction = Transaction.new_unsigned(message)
                transaction = Transaction.new_signed_with_payer(
                    [transfer_instruction],
                    self.admin_keypair.pubkey(),
                    [self.admin_keypair],
                    recent_blockhash.value.blockhash
                )
                
                # Send transaction
                response = await client.send_transaction(transaction)
                transaction_signature = str(response.value)
                
                # Confirm transaction
                confirmation = await client.confirm_transaction(transaction_signature)
                
                if confirmation.value[0].err:
                    raise ValueError(f"Transaction failed: {confirmation.value[0].err}")
                
                # Mark withdrawal as completed
                await referral_service.complete_sol_withdrawal(
                    withdrawal_id=withdrawal.id,
                    transaction_signature=transaction_signature
                )
                await db.commit()
                
                logger.info(
                    "Commission withdrawal completed successfully",
                    withdrawal_id=withdrawal.id,
                    user_id=withdrawal.user_id,
                    amount_sol=withdrawal.amount_sol,
                    transaction_signature=transaction_signature,
                    admin_balance_after=admin_balance_sol - withdrawal.amount_sol
                )
                
                return True
                
        except Exception as e:
            logger.error(
                "Failed to send withdrawal transaction",
                withdrawal_id=withdrawal.id,
                user_id=withdrawal.user_id,
                amount_sol=withdrawal.amount_sol,
                error=str(e)
            )
            raise
    
    async def get_admin_balance(self) -> float:
        """Get current admin wallet balance in SOL."""
        try:
            async with AsyncClient(self.rpc_url) as client:
                balance = await client.get_balance(self.admin_keypair.pubkey())
                return balance.value / 1_000_000_000
        except Exception as e:
            logger.error("Failed to get admin balance", error=str(e))
            return 0.0
    
    async def estimate_withdrawal_fees(self, withdrawal_count: int) -> float:
        """Estimate total SOL needed for withdrawal fees."""
        # Each transaction costs ~0.000005 SOL
        return withdrawal_count * 0.000005
    
    def is_configured(self) -> bool:
        """Check if service is properly configured."""
        return bool(
            self.rpc_url and 
            self.admin_private_key and 
            hasattr(self, 'admin_keypair')
        )


# Singleton instance
withdrawal_service = CommissionWithdrawalService()


# Background task runner
async def run_withdrawal_processor():
    """Background task to process withdrawals periodically."""
    if not withdrawal_service.is_configured():
        logger.error("Commission withdrawal service not configured properly")
        return
    
    logger.info("Starting commission withdrawal processor")
    
    while True:
        try:
            # Process withdrawals every 5 minutes
            processed = await withdrawal_service.process_pending_withdrawals()
            
            if processed > 0:
                logger.info(f"Processed {processed} commission withdrawals")
            
            # Wait 5 minutes before next check
            await asyncio.sleep(300)
            
        except Exception as e:
            logger.error(
                "Error in withdrawal processor loop",
                error=str(e)
            )
            # Wait 1 minute before retrying on error
            await asyncio.sleep(60)


# Manual processing function
async def process_withdrawals_now() -> dict:
    """Process withdrawals immediately (for manual triggering)."""
    if not withdrawal_service.is_configured():
        return {
            "success": False,
            "error": "Service not configured properly"
        }
    
    try:
        admin_balance = await withdrawal_service.get_admin_balance()
        processed = await withdrawal_service.process_pending_withdrawals()
        
        return {
            "success": True,
            "processed_withdrawals": processed,
            "admin_balance_sol": admin_balance,
            "processed_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error("Manual withdrawal processing failed", error=str(e))
        return {
            "success": False,
            "error": str(e),
            "processed_at": datetime.utcnow().isoformat()
        }


if __name__ == "__main__":
    # For testing
    import asyncio
    
    async def test():
        result = await process_withdrawals_now()
        print(f"Withdrawal processing result: {result}")
    
    asyncio.run(test())