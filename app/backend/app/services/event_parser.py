"""
Event parser service for Solana Mafia program events.
Handles parsing, validation, and transformation of blockchain events into database models.
"""

import json
import base64
from typing import Dict, Any, Optional, List, Union
from datetime import datetime
from dataclasses import dataclass
from enum import Enum
import struct
import base58

import structlog
from solders.pubkey import Pubkey

from app.core.config import SolanaConfig
from app.core.exceptions import ValidationError, SolanaError
from app.services.solana_client import TransactionInfo


logger = structlog.get_logger(__name__)


class EventType(Enum):
    """Enumeration of all supported event types from the Solana program."""
    PLAYER_CREATED = "PlayerCreated"
    BUSINESS_CREATED = "BusinessCreated"
    BUSINESS_CREATED_IN_SLOT = "BusinessCreatedInSlot"  # 🆕 Новое событие из контракта
    BUSINESS_UPGRADED = "BusinessUpgraded" 
    BUSINESS_UPGRADED_IN_SLOT = "BusinessUpgradedInSlot"  # 🆕 Новое событие из контракта
    BUSINESS_SOLD = "BusinessSold"
    BUSINESS_SOLD_FROM_SLOT = "BusinessSoldFromSlot"  # 🆕 Новое событие из контракта
    EARNINGS_UPDATED = "EarningsUpdated"
    EARNINGS_CLAIMED = "EarningsClaimed"
    BUSINESS_TRANSFERRED = "BusinessTransferred"
    BUSINESS_DEACTIVATED = "BusinessDeactivated"
    SLOT_UNLOCKED = "SlotUnlocked"
    PREMIUM_SLOT_PURCHASED = "PremiumSlotPurchased"
    REFERRAL_BONUS_ADDED = "ReferralBonusAdded"


@dataclass
class ParsedEvent:
    """Parsed event data from a Solana transaction."""
    event_type: EventType
    signature: str
    slot: int
    block_time: Optional[datetime]
    data: Dict[str, Any]
    raw_data: Dict[str, Any]
    instruction_index: Optional[int] = None


@dataclass
class PlayerCreatedEvent:
    """Player created event data."""
    wallet: str
    referrer: Optional[str]
    slot_unlocked: int
    block_time: datetime
    signature: str


@dataclass  
class BusinessCreatedEvent:
    """Business created event data."""
    business_id: str
    owner: str
    business_type: int
    name: str
    slot_index: int
    cost: int
    earnings_per_hour: int
    block_time: datetime
    signature: str


@dataclass
class BusinessUpgradedEvent:
    """Business upgraded event data."""
    business_id: str
    owner: str
    old_level: int
    new_level: int
    upgrade_cost: int
    new_earnings_per_hour: int
    block_time: datetime
    signature: str


@dataclass
class BusinessSoldEvent:
    """Business sold event data."""
    business_id: str
    seller: str
    buyer: Optional[str]
    business_type: int
    sale_price: int
    penalty_amount: int
    days_held: int
    block_time: datetime
    signature: str


@dataclass
class EarningsUpdatedEvent:
    """Earnings updated event data."""
    wallet: str
    earnings_added: int           # 🔧 FIXED: earnings_added (не earnings_amount)
    total_pending: int           # 🔧 FIXED: total_pending (не total_earnings)
    next_earnings_time: datetime # 🔧 FIXED: next_earnings_time (не last_update)
    businesses_count: int        # 🆕 NEW: количество бизнесов
    block_time: datetime
    signature: str


@dataclass
class EarningsClaimedEvent:
    """Earnings claimed event data."""
    wallet: str
    amount_claimed: int
    treasury_fee: int
    net_amount: int
    block_time: datetime
    signature: str




@dataclass
class SlotEvent:
    """Slot unlocked/purchased event data."""
    wallet: str
    slot_index: int
    cost: int
    is_premium: bool
    block_time: datetime
    signature: str


class EventParser:
    """
    Parser for Solana Mafia program events.
    
    Converts raw transaction logs and instruction data into structured events
    that can be stored in the database and processed by the indexer.
    """
    
    def __init__(self):
        """Initialize the event parser."""
        self.logger = logger.bind(service="event_parser")
        self.event_signatures = SolanaConfig.EVENT_SIGNATURES
        
    def parse_transaction_events(self, tx_info: TransactionInfo) -> List[ParsedEvent]:
        """
        Parse all events from a transaction.
        
        Args:
            tx_info: Transaction information from Solana
            
        Returns:
            List of parsed events
            
        Raises:
            ValidationError: If event parsing fails
        """
        try:
            parsed_events = []
            
            # Parse events from logs
            log_events = self._parse_events_from_logs(tx_info)
            parsed_events.extend(log_events)
            
            # Parse events from instruction data (if needed)
            instruction_events = self._parse_events_from_instructions(tx_info)
            parsed_events.extend(instruction_events)
            
            self.logger.info(
                "Parsed transaction events",
                signature=tx_info.signature,
                event_count=len(parsed_events)
            )
            
            return parsed_events
            
        except Exception as e:
            self.logger.error(
                "Failed to parse transaction events",
                signature=tx_info.signature,
                error=str(e)
            )
            raise ValidationError(f"Failed to parse events: {e}")
    
    def _parse_anchor_events(self, log_line: str, tx_info: TransactionInfo) -> List[ParsedEvent]:
        """Parse Anchor events from Program data logs."""
        events = []
        
        try:
            # Extract base64 data from "Program data: <base64_data>"
            if "Program data:" not in log_line:
                return events
                
            data_part = log_line.split("Program data:", 1)[1].strip()
            
            # Decode base64 data
            try:
                decoded_data = base64.b64decode(data_part)
            except Exception as e:
                self.logger.debug("Failed to decode base64 event data", error=str(e))
                return events
                
            # Anchor events typically start with an 8-byte discriminator
            if len(decoded_data) < 8:
                return events
                
            # Extract discriminator (first 8 bytes)
            discriminator = decoded_data[:8]
            event_data = decoded_data[8:]
            
            # Try to identify event type by discriminator or data pattern
            # For now, we'll try to parse based on the transaction context
            parsed_event = self._decode_anchor_event_data(discriminator, event_data, tx_info)
            if parsed_event:
                events.append(parsed_event)
                
        except Exception as e:
            self.logger.debug(
                "Failed to parse anchor event",
                log_line=log_line,
                error=str(e)
            )
            
        return events
    
    def _decode_anchor_event_data(self, discriminator: bytes, data: bytes, tx_info: TransactionInfo) -> Optional[ParsedEvent]:
        """
        Decode Anchor event data based on discriminator.
        
        This is a simplified version that tries to identify events based on the transaction context
        and data patterns. In a production system, you'd have proper IDL-based parsing.
        """
        try:
            # Known discriminators for our events (calculated from event names)
            # BusinessCreatedInSlot discriminator is calculated from hash("event:BusinessCreatedInSlot")
            # The discriminator we see is: 4a191ae88d56371c
            
            discriminator_hex = discriminator.hex()
            
            # 🔧 FIXED: Правильные discriminator'ы из реальных транзакций
            if discriminator_hex == "4a191ae88d56371c" and len(data) >= 69:  # Real structure is 69 bytes
                # Parse BusinessCreatedInSlot event with level field
                return self._parse_business_created_in_slot_event(discriminator, data, tx_info)
            elif discriminator_hex == "f8e9e74d11085e42" and len(data) >= 57:
                # Parse EarningsUpdated event (57 bytes)
                return self._parse_earnings_updated_event(discriminator, data, tx_info)
            elif discriminator_hex == "0aea7413441595f4" and len(data) >= 40:
                # Parse BusinessSoldFromSlot event
                return self._parse_business_sold_from_slot_event(discriminator, data, tx_info)
            elif discriminator_hex == "fe094a515c05bddc" and len(data) >= 56:
                # Parse PlayerCreated event (56 bytes)
                return self._parse_player_created_event(discriminator, data, tx_info)
            elif discriminator_hex == "3fe9746a44105602" and len(data) >= 59:
                # Parse BusinessCreated event (59+ bytes)
                return self._parse_business_created_event(discriminator, data, tx_info)
            elif discriminator_hex == "6aaa9a69152bbd61" and len(data) >= 48:
                # Parse EarningsClaimed event (48 bytes)
                return self._parse_earnings_claimed_event(discriminator, data, tx_info)
            elif discriminator_hex == "a0a9e0fdbe38a29d":
                # Parse BusinessUpgraded event
                return self._parse_business_upgraded_event(discriminator, data, tx_info)
            elif discriminator_hex == "667539291574c92d":
                # Parse BusinessUpgradedInSlot event  
                return self._parse_business_upgraded_in_slot_event(discriminator, data, tx_info)
            elif discriminator_hex == "2ff123a4b9c3e2c3":
                # Parse BusinessSold event
                return self._parse_business_sold_event_legacy(discriminator, data, tx_info)
            
            # Fallback to old method for other events
            business_creation_logs = [log for log in tx_info.logs if "Business created" in log]
            
            if business_creation_logs and len(data) >= 40:  # Minimum size for business event data
                # Try to parse as BusinessCreated event
                # This is a simplified parsing - in reality you'd use the IDL
                return self._parse_business_created_event(discriminator, data, tx_info)
                
                
        except Exception as e:
            self.logger.debug("Failed to decode anchor event data", error=str(e))
            
        return None
    
    def _parse_business_created_in_slot_event(self, discriminator: bytes, data: bytes, tx_info: TransactionInfo) -> Optional[ParsedEvent]:
        """Parse BusinessCreatedInSlot event from anchor data."""
        try:
            # BusinessCreatedInSlot REAL event structure (69 bytes without discriminator):
            # player: Pubkey (32 bytes, offset 0-31)
            # slot_index: u8 (1 byte, offset 32) 
            # business_type: u8 (1 byte, offset 33)
            # level: u8 (1 byte, offset 34) # 🆕 NEW: Added level field!
            # padding: 5 bytes (offset 35-39, Rust alignment to u64)
            # base_cost: u64 (8 bytes, offset 40-47) 
            # slot_cost: u64 (8 bytes, offset 48-55)
            # total_paid: u64 (8 bytes, offset 56-63)
            # daily_rate: u16 (2 bytes, offset 64-65)
            # created_at: u32 (4 bytes, offset 66-69) # 🔧 REAL: Actually u32, not i64!
            # Total: 69 bytes (discriminator handled separately)
            
            # 🔧 МАКСИМАЛЬНО ГИБКАЯ ПРОВЕРКА: Нужны минимально данные до level (35 байт)
            # level находится на offset 34, поэтому нужно минимум 35 байт
            if len(data) < 35:  # Минимальные данные до level включительно
                self.logger.debug("Insufficient data for BusinessCreatedInSlot - need at least level field", 
                                data_len=len(data), needed_minimum=35)
                return None
                
            # 🔧 ГИБКИЙ ПАРСИНГ: Парсим только доступные поля
            player_bytes = data[0:32]  # Discriminator handled separately
            slot_index = struct.unpack('<B', data[32:33])[0]
            business_type = struct.unpack('<B', data[33:34])[0] 
            level = struct.unpack('<B', data[34:35])[0]  # 🆕 Parse level field
            
            # 🔧 ГИБКИЙ ПАРСИНГ ПОЛЕЙ: Проверяем достаточность данных для каждого поля
            base_cost = 0
            slot_cost = 0
            total_paid = 0
            daily_rate = 0
            created_at_raw = 0
            
            try:
                if len(data) >= 43:  # Есть base_cost
                    base_cost = struct.unpack('<Q', data[35:43])[0]
                if len(data) >= 51:  # Есть slot_cost
                    slot_cost = struct.unpack('<Q', data[43:51])[0]
                if len(data) >= 59:  # Есть total_paid  
                    total_paid = struct.unpack('<Q', data[51:59])[0]
                if len(data) >= 61:  # Есть daily_rate
                    daily_rate = struct.unpack('<H', data[59:61])[0]
                if len(data) >= 65:  # Есть created_at
                    created_at_raw = struct.unpack('<I', data[61:65])[0]  # u32, not i64
            except struct.error as e:
                self.logger.debug("Partial parsing successful despite struct error", error=str(e), data_len=len(data))
            
            # 🔧 Fallback для created_at если данных нет или значение 0
            created_at = created_at_raw if created_at_raw > 0 else (int(tx_info.block_time.timestamp()) if tx_info.block_time else 0)
            
            # Convert player bytes to pubkey string
            player_pubkey = base58.b58encode(player_bytes).decode('ascii')
            
            # daily_rate from contract is already the correct daily value - don't divide by 24!
            # Convert daily_rate to earnings_per_hour for compatibility with handlers
            earnings_per_hour = daily_rate // 24 if daily_rate > 0 else 0
            
            event_data = {
                "business_id": f"business_{tx_info.slot}_{slot_index}",
                "owner": player_pubkey,
                "business_type": business_type,
                "name": f"Business {business_type}",
                "slot_index": slot_index,
                "level": level,  # 🆕 ADD: Level field from the event
                "cost": base_cost,
                "base_cost": base_cost,  # Add base_cost field
                "slot_cost": slot_cost,  # Add slot_cost field
                "total_paid": total_paid,  # Add total_paid field
                "daily_rate": daily_rate,  # Store original daily_rate from contract
                "earnings_per_hour": earnings_per_hour,  # Add for handler compatibility
            }
            
            # 🔍 DEBUG: Add detailed parsing info
            self.logger.info(f"🔍 DEBUG RAW: data_len={len(data)}, hex_preview={data[:80].hex()}")
            self.logger.info(f"🔍 DEBUG FIELDS: slot_index={slot_index}, business_type={business_type}, level={level}")
            self.logger.info(f"🔍 DEBUG COSTS: base_cost={base_cost}, slot_cost={slot_cost}, total_paid={total_paid}")
            self.logger.info(f"🔍 DEBUG OTHER: daily_rate={daily_rate}, created_at_raw={created_at_raw}")
            
            self.logger.info(
                f"Parsed BusinessCreatedInSlot event - LEVEL={level}",  # 🆕 FORCED: Show level explicitly
                player=player_pubkey,
                slot_index=slot_index,
                business_type=business_type,
                level=level,  # 🆕 LOG: Level field
                base_cost=base_cost,
                slot_cost=slot_cost,
                total_paid=total_paid,
                daily_rate=daily_rate,
                earnings_per_hour=earnings_per_hour
            )
            
            return ParsedEvent(
                event_type=EventType.BUSINESS_CREATED_IN_SLOT,
                signature=tx_info.signature,
                slot=tx_info.slot,
                block_time=tx_info.block_time,
                data=event_data,
                raw_data={"discriminator": discriminator.hex(), "data": data.hex()}
            )
            
        except Exception as e:
            self.logger.debug("Failed to parse BusinessCreatedInSlot event", error=str(e))
            return None
    
    def _parse_business_sold_from_slot_event(self, discriminator: bytes, data: bytes, tx_info: TransactionInfo) -> Optional[ParsedEvent]:
        """Parse BusinessSoldFromSlot event from anchor data."""
        try:
            # BusinessSoldFromSlot event structure (based on actual transaction data analysis):
            # player: Pubkey (32 bytes)
            # slot_index: u8 (1 byte)
            # business_type: u8 (1 byte)
            # padding: 2 bytes
            # total_invested: u64 (8 bytes) - position 34
            # days_held: u64 (8 bytes) - position 42  
            # base_fee_percent: u8 (1 byte) - position 50
            # slot_discount: u8 (1 byte) - position 51
            # final_fee_percent: u8 (1 byte) - position 52
            # padding: 3 bytes
            # return_amount: u64 (8 bytes) - position 56
            # sold_at: i64 (8 bytes) - position 64
            # Total: 72 bytes minimum
            
            if len(data) < 40:  # Need at least player + slot_index + business_type + total_invested
                self.logger.debug("Insufficient data for BusinessSoldFromSlot", data_len=len(data))
                return None
                
            # Unpack the event data based on actual transaction structure
            player_bytes = data[0:32]
            slot_index = struct.unpack('<B', data[32:33])[0]
            business_type = struct.unpack('<B', data[33:34])[0]
            
            # Extract total_invested from position 34 (confirmed from transaction analysis)
            total_invested = struct.unpack('<Q', data[34:42])[0] if len(data) >= 42 else 0
            
            # Extract other fields if available
            days_held = 0
            base_fee_percent = 25  # Default early exit fee
            slot_discount = 0
            return_amount = total_invested  # Fallback
            sold_at = int(tx_info.block_time.timestamp()) if tx_info.block_time else 0
            
            # Extract return_amount from position 53 as u32 (confirmed from actual data)
            if len(data) >= 57:  # Need at least 57 bytes for return_amount at position 53
                try:
                    return_amount = struct.unpack('<I', data[53:57])[0]
                except:
                    # Fallback to scan if exact position fails
                    for test_pos in range(50, min(len(data)-4, 60), 1):
                        try:
                            test_amount = struct.unpack('<I', data[test_pos:test_pos+4])[0]
                            # Look for reasonable return amount less than total_invested
                            if 0 < test_amount < total_invested:
                                return_amount = test_amount
                                break
                        except:
                            continue
            
            # Convert player bytes to pubkey string
            player_pubkey = base58.b58encode(player_bytes).decode('ascii')
            
            # Calculate final fee percent
            final_fee_percent = max(0, base_fee_percent - slot_discount)
            
            event_data = {
                "business_id": f"business_{tx_info.slot}_{slot_index}",  # Generate business_id
                "player": player_pubkey,
                "seller": player_pubkey,  # For compatibility
                "slot_index": slot_index,
                "business_type": business_type,
                "total_invested": total_invested,
                "days_held": days_held,
                "base_fee_percent": base_fee_percent,
                "slot_discount": slot_discount, 
                "final_fee_percent": final_fee_percent,
                "return_amount": return_amount,
                "sale_price": return_amount,  # For handler compatibility
                "sold_at": sold_at,
            }
            
            self.logger.info(
                "Parsed BusinessSoldFromSlot event",
                player=player_pubkey,
                slot_index=slot_index,
                business_type=business_type,
                total_invested=total_invested,
                days_held=days_held,
                return_amount=return_amount
            )
            
            return ParsedEvent(
                event_type=EventType.BUSINESS_SOLD_FROM_SLOT,
                signature=tx_info.signature,
                slot=tx_info.slot,
                block_time=tx_info.block_time,
                data=event_data,
                raw_data={"discriminator": discriminator.hex(), "data": data.hex()}
            )
            
        except Exception as e:
            self.logger.debug("Failed to parse BusinessSoldFromSlot event", error=str(e))
            return None
    
    def _parse_earnings_updated_event(self, discriminator: bytes, data: bytes, tx_info: TransactionInfo) -> Optional[ParsedEvent]:
        """Parse EarningsUpdated event from anchor data."""
        try:
            # EarningsUpdated event structure from contract:
            # player: Pubkey (32 bytes)
            # earnings_added: u64 (8 bytes)
            # total_pending: u64 (8 bytes)
            # next_earnings_time: i64 (8 bytes)
            # businesses_count: u8 (1 byte)
            # Total: 57 bytes minimum
            
            if len(data) < 57:
                self.logger.debug("Insufficient data for EarningsUpdated", data_len=len(data))
                return None
                
            # Unpack the event data
            player_bytes = data[0:32]
            earnings_added = struct.unpack('<Q', data[32:40])[0]
            total_pending = struct.unpack('<Q', data[40:48])[0]
            next_earnings_time = struct.unpack('<q', data[48:56])[0]
            businesses_count = struct.unpack('<B', data[56:57])[0]
            
            # Convert player bytes to pubkey string
            player_pubkey = base58.b58encode(player_bytes).decode('ascii')
            
            event_data = {
                "player": player_pubkey,  # Correct field name from contract
                "earnings_added": earnings_added,
                "total_pending": total_pending,
                "next_earnings_time": next_earnings_time,
                "businesses_count": businesses_count,
            }
            
            self.logger.info(
                "Parsed EarningsUpdated event",
                player=player_pubkey,
                earnings_added=earnings_added,
                total_pending=total_pending,
                next_earnings_time=next_earnings_time,
                businesses_count=businesses_count
            )
            
            return ParsedEvent(
                event_type=EventType.EARNINGS_UPDATED,
                signature=tx_info.signature,
                slot=tx_info.slot,
                block_time=tx_info.block_time,
                data=event_data,
                raw_data={"discriminator": discriminator.hex(), "data": data.hex()}
            )
            
        except Exception as e:
            self.logger.debug("Failed to parse EarningsUpdated event", error=str(e))
            return None
    
    def _parse_earnings_log(self, log_content: str, tx_info: TransactionInfo) -> Optional[ParsedEvent]:
        """Parse human-readable earnings update log."""
        try:
            # Example log: "💰 Earnings updated for player: DfDkPhcm93C4JyXVRdz8M9B7cP8aeZKS9DNxS5cTxEmE, added: 2776 lamports"
            
            import re
            pattern = r"💰 Earnings updated for player: ([A-Za-z0-9]+), added: (\d+) lamports"
            match = re.search(pattern, log_content)
            
            if not match:
                return None
                
            player_wallet = match.group(1)
            earnings_added = int(match.group(2))
            
            # Create minimal event data from log
            event_data = {
                "player": player_wallet,
                "earnings_added": earnings_added,
                "total_pending": earnings_added,  # Fallback - we don't know actual total from log
                "next_earnings_time": int(tx_info.block_time.timestamp()) + 60 if tx_info.block_time else 0,  # Estimate
                "businesses_count": 1,  # Fallback - we don't know from log
            }
            
            self.logger.info(
                "Parsed earnings update from human-readable log",
                player=player_wallet,
                earnings_added=earnings_added,
                source="log_fallback"
            )
            
            return ParsedEvent(
                event_type=EventType.EARNINGS_UPDATED,
                signature=tx_info.signature,
                slot=tx_info.slot,
                block_time=tx_info.block_time,
                data=event_data,
                raw_data={"log": log_content, "source": "human_readable_log"}
            )
            
        except Exception as e:
            self.logger.debug("Failed to parse earnings log", log=log_content, error=str(e))
            return None
    
    def _parse_business_created_event(self, discriminator: bytes, data: bytes, tx_info: TransactionInfo) -> Optional[ParsedEvent]:
        """Parse BusinessCreated event from anchor data."""
        try:
            # This is a simplified parser based on expected data structure
            # In production, you'd use proper IDL-based deserialization
            
            # Extract basic fields (this is an approximation)
            if len(data) < 40:
                return None
                
            # Try to extract some basic information
            # Note: This is very basic and may not match the exact struct layout
            business_type = struct.unpack('<I', data[0:4])[0] if len(data) >= 4 else 0
            slot_index = struct.unpack('<I', data[4:8])[0] if len(data) >= 8 else 0
            
            # Look for additional context in logs
            business_log = None
            for log in tx_info.logs:
                if "Business created" in log:
                    business_log = log
                    break
                    
            # Extract information from the human-readable log
            investment_amount = 0
            serial_number = 0
            if business_log:
                parts = business_log.split()
                for i, part in enumerate(parts):
                    if part == "Investment:" and i + 1 < len(parts):
                        try:
                            investment_amount = int(parts[i + 1])
                        except ValueError:
                            pass
                    elif part == "Serial:" and i + 1 < len(parts):
                        try:
                            serial_number = int(parts[i + 1])
                        except ValueError:
                            pass
            
            event_data = {
                "business_type": business_type,
                "slot_index": slot_index,
                "investment_amount": investment_amount,
                "serial_number": serial_number,
                "owner": str(tx_info.accounts[0]) if tx_info.accounts else "",
                "business_id": f"business_{tx_info.slot}_{serial_number}"
            }
            
            return ParsedEvent(
                event_type=EventType.BUSINESS_CREATED,
                signature=tx_info.signature,
                slot=tx_info.slot,
                block_time=tx_info.block_time,
                data=event_data,
                raw_data={"discriminator": discriminator.hex(), "data": data.hex()}
            )
            
        except Exception as e:
            self.logger.debug("Failed to parse business created event", error=str(e))
            return None
    
            
    def _parse_events_from_logs(self, tx_info: TransactionInfo) -> List[ParsedEvent]:
        """Parse events from transaction logs."""
        events = []
        
        for log_line in tx_info.logs:
            # Handle Anchor events in "Program data:" logs
            if "Program data:" in log_line:
                events.extend(self._parse_anchor_events(log_line, tx_info))
                continue
                
            # Handle legacy events in "Program log:" logs
            if "Program log:" not in log_line:
                continue
                
            try:
                log_content = log_line.split("Program log:", 1)[1].strip()
                
                # Check for human-readable earnings update logs
                if "💰 Earnings updated for player:" in log_content:
                    parsed_event = self._parse_earnings_log(log_content, tx_info)
                    if parsed_event:
                        events.append(parsed_event)
                        continue
                
                # Check each event signature
                for event_type_name, event_signature in self.event_signatures.items():
                    if log_content.startswith(f"{event_signature}:"):
                        event_data_str = log_content.split(":", 1)[1].strip()
                        
                        try:
                            event_data = json.loads(event_data_str)
                        except json.JSONDecodeError:
                            # Handle non-JSON event data
                            event_data = {"raw": event_data_str}
                            
                        parsed_event = ParsedEvent(
                            event_type=EventType(event_type_name),
                            signature=tx_info.signature,
                            slot=tx_info.slot,
                            block_time=tx_info.block_time,
                            data=event_data,
                            raw_data={"log": log_line}
                        )
                        
                        events.append(parsed_event)
                        break
                        
            except Exception as e:
                self.logger.warning(
                    "Failed to parse log event",
                    log=log_line,
                    error=str(e)
                )
                
        return events
        
    def _parse_events_from_instructions(self, tx_info: TransactionInfo) -> List[ParsedEvent]:
        """Parse events from instruction data (if any custom encoding is used)."""
        events = []
        
        # For now, we primarily rely on log-based events
        # This method can be extended if the program uses custom instruction data encoding
        
        return events
        
    def parse_player_created_event(self, event: ParsedEvent) -> PlayerCreatedEvent:
        """Parse a PlayerCreated event."""
        try:
            data = event.data
            return PlayerCreatedEvent(
                wallet=data["wallet"],
                referrer=data.get("referrer"),
                slot_unlocked=data["slots_unlocked"],
                block_time=event.block_time or datetime.utcnow(),
                signature=event.signature
            )
        except KeyError as e:
            raise ValidationError(f"Missing field in PlayerCreated event: {e}")
            
    def parse_business_created_event(self, event: ParsedEvent) -> BusinessCreatedEvent:
        """Parse a BusinessCreated event."""
        try:
            data = event.data
            return BusinessCreatedEvent(
                business_id=data["business_id"],
                owner=data["owner"],
                business_type=data["business_type"],
                name=data["name"],
                slot_index=data["slot_index"],
                cost=data["cost"],
                earnings_per_hour=data["earnings_per_hour"],
                block_time=event.block_time or datetime.utcnow(),
                signature=event.signature
            )
        except KeyError as e:
            raise ValidationError(f"Missing field in BusinessCreated event: {e}")
            
    def parse_business_upgraded_event(self, event: ParsedEvent) -> BusinessUpgradedEvent:
        """Parse a BusinessUpgraded event."""
        try:
            data = event.data
            return BusinessUpgradedEvent(
                business_id=data["business_id"],
                owner=data["owner"],
                old_level=data["old_level"],
                new_level=data["new_level"],
                upgrade_cost=data["upgrade_cost"],
                new_earnings_per_hour=data["new_earnings_per_hour"],
                block_time=event.block_time or datetime.utcnow(),
                signature=event.signature
            )
        except KeyError as e:
            raise ValidationError(f"Missing field in BusinessUpgraded event: {e}")
            
    def parse_business_sold_event(self, event: ParsedEvent) -> BusinessSoldEvent:
        """Parse a BusinessSold event."""
        try:
            data = event.data
            return BusinessSoldEvent(
                business_id=data["business_id"],
                seller=data["seller"],
                buyer=data.get("buyer"),
                business_type=data["business_type"],
                sale_price=data["sale_price"],
                penalty_amount=data["penalty_amount"],
                days_held=data["days_held"],
                block_time=event.block_time or datetime.utcnow(),
                signature=event.signature
            )
        except KeyError as e:
            raise ValidationError(f"Missing field in BusinessSold event: {e}")
            
    def parse_earnings_updated_event(self, event: ParsedEvent) -> EarningsUpdatedEvent:
        """Parse an EarningsUpdated event with correct field mapping."""
        try:
            data = event.data
            
            # 🔧 FIXED: Map contract fields to our event structure
            return EarningsUpdatedEvent(
                wallet=data["player"],                    # player → wallet
                earnings_added=data["earnings_added"],    # earnings_added (правильное поле)
                total_pending=data["total_pending"],      # total_pending (правильное поле) 
                next_earnings_time=datetime.fromtimestamp(data["next_earnings_time"]) if "next_earnings_time" in data else event.block_time,
                businesses_count=data.get("businesses_count", 0),  # новое поле (может отсутствовать в старых событиях)
                block_time=event.block_time or datetime.utcnow(),
                signature=event.signature
            )
        except KeyError as e:
            self.logger.error(
                "Failed to parse EarningsUpdated event", 
                event_data=event.data,
                error=str(e),
                signature=event.signature
            )
            raise ValidationError(f"Missing field in EarningsUpdated event: {e}. Available fields: {list(event.data.keys())}")
            
    def parse_earnings_claimed_event(self, event: ParsedEvent) -> EarningsClaimedEvent:
        """Parse an EarningsClaimed event."""
        try:
            data = event.data
            return EarningsClaimedEvent(
                wallet=data["wallet"],
                amount_claimed=data["amount_claimed"],
                treasury_fee=data["treasury_fee"],
                net_amount=data["net_amount"],
                block_time=event.block_time or datetime.utcnow(),
                signature=event.signature
            )
        except KeyError as e:
            raise ValidationError(f"Missing field in EarningsClaimed event: {e}")
            
            
    def parse_slot_event(self, event: ParsedEvent) -> SlotEvent:
        """Parse a slot-related event (unlocked/purchased)."""
        try:
            data = event.data
            return SlotEvent(
                wallet=data["wallet"],
                slot_index=data["slot_index"],
                cost=data["cost"],
                is_premium=data.get("is_premium", False),
                block_time=event.block_time or datetime.utcnow(),
                signature=event.signature
            )
        except KeyError as e:
            raise ValidationError(f"Missing field in Slot event: {e}")
            
    def validate_event_data(self, event: ParsedEvent) -> bool:
        """
        Validate event data consistency and required fields.
        
        Args:
            event: Parsed event to validate
            
        Returns:
            True if valid, False otherwise
        """
        try:
            # Basic validation
            if not event.signature or not event.slot:
                return False
                
            # Type-specific validation
            if event.event_type == EventType.PLAYER_CREATED:
                required_fields = ["wallet"]
            elif event.event_type == EventType.BUSINESS_CREATED:
                required_fields = ["business_id", "owner", "business_type"]
            elif event.event_type == EventType.BUSINESS_UPGRADED:
                required_fields = ["business_id", "owner", "old_level", "new_level"]
            elif event.event_type == EventType.BUSINESS_SOLD:
                required_fields = ["business_id", "seller", "sale_price"]
            elif event.event_type == EventType.EARNINGS_UPDATED:
                required_fields = ["player", "earnings_added"]  # 🔧 FIXED: правильные поля из контракта
            elif event.event_type == EventType.EARNINGS_CLAIMED:
                required_fields = ["wallet", "amount_claimed"]
            else:
                # For other event types, basic validation is sufficient
                return True
                
            # Check required fields exist
            for field in required_fields:
                if field not in event.data:
                    self.logger.warning(
                        "Missing required field in event",
                        event_type=event.event_type.value,
                        field=field,
                        signature=event.signature
                    )
                    return False
                    
            return True
            
        except Exception as e:
            self.logger.error(
                "Event validation error",
                event_type=event.event_type.value,
                signature=event.signature,
                error=str(e)
            )
            return False
    
    def parse_logs_for_events(
        self, 
        logs: List[str], 
        signature: str, 
        slot: int, 
        block_time: Optional[int]
    ) -> List[ParsedEvent]:
        """
        Parse events directly from WebSocket logs for real-time processing.
        
        Args:
            logs: List of log messages from WebSocket notification
            signature: Transaction signature
            slot: Slot number
            block_time: Block timestamp (Unix timestamp)
            
        Returns:
            List of parsed events
        """
        try:
            parsed_events = []
            
            # 🔍 ДЕТАЛЬНОЕ ЛОГИРОВАНИЕ: Показываем все входящие логи
            self.logger.info(
                "🔍 REAL-TIME LOGS DEBUG: Received logs for parsing",
                signature=signature,
                log_count=len(logs),
                logs_preview=[log[:100] + "..." if len(log) > 100 else log for log in logs[:5]]
            )
            
            # Convert block_time to datetime if provided
            block_time_dt = None
            if block_time:
                block_time_dt = datetime.fromtimestamp(block_time)
            
            for i, log_line in enumerate(logs):
                self.logger.debug(
                    f"🔍 REAL-TIME LOG #{i}: Processing line",
                    signature=signature,
                    line=log_line[:200] + "..." if len(log_line) > 200 else log_line,
                    has_program_data="Program data:" in log_line,
                    has_program_log="Program log:" in log_line
                )
                
                # Handle Anchor events in "Program data:" logs
                if "Program data:" in log_line:
                    self.logger.info(
                        "🎯 REAL-TIME: Found Program data line",
                        signature=signature,
                        line_preview=log_line[:100] + "..." if len(log_line) > 100 else log_line
                    )
                    events = self._parse_anchor_events_from_log(log_line, signature, slot, block_time_dt)
                    parsed_events.extend(events)
                    continue
                    
                # Handle legacy events in "Program log:" logs
                if "Program log:" not in log_line:
                    continue
                
                self.logger.info(
                    "🎯 REAL-TIME: Found Program log line",
                    signature=signature,
                    line_preview=log_line[:100] + "..." if len(log_line) > 100 else log_line
                )
                    
                try:
                    log_content = log_line.split("Program log:", 1)[1].strip()
                    
                    # Check for human-readable earnings update logs
                    if "💰 Earnings updated for player:" in log_content:
                        parsed_event = self._parse_earnings_log_direct(log_content, signature, slot, block_time_dt)
                        if parsed_event:
                            parsed_events.append(parsed_event)
                            continue
                    
                    # Check each event signature
                    for event_type_name, event_signature in self.event_signatures.items():
                        if log_content.startswith(f"{event_signature}:"):
                            event_data_str = log_content.split(":", 1)[1].strip()
                            
                            try:
                                event_data = json.loads(event_data_str)
                            except json.JSONDecodeError:
                                # Handle non-JSON event data
                                event_data = {"raw": event_data_str}
                                
                            parsed_event = ParsedEvent(
                                event_type=EventType(event_type_name),
                                signature=signature,
                                slot=slot,
                                block_time=block_time_dt,
                                data=event_data,
                                raw_data={"log": log_line}
                            )
                            
                            parsed_events.append(parsed_event)
                            break
                            
                except Exception as e:
                    self.logger.warning(
                        "Failed to parse log event in real-time",
                        log=log_line,
                        signature=signature,
                        error=str(e)
                    )
                    continue
            
            self.logger.debug(
                "Real-time log parsing completed",
                signature=signature,
                log_count=len(logs),
                event_count=len(parsed_events)
            )
            
            return parsed_events
            
        except Exception as e:
            self.logger.error(
                "Failed to parse logs for events",
                signature=signature,
                error=str(e)
            )
            return []
    
    def _parse_anchor_events_from_log(
        self, 
        log_line: str, 
        signature: str, 
        slot: int, 
        block_time: Optional[datetime]
    ) -> List[ParsedEvent]:
        """Parse Anchor events from a single log line for real-time processing."""
        events = []
        
        try:
            # Extract base64 data from "Program data: <base64_data>"
            if "Program data:" not in log_line:
                return events
                
            data_part = log_line.split("Program data:", 1)[1].strip()
            
            # 🔍 ДЕТАЛЬНОЕ ЛОГИРОВАНИЕ
            self.logger.info(
                "🔍 REAL-TIME ANCHOR EVENT DEBUG",
                signature=signature,
                data_part_length=len(data_part),
                data_part_preview=data_part[:100] + "..." if len(data_part) > 100 else data_part,
                full_log_line=log_line
            )
            
            # Decode base64 data
            try:
                decoded_data = base64.b64decode(data_part)
                self.logger.info(
                    "✅ REAL-TIME: Base64 decoded successfully",
                    signature=signature,
                    decoded_length=len(decoded_data),
                    decoded_hex=decoded_data[:32].hex() if len(decoded_data) >= 32 else decoded_data.hex()
                )
            except Exception as e:
                self.logger.error(
                    "❌ REAL-TIME: Failed to decode base64 event data",
                    signature=signature,
                    error=str(e),
                    data_part=data_part[:200]
                )
                return events
                
            # Anchor events typically start with an 8-byte discriminator
            if len(decoded_data) < 8:
                self.logger.warning(
                    "⚠️ REAL-TIME: Decoded data too short for discriminator",
                    signature=signature,
                    decoded_length=len(decoded_data)
                )
                return events
                
            # Extract discriminator (first 8 bytes)
            discriminator = decoded_data[:8]
            event_data = decoded_data[8:]
            
            self.logger.info(
                "🔍 REAL-TIME: Parsing discriminator",
                signature=signature,
                discriminator_hex=discriminator.hex(),
                event_data_length=len(event_data)
            )
            
            # Parse the event using existing discriminator logic
            parsed_event = self._decode_anchor_event_data_direct(
                discriminator, event_data, signature, slot, block_time
            )
            if parsed_event:
                events.append(parsed_event)
                self.logger.info(
                    "✅ REAL-TIME: Successfully parsed anchor event",
                    signature=signature,
                    event_type=parsed_event.event_type.value if parsed_event.event_type else "unknown"
                )
            else:
                self.logger.warning(
                    "⚠️ REAL-TIME: Failed to parse event from discriminator",
                    signature=signature,
                    discriminator_hex=discriminator.hex()
                )
                
        except Exception as e:
            self.logger.debug(
                "Failed to parse anchor event in real-time",
                log_line=log_line,
                error=str(e)
            )
            
        return events
    
    def _decode_anchor_event_data_direct(
        self, 
        discriminator: bytes, 
        data: bytes, 
        signature: str, 
        slot: int, 
        block_time: Optional[datetime]
    ) -> Optional[ParsedEvent]:
        """Decode Anchor event data for real-time processing."""
        try:
            discriminator_hex = discriminator.hex()
            
            # 🔧 FIXED: Все правильные discriminator'ы из реальных транзакций
            if discriminator_hex == "4a191ae88d56371c" and len(data) >= 64:  # Реальный discriminator
                # Parse BusinessCreatedInSlot event (64 bytes в реальных данных)
                return self._parse_business_created_in_slot_event_direct(
                    discriminator, data, signature, slot, block_time
                )
            elif discriminator_hex == "f8e9e74d11085e42" and len(data) >= 57:
                # Parse EarningsUpdated event (57 bytes)
                return self._parse_earnings_updated_event_direct(
                    discriminator, data, signature, slot, block_time
                )
            elif discriminator_hex == "0aea7413441595f4" and len(data) >= 40:
                # Parse BusinessSoldFromSlot event (40+ bytes)
                return self._parse_business_sold_from_slot_event_direct(
                    discriminator, data, signature, slot, block_time
                )
            elif discriminator_hex == "fe094a515c05bddc" and len(data) >= 56:
                # Parse PlayerCreated event (56 bytes)
                return self._parse_player_created_event_direct(
                    discriminator, data, signature, slot, block_time
                )
            elif discriminator_hex == "3fe9746a44105602" and len(data) >= 59:
                # Parse BusinessCreated event (59+ bytes)
                return self._parse_business_created_event_direct(
                    discriminator, data, signature, slot, block_time
                )
            elif discriminator_hex == "6aaa9a69152bbd61" and len(data) >= 48:
                # Parse EarningsClaimed event (48 bytes)
                return self._parse_earnings_claimed_event_direct(
                    discriminator, data, signature, slot, block_time
                )
            elif discriminator_hex == "a0a9e0fdbe38a29d":
                # Parse BusinessUpgraded event
                return self._parse_business_upgraded_event_direct(
                    discriminator, data, signature, slot, block_time
                )
            elif discriminator_hex == "667539291574c92d":
                # Parse BusinessUpgradedInSlot event
                return self._parse_business_upgraded_in_slot_event_direct(
                    discriminator, data, signature, slot, block_time
                )
            elif discriminator_hex == "2ff123a4b9c3e2c3":
                # Parse BusinessSold event (legacy)
                return self._parse_business_sold_event_legacy_direct(
                    discriminator, data, signature, slot, block_time
                )
            
        except Exception as e:
            self.logger.debug("Failed to decode anchor event data in real-time", error=str(e))
            
        return None
    
    def _parse_business_created_in_slot_event_direct(
        self, 
        discriminator: bytes, 
        data: bytes, 
        signature: str, 
        slot: int, 
        block_time: Optional[datetime]
    ) -> Optional[ParsedEvent]:
        """Parse BusinessCreatedInSlot event for real-time processing."""
        try:
            # 🔧 ИСПРАВЛЕНИЕ: discriminator уже извлечен выше!
            # BusinessCreatedInSlot structure (69 bytes WITHOUT discriminator):
            # player: Pubkey (32 bytes, offset 0-31)
            # slot_index: u8 (1 byte, offset 32)
            # business_type: u8 (1 byte, offset 33)
            # level: u8 (1 byte, offset 34)
            # padding: 5 bytes (offset 35-39, Rust alignment)
            # base_cost: u64 (8 bytes, offset 40-47)  
            # slot_cost: u64 (8 bytes, offset 48-55)
            # total_paid: u64 (8 bytes, offset 56-63)
            # daily_rate: u16 (2 bytes, offset 64-65)
            # created_at: u32 (4 bytes, offset 66-69)
            # Total: 69 bytes (discriminator already removed)
            
            if len(data) < 66:  # Минимально до daily_rate
                self.logger.debug(f"Insufficient data for BusinessCreatedInSlot: {len(data)} bytes, need 66")
                return None
                
            # 🔧 ИСПРАВЛЕННЫЕ ОФФСЕТЫ: без discriminator
            player_bytes = data[0:32]  # Теперь player с начала
            slot_index = struct.unpack('<B', data[32:33])[0]
            business_type = struct.unpack('<B', data[33:34])[0]  # 🔧 ИСПРАВЛЕНО: -8 
            level = struct.unpack('<B', data[34:35])[0]  # 🔧 ИСПРАВЛЕНО: -8
            # Skip padding (5 bytes) to align to u64
            base_cost = struct.unpack('<Q', data[40:48])[0]  # 🔧 ИСПРАВЛЕНО: -8
            slot_cost = struct.unpack('<Q', data[48:56])[0]  # 🔧 ИСПРАВЛЕНО: -8
            total_paid = struct.unpack('<Q', data[56:64])[0]  # 🔧 ИСПРАВЛЕНО: -8
            daily_rate = struct.unpack('<H', data[64:66])[0]  # 🔧 ИСПРАВЛЕНО: -8
            # Use block_time since created_at field is truncated
            created_at_raw = int(block_time.timestamp()) if block_time else 0
            
            # Convert player bytes to address string
            player_pubkey = Pubkey(player_bytes)
            player_address = str(player_pubkey)
            
            event_data = {
                "owner": player_address,
                "slot_index": slot_index,
                "business_type": business_type,
                "level": level,  # 🆕 ADD: Level field from the event
                "base_cost": base_cost,
                "slot_cost": slot_cost,
                "total_paid": total_paid,
                "daily_rate": daily_rate,
                "signature": signature
            }
            
            return ParsedEvent(
                event_type=EventType.BUSINESS_CREATED_IN_SLOT,
                signature=signature,
                slot=slot,
                block_time=block_time,
                data=event_data,
                raw_data={
                    "discriminator": discriminator.hex(),
                    "raw_data": data.hex()
                }
            )
            
        except Exception as e:
            self.logger.debug("Failed to parse BusinessCreatedInSlot in real-time", error=str(e))
            return None
    
    def _parse_earnings_updated_event_direct(
        self, 
        discriminator: bytes, 
        data: bytes, 
        signature: str, 
        slot: int, 
        block_time: Optional[datetime]
    ) -> Optional[ParsedEvent]:
        """Parse EarningsUpdated event for real-time processing."""
        try:
            # EarningsUpdated structure:
            # player: Pubkey (32 bytes)
            # earnings_added: u64 (8 bytes)
            # total_pending: u64 (8 bytes)
            # next_earnings_time: i64 (8 bytes)
            # businesses_count: u8 (1 byte)
            # Total: 57 bytes
            
            if len(data) < 57:
                self.logger.debug(f"Insufficient data for EarningsUpdated: {len(data)} bytes, need 57")
                return None
                
            # Parse earnings updated event data with all fields
            player_bytes = data[0:32]
            earnings_added = struct.unpack('<Q', data[32:40])[0]
            total_pending = struct.unpack('<Q', data[40:48])[0]
            next_earnings_time = struct.unpack('<q', data[48:56])[0]
            businesses_count = struct.unpack('<B', data[56:57])[0]
            
            player_pubkey = Pubkey(player_bytes)
            player_address = str(player_pubkey)
            
            # Convert timestamp to datetime
            next_earnings_dt = None
            if next_earnings_time > 0:
                next_earnings_dt = datetime.fromtimestamp(next_earnings_time)
            
            event_data = {
                "player": player_address,
                "earnings_added": earnings_added,
                "total_pending": total_pending,
                "next_earnings_time": next_earnings_dt.isoformat() if next_earnings_dt else None,
                "businesses_count": businesses_count,
                "signature": signature
            }
            
            return ParsedEvent(
                event_type=EventType.EARNINGS_UPDATED,
                signature=signature,
                slot=slot,
                block_time=block_time,
                data=event_data,
                raw_data={
                    "discriminator": discriminator.hex(),
                    "raw_data": data.hex()
                }
            )
            
        except Exception as e:
            self.logger.debug("Failed to parse EarningsUpdated in real-time", error=str(e))
            return None
    
    def _parse_earnings_log_direct(
        self, 
        log_content: str, 
        signature: str, 
        slot: int, 
        block_time: Optional[datetime]
    ) -> Optional[ParsedEvent]:
        """Parse earnings log for real-time processing."""
        try:
            # Parse human-readable earnings log
            # Format: "💰 Earnings updated for player: ABC123... | Added: 1000 | Total: 5000 | Businesses: 3"
            
            parts = log_content.split(" | ")
            if len(parts) < 4:
                return None
            
            # Extract player address
            player_part = parts[0].replace("💰 Earnings updated for player:", "").strip()
            
            # Extract amounts
            added_part = parts[1].replace("Added:", "").strip()
            total_part = parts[2].replace("Total:", "").strip()
            businesses_part = parts[3].replace("Businesses:", "").strip()
            
            try:
                earnings_added = int(added_part)
                total_pending = int(total_part)
                businesses_count = int(businesses_part)
            except ValueError:
                return None
            
            event_data = {
                "player": player_part,
                "earnings_added": earnings_added,
                "total_pending": total_pending,
                "businesses_count": businesses_count,
                "signature": signature
            }
            
            return ParsedEvent(
                event_type=EventType.EARNINGS_UPDATED,
                signature=signature,
                slot=slot,
                block_time=block_time,
                data=event_data,
                raw_data={"log": log_content}
            )
            
        except Exception as e:
            self.logger.debug("Failed to parse earnings log in real-time", error=str(e))
            return None
    
    def _parse_player_created_event_direct(
        self, 
        discriminator: bytes, 
        data: bytes, 
        signature: str, 
        slot: int, 
        block_time: Optional[datetime]
    ) -> Optional[ParsedEvent]:
        """Parse PlayerCreated event for real-time processing."""
        try:
            # PlayerCreated structure: wallet(32) + entry_fee(8) + created_at(8) + next_earnings_time(8) = 56 bytes
            if len(data) < 56:
                return None
                
            player_bytes = data[0:32]
            entry_fee = struct.unpack('<Q', data[32:40])[0]
            created_at = struct.unpack('<q', data[40:48])[0]
            next_earnings_time = struct.unpack('<q', data[48:56])[0]
            
            player_pubkey = Pubkey(player_bytes)
            player_address = str(player_pubkey)
            
            event_data = {
                "wallet": player_address,
                "entry_fee": entry_fee,
                "created_at": datetime.fromtimestamp(created_at).isoformat() if created_at > 0 else None,
                "next_earnings_time": datetime.fromtimestamp(next_earnings_time).isoformat() if next_earnings_time > 0 else None,
                "signature": signature
            }
            
            return ParsedEvent(
                event_type=EventType.PLAYER_CREATED,
                signature=signature,
                slot=slot,
                block_time=block_time,
                data=event_data,
                raw_data={"discriminator": discriminator.hex(), "raw_data": data.hex()}
            )
            
        except Exception as e:
            self.logger.debug("Failed to parse PlayerCreated in real-time", error=str(e))
            return None
    
    def _parse_business_created_event_direct(
        self, 
        discriminator: bytes, 
        data: bytes, 
        signature: str, 
        slot: int, 
        block_time: Optional[datetime]
    ) -> Optional[ParsedEvent]:
        """Parse BusinessCreated event for real-time processing."""
        try:
            # BusinessCreated structure: player(32) + business_type(1) + invested_amount(8) + daily_rate(2) + treasury_fee(8) + created_at(8) = 59 bytes
            if len(data) < 59:
                return None
                
            player_bytes = data[0:32]
            business_type = struct.unpack('<B', data[32:33])[0]
            # Skip 7 bytes padding
            invested_amount = struct.unpack('<Q', data[40:48])[0]
            daily_rate = struct.unpack('<H', data[48:50])[0]
            # Skip 6 bytes padding
            treasury_fee = struct.unpack('<Q', data[56:64])[0]
            created_at = struct.unpack('<q', data[64:72])[0]
            
            player_pubkey = Pubkey(player_bytes)
            player_address = str(player_pubkey)
            
            event_data = {
                "player": player_address,
                "business_type": business_type,
                "invested_amount": invested_amount,
                "daily_rate": daily_rate,
                "treasury_fee": treasury_fee,
                "created_at": datetime.fromtimestamp(created_at).isoformat() if created_at > 0 else None,
                "signature": signature
            }
            
            return ParsedEvent(
                event_type=EventType.BUSINESS_CREATED,
                signature=signature,
                slot=slot,
                block_time=block_time,
                data=event_data,
                raw_data={"discriminator": discriminator.hex(), "raw_data": data.hex()}
            )
            
        except Exception as e:
            self.logger.debug("Failed to parse BusinessCreated in real-time", error=str(e))
            return None
    
    def _parse_earnings_claimed_event_direct(
        self, 
        discriminator: bytes, 
        data: bytes, 
        signature: str, 
        slot: int, 
        block_time: Optional[datetime]
    ) -> Optional[ParsedEvent]:
        """Parse EarningsClaimed event for real-time processing."""
        try:
            # EarningsClaimed structure: player(32) + amount(8) + claimed_at(8) = 48 bytes
            if len(data) < 48:
                return None
                
            player_bytes = data[0:32]
            amount = struct.unpack('<Q', data[32:40])[0]
            claimed_at = struct.unpack('<q', data[40:48])[0]
            
            player_pubkey = Pubkey(player_bytes)
            player_address = str(player_pubkey)
            
            event_data = {
                "player": player_address,
                "amount": amount,
                "claimed_at": datetime.fromtimestamp(claimed_at).isoformat() if claimed_at > 0 else None,
                "signature": signature
            }
            
            return ParsedEvent(
                event_type=EventType.EARNINGS_CLAIMED,
                signature=signature,
                slot=slot,
                block_time=block_time,
                data=event_data,
                raw_data={"discriminator": discriminator.hex(), "raw_data": data.hex()}
            )
            
        except Exception as e:
            self.logger.debug("Failed to parse EarningsClaimed in real-time", error=str(e))
            return None
    
    def _parse_player_created_event(self, discriminator: bytes, data: bytes, tx_info: TransactionInfo) -> Optional[ParsedEvent]:
        """Parse PlayerCreated event from anchor data."""
        try:
            # PlayerCreated structure: wallet(32) + entry_fee(8) + created_at(8) + next_earnings_time(8) = 56 bytes
            if len(data) < 56:
                self.logger.debug("Insufficient data for PlayerCreated", data_len=len(data))
                return None
                
            player_bytes = data[0:32]
            entry_fee = struct.unpack('<Q', data[32:40])[0]
            created_at = struct.unpack('<q', data[40:48])[0]
            next_earnings_time = struct.unpack('<q', data[48:56])[0]
            
            player_pubkey = base58.b58encode(player_bytes).decode('ascii')
            
            event_data = {
                "wallet": player_pubkey,
                "entry_fee": entry_fee,
                "created_at": created_at,
                "next_earnings_time": next_earnings_time,
            }
            
            return ParsedEvent(
                event_type=EventType.PLAYER_CREATED,
                signature=tx_info.signature,
                slot=tx_info.slot,
                block_time=tx_info.block_time,
                data=event_data,
                raw_data={"discriminator": discriminator.hex(), "data": data.hex()}
            )
            
        except Exception as e:
            self.logger.debug("Failed to parse PlayerCreated event", error=str(e))
            return None

    def _parse_earnings_claimed_event(self, discriminator: bytes, data: bytes, tx_info: TransactionInfo) -> Optional[ParsedEvent]:
        """Parse EarningsClaimed event from anchor data."""
        try:
            # EarningsClaimed structure: player(32) + amount(8) + claimed_at(8) = 48 bytes
            if len(data) < 48:
                self.logger.debug("Insufficient data for EarningsClaimed", data_len=len(data))
                return None
                
            player_bytes = data[0:32]
            amount = struct.unpack('<Q', data[32:40])[0]
            claimed_at = struct.unpack('<q', data[40:48])[0]
            
            player_pubkey = base58.b58encode(player_bytes).decode('ascii')
            
            event_data = {
                "player": player_pubkey,
                "amount": amount,
                "claimed_at": claimed_at,
            }
            
            return ParsedEvent(
                event_type=EventType.EARNINGS_CLAIMED,
                signature=tx_info.signature,
                slot=tx_info.slot,
                block_time=tx_info.block_time,
                data=event_data,
                raw_data={"discriminator": discriminator.hex(), "data": data.hex()}
            )
            
        except Exception as e:
            self.logger.debug("Failed to parse EarningsClaimed event", error=str(e))
            return None

    def _parse_business_upgraded_event(self, discriminator: bytes, data: bytes, tx_info: TransactionInfo) -> Optional[ParsedEvent]:
        """Parse BusinessUpgraded event from anchor data."""
        try:
            # BusinessUpgraded structure estimation - will need actual struct analysis
            if len(data) < 60:
                self.logger.debug("Insufficient data for BusinessUpgraded", data_len=len(data))
                return None
                
            player_bytes = data[0:32]
            business_index = struct.unpack('<B', data[32:33])[0]
            new_level = struct.unpack('<B', data[33:34])[0]
            # Skip padding
            upgrade_cost = struct.unpack('<Q', data[40:48])[0]
            new_daily_rate = struct.unpack('<H', data[48:50])[0]
            
            player_pubkey = base58.b58encode(player_bytes).decode('ascii')
            
            event_data = {
                "player": player_pubkey,
                "business_index": business_index,
                "new_level": new_level,
                "upgrade_cost": upgrade_cost,
                "new_daily_rate": new_daily_rate,
            }
            
            return ParsedEvent(
                event_type=EventType.BUSINESS_UPGRADED,
                signature=tx_info.signature,
                slot=tx_info.slot,
                block_time=tx_info.block_time,
                data=event_data,
                raw_data={"discriminator": discriminator.hex(), "data": data.hex()}
            )
            
        except Exception as e:
            self.logger.debug("Failed to parse BusinessUpgraded event", error=str(e))
            return None

    def _parse_business_upgraded_in_slot_event(self, discriminator: bytes, data: bytes, tx_info: TransactionInfo) -> Optional[ParsedEvent]:
        """Parse BusinessUpgradedInSlot event from anchor data."""
        try:
            # BusinessUpgradedInSlot structure from REAL transaction analysis (53+ bytes)
            # Allow flexibility for future contract changes
            if len(data) < 45:  # Minimum: player(32) + levels(3) + cost(8) + rate(2) = 45
                self.logger.debug("Insufficient data for BusinessUpgradedInSlot", data_len=len(data))
                return None
                
            player_bytes = data[0:32]
            slot_index = struct.unpack('<B', data[32:33])[0]
            old_level = struct.unpack('<B', data[33:34])[0]
            new_level = struct.unpack('<B', data[34:35])[0]
            # Fixed positions from real transaction data (with fallback)
            upgrade_cost = 0
            new_daily_rate = 0
            
            # Try to extract upgrade_cost (8 bytes) at expected position
            if len(data) >= 43:
                upgrade_cost = struct.unpack('<Q', data[35:43])[0]  # 35-42 (8 bytes)
            
            # Try to extract daily_rate (2 bytes) at expected position  
            if len(data) >= 45:
                new_daily_rate = struct.unpack('<H', data[43:45])[0]  # 43-44 (2 bytes)
            # upgraded_at would be at later position
            
            player_pubkey = base58.b58encode(player_bytes).decode('ascii')
            
            event_data = {
                "player": player_pubkey,
                "slot_index": slot_index,
                "old_level": old_level,
                "new_level": new_level,
                "upgrade_cost": upgrade_cost,
                "new_daily_rate": new_daily_rate,
            }
            
            return ParsedEvent(
                event_type=EventType.BUSINESS_UPGRADED_IN_SLOT,
                signature=tx_info.signature,
                slot=tx_info.slot,
                block_time=tx_info.block_time,
                data=event_data,
                raw_data={"discriminator": discriminator.hex(), "data": data.hex()}
            )
            
        except Exception as e:
            self.logger.debug("Failed to parse BusinessUpgradedInSlot event", error=str(e))
            return None

    def _parse_business_sold_event_legacy(self, discriminator: bytes, data: bytes, tx_info: TransactionInfo) -> Optional[ParsedEvent]:
        """Parse legacy BusinessSold event from anchor data."""
        try:
            # Legacy BusinessSold structure estimation
            if len(data) < 60:
                self.logger.debug("Insufficient data for legacy BusinessSold", data_len=len(data))
                return None
                
            player_bytes = data[0:32]
            business_index = struct.unpack('<B', data[32:33])[0]
            # Extract other fields as available
            
            player_pubkey = base58.b58encode(player_bytes).decode('ascii')
            
            event_data = {
                "player": player_pubkey,
                "business_index": business_index,
            }
            
            return ParsedEvent(
                event_type=EventType.BUSINESS_SOLD,
                signature=tx_info.signature,
                slot=tx_info.slot,
                block_time=tx_info.block_time,
                data=event_data,
                raw_data={"discriminator": discriminator.hex(), "data": data.hex()}
            )
            
        except Exception as e:
            self.logger.debug("Failed to parse legacy BusinessSold event", error=str(e))
            return None

    # 🆕 ADD: Direct parsing methods for new events
    def _parse_business_upgraded_event_direct(
        self, 
        discriminator: bytes, 
        data: bytes, 
        signature: str, 
        slot: int, 
        block_time: Optional[datetime]
    ) -> Optional[ParsedEvent]:
        """Parse BusinessUpgraded event for real-time processing."""
        try:
            if len(data) < 60:
                return None
                
            player_bytes = data[0:32]
            business_index = struct.unpack('<B', data[32:33])[0]
            new_level = struct.unpack('<B', data[33:34])[0]
            upgrade_cost = struct.unpack('<Q', data[40:48])[0]
            new_daily_rate = struct.unpack('<H', data[48:50])[0]
            
            player_pubkey = Pubkey(player_bytes)
            player_address = str(player_pubkey)
            
            event_data = {
                "player": player_address,
                "business_index": business_index,
                "new_level": new_level,
                "upgrade_cost": upgrade_cost,
                "new_daily_rate": new_daily_rate,
                "signature": signature
            }
            
            return ParsedEvent(
                event_type=EventType.BUSINESS_UPGRADED,
                signature=signature,
                slot=slot,
                block_time=block_time,
                data=event_data,
                raw_data={"discriminator": discriminator.hex(), "raw_data": data.hex()}
            )
            
        except Exception as e:
            self.logger.debug("Failed to parse BusinessUpgraded in real-time", error=str(e))
            return None

    def _parse_business_upgraded_in_slot_event_direct(
        self, 
        discriminator: bytes, 
        data: bytes, 
        signature: str, 
        slot: int, 
        block_time: Optional[datetime]
    ) -> Optional[ParsedEvent]:
        """Parse BusinessUpgradedInSlot event for real-time processing."""
        try:
            # Allow flexibility for future contract changes
            if len(data) < 45:  # Minimum: player(32) + levels(3) + cost(8) + rate(2) = 45
                return None
                
            player_bytes = data[0:32]
            slot_index = struct.unpack('<B', data[32:33])[0]
            old_level = struct.unpack('<B', data[33:34])[0]
            new_level = struct.unpack('<B', data[34:35])[0]
            # Fixed positions from real transaction analysis (with fallback)
            upgrade_cost = 0
            new_daily_rate = 0
            
            # Try to extract upgrade_cost (8 bytes) at expected position
            if len(data) >= 43:
                upgrade_cost = struct.unpack('<Q', data[35:43])[0]  # 35-42 (8 bytes)
            
            # Try to extract daily_rate (2 bytes) at expected position  
            if len(data) >= 45:
                new_daily_rate = struct.unpack('<H', data[43:45])[0]  # 43-44 (2 bytes)
            
            player_pubkey = Pubkey(player_bytes)
            player_address = str(player_pubkey)
            
            event_data = {
                "player": player_address,
                "slot_index": slot_index,
                "old_level": old_level,
                "new_level": new_level,
                "upgrade_cost": upgrade_cost,
                "new_daily_rate": new_daily_rate,
                "signature": signature
            }
            
            return ParsedEvent(
                event_type=EventType.BUSINESS_UPGRADED_IN_SLOT,
                signature=signature,
                slot=slot,
                block_time=block_time,
                data=event_data,
                raw_data={"discriminator": discriminator.hex(), "raw_data": data.hex()}
            )
            
        except Exception as e:
            self.logger.debug("Failed to parse BusinessUpgradedInSlot in real-time", error=str(e))
            return None

    def _parse_business_sold_event_legacy_direct(
        self, 
        discriminator: bytes, 
        data: bytes, 
        signature: str, 
        slot: int, 
        block_time: Optional[datetime]
    ) -> Optional[ParsedEvent]:
        """Parse legacy BusinessSold event for real-time processing."""
        try:
            if len(data) < 40:
                return None
                
            player_bytes = data[0:32]
            business_index = struct.unpack('<B', data[32:33])[0]
            
            player_pubkey = Pubkey(player_bytes)
            player_address = str(player_pubkey)
            
            event_data = {
                "player": player_address,
                "business_index": business_index,
                "signature": signature
            }
            
            return ParsedEvent(
                event_type=EventType.BUSINESS_SOLD,
                signature=signature,
                slot=slot,
                block_time=block_time,
                data=event_data,
                raw_data={"discriminator": discriminator.hex(), "raw_data": data.hex()}
            )
            
        except Exception as e:
            self.logger.debug("Failed to parse legacy BusinessSold in real-time", error=str(e))
            return None

    def _parse_business_sold_from_slot_event_direct(
        self, 
        discriminator: bytes, 
        data: bytes, 
        signature: str, 
        slot: int, 
        block_time: Optional[datetime]
    ) -> Optional[ParsedEvent]:
        """Parse BusinessSoldFromSlot event for real-time processing."""
        try:
            # BusinessSoldFromSlot event structure (same as non-direct version):
            # player: Pubkey (32 bytes)
            # slot_index: u8 (1 byte)
            # business_type: u8 (1 byte)
            # padding: 2 bytes
            # total_invested: u64 (8 bytes) - position 34
            # days_held: u64 (8 bytes) - position 42  
            # base_fee_percent: u8 (1 byte) - position 50
            # slot_discount: u8 (1 byte) - position 51
            # final_fee_percent: u8 (1 byte) - position 52
            # padding: 3 bytes
            # return_amount: u64 (8 bytes) - position 56
            # sold_at: i64 (8 bytes) - position 64
            # Total: 72 bytes minimum
            
            if len(data) < 40:  # Need at least player + slot_index + business_type + total_invested
                self.logger.debug("Insufficient data for BusinessSoldFromSlot real-time", data_len=len(data))
                return None
                
            # Unpack the event data based on actual transaction structure
            player_bytes = data[0:32]
            slot_index = struct.unpack('<B', data[32:33])[0]
            business_type = struct.unpack('<B', data[33:34])[0]
            
            # Extract total_invested from position 34 (confirmed from transaction analysis)
            total_invested = struct.unpack('<Q', data[34:42])[0] if len(data) >= 42 else 0
            
            # Extract other fields if available
            days_held = struct.unpack('<Q', data[44:52])[0] if len(data) >= 52 else 0
            base_fee_percent = struct.unpack('<B', data[52:53])[0] if len(data) >= 53 else 25
            slot_discount = struct.unpack('<B', data[53:54])[0] if len(data) >= 54 else 0
            return_amount = 0  # Will extract from correct position
            sold_at = int(block_time.timestamp()) if block_time else 0
            
            # Extract return_amount from position 53 as u32 (confirmed from actual data)
            if len(data) >= 57:  # Need at least 57 bytes for return_amount at position 53
                try:
                    return_amount = struct.unpack('<I', data[53:57])[0]
                except:
                    # Fallback to scan if exact position fails
                    for test_pos in range(50, min(len(data)-4, 60), 1):
                        try:
                            test_amount = struct.unpack('<I', data[test_pos:test_pos+4])[0]
                            # Look for reasonable return amount less than total_invested
                            if 0 < test_amount < total_invested:
                                return_amount = test_amount
                                break
                        except:
                            continue
            
            # If still no return_amount found, use total_invested as last resort
            if return_amount == 0:
                return_amount = total_invested
            
            # Convert player bytes to pubkey string
            player_pubkey = base58.b58encode(player_bytes).decode('ascii')
            
            # Calculate final fee percent
            final_fee_percent = max(0, base_fee_percent - slot_discount)
            
            event_data = {
                "business_id": f"business_{slot}_{slot_index}",  # Generate business_id
                "player": player_pubkey,
                "seller": player_pubkey,  # For compatibility
                "slot_index": slot_index,
                "business_type": business_type,
                "total_invested": total_invested,
                "days_held": days_held,
                "base_fee_percent": base_fee_percent,
                "slot_discount": slot_discount, 
                "final_fee_percent": final_fee_percent,
                "return_amount": return_amount,
                "sale_price": return_amount,  # For handler compatibility
                "sold_at": sold_at,
            }
            
            self.logger.info(
                "Parsed BusinessSoldFromSlot event real-time",
                player=player_pubkey,
                slot_index=slot_index,
                business_type=business_type,
                total_invested=total_invested,
                days_held=days_held,
                return_amount=return_amount
            )
            
            return ParsedEvent(
                event_type=EventType.BUSINESS_SOLD_FROM_SLOT,
                signature=signature,
                slot=slot,
                block_time=block_time,
                data=event_data,
                raw_data={"discriminator": discriminator.hex(), "data": data.hex()}
            )
            
        except Exception as e:
            self.logger.debug("Failed to parse BusinessSoldFromSlot in real-time", error=str(e))
            return None
            
    def get_event_parser_by_type(self, event_type: EventType):
        """Get the appropriate parser function for an event type."""
        parsers = {
            EventType.PLAYER_CREATED: self.parse_player_created_event,
            EventType.BUSINESS_CREATED: self.parse_business_created_event,
            EventType.BUSINESS_CREATED_IN_SLOT: self.parse_business_created_event,
            EventType.BUSINESS_UPGRADED: self.parse_business_upgraded_event,
            EventType.BUSINESS_UPGRADED_IN_SLOT: self.parse_business_upgraded_event,
            EventType.BUSINESS_SOLD: self.parse_business_sold_event,
            EventType.BUSINESS_SOLD_FROM_SLOT: self.parse_business_sold_event,
            EventType.EARNINGS_UPDATED: self.parse_earnings_updated_event,
            EventType.EARNINGS_CLAIMED: self.parse_earnings_claimed_event,
            EventType.SLOT_UNLOCKED: self.parse_slot_event,
            EventType.PREMIUM_SLOT_PURCHASED: self.parse_slot_event,
        }
        return parsers.get(event_type)


# Global parser instance
_parser: Optional[EventParser] = None


def get_event_parser() -> EventParser:
    """Get or create a global event parser instance."""
    global _parser
    if _parser is None:
        _parser = EventParser()
    return _parser