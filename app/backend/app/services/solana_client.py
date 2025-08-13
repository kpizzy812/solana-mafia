"""
Solana RPC client service for interacting with the Solana blockchain.
Provides methods for fetching transactions, account data, and program logs.
"""

import asyncio
from typing import List, Dict, Any, Optional, Union, Callable
from dataclasses import dataclass
from datetime import datetime
import base64
import json
import websockets
import uuid

from solana.rpc.async_api import AsyncClient
from solana.rpc.commitment import Commitment
from solana.rpc.types import TxOpts
from solders.pubkey import Pubkey
from solders.signature import Signature
from solders.transaction_status import TransactionConfirmationStatus
import structlog

from app.core.config import settings, SolanaConfig
from app.core.exceptions import SolanaRPCError


logger = structlog.get_logger(__name__)


@dataclass
class TransactionInfo:
    """Transaction information from Solana blockchain."""
    signature: str
    slot: int
    block_time: Optional[datetime]
    success: bool
    logs: List[str]
    accounts: List[str]
    instructions: List[Dict[str, Any]]
    events: List[Dict[str, Any]]


@dataclass
class AccountInfo:
    """Account information from Solana blockchain."""
    pubkey: str
    lamports: int
    owner: str
    executable: bool
    rent_epoch: int
    data: bytes


class SolanaClient:
    """
    Async Solana RPC client for blockchain interactions.
    
    Provides high-level methods for:
    - Fetching transaction data and logs
    - Retrieving account information
    - Parsing program events
    - Monitoring blockchain state
    """
    
    def __init__(self):
        """Initialize Solana client with configuration."""
        self.rpc_config = SolanaConfig.get_rpc_config()
        self.client = AsyncClient(
            endpoint=self.rpc_config["endpoint"],
            commitment=Commitment(self.rpc_config["commitment"]),
            timeout=self.rpc_config["timeout"]
        )
        self.program_id = Pubkey.from_string(settings.solana_program_id)
        self.logger = logger.bind(service="solana_client")
        
    async def __aenter__(self):
        """Async context manager entry."""
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
        
    async def close(self):
        """Close the RPC client connection."""
        await self.client.close()
        
    async def get_health(self) -> bool:
        """Check if the RPC endpoint is healthy."""
        try:
            response = await self.client.get_health()
            return response.value == "ok"
        except Exception as e:
            self.logger.error("Health check failed", error=str(e))
            return False
            
    async def get_slot(self) -> int:
        """Get the current slot number."""
        try:
            response = await self.client.get_slot()
            return response.value
        except Exception as e:
            self.logger.error("Failed to get slot", error=str(e))
            raise SolanaRPCError(f"Failed to get slot: {e}")
            
    async def get_block_time(self, slot: int) -> Optional[datetime]:
        """Get block time for a given slot."""
        try:
            response = await self.client.get_block_time(slot)
            if response.value:
                return datetime.fromtimestamp(response.value)
            return None
        except Exception as e:
            self.logger.warning("Failed to get block time", slot=slot, error=str(e))
            return None
            
    async def get_signatures_for_address(
        self,
        address: Union[str, Pubkey],
        limit: int = 1000,
        before: Optional[str] = None,
        until: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get transaction signatures for an address."""
        try:
            if isinstance(address, str):
                address = Pubkey.from_string(address)
                
            response = await self.client.get_signatures_for_address(
                address,
                limit=limit,
                before=Signature.from_string(before) if before else None,
                until=Signature.from_string(until) if until else None
            )
            
            signatures = []
            for sig_info in response.value:
                signatures.append({
                    "signature": str(sig_info.signature),
                    "slot": sig_info.slot,
                    "err": sig_info.err,
                    "memo": sig_info.memo,
                    "block_time": datetime.fromtimestamp(sig_info.block_time) if sig_info.block_time else None
                })
                
            return signatures
            
        except Exception as e:
            self.logger.error("Failed to get signatures", address=str(address), error=str(e))
            raise SolanaRPCError(f"Failed to get signatures for address: {e}")
            
    async def get_transaction(self, signature: str) -> Optional[TransactionInfo]:
        """Get detailed transaction information."""
        try:
            self.logger.info(f"🔍 SolanaClient: Requesting transaction {signature[:20]}...")
            sig = Signature.from_string(signature)
            response = await self.client.get_transaction(
                sig,
                encoding="json",
                max_supported_transaction_version=0
            )
            
            self.logger.info(f"📡 SolanaClient: Got response for {signature[:20]}... - response.value: {response.value is not None}")
            
            if not response.value:
                self.logger.warning(f"❌ SolanaClient: No transaction data returned for {signature[:20]}...")
                return None
                
            tx = response.value
            meta = tx.transaction.meta
            
            if not meta:
                self.logger.warning(f"❌ SolanaClient: No meta data for {signature[:20]}...")
                return None
                
            self.logger.info(f"✅ SolanaClient: Successfully parsed transaction {signature[:20]}... slot: {tx.slot}")
            # Parse transaction data
            transaction_info = TransactionInfo(
                signature=signature,
                slot=tx.slot,
                block_time=datetime.fromtimestamp(tx.block_time) if tx.block_time else None,
                success=meta.err is None,
                logs=meta.log_messages or [],
                accounts=[str(acc) for acc in tx.transaction.transaction.message.account_keys],
                instructions=[],
                events=[]
            )
            
            # Parse instructions
            if hasattr(tx.transaction.transaction.message, 'instructions'):
                for idx, instr in enumerate(tx.transaction.transaction.message.instructions):
                    instruction_data = {
                        "program_id_index": instr.program_id_index,
                        "accounts": list(instr.accounts),
                        "data": str(instr.data) if instr.data else "",
                        "index": idx
                    }
                    transaction_info.instructions.append(instruction_data)
            
            # Parse events from logs
            transaction_info.events = self._parse_events_from_logs(transaction_info.logs)
            
            return transaction_info
            
        except Exception as e:
            self.logger.error("Failed to get transaction", signature=signature, error=str(e))
            raise SolanaRPCError(f"Failed to get transaction: {e}")
            
    async def get_account_info(self, address: Union[str, Pubkey]) -> Optional[AccountInfo]:
        """Get account information."""
        try:
            if isinstance(address, str):
                address = Pubkey.from_string(address)
                
            response = await self.client.get_account_info(address)
            
            if not response.value:
                return None
                
            account = response.value
            
            return AccountInfo(
                pubkey=str(address),
                lamports=account.lamports,
                owner=str(account.owner),
                executable=account.executable,
                rent_epoch=account.rent_epoch,
                data=account.data
            )
            
        except Exception as e:
            self.logger.error("Failed to get account info", address=str(address), error=str(e))
            raise SolanaRPCError(f"Failed to get account info: {e}")
            
    async def get_program_accounts(
        self,
        program_id: Optional[Union[str, Pubkey]] = None,
        filters: Optional[List[Dict[str, Any]]] = None
    ) -> List[AccountInfo]:
        """Get all accounts owned by a program."""
        try:
            if program_id is None:
                program_id = self.program_id
            elif isinstance(program_id, str):
                program_id = Pubkey.from_string(program_id)
                
            response = await self.client.get_program_accounts(
                program_id,
                filters=filters or []
            )
            
            accounts = []
            for account_data in response.value:
                account_info = AccountInfo(
                    pubkey=str(account_data.pubkey),
                    lamports=account_data.account.lamports,
                    owner=str(account_data.account.owner),
                    executable=account_data.account.executable,
                    rent_epoch=account_data.account.rent_epoch,
                    data=account_data.account.data
                )
                accounts.append(account_info)
                
            return accounts
            
        except Exception as e:
            self.logger.error("Failed to get program accounts", program_id=str(program_id), error=str(e))
            raise SolanaRPCError(f"Failed to get program accounts: {e}")
            
    def _parse_events_from_logs(self, logs: List[str]) -> List[Dict[str, Any]]:
        """Parse events from transaction logs."""
        events = []
        
        for log in logs:
            # Look for program log messages that contain event data
            if f"Program {self.program_id} invoke" in log:
                continue
                
            # Parse custom event logs (format: "Program log: EVENT_NAME: {data}")
            if "Program log:" in log:
                try:
                    log_content = log.split("Program log:", 1)[1].strip()
                    
                    # Check if this is an event log
                    for event_name, event_signature in SolanaConfig.EVENT_SIGNATURES.items():
                        if log_content.startswith(f"{event_signature}:"):
                            event_data_str = log_content.split(":", 1)[1].strip()
                            try:
                                event_data = json.loads(event_data_str)
                                events.append({
                                    "event_type": event_name,
                                    "data": event_data
                                })
                            except json.JSONDecodeError:
                                # If not JSON, store as raw string
                                events.append({
                                    "event_type": event_name,
                                    "data": {"raw": event_data_str}
                                })
                            break
                            
                except Exception as e:
                    self.logger.warning("Failed to parse event from log", log=log, error=str(e))
                    
        return events
        
    async def monitor_program_logs(
        self,
        callback,
        since_slot: Optional[int] = None
    ):
        """Monitor program logs for new transactions (websocket-like functionality)."""
        try:
            current_slot = await self.get_slot()
            start_slot = since_slot or current_slot
            
            self.logger.info("Starting program log monitoring", start_slot=start_slot)
            
            while True:
                try:
                    # Get signatures for our program
                    signatures = await self.get_signatures_for_address(
                        self.program_id,
                        limit=100
                    )
                    
                    # Filter for new transactions
                    new_signatures = [
                        sig for sig in signatures 
                        if sig["slot"] > start_slot and not sig["err"]
                    ]
                    
                    # Process new transactions
                    for sig_info in new_signatures:
                        try:
                            tx_info = await self.get_transaction(sig_info["signature"])
                            if tx_info and tx_info.events:
                                await callback(tx_info)
                                start_slot = max(start_slot, tx_info.slot)
                        except Exception as e:
                            self.logger.error(
                                "Failed to process transaction",
                                signature=sig_info["signature"],
                                error=str(e)
                            )
                    
                    # Wait before next poll
                    await asyncio.sleep(settings.indexer_poll_interval)
                    
                except Exception as e:
                    self.logger.error("Error in monitoring loop", error=str(e))
                    await asyncio.sleep(settings.indexer_retry_delay)
                    
        except Exception as e:
            self.logger.error("Failed to start monitoring", error=str(e))
            raise SolanaRPCError(f"Failed to monitor program logs: {e}")
    
    async def monitor_program_logs_realtime(
        self,
        callback: Callable[[TransactionInfo], Any],
        auto_reconnect: bool = True
    ):
        """
        🚀 ENHANCED Real-time WebSocket monitoring with Helius support.
        Provides instant notifications with robust error handling and reconnection.
        """
        # Use configured WebSocket URL from settings (Helius support)
        ws_config = SolanaConfig.get_websocket_config()
        ws_url = ws_config["endpoint"]
        
        reconnect_attempts = 0
        max_reconnect_attempts = 10
        base_retry_delay = 2
        
        while reconnect_attempts < max_reconnect_attempts:
            try:
                self.logger.info("🔌 Connecting to Helius WebSocket", url=ws_url, attempt=reconnect_attempts + 1)
                
                # Enhanced connection with custom headers and timeout
                headers = {
                    "User-Agent": "SolanaMafia-Backend/1.0",
                    "Origin": "https://localhost:8000"
                }
                
                async with websockets.connect(
                    ws_url, 
                    ping_interval=30, 
                    ping_timeout=10,
                    close_timeout=5,
                    extra_headers=headers,
                    max_size=None  # Remove message size limit
                ) as websocket:
                    # Subscribe to program logs with enhanced parameters
                    subscription_id = str(uuid.uuid4())
                    subscribe_msg = {
                        "jsonrpc": "2.0",
                        "id": subscription_id,
                        "method": "logsSubscribe",
                        "params": [
                            {
                                "mentions": [str(self.program_id)]
                            },
                            {
                                "commitment": "confirmed"
                            }
                        ]
                    }
                    
                    await websocket.send(json.dumps(subscribe_msg))
                    self.logger.info("✅ Subscribed to program logs", program_id=str(self.program_id))
                    
                    # Reset reconnect counter on successful connection
                    reconnect_attempts = 0
                    
                    # Process incoming messages with enhanced error handling
                    async for raw_message in websocket:
                        try:
                            message = json.loads(raw_message)
                            
                            # Skip subscription confirmation
                            if "id" in message and message.get("id") == subscription_id:
                                sub_id = message.get("result")
                                self.logger.info("🎯 WebSocket subscription confirmed", subscription_id=sub_id)
                                continue
                            
                            # Process log notification
                            if "method" in message and message["method"] == "logsNotification":
                                await self._process_log_notification_enhanced(message, callback)
                            
                            # Handle errors in subscription
                            elif "error" in message:
                                self.logger.error("❌ WebSocket subscription error", error=message["error"])
                                raise SolanaRPCError(f"Subscription error: {message['error']}")
                                
                        except json.JSONDecodeError as e:
                            self.logger.error("🚨 Failed to parse WebSocket message", error=str(e), raw_message=raw_message[:200])
                        except Exception as e:
                            self.logger.error("⚠️ Error processing WebSocket message", error=str(e), error_type=type(e).__name__)
                            continue
                            
            except websockets.exceptions.ConnectionClosed as e:
                reconnect_attempts += 1
                if auto_reconnect and reconnect_attempts < max_reconnect_attempts:
                    retry_delay = min(base_retry_delay * (2 ** reconnect_attempts), 60)
                    self.logger.warning(
                        "🔄 WebSocket connection closed, reconnecting", 
                        error=str(e), 
                        attempt=reconnect_attempts,
                        retry_delay=retry_delay
                    )
                    await asyncio.sleep(retry_delay)
                    continue
                else:
                    self.logger.error("❌ Max reconnection attempts reached", attempts=reconnect_attempts)
                    break
                    
            except websockets.exceptions.InvalidURI as e:
                self.logger.error("❌ Invalid WebSocket URI", url=ws_url, error=str(e))
                raise SolanaRPCError(f"Invalid WebSocket URI: {ws_url} - {e}")
                
            except OSError as e:
                reconnect_attempts += 1
                if "Connection refused" in str(e) or "Name or service not known" in str(e):
                    self.logger.error("❌ WebSocket endpoint not available", url=ws_url, error=str(e))
                    if auto_reconnect and reconnect_attempts < max_reconnect_attempts:
                        retry_delay = min(base_retry_delay * reconnect_attempts, 30)
                        self.logger.info(f"🔄 Retrying connection in {retry_delay} seconds...")
                        await asyncio.sleep(retry_delay)
                        continue
                    else:
                        raise SolanaRPCError(f"WebSocket endpoint not available: {e}")
                else:
                    self.logger.error("🚨 WebSocket network error", error=str(e))
                    if auto_reconnect and reconnect_attempts < max_reconnect_attempts:
                        await asyncio.sleep(base_retry_delay * reconnect_attempts)
                        continue
                    else:
                        raise SolanaRPCError(f"WebSocket network error: {e}")
                        
            except Exception as e:
                reconnect_attempts += 1
                self.logger.error(
                    "⚠️ Unexpected WebSocket error", 
                    error=str(e), 
                    error_type=type(e).__name__,
                    attempt=reconnect_attempts
                )
                if auto_reconnect and reconnect_attempts < max_reconnect_attempts:
                    retry_delay = min(base_retry_delay * reconnect_attempts, 60)
                    await asyncio.sleep(retry_delay)
                    continue
                else:
                    raise SolanaRPCError(f"Failed to monitor program logs via WebSocket: {e}")
        
        self.logger.error("❌ WebSocket monitoring stopped after max retry attempts")
    
    async def _process_log_notification_enhanced(self, message: Dict[str, Any], callback: Callable[[TransactionInfo], Any]):
        """
        🚀 ENHANCED log notification processing with EventParser integration.
        Provides immediate event parsing and robust error handling.
        """
        try:
            params = message.get("params", {})
            result = params.get("result", {})
            context = result.get("context", {})
            value = result.get("value", {})
            
            signature = value.get("signature")
            logs = value.get("logs", [])
            slot = context.get("slot", 0)
            
            if not signature:
                self.logger.debug("❌ No signature in log notification", result=result)
                return
            
            self.logger.info("🔥 Received real-time log notification", signature=signature[:20], slot=slot, logs_count=len(logs))
            
            # 🚀 FAST TRACK: Parse events directly from logs without fetching full transaction
            if logs:
                try:
                    from app.services.event_parser import get_event_parser
                    parser = get_event_parser()
                    
                    # Parse events directly from WebSocket logs (MUCH FASTER!)
                    parsed_events = parser.parse_logs_for_events(
                        logs=logs,
                        signature=signature,
                        slot=slot,
                        block_time=None  # Will be estimated
                    )
                    
                    if parsed_events:
                        self.logger.info(
                            "✅ Fast-track parsed events from logs", 
                            signature=signature[:20],
                            event_count=len(parsed_events),
                            event_types=[e.event_type.value for e in parsed_events]
                        )
                        
                        # Create minimal TransactionInfo for fast processing
                        fast_tx_info = TransactionInfo(
                            signature=signature,
                            slot=slot,
                            block_time=None,  # Will be fetched later if needed
                            success=True,
                            logs=logs,
                            accounts=[],
                            instructions=[],
                            events=[{"event_type": e.event_type.value, "data": e.data} for e in parsed_events]
                        )
                        
                        # Trigger callback immediately with parsed events
                        await callback(fast_tx_info)
                        return
                        
                except Exception as e:
                    self.logger.warning("⚠️ Fast-track parsing failed, falling back to full transaction fetch", error=str(e))
            
            # FALLBACK: Fetch full transaction details (slower but comprehensive)
            try:
                self.logger.debug("🐌 Falling back to full transaction fetch", signature=signature[:20])
                tx_info = await self.get_transaction(signature)
                if tx_info:
                    if tx_info.events:
                        self.logger.info(
                            "✅ Full transaction processed", 
                            signature=signature[:20], 
                            events_count=len(tx_info.events)
                        )
                        await callback(tx_info)
                    else:
                        self.logger.debug("ℹ️ Transaction has no events", signature=signature[:20])
                else:
                    self.logger.warning("❌ Failed to fetch transaction details", signature=signature[:20])
                    
            except Exception as e:
                self.logger.error("❌ Failed to fetch full transaction", signature=signature[:20], error=str(e))
            
        except Exception as e:
            self.logger.error("❌ Failed to process log notification", error=str(e), message_keys=list(message.keys()) if message else [])

    async def _process_log_notification(self, message: Dict[str, Any], callback: Callable[[TransactionInfo], Any]):
        """Legacy log notification processing - redirects to enhanced version."""
        await self._process_log_notification_enhanced(message, callback)


# Global client instance
_client: Optional[SolanaClient] = None


async def get_solana_client() -> SolanaClient:
    """Get or create a global Solana client instance."""
    global _client
    if _client is None:
        _client = SolanaClient()
    return _client


async def close_solana_client():
    """Close the global Solana client instance."""
    global _client
    if _client:
        await _client.close()
        _client = None