"""
Dynamic pricing service for entry fee management.
Controls entry fee based on player count and SOL price.
"""

import asyncio
import logging
import json
from pathlib import Path
from typing import Optional
import base58
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from solana.rpc.async_api import AsyncClient
from anchorpy import Program, Provider, Wallet

from app.core.config import settings
from app.services.coingecko_service import coingecko_service
from app.models.player import Player
from app.core.database import get_async_session
from sqlalchemy import text

logger = logging.getLogger(__name__)

class DynamicPricingService:
    """Service for managing dynamic entry fee pricing"""
    
    def __init__(self):
        self.sol_price_cache = None
        self.last_entry_fee = None
        self.admin_keypair = None
        self._setup_admin_keypair()
        
    def _setup_admin_keypair(self):
        """Setup admin keypair from private key"""
        if not settings.admin_private_key:
            logger.warning("ADMIN_PRIVATE_KEY not set - dynamic pricing disabled")
            return
            
        try:
            # Decode base58 private key
            private_key_bytes = base58.b58decode(settings.admin_private_key)
            self.admin_keypair = Keypair.from_bytes(private_key_bytes)
            logger.info(f"Admin keypair loaded: {self.admin_keypair.pubkey()}")
        except Exception as e:
            logger.error(f"Failed to load admin keypair: {e}")
            self.admin_keypair = None
    
    def calculate_entry_fee_usd(self, total_players: int) -> float:
        """Calculate entry fee in USD based on player count"""
        if total_players <= 100:
            # Phase 1: $2 to $10 over first 100 players (linear)
            return 2.0 + (8.0 * total_players / 100)
        elif total_players <= 500:
            # Phase 2: $10 to $20 over players 100-500 (slower growth)
            return 10.0 + (10.0 * (total_players - 100) / 400)
        else:
            # Phase 3: Cap at $20
            return 20.0
    
    def calculate_entry_fee_lamports(self, total_players: int, sol_price_usd: float) -> int:
        """Calculate entry fee in lamports"""
        fee_usd = self.calculate_entry_fee_usd(total_players)
        fee_sol = fee_usd / sol_price_usd
        return int(fee_sol * 1_000_000_000)  # Convert to lamports
    
    async def get_total_players(self) -> int:
        """Get total player count from database"""
        try:
            async with get_async_session() as session:
                result = await session.execute(text("SELECT COUNT(*) FROM players WHERE has_paid_entry = true"))
                count = result.scalar()
                return count or 0
        except Exception as e:
            logger.error(f"Failed to get player count: {e}")
            return 0
    
    async def update_entry_fee_if_needed(self) -> bool:
        """Update entry fee if SOL price or player count changed significantly"""
        try:
            if not self.admin_keypair:
                logger.warning("Admin keypair not available - skipping update")
                return False
                
            # Get current SOL price
            sol_price = await coingecko_service.get_sol_price_usd()
            if not sol_price:
                logger.warning("Could not fetch SOL price")
                return False
                
            # Get total players
            total_players = await self.get_total_players()
            
            # Calculate new entry fee
            new_fee_lamports = self.calculate_entry_fee_lamports(total_players, sol_price)
            
            # Check if significant change (>5% or different by >0.001 SOL)
            if self.last_entry_fee is not None:
                change_percent = abs(new_fee_lamports - self.last_entry_fee) / self.last_entry_fee
                change_sol = abs(new_fee_lamports - self.last_entry_fee) / 1_000_000_000
                
                if change_percent < 0.05 and change_sol < 0.001:
                    logger.debug(f"Entry fee unchanged: {new_fee_lamports} lamports")
                    return False
            
            # Send update transaction
            success = await self._send_update_transaction(new_fee_lamports)
            
            if success:
                self.last_entry_fee = new_fee_lamports
                fee_usd = self.calculate_entry_fee_usd(total_players)
                logger.info(
                    f"Entry fee updated: {new_fee_lamports} lamports "
                    f"(${fee_usd:.2f} at ${sol_price:.2f}/SOL, {total_players} players)"
                )
                return True
                
            return False
            
        except Exception as e:
            logger.error(f"Failed to update entry fee: {e}")
            return False
    
    async def _send_update_transaction(self, new_fee_lamports: int) -> bool:
        """Send update_entry_fee transaction to smart contract"""
        try:
            if not self.admin_keypair:
                return False
                
            # Load program IDL
            idl_path = Path(__file__).parent.parent.parent / "idl" / "solana_mafia.json"
            if not idl_path.exists():
                logger.error(f"IDL file not found: {idl_path}")
                return False
                
            with open(idl_path, 'r') as f:
                idl = json.load(f)
            
            # Setup provider and program
            client = AsyncClient(settings.solana_rpc_url)
            wallet = Wallet(self.admin_keypair)
            provider = Provider(client, wallet)
            
            # Build raw instruction manually since anchorpy has issues with our IDL
            try:
                from solana.transaction import Transaction
                from solders.instruction import Instruction, AccountMeta
                import struct
                
                # Find the update_entry_fee instruction discriminator from IDL
                update_entry_fee_discriminator = None
                for instruction in idl.get('instructions', []):
                    if instruction.get('name') == 'update_entry_fee':
                        update_entry_fee_discriminator = bytes(instruction.get('discriminator', []))
                        break
                
                if not update_entry_fee_discriminator:
                    logger.error("update_entry_fee instruction not found in IDL")
                    return False
                
                # Serialize the new_fee_lamports as u64 (8 bytes, little endian)
                fee_bytes = struct.pack('<Q', new_fee_lamports)
                
                # Build instruction data: discriminator + serialized args
                instruction_data = update_entry_fee_discriminator + fee_bytes
                
                program_id = Pubkey.from_string(settings.solana_program_id)
                
                # Find GameConfig PDA
                game_config_pda = Pubkey.find_program_address(
                    seeds=[b"game_config"],
                    program_id=program_id
                )[0]
                
                # Build accounts for the instruction
                accounts = [
                    AccountMeta(pubkey=self.admin_keypair.pubkey(), is_signer=True, is_writable=False),  # authority
                    AccountMeta(pubkey=game_config_pda, is_signer=False, is_writable=True),  # game_config
                ]
                
                # Create the instruction
                ix = Instruction(
                    program_id=program_id,
                    accounts=accounts,
                    data=instruction_data
                )
                
                # Create and send transaction
                tx = Transaction()
                tx.add(ix)
                
                # Send transaction
                from solana.rpc.types import TxOpts
                from solana.rpc.commitment import Confirmed
                signature = await client.send_transaction(
                    tx,
                    self.admin_keypair,
                    opts=TxOpts(preflight_commitment=Confirmed)
                )
                
                logger.info(f"Entry fee update transaction sent (raw): {signature.value}")
                await client.close()
                return True
                
            except Exception as raw_error:
                logger.error(f"Failed to send raw transaction: {raw_error}")
                import traceback
                logger.error(f"Raw transaction traceback: {traceback.format_exc()}")
                return False
            
        except Exception as e:
            import traceback
            logger.error(f"Failed to send update transaction: {e}")
            logger.error(f"Full traceback: {traceback.format_exc()}")
            return False
    
    async def start_price_monitoring(self):
        """Start continuous price monitoring and updates"""
        if not settings.dynamic_pricing_enabled:
            logger.info("Dynamic pricing disabled")
            return
            
        if not self.admin_keypair:
            logger.error("Admin keypair not available - dynamic pricing disabled")
            return
            
        logger.info(f"Starting dynamic pricing service (interval: {settings.price_update_interval}s)")
        
        while True:
            try:
                await self.update_entry_fee_if_needed()
                await asyncio.sleep(settings.price_update_interval)
            except Exception as e:
                logger.error(f"Error in pricing loop: {e}")
                await asyncio.sleep(60)  # Wait 1 minute on error

# Global instance
dynamic_pricing_service = DynamicPricingService()