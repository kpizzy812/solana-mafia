"""
Transaction service for sending Solana transactions.
Handles earnings updates and other admin operations.
"""

import asyncio
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import base58
import json

from solana.rpc.async_api import AsyncClient
from solana.rpc.commitment import Commitment
from solana.rpc.types import TxOpts
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from solders.instruction import Instruction, AccountMeta
from solders.system_program import ID as SYSTEM_PROGRAM_ID
from solders.message import MessageV0
from solders.transaction import VersionedTransaction
from solders.hash import Hash
from solders.signature import Signature
import structlog

from app.core.config import settings
from app.core.exceptions import SolanaRPCError
from app.services.solana_client import get_solana_client
from app.services.pda_validator import validate_players_before_earnings


logger = structlog.get_logger(__name__)


@dataclass 
class TransactionResult:
    """Result of a sent transaction."""
    signature: str
    success: bool
    error: Optional[str] = None


class TransactionService:
    """
    Service for creating and sending Solana transactions.
    Handles admin operations like earnings updates.
    """
    
    def __init__(self):
        """Initialize transaction service."""
        self.logger = logger.bind(service="transaction_service")
        self.program_id = Pubkey.from_string(settings.solana_program_id)
        self.client: Optional[AsyncClient] = None
        self.admin_keypair: Optional[Keypair] = None
        
    async def initialize(self):
        """Initialize the service with admin keypair."""
        try:
            if not settings.admin_private_key:
                raise ValueError("Admin private key not configured")
                
            # Initialize admin keypair from base58 private key
            self.admin_keypair = Keypair.from_base58_string(settings.admin_private_key)
            
            # Get Solana client
            solana_client = await get_solana_client()
            self.client = solana_client.client
            
            self.logger.info("Transaction service initialized", admin_pubkey=str(self.admin_keypair.pubkey()))
            
        except Exception as e:
            self.logger.error("Failed to initialize transaction service", error=str(e))
            raise SolanaRPCError(f"Failed to initialize transaction service: {e}")
            
            
    async def claim_player_earnings(self, player_wallet: str, player_private_key: str) -> TransactionResult:
        """
        Send claim_earnings transaction for a player (requires player's private key).
        
        Args:
            player_wallet: Player's wallet address
            player_private_key: Player's base58 private key
            
        Returns:
            TransactionResult with signature and status
        """
        try:
            # Initialize player keypair from base58 private key
            player_keypair = Keypair.from_base58_string(player_private_key)
            player_pubkey = Pubkey.from_string(player_wallet)
            
            # Verify keypair matches wallet
            if player_keypair.pubkey() != player_pubkey:
                raise ValueError("Private key does not match wallet address")
            
            # Derive PDAs
            game_state_pda, _ = Pubkey.find_program_address(
                [b"game_state"], 
                self.program_id
            )
            
            treasury_pda, _ = Pubkey.find_program_address(
                [b"treasury"], 
                self.program_id
            )
            
            player_pda, _ = Pubkey.find_program_address(
                [b"player", player_pubkey.__bytes__()], 
                self.program_id
            )
            
            # Create instruction data (empty for this instruction)
            instruction_data = b""
            
            # Build instruction accounts for ClaimEarnings
            accounts = [
                AccountMeta(pubkey=player_pubkey, is_signer=True, is_writable=True),  # player_owner
                AccountMeta(pubkey=player_pda, is_signer=False, is_writable=True),  # player
                AccountMeta(pubkey=treasury_pda, is_signer=False, is_writable=True),  # treasury_pda
                AccountMeta(pubkey=game_state_pda, is_signer=False, is_writable=True),  # game_state (mut)
                AccountMeta(pubkey=SYSTEM_PROGRAM_ID, is_signer=False, is_writable=False),  # system_program
            ]
            
            # Get instruction discriminator for claim_earnings
            instruction_discriminator = self._get_instruction_discriminator("claim_earnings")
            full_instruction_data = instruction_discriminator + instruction_data
            
            instruction = Instruction(
                program_id=self.program_id,
                accounts=accounts,
                data=full_instruction_data
            )
            
            # Get recent blockhash
            recent_blockhash_resp = await self.client.get_latest_blockhash()
            recent_blockhash = recent_blockhash_resp.value.blockhash
            
            # Create versioned transaction signed by player
            message = MessageV0.try_compile(
                payer=player_pubkey,
                instructions=[instruction],
                address_lookup_table_accounts=[],
                recent_blockhash=recent_blockhash,
            )
            
            # Create and sign transaction with player's keypair
            transaction = VersionedTransaction(message, [player_keypair])
            
            # Send transaction
            opts = TxOpts(skip_preflight=False, preflight_commitment="confirmed")
            response = await self.client.send_transaction(transaction, opts=opts)
            
            signature = str(response.value)
            
            # Wait for confirmation
            sig_obj = Signature.from_string(signature)
            confirmation = await self.client.confirm_transaction(
                sig_obj,
                commitment="confirmed"
            )
            
            success = confirmation.value[0].err is None
            error_msg = str(confirmation.value[0].err) if not success else None
            
            self.logger.info(
                "Player earnings claim transaction sent",
                player_wallet=player_wallet,
                signature=signature,
                success=success
            )
            
            return TransactionResult(
                signature=signature,
                success=success,
                error=error_msg
            )
            
        except Exception as e:
            self.logger.error(
                "Failed to claim player earnings",
                player_wallet=player_wallet,
                error=str(e)
            )
            return TransactionResult(
                signature="",
                success=False,
                error=str(e)
            )

    async def update_player_earnings_permissionless(self, player_wallet: str) -> TransactionResult:
        """
        Send permissionless update_earnings transaction for a player.
        Anyone can call this - no admin privileges required.
        
        ✨ ENHANCED with PDA validation to prevent transaction failures!
        
        Args:
            player_wallet: Player's wallet address
            
        Returns:
            TransactionResult with signature and status
        """
        try:
            if not self.admin_keypair or not self.client:
                await self.initialize()
            
            # 🔍 ENHANCED: Pre-validate Player PDA to prevent transaction failures
            valid_wallets = await validate_players_before_earnings([player_wallet])
            
            if not valid_wallets:
                self.logger.warning(
                    "🚫 Player PDA validation failed - skipping transaction",
                    wallet=player_wallet
                )
                return TransactionResult(
                    signature="",
                    success=False,
                    error="Player PDA does not exist in blockchain - transaction would fail"
                )
                
            player_pubkey = Pubkey.from_string(player_wallet)
            
            # Derive player PDA
            player_pda, _ = Pubkey.find_program_address(
                [b"player", player_pubkey.__bytes__()], 
                self.program_id
            )
            
            # Create instruction data (empty for permissionless update)
            instruction_data = b""
            
            # Build instruction for permissionless UpdateEarnings (only needs player account)
            accounts = [
                AccountMeta(pubkey=player_pda, is_signer=False, is_writable=True),  # player
            ]
            
            # Get instruction discriminator for update_earnings
            instruction_discriminator = self._get_instruction_discriminator("update_earnings")
            full_instruction_data = instruction_discriminator + instruction_data
            
            instruction = Instruction(
                program_id=self.program_id,
                accounts=accounts,
                data=full_instruction_data
            )
            
            # Get recent blockhash
            recent_blockhash_resp = await self.client.get_latest_blockhash()
            recent_blockhash = recent_blockhash_resp.value.blockhash
            
            # Create versioned transaction using admin as payer (admin pays fees but no authority check)
            message = MessageV0.try_compile(
                payer=self.admin_keypair.pubkey(),
                instructions=[instruction],
                address_lookup_table_accounts=[],
                recent_blockhash=recent_blockhash,
            )
            
            # Create and sign transaction with admin keypair (only for paying fees)
            transaction = VersionedTransaction(message, [self.admin_keypair])
            
            # Send transaction
            opts = TxOpts(skip_preflight=False, preflight_commitment="confirmed")
            response = await self.client.send_transaction(transaction, opts=opts)
            
            signature = str(response.value)
            
            # Wait for confirmation
            sig_obj = Signature.from_string(signature)
            confirmation = await self.client.confirm_transaction(
                sig_obj,
                commitment="confirmed"
            )
            
            success = confirmation.value[0].err is None
            error_msg = str(confirmation.value[0].err) if not success else None
            
            self.logger.info(
                "Permissionless earnings update transaction sent",
                player_wallet=player_wallet,
                signature=signature,
                success=success
            )
            
            return TransactionResult(
                signature=signature,
                success=success,
                error=error_msg
            )
            
        except Exception as e:
            self.logger.error(
                "Failed to send permissionless earnings update",
                player_wallet=player_wallet,
                error=str(e)
            )
            return TransactionResult(
                signature="",
                success=False,
                error=str(e)
            )
            
    def _get_instruction_discriminator(self, instruction_name: str) -> bytes:
        """
        Get instruction discriminator for Anchor instructions.
        This should match the Anchor framework's instruction hash.
        """
        # Anchor uses the first 8 bytes of SHA256 hash of "global:{instruction_name}"
        import hashlib
        namespace = f"global:{instruction_name}"
        hash_result = hashlib.sha256(namespace.encode()).digest()
        return hash_result[:8]
        
    async def batch_update_earnings(self, player_wallets: List[str]) -> List[TransactionResult]:
        """
        Send multiple earnings update transactions.
        
        Args:
            player_wallets: List of player wallet addresses
            
        Returns:
            List of TransactionResult for each player
        """
        try:
            self.logger.info("Starting batch earnings update", players_count=len(player_wallets))
            
            results = []
            
            # Process in batches to avoid overwhelming RPC
            batch_size = 5
            for i in range(0, len(player_wallets), batch_size):
                batch = player_wallets[i:i + batch_size]
                
                # Process batch concurrently
                batch_tasks = [
                    self.update_player_earnings_permissionless(wallet) 
                    for wallet in batch
                ]
                
                batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
                
                for wallet, result in zip(batch, batch_results):
                    if isinstance(result, Exception):
                        results.append(TransactionResult(
                            signature="",
                            success=False,
                            error=str(result)
                        ))
                    else:
                        results.append(result)
                        
                # Brief pause between batches
                if i + batch_size < len(player_wallets):
                    await asyncio.sleep(2)
                    
            successful = sum(1 for r in results if r.success)
            failed = len(results) - successful
            
            self.logger.info(
                "Batch earnings update completed",
                total=len(results),
                successful=successful,
                failed=failed
            )
            
            return results
            
        except Exception as e:
            self.logger.error("Failed batch earnings update", error=str(e))
            raise SolanaRPCError(f"Failed batch earnings update: {e}")
    
    async def update_players_earnings_batch_transaction(
        self, 
        player_wallets: List[str], 
        skip_validation: bool = False
    ) -> TransactionResult:
        """
        🚀 TRUE BATCH: Send ONE transaction with multiple update_earnings instructions.
        
        ✨ ENHANCED with PDA validation to prevent "Blockhash not found" errors!
        
        More efficient than multiple transactions:
        - 1 RPC call instead of N calls
        - Lower network overhead
        - Atomic execution (all succeed or all fail)
        - Pre-validates all Player PDAs exist in blockchain
        
        Args:
            player_wallets: List of player wallet addresses (max 5-10 recommended)
            skip_validation: Skip PDA validation (for testing only)
            
        Returns:
            Single TransactionResult for the batch transaction
        """
        try:
            if not self.admin_keypair or not self.client:
                await self.initialize()
            
            if len(player_wallets) > 10:
                raise ValueError(f"Batch size {len(player_wallets)} too large, max 10 recommended")
            
            # 🔍 ENHANCED: Pre-validate Player PDAs to prevent transaction failures
            original_count = len(player_wallets)
            
            if not skip_validation:
                self.logger.info(
                    "🔍 Validating Player PDAs before batch transaction",
                    players_count=original_count
                )
                
                # Фильтруем только валидные игроков (с существующими PDA)
                valid_player_wallets = await validate_players_before_earnings(player_wallets)
                
                filtered_count = len(valid_player_wallets)
                invalid_count = original_count - filtered_count
                
                if invalid_count > 0:
                    invalid_wallets = [w for w in player_wallets if w not in valid_player_wallets]
                    self.logger.warning(
                        "🚫 Filtered out players with invalid PDAs",
                        original_count=original_count,
                        valid_count=filtered_count,
                        invalid_count=invalid_count,
                        invalid_wallets=invalid_wallets[:3]  # Показываем первые 3
                    )
                
                if not valid_player_wallets:
                    self.logger.error("❌ No valid players found after PDA validation")
                    return TransactionResult(
                        signature="",
                        success=False,
                        error="No valid players found - all Player PDAs are missing in blockchain"
                    )
                
                # Используем только валидные кошельки
                player_wallets = valid_player_wallets
                
                self.logger.info(
                    "✅ PDA validation completed",
                    valid_players=len(player_wallets),
                    filtered_out=invalid_count
                )
            else:
                self.logger.warning("⚠️ Skipping PDA validation (testing mode)")
                
            self.logger.info(
                "Creating batch earnings transaction",
                players_count=len(player_wallets),
                players=player_wallets
            )
            
            instructions = []
            
            # Create update_earnings instruction for each player
            for wallet in player_wallets:
                player_pubkey = Pubkey.from_string(wallet)
                
                # Derive player PDA
                player_pda, _ = Pubkey.find_program_address(
                    [b"player", player_pubkey.__bytes__()], 
                    self.program_id
                )
                
                # Create instruction data (empty for permissionless update)
                instruction_data = b""
                
                # Build instruction for permissionless UpdateEarnings
                accounts = [
                    AccountMeta(pubkey=player_pda, is_signer=False, is_writable=True),  # player
                ]
                
                # Get instruction discriminator for update_earnings
                instruction_discriminator = self._get_instruction_discriminator("update_earnings")
                full_instruction_data = instruction_discriminator + instruction_data
                
                instruction = Instruction(
                    program_id=self.program_id,
                    accounts=accounts,
                    data=full_instruction_data
                )
                
                instructions.append(instruction)
            
            # Get recent blockhash
            recent_blockhash_resp = await self.client.get_latest_blockhash()
            recent_blockhash = recent_blockhash_resp.value.blockhash
            
            # Create versioned transaction with ALL instructions
            message = MessageV0.try_compile(
                payer=self.admin_keypair.pubkey(),
                instructions=instructions,  # Multiple instructions in one transaction
                address_lookup_table_accounts=[],
                recent_blockhash=recent_blockhash,
            )
            
            transaction = VersionedTransaction(message, [self.admin_keypair])
            
            # Send the batch transaction
            self.logger.info(
                "Sending batch earnings transaction",
                instructions_count=len(instructions),
                players=player_wallets
            )
            
            result = await self.client.send_transaction(
                transaction,
                opts=TxOpts(
                    skip_confirmation=True,
                    skip_preflight=False,
                    max_retries=3
                )
            )
            
            signature = str(result.value)
            
            self.logger.info(
                "✅ Batch earnings transaction sent successfully",
                signature=signature[:20] + "...",
                players_count=len(player_wallets)
            )
            
            return TransactionResult(
                signature=signature,
                success=True,
                error=None
            )
            
        except Exception as e:
            error_msg = f"Batch earnings transaction failed: {e}"
            self.logger.error(
                "❌ Batch earnings transaction failed",
                error=str(e),
                players_count=len(player_wallets)
            )
            
            return TransactionResult(
                signature="",
                success=False,
                error=error_msg
            )


# Global service instance
_transaction_service: Optional[TransactionService] = None


async def get_transaction_service() -> TransactionService:
    """Get or create a global transaction service instance."""
    global _transaction_service
    if _transaction_service is None:
        _transaction_service = TransactionService()
        await _transaction_service.initialize()
    return _transaction_service