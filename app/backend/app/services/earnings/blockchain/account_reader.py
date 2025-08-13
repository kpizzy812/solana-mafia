"""
Blockchain account reading with progressive fallback.
"""

import os
from typing import List, Dict
import structlog

from solders.pubkey import Pubkey

from app.services.adaptive_rpc_client import AdaptiveRpcClient
from app.services.earnings.core.types import PlayerAccountData
from .data_parser import DataParser
from .real_data_parser import RealDataParser


logger = structlog.get_logger(__name__)


class AccountReader:
    """
    Reads player account data from blockchain with progressive fallback.
    """
    
    def __init__(self, rpc_client: AdaptiveRpcClient, stats):
        """Initialize the account reader."""
        self.rpc_client = rpc_client
        self.stats = stats
        
        # Переключатель между mock и реальными данными
        use_real_data = os.getenv('USE_REAL_BLOCKCHAIN_DATA', 'true').lower() == 'true'
        
        if use_real_data:
            self.data_parser = RealDataParser()
            self.logger = logger.bind(service="account_reader", data_source="blockchain")
        else:
            self.data_parser = DataParser()
            self.logger = logger.bind(service="account_reader", data_source="mock")
            
        self.batch_size_accounts = int(os.getenv('BATCH_SIZE_ACCOUNTS', '500'))
        
        self.logger.info(
            "AccountReader initialized",
            data_source="blockchain" if use_real_data else "mock",
            batch_size=self.batch_size_accounts
        )
        
    def get_player_pda(self, wallet: str) -> Pubkey:
        """Get player PDA address."""
        wallet_pubkey = Pubkey.from_string(wallet)
        program_id = Pubkey.from_string(os.getenv('SOLANA_PROGRAM_ID'))
        
        pda, _ = Pubkey.find_program_address(
            [b"player", bytes(wallet_pubkey)],
            program_id
        )
        return pda
    
    async def get_all_player_states_batch(self, wallets: List[str]) -> Dict[str, PlayerAccountData]:
        """
        Get all player states using batch operations with progressive fallback.
        
        Fallback strategy:
        1. Try full batch (500 accounts)
        2. Try half batch (250 accounts) 
        3. Try small batch (50 accounts)
        4. Individual account reads
        """
        player_states = {}
        failed_wallets = []
        
        # Convert wallets to PDAs
        wallet_to_pda = {wallet: self.get_player_pda(wallet) for wallet in wallets}
        
        batch_sizes = [self.batch_size_accounts, self.batch_size_accounts // 2, 50, 1]
        
        for batch_size in batch_sizes:
            if not failed_wallets and batch_size != self.batch_size_accounts:
                # Only use smaller batches if previous attempts failed
                continue
                
            wallets_to_process = failed_wallets if failed_wallets else wallets
            failed_wallets = []
            
            self.logger.info(
                f"Attempting batch read with size {batch_size}",
                wallets_count=len(wallets_to_process)
            )
            
            # Process in batches
            for i in range(0, len(wallets_to_process), batch_size):
                batch_wallets = wallets_to_process[i:i + batch_size]
                batch_pdas = [wallet_to_pda[wallet] for wallet in batch_wallets]
                
                try:
                    self.stats.batch_reads_attempted += 1
                    
                    # Get multiple accounts
                    response = await self.rpc_client.get_multiple_accounts(batch_pdas)
                    
                    if response.value and len(response.value) == len(batch_pdas):
                        # Success - parse all accounts
                        for j, account_data in enumerate(response.value):
                            wallet = batch_wallets[j]
                            
                            if account_data:
                                try:
                                    parsed_data = self.data_parser.parse_player_account_data(
                                        wallet, wallet_to_pda[wallet], account_data.data
                                    )
                                    player_states[wallet] = parsed_data
                                except Exception as e:
                                    self.logger.warning(
                                        "Failed to parse player data",
                                        wallet=wallet,
                                        error=str(e)
                                    )
                                    failed_wallets.append(wallet)
                            else:
                                self.logger.warning("Player account not found", wallet=wallet)
                        
                        self.stats.batch_reads_successful += 1
                        
                    else:
                        # Partial response - add to failed
                        self.logger.warning(
                            "Partial batch response",
                            expected=len(batch_pdas),
                            received=len(response.value) if response.value else 0
                        )
                        failed_wallets.extend(batch_wallets)
                        
                except Exception as e:
                    self.logger.warning(
                        f"Batch read failed with size {batch_size}",
                        error=str(e),
                        batch_wallets_count=len(batch_wallets)
                    )
                    failed_wallets.extend(batch_wallets)
            
            # If we successfully processed all wallets, break
            if not failed_wallets:
                break
        
        # Final fallback: individual reads for any remaining failures
        if failed_wallets:
            self.logger.info(
                "Falling back to individual reads",
                failed_count=len(failed_wallets)
            )
            
            for wallet in failed_wallets:
                try:
                    pda = wallet_to_pda[wallet]
                    response = await self.rpc_client.get_account(pda)
                    
                    if response.value:
                        parsed_data = self.data_parser.parse_player_account_data(
                            wallet, pda, response.value.data
                        )
                        player_states[wallet] = parsed_data
                        self.stats.individual_reads_fallback += 1
                    else:
                        self.logger.warning("Player account not found", wallet=wallet)
                        
                except Exception as e:
                    self.logger.error(
                        "Individual read failed",
                        wallet=wallet,
                        error=str(e)
                    )
        
        self.logger.info(
            "Batch reading completed",
            total_requested=len(wallets),
            successful=len(player_states),
            failed=len(wallets) - len(player_states)
        )
        
        return player_states