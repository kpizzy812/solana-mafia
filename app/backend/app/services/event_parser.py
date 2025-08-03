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
    BUSINESS_UPGRADED = "BusinessUpgraded" 
    BUSINESS_SOLD = "BusinessSold"
    EARNINGS_UPDATED = "EarningsUpdated"
    EARNINGS_CLAIMED = "EarningsClaimed"
    BUSINESS_NFT_MINTED = "BusinessNFTMinted"
    BUSINESS_NFT_BURNED = "BusinessNFTBurned"
    BUSINESS_NFT_UPGRADED = "BusinessNFTUpgraded"
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
    nft_mint: str
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
    nft_mint: str
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
    nft_mint: str
    block_time: datetime
    signature: str


@dataclass
class EarningsUpdatedEvent:
    """Earnings updated event data."""
    wallet: str
    earnings_amount: int
    total_earnings: int
    last_update: datetime
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
class BusinessNFTEvent:
    """Business NFT event data (minted/burned/upgraded)."""
    nft_mint: str
    business_id: str
    owner: str
    business_type: int
    level: int
    metadata_uri: Optional[str]
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
            
    def _parse_events_from_logs(self, tx_info: TransactionInfo) -> List[ParsedEvent]:
        """Parse events from transaction logs."""
        events = []
        
        for log_line in tx_info.logs:
            if "Program log:" not in log_line:
                continue
                
            try:
                log_content = log_line.split("Program log:", 1)[1].strip()
                
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
                nft_mint=data["nft_mint"],
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
                nft_mint=data["nft_mint"],
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
                nft_mint=data["nft_mint"],
                block_time=event.block_time or datetime.utcnow(),
                signature=event.signature
            )
        except KeyError as e:
            raise ValidationError(f"Missing field in BusinessSold event: {e}")
            
    def parse_earnings_updated_event(self, event: ParsedEvent) -> EarningsUpdatedEvent:
        """Parse an EarningsUpdated event."""
        try:
            data = event.data
            return EarningsUpdatedEvent(
                wallet=data["wallet"],
                earnings_amount=data["earnings_amount"],
                total_earnings=data["total_earnings"],
                last_update=datetime.fromtimestamp(data["last_update"]) if "last_update" in data else event.block_time,
                block_time=event.block_time or datetime.utcnow(),
                signature=event.signature
            )
        except KeyError as e:
            raise ValidationError(f"Missing field in EarningsUpdated event: {e}")
            
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
            
    def parse_business_nft_event(self, event: ParsedEvent) -> BusinessNFTEvent:
        """Parse a BusinessNFT event (minted/burned/upgraded)."""
        try:
            data = event.data
            return BusinessNFTEvent(
                nft_mint=data["nft_mint"],
                business_id=data["business_id"],
                owner=data["owner"],
                business_type=data["business_type"],
                level=data["level"],
                metadata_uri=data.get("metadata_uri"),
                block_time=event.block_time or datetime.utcnow(),
                signature=event.signature
            )
        except KeyError as e:
            raise ValidationError(f"Missing field in BusinessNFT event: {e}")
            
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
                required_fields = ["business_id", "owner", "business_type", "nft_mint"]
            elif event.event_type == EventType.BUSINESS_UPGRADED:
                required_fields = ["business_id", "owner", "old_level", "new_level"]
            elif event.event_type == EventType.BUSINESS_SOLD:
                required_fields = ["business_id", "seller", "sale_price"]
            elif event.event_type == EventType.EARNINGS_UPDATED:
                required_fields = ["wallet", "earnings_amount"]
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
            
    def get_event_parser_by_type(self, event_type: EventType):
        """Get the appropriate parser function for an event type."""
        parsers = {
            EventType.PLAYER_CREATED: self.parse_player_created_event,
            EventType.BUSINESS_CREATED: self.parse_business_created_event,
            EventType.BUSINESS_UPGRADED: self.parse_business_upgraded_event,
            EventType.BUSINESS_SOLD: self.parse_business_sold_event,
            EventType.EARNINGS_UPDATED: self.parse_earnings_updated_event,
            EventType.EARNINGS_CLAIMED: self.parse_earnings_claimed_event,
            EventType.BUSINESS_NFT_MINTED: self.parse_business_nft_event,
            EventType.BUSINESS_NFT_BURNED: self.parse_business_nft_event,
            EventType.BUSINESS_NFT_UPGRADED: self.parse_business_nft_event,
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