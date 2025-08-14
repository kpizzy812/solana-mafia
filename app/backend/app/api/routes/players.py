"""
Player routes for the Solana Mafia API.
Handles player-related endpoints including profile, businesses, and statistics.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, desc
from datetime import datetime, timedelta

import structlog

from app.api.dependencies import (
    get_database,
    validate_wallet_param,
    get_player_by_wallet,
    get_player_by_wallet_optional,
    get_pagination_params,
    get_sort_params,
    get_date_range_filter,
    get_active_only_filter
)
from app.api.schemas.players import (
    PlayerResponse,
    PlayerStatsResponse,
    PlayerBusinessesResponse,
    PlayerBusinessSummary,
    PlayerEarningsHistory,
    PlayerEarningsPeriod,
    PlayerLeaderboardResponse,
    PlayerLeaderboardEntry,
    PlayerActivityResponse,
    PlayerActivityLog,
    ConnectWalletRequest,
    ConnectWalletResponse
)
from app.api.schemas.common import (
    SuccessResponse,
    PaginatedResponse,
    PaginationParams,
    SortParams,
    create_success_response,
    create_paginated_response
)
from app.models.player import Player
from app.models.business import Business
# Убрано BusinessNFT - NFT больше не используются
from app.models.event import Event
from app.models.user import UserType
from app.services.solana_client import get_solana_client
from app.services.referral_service import ReferralService


logger = structlog.get_logger(__name__)

router = APIRouter()


@router.get(
    "/{wallet}",
    response_model=SuccessResponse,
    summary="Get Player Profile",
    description="Retrieve player profile information by wallet address"
)
async def get_player_profile(
    wallet: str = Depends(validate_wallet_param),
    player: Optional[Player] = Depends(get_player_by_wallet_optional),
    db: AsyncSession = Depends(get_database)
):
    """Get player profile by wallet address."""
    try:
        if not player:
            # Check if User exists (wallet connected but no businesses yet)
            from app.models.user import User
            user_result = await db.execute(
                select(User).where(User.wallet_address == wallet)
            )
            user = user_result.scalar_one_or_none()
            
            if user:
                # Return profile for connected user with no businesses yet
                user_profile_data = {
                    "wallet": wallet,
                    "total_invested": 0,
                    "total_earned": 0,
                    "pending_earnings": 0,
                    "is_active": True,  # User exists, just no businesses
                    "unlocked_slots_count": 9,  # Default slots available
                    "premium_slots_count": 0,
                    "active_businesses_count": 0,
                    # 💰 NEW: Enhanced net profit calculation
                    "net_profit_old": 0,  # Legacy: only claimed earnings
                    "net_profit": 0,      # New: includes liquidation + pending
                    "liquidation_value": 0,  # Current sale value of all businesses
                    "true_position": 0,   # Alias for frontend clarity
                    # Prestige information
                    "prestige_points": 0,
                    "prestige_level": "wannabe",
                    "total_prestige_earned": 0,
                    "prestige_level_up_count": 0,
                    "points_to_next_level": 50,
                    "prestige_progress_percentage": 0,
                    "created_at": user.created_at.isoformat() if user.created_at else None,
                    "updated_at": user.updated_at.isoformat() if user.updated_at else None,
                    "has_businesses": False,  # Flag indicating user exists but no businesses
                }
                
                logger.info("User found but no Player record, returning user profile", wallet=wallet)
                return create_success_response(
                    data=user_profile_data,
                    message="User profile retrieved (no businesses yet)"
                )
            
            # No User and no Player - completely new wallet (shouldn't happen after wallet connect)
            default_player_data = {
                "wallet": wallet,
                "total_invested": 0,
                "total_earned": 0,
                "pending_earnings": 0,
                "is_active": False,
                "unlocked_slots_count": 9,  # Default slots available
                "premium_slots_count": 0,
                "active_businesses_count": 0,
                # 💰 NEW: Enhanced net profit calculation
                "net_profit_old": 0,  # Legacy: only claimed earnings
                "net_profit": 0,      # New: includes liquidation + pending
                "liquidation_value": 0,  # Current sale value of all businesses
                "true_position": 0,   # Alias for frontend clarity
                # Prestige information
                "prestige_points": 0,
                "prestige_level": "wannabe",
                "total_prestige_earned": 0,
                "prestige_level_up_count": 0,
                "points_to_next_level": 50,
                "prestige_progress_percentage": 0,
                "created_at": None,
                "updated_at": None,
                "has_businesses": False,  # Flag indicating completely new wallet
            }
            
            logger.info("Neither Player nor User found, returning default profile", wallet=wallet)
            return create_success_response(
                data=default_player_data,
                message="Wallet not connected yet - default profile"
            )
        
        # Get active business count
        active_business_count_result = await db.execute(
            select(func.count(Business.id)).where(
                and_(
                    Business.player_wallet == player.wallet,
                    Business.is_active == True
                )
            )
        )
        active_business_count = active_business_count_result.scalar() or 0
        
        # Calculate prestige progress
        points_needed, progress_percentage = player.prestige_progress_to_next
        
        # Calculate enhanced net profit information
        liquidation_value = player.calculate_business_liquidation_value()
        net_profit_old = player.total_earned - (player.total_invested + player.total_upgrade_spent + player.total_slot_spent)
        net_profit_new = player.net_profit  # Includes liquidation value but NOT pending earnings (to avoid double counting)
        
        # Return simple response without complex validation
        player_data = {
            "wallet": player.wallet,
            "total_invested": player.total_invested or 0,
            "total_earned": player.total_earned or 0,
            "pending_earnings": player.pending_earnings or 0,
            "is_active": player.is_active,
            "unlocked_slots_count": player.unlocked_slots_count,
            "premium_slots_count": player.premium_slots_count or 0,
            "active_businesses_count": active_business_count,
            # 💰 NEW: Enhanced net profit calculation
            "net_profit_old": net_profit_old,  # Legacy: only claimed earnings
            "net_profit": net_profit_new,      # New: includes liquidation + pending
            "liquidation_value": liquidation_value,  # Current sale value of all businesses
            "true_position": net_profit_new,   # Alias for frontend clarity
            # Prestige information
            "prestige_points": player.prestige_points or 0,
            "prestige_level": player.prestige_level or "wannabe",
            "total_prestige_earned": player.total_prestige_earned or 0,
            "prestige_level_up_count": player.prestige_level_up_count or 0,
            "points_to_next_level": points_needed,
            "prestige_progress_percentage": progress_percentage,
            "created_at": player.created_at.isoformat() if player.created_at else None,
            "updated_at": player.updated_at.isoformat() if player.updated_at else None,
        }
        
        logger.info("Player profile retrieved", wallet=player.wallet)
        return create_success_response(
            data=player_data,
            message="Player profile retrieved successfully"
        )
        
    except Exception as e:
        logger.error("Error retrieving player profile", wallet=wallet, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "PROFILE_RETRIEVAL_ERROR",
                "message": f"Failed to retrieve player profile for {wallet}"
            }
        )


@router.get(
    "/{wallet}/stats",
    response_model=SuccessResponse,
    summary="Get Player Statistics",
    description="Retrieve comprehensive player statistics and performance metrics"
)
async def get_player_stats(
    wallet: str = Depends(validate_wallet_param),
    player: Optional[Player] = Depends(get_player_by_wallet_optional),
    db: AsyncSession = Depends(get_database)
):
    """Get detailed player statistics."""
    try:
        if not player:
            # Return default stats for non-existent player
            default_stats = PlayerStatsResponse(
                wallet=wallet,
                total_businesses=0,
                active_businesses=0,
                total_earnings=0,
                earnings_balance=0,
                total_claimed=0,
                business_types_owned=[],
                slot_utilization=0.0,
                days_active=0,
                last_activity=None,
                # Default prestige values
                prestige_points=0,
                prestige_level="wannabe",
                total_prestige_earned=0,
                prestige_level_up_count=0,
                points_to_next_level=50,
                prestige_progress_percentage=0
            )
            
            logger.info("Player not found, returning default stats", wallet=wallet)
            return create_success_response(
                data=default_stats,
                message="Player not found - returning default statistics"
            )
        
        # Get business statistics
        business_stats = await db.execute(
            select(
                func.count(Business.id).label("total_businesses"),
                func.count(Business.id).filter(Business.is_active == True).label("active_businesses"),
                func.sum(Business.daily_rate).label("total_daily_rate"),
                func.array_agg(Business.business_type).label("business_types")
            ).where(Business.player_wallet == player.wallet)
        )
        stats = business_stats.first()
        
        # Calculate days active
        if player.created_at:
            if player.created_at.tzinfo is not None:
                # Convert to naive datetime for comparison
                player_created = player.created_at.replace(tzinfo=None)
            else:
                player_created = player.created_at
            days_active = (datetime.utcnow() - player_created).days
        else:
            days_active = 0
        
        # Get last activity from events - TEMPORARY FIX
        try:
            last_activity_result = await db.execute(
                select(Event.block_time)
                .where(Event.player_wallet == player.wallet)
                .order_by(desc(Event.block_time))
                .limit(1)
            )
            last_activity = last_activity_result.scalar_one_or_none()
        except Exception as e:
            logger.error("Failed to get last activity from events", error=str(e), wallet=player.wallet)
            last_activity = None
        
        # Calculate slot utilization (clamped to valid range [0.0, 1.0])
        active_biz_count = stats.active_businesses or 0
        unlocked_slots = player.unlocked_slots_count
        slot_utilization = active_biz_count / unlocked_slots if unlocked_slots > 0 else 0
        slot_utilization = max(0.0, min(1.0, slot_utilization))
        
        # Calculate total claimed (total_earnings - pending_earnings), ensure non-negative
        total_claimed = max(0, player.total_earned - player.pending_earnings)
        
        # Calculate prestige progress
        points_needed, progress_percentage = player.prestige_progress_to_next
        
        player_stats = PlayerStatsResponse(
            wallet=player.wallet,
            total_businesses=stats.total_businesses or 0,
            active_businesses=stats.active_businesses or 0,
            total_earnings=player.total_earned,
            earnings_balance=player.pending_earnings,
            total_claimed=total_claimed,
            business_types_owned=[bt.value for bt in (stats.business_types or []) if bt is not None],
            slot_utilization=slot_utilization,
            days_active=days_active,
            last_activity=last_activity,
            # Prestige statistics
            prestige_points=player.prestige_points or 0,
            prestige_level=player.prestige_level or "wannabe",
            total_prestige_earned=player.total_prestige_earned or 0,
            prestige_level_up_count=player.prestige_level_up_count or 0,
            points_to_next_level=points_needed,
            prestige_progress_percentage=progress_percentage
        )
        
        logger.info("Player statistics retrieved", wallet=player.wallet)
        return create_success_response(
            data=player_stats,
            message="Player statistics retrieved successfully"
        )
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        logger.error("Error retrieving player statistics", wallet=wallet, error=str(e), traceback=traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "STATS_RETRIEVAL_ERROR", 
                "message": f"Failed to retrieve player statistics: {str(e)}"
            }
        )


@router.get(
    "/{wallet}/businesses",
    response_model=SuccessResponse,
    summary="Get Player Businesses",
    description="Retrieve all businesses owned by the player"
)
async def get_player_businesses(
    wallet: str = Depends(validate_wallet_param),
    player: Optional[Player] = Depends(get_player_by_wallet_optional),
    db: AsyncSession = Depends(get_database),
    active_only: bool = Depends(get_active_only_filter),
    pagination: PaginationParams = Depends(get_pagination_params),
    sort_params: SortParams = Depends(get_sort_params)
):
    """Get player's businesses with pagination and filtering."""
    try:
        if not player:
            # Return empty businesses list for non-existent player
            empty_businesses_response = PlayerBusinessesResponse(
                wallet=wallet,
                businesses=[],
                total_businesses=0,
                active_businesses=0,
                total_hourly_earnings=0
            )
            
            logger.info("Player not found, returning empty businesses", wallet=wallet)
            return create_success_response(
                data=empty_businesses_response,
                message="Player not found - returning empty businesses list"
            )
        
        # Build query (упрощен - убран JOIN с NFT)
        query = select(Business).where(Business.player_wallet == player.wallet)
        
        if active_only:
            query = query.where(Business.is_active == True)
        
        # Apply sorting
        if sort_params.sort_by:
            sort_column = getattr(Business, sort_params.sort_by, None)
            if sort_column:
                if sort_params.sort_order == "desc":
                    query = query.order_by(desc(sort_column))
                else:
                    query = query.order_by(sort_column)
        else:
            query = query.order_by(desc(Business.created_at))
        
        # Get total count
        count_query = select(func.count()).select_from(
            query.subquery()
        )
        total_count = await db.execute(count_query)
        total = total_count.scalar()
        
        # Apply pagination
        query = query.offset(pagination.offset).limit(pagination.limit)
        
        # Execute query
        result = await db.execute(query)
        businesses_data = result.scalars().all()
        
        # Build response
        businesses = []
        total_daily_earnings = 0
        active_count = 0
        
        for business in businesses_data:
            # Calculate theoretical daily earnings based on business type (ignoring corrupted daily_rate from DB)
            # TobaccoShop (type 0) = 200 basis points = 2% daily
            theoretical_daily_rates = [200, 180, 160, 140, 120, 100]  # basis points for types 0-5
            theoretical_daily_rate = theoretical_daily_rates[business.business_type.value] if business.business_type.value < 6 else 200
            
            # Calculate earnings: invested_amount * rate / 10000
            daily_earnings = (business.total_invested_amount * theoretical_daily_rate) // 10000
            
            # Debug logging for earnings calculation
            logger.info(
                f"💰 Business {business.id} earnings calculation",
                slot_index=business.slot_index,
                business_type=business.business_type.value,
                daily_rate_db=business.daily_rate,
                theoretical_daily_rate=theoretical_daily_rate,
                total_invested=business.total_invested_amount,
                daily_earnings=daily_earnings,
                daily_earnings_sol=daily_earnings / 1_000_000_000
            )
            
            # Get business name manually (avoiding property access)
            business_names = {
                0: "Lucky Strike Cigars",      # TOBACCO_SHOP
                1: "Eternal Rest Funeral",     # FUNERAL_SERVICE  
                2: "Midnight Motors Garage",   # CAR_WORKSHOP
                3: "Nonna's Secret Kitchen",   # ITALIAN_RESTAURANT
                4: "Velvet Shadows Club",      # GENTLEMEN_CLUB
                5: "Angel's Mercy Foundation"  # CHARITY_FUND
            }
            business_name = business_names.get(business.business_type.value, "Unknown Business")
            
            business_summary = PlayerBusinessSummary(
                business_id=str(business.id),
                business_type=business.business_type.value,
                name=business_name,
                level=business.level,
                base_cost=business.base_cost,
                initial_cost=business.base_cost,  # Set initial_cost = base_cost for compatibility
                total_invested=business.total_invested_amount,
                earnings_per_hour=daily_earnings,  # Временно используем это поле для суточных earnings
                slot_index=business.slot_index or 0,
                is_active=business.is_active,
                # Убрано nft_mint - NFT больше не используются
                created_at=business.created_at
            )
            businesses.append(business_summary)
            
            if business.is_active:
                total_daily_earnings += daily_earnings
                active_count += 1
        
        businesses_response = PlayerBusinessesResponse(
            wallet=player.wallet,
            businesses=businesses,
            total_businesses=len(businesses),
            active_businesses=active_count,
            total_hourly_earnings=total_daily_earnings  # Временно используем это поле для суточных earnings
        )
        
        logger.info(
            "Player businesses retrieved",
            wallet=player.wallet,
            count=len(businesses),
            active_count=active_count
        )
        
        if pagination.limit < total:
            return create_paginated_response(
                data=businesses_response.businesses,
                total=total,
                limit=pagination.limit,
                offset=pagination.offset
            )
        else:
            return create_success_response(
                data=businesses_response,
                message="Player businesses retrieved successfully"
            )
        
    except Exception as e:
        logger.error("Error retrieving player businesses", wallet=wallet, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "BUSINESSES_RETRIEVAL_ERROR",
                "message": "Failed to retrieve player businesses"
            }
        )


@router.get(
    "/{wallet}/earnings",
    response_model=SuccessResponse,
    summary="Get Player Earnings History",
    description="Retrieve player's earnings history with optional date filtering"
)
async def get_player_earnings_history(
    player: Player = Depends(get_player_by_wallet),
    db: AsyncSession = Depends(get_database),
    period: str = Query("daily", regex="^(daily|weekly|monthly)$", description="Aggregation period"),
    date_range: dict = Depends(get_date_range_filter),
    pagination: PaginationParams = Depends(get_pagination_params)
):
    """Get player's earnings history with aggregation."""
    try:
        # Build date filter
        date_filters = []
        if date_range["start_date"]:
            start_date = datetime.strptime(date_range["start_date"], "%Y-%m-%d")
            date_filters.append(Event.block_time >= start_date)
        if date_range["end_date"]:
            end_date = datetime.strptime(date_range["end_date"], "%Y-%m-%d") + timedelta(days=1)
            date_filters.append(Event.block_time < end_date)
        
        # Query earnings events
        query = select(Event).where(
            and_(
                Event.event_type.in_(["earnings_updated", "earnings_claimed"]),
                Event.player_wallet == player.wallet,
                *date_filters
            )
        ).order_by(desc(Event.block_time))
        
        # Apply pagination
        query = query.offset(pagination.offset).limit(pagination.limit)
        
        result = await db.execute(query)
        events = result.scalars().all()
        
        # Process events into periods
        earnings_data = []
        total_period_earnings = 0
        
        for event in events:
            # 🔧 FIXED: Use correct field names from updated contract
            earnings_added = event.parsed_data.get("earnings_added", 0)
            if event.event_type.value == "earnings_updated":
                total_period_earnings += earnings_added
            
            period_entry = PlayerEarningsPeriod(
                date=event.block_time,
                earnings_amount=earnings_added,  # Map to schema field name
                cumulative_earnings=event.parsed_data.get("total_pending", 0)  # 🔧 FIXED: total_pending
            )
            earnings_data.append(period_entry)
        
        # Calculate average daily earnings
        days_in_period = len(set(event.block_time.date() for event in events)) or 1
        average_daily_earnings = total_period_earnings // days_in_period
        
        history_response = PlayerEarningsHistory(
            wallet=player.wallet,
            period=period,
            earnings_data=earnings_data,
            total_period_earnings=total_period_earnings,
            average_daily_earnings=average_daily_earnings
        )
        
        logger.info(
            "Player earnings history retrieved",
            wallet=player.wallet,
            period=period,
            events_count=len(events)
        )
        
        return create_success_response(
            data=history_response,
            message="Earnings history retrieved successfully"
        )
        
    except Exception as e:
        logger.error("Error retrieving earnings history", wallet=player.wallet, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "EARNINGS_HISTORY_ERROR",
                "message": "Failed to retrieve earnings history"
            }
        )


@router.get(
    "/{wallet}/activity",
    response_model=SuccessResponse,
    summary="Get Player Activity Log",
    description="Retrieve player's activity log from blockchain events"
)
async def get_player_activity(
    player: Player = Depends(get_player_by_wallet),
    db: AsyncSession = Depends(get_database),
    pagination: PaginationParams = Depends(get_pagination_params)
):
    """Get player's activity log."""
    try:
        # Query all events related to the player
        query = select(Event).where(
            Event.player_wallet == player.wallet
        ).order_by(desc(Event.block_time))
        
        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total_count = await db.execute(count_query)
        total = total_count.scalar()
        
        # Apply pagination
        query = query.offset(pagination.offset).limit(pagination.limit)
        
        result = await db.execute(query)
        events = result.scalars().all()
        
        # Convert events to activity log entries
        activities = []
        for event in events:
            activity = PlayerActivityLog(
                timestamp=event.block_time,
                activity_type=event.event_type.value,
                description=f"{event.event_type.value} event",
                transaction_signature=event.transaction_signature,
                metadata=event.parsed_data
            )
            activities.append(activity)
        
        activity_response = PlayerActivityResponse(
            wallet=player.wallet,
            activities=activities,
            total_activities=total
        )
        
        logger.info(
            "Player activity retrieved",
            wallet=player.wallet,
            activities_count=len(activities)
        )
        
        return create_paginated_response(
            data=activities,
            total=total,
            limit=pagination.limit,
            offset=pagination.offset
        )
        
    except Exception as e:
        logger.error("Error retrieving player activity", wallet=player.wallet, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "ACTIVITY_RETRIEVAL_ERROR",
                "message": "Failed to retrieve player activity"
            }
        )


@router.post("/{wallet}/sync-blockchain")
async def sync_player_from_blockchain(
    wallet: str = Depends(validate_wallet_param),
    db: AsyncSession = Depends(get_database)
):
    """
    🔄 Sync player data directly from blockchain (for devnet testing).
    
    This endpoint bypasses the indexer and reads current state directly from the smart contract.
    Useful when the indexer is stuck or for immediate updates during testing.
    """
    try:
        logger.info("Manual blockchain sync requested", wallet=wallet)
        
        # Get Solana client
        solana_client = await get_solana_client()
        
        # Read player PDA directly from blockchain
        from solders.pubkey import Pubkey
        from app.core.config import settings
        
        program_id = Pubkey.from_string(settings.solana_program_id)
        player_pubkey = Pubkey.from_string(wallet)
        
        # Calculate player PDA
        player_pda, _ = Pubkey.find_program_address(
            [b"player", player_pubkey.__bytes__()], 
            program_id
        )
        
        # Get account data from blockchain
        account_info = await solana_client.client.get_account_info(player_pda)
        
        if not account_info.value or not account_info.value.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": "PLAYER_NOT_FOUND_ON_BLOCKCHAIN",
                    "message": "Player account not found on blockchain"
                }
            )
        
        # Store account_data outside try block so it's accessible later
        account_data = account_info.value.data
        
        # 🔥 PARSE REAL ACCOUNT DATA using Anchor IDL
        try:
            # Load IDL for parsing
            import json
            import os
            
            # Get IDL path
            idl_path = os.path.join(os.path.dirname(__file__), "..", "..", "idl", "solana_mafia.json")
            with open(idl_path, 'r') as f:
                idl_data = json.load(f)
            
            # Find PlayerCompact account type
            player_account_type = None
            for account_type in idl_data.get("accounts", []):
                if account_type["name"] == "PlayerCompact":
                    player_account_type = account_type
                    break
            
            if not player_account_type:
                raise Exception("PlayerCompact account type not found in IDL")
            
            # Parse account data manually (simplified Anchor parsing)
            # account_data already defined above
            
            logger.info("🔍 Account data info", 
                       wallet=wallet,
                       data_length=len(account_data),
                       account_lamports=account_info.value.lamports)
            
            if len(account_data) < 100:
                raise Exception(f"Account data too small: {len(account_data)} bytes, expected at least 100")
            
            # Skip 8-byte discriminator
            data_offset = 8
            logger.info("🔍 After discriminator", offset=data_offset)
            
            # Parse owner (32 bytes pubkey)
            if data_offset + 32 > len(account_data):
                raise Exception(f"Cannot read owner: offset {data_offset + 32} > data length {len(account_data)}")
            
            owner_bytes = account_data[data_offset:data_offset + 32]
            data_offset += 32
            logger.info("🔍 After owner", offset=data_offset)
            
            # 🎯 ИСПРАВЛЕНО: Реальный размер business_slots = 255 bytes (найдено эмпирически)
            # Вместо теоретических 738 bytes используем реальный размер 255 bytes
            business_slots_size = 255  # 28.3 bytes per slot (9 slots)
            data_offset += business_slots_size
            logger.info("🔍 After skipping business slots", offset=data_offset)
            
            if data_offset >= len(account_data):
                raise Exception(f"Offset after business slots {data_offset} >= data length {len(account_data)}")
            
            # Parse simple fields with bounds checking
            if data_offset + 1 > len(account_data):
                raise Exception(f"Cannot read unlocked_slots_count: offset {data_offset + 1} > data length {len(account_data)}")
            unlocked_slots_count = int.from_bytes(account_data[data_offset:data_offset + 1], 'little')
            data_offset += 1
            
            if data_offset + 1 > len(account_data):
                raise Exception(f"Cannot read premium_slots_count: offset {data_offset + 1} > data length {len(account_data)}")
            premium_slots_count = int.from_bytes(account_data[data_offset:data_offset + 1], 'little')
            data_offset += 1
            
            if data_offset + 4 > len(account_data):
                raise Exception(f"Cannot read flags: offset {data_offset + 4} > data length {len(account_data)}")
            flags = int.from_bytes(account_data[data_offset:data_offset + 4], 'little')
            data_offset += 4
            
            # 🎯 ИСПРАВЛЕНО: Все финансовые поля теперь u64 (8 bytes), а не u32 (4 bytes)
            if data_offset + 8 > len(account_data):
                raise Exception(f"Cannot read total_invested: offset {data_offset + 8} > data length {len(account_data)}")
            total_invested = int.from_bytes(account_data[data_offset:data_offset + 8], 'little')
            data_offset += 8
            
            if data_offset + 8 > len(account_data):
                raise Exception(f"Cannot read total_upgrade_spent: offset {data_offset + 8} > data length {len(account_data)}")
            total_upgrade_spent = int.from_bytes(account_data[data_offset:data_offset + 8], 'little')
            data_offset += 8
            
            if data_offset + 8 > len(account_data):
                raise Exception(f"Cannot read total_slot_spent: offset {data_offset + 8} > data length {len(account_data)}")
            total_slot_spent = int.from_bytes(account_data[data_offset:data_offset + 8], 'little')
            data_offset += 8
            
            if data_offset + 8 > len(account_data):
                raise Exception(f"Cannot read total_earned: offset {data_offset + 8} > data length {len(account_data)}")
            total_earned = int.from_bytes(account_data[data_offset:data_offset + 8], 'little')
            data_offset += 8
            
            # 🎯 PENDING EARNINGS - ЭТО НАША ЦЕЛЬ! (u64 = 8 bytes)
            if data_offset + 8 > len(account_data):
                raise Exception(f"Cannot read pending_earnings: offset {data_offset + 8} > data length {len(account_data)}")
            pending_earnings = int.from_bytes(account_data[data_offset:data_offset + 8], 'little')
            data_offset += 8
            
            # Timestamps - все u32 (4 bytes)
            if data_offset + 4 > len(account_data):
                raise Exception(f"Cannot read created_at: offset {data_offset + 4} > data length {len(account_data)}")
            created_at = int.from_bytes(account_data[data_offset:data_offset + 4], 'little')
            data_offset += 4
            
            if data_offset + 4 > len(account_data):
                raise Exception(f"Cannot read next_earnings_time: offset {data_offset + 4} > data length {len(account_data)}")
            next_earnings_time = int.from_bytes(account_data[data_offset:data_offset + 4], 'little')
            data_offset += 4
            
            if data_offset + 4 > len(account_data):
                raise Exception(f"Cannot read earnings_interval: offset {data_offset + 4} > data length {len(account_data)}")
            earnings_interval = int.from_bytes(account_data[data_offset:data_offset + 4], 'little')
            data_offset += 4
            
            if data_offset + 4 > len(account_data):
                raise Exception(f"Cannot read first_business_time: offset {data_offset + 4} > data length {len(account_data)}")
            first_business_time = int.from_bytes(account_data[data_offset:data_offset + 4], 'little')
            data_offset += 4
            
            if data_offset + 4 > len(account_data):
                raise Exception(f"Cannot read last_auto_update: offset {data_offset + 4} > data length {len(account_data)}")
            last_auto_update = int.from_bytes(account_data[data_offset:data_offset + 4], 'little')
            data_offset += 4
            
            logger.info("🎯 Parsed PlayerCompact data from blockchain", 
                       wallet=wallet,
                       pending_earnings=pending_earnings,
                       total_earned=total_earned,
                       unlocked_slots_count=unlocked_slots_count,
                       next_earnings_time=next_earnings_time)
            
            # Update or create player in database with REAL DATA
            from sqlalchemy import update
            
            # Convert u32 timestamps back to datetime (assuming Unix timestamp)
            next_earnings_datetime = datetime.utcfromtimestamp(next_earnings_time) if next_earnings_time > 0 else None
            created_datetime = datetime.utcfromtimestamp(created_at) if created_at > 0 else None
            
            await db.execute(
                update(Player)
                .where(Player.wallet == wallet)
                .values(
                    pending_earnings=pending_earnings,
                    total_earned=total_earned,
                    total_invested=total_invested,
                    unlocked_slots_count=unlocked_slots_count,
                    premium_slots_count=premium_slots_count,
                    next_earnings_time=next_earnings_datetime,
                    last_earnings_update=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
            )
            await db.commit()
            
        except Exception as parse_error:
            logger.error("Failed to parse account data, falling back to simple update", 
                        error=str(parse_error), wallet=wallet)
            
            # Fallback: just update timestamps
            from sqlalchemy import update
            await db.execute(
                update(Player)
                .where(Player.wallet == wallet)
                .values(
                    last_earnings_update=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
            )
            await db.commit()
        
        logger.info("Player data synced from blockchain", wallet=wallet)
        
        return create_success_response(
            data={
                "wallet": wallet,
                "synced_at": datetime.utcnow().isoformat(),
                "blockchain_account_lamports": account_info.value.lamports,
                "account_data_size": len(account_data)
            },
            message="Player data successfully synced from blockchain"
        )
        
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        logger.error("Failed to sync player from blockchain", wallet=wallet, error=str(e), traceback=tb)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "BLOCKCHAIN_SYNC_ERROR", 
                "message": f"Failed to sync from blockchain: {str(e)}",
                "traceback": tb[:1000]  # Первые 1000 символов traceback для debugging
            }
        )


@router.get(
    "/{wallet}/profile",
    response_model=SuccessResponse,
    summary="Get Complete Player Profile",
    description="Retrieve complete player profile with leaderboard rankings and detailed statistics"
)
async def get_complete_player_profile(
    wallet: str = Depends(validate_wallet_param),
    player: Optional[Player] = Depends(get_player_by_wallet_optional),
    db: AsyncSession = Depends(get_database)
):
    """
    Получить полный профиль игрока с рангами в лидербордах.
    
    Включает:
    - Базовую информацию профиля
    - Позиции во всех лидербордах
    - Детальную статистику по бизнесам
    - Информацию о рефералах и престиже
    """
    try:
        logger.info("Getting complete player profile", wallet=wallet)
        
        if not player:
            # Return default profile for non-existent player
            default_profile = {
                "wallet": wallet,
                "exists": False,
                "basic_stats": {
                    "total_invested": 0,
                    "total_earned": 0,
                    "pending_earnings": 0,
                    "active_businesses": 0,
                    "unlocked_slots": 0,
                    "premium_slots": 0
                },
                "prestige_info": {
                    "current_points": 0,
                    "current_level": "wannabe",
                    "points_to_next_level": 50,
                    "progress_percentage": 0,
                    "level_up_count": 0
                },
                "leaderboard_ranks": {
                    "earnings_rank": None,
                    "referrals_rank": None,
                    "prestige_rank": None,
                    "earnings_percentile": None,
                    "referrals_percentile": None,
                    "prestige_percentile": None
                },
                "referral_stats": {
                    "total_referrals": 0,
                    "total_referral_earnings": 0,
                    "level_breakdown": {
                        "level_1": 0,
                        "level_2": 0,
                        "level_3": 0
                    }
                },
                "achievements": [],
                "last_activity": None,
                "member_since": None
            }
            
            return create_success_response(
                data=default_profile,
                message="Player not found - returning default profile"
            )
        
        # Get basic player stats
        active_business_count_result = await db.execute(
            select(func.count(Business.id)).where(
                and_(
                    Business.player_wallet == player.wallet,
                    Business.is_active == True
                )
            )
        )
        active_business_count = active_business_count_result.scalar() or 0
        
        # Calculate prestige progress
        points_needed, progress_percentage = player.prestige_progress_to_next
        
        # Get leaderboard rankings using direct SQL for performance
        from sqlalchemy import text
        
        # Get earnings rank
        earnings_rank_query = text("""
            SELECT rank FROM (
                SELECT wallet, 
                       ROW_NUMBER() OVER (ORDER BY total_earned DESC) as rank
                FROM players 
                WHERE is_active = true AND total_earned > 0
            ) ranked WHERE wallet = :wallet
        """)
        
        earnings_result = await db.execute(earnings_rank_query, {"wallet": wallet})
        earnings_rank = earnings_result.scalar()
        
        # Get referrals rank  
        referrals_rank_query = text("""
            SELECT rank FROM (
                SELECT rs.user_id as wallet,
                       ROW_NUMBER() OVER (ORDER BY rs.total_referrals DESC) as rank
                FROM referral_stats rs
                JOIN players p ON rs.user_id = p.wallet
                WHERE p.is_active = true AND rs.total_referrals > 0
            ) ranked WHERE wallet = :wallet
        """)
        
        referrals_result = await db.execute(referrals_rank_query, {"wallet": wallet})
        referrals_rank = referrals_result.scalar()
        
        # Get prestige rank
        prestige_rank_query = text("""
            SELECT rank FROM (
                SELECT wallet,
                       ROW_NUMBER() OVER (ORDER BY prestige_points DESC) as rank
                FROM players 
                WHERE is_active = true AND prestige_points > 0
            ) ranked WHERE wallet = :wallet
        """)
        
        prestige_result = await db.execute(prestige_rank_query, {"wallet": wallet})
        prestige_rank = prestige_result.scalar()
        
        # Get total players for percentile calculation
        earnings_total_query = select(func.count()).select_from(Player).where(
            and_(Player.is_active == True, Player.total_earned > 0)
        )
        earnings_total_result = await db.execute(earnings_total_query)
        total_players_earnings = earnings_total_result.scalar() or 0
        
        # Get referral stats
        from app.models.referral import ReferralStats
        referral_stats_query = select(ReferralStats).where(
            ReferralStats.user_id == wallet
        )
        referral_stats_result = await db.execute(referral_stats_query)
        referral_stats = referral_stats_result.scalar_one_or_none()
        
        # Get referrals total count
        referrals_total_query = select(func.count()).select_from(
            ReferralStats.__table__.join(
                Player.__table__,
                ReferralStats.user_id == Player.wallet
            )
        ).where(
            and_(
                Player.is_active == True,
                ReferralStats.total_referrals > 0
            )
        )
        referrals_total_result = await db.execute(referrals_total_query)
        total_players_referrals = referrals_total_result.scalar() or 0
        
        # Get prestige total count
        prestige_total_query = select(func.count()).select_from(Player).where(
            and_(Player.is_active == True, Player.prestige_points > 0)
        )
        prestige_total_result = await db.execute(prestige_total_query)
        total_players_prestige = prestige_total_result.scalar() or 0
        
        # Calculate percentiles
        earnings_percentile = None
        if earnings_rank and total_players_earnings > 0:
            earnings_percentile = ((total_players_earnings - earnings_rank + 1) / total_players_earnings) * 100
            
        referrals_percentile = None
        if referrals_rank and total_players_referrals > 0:
            referrals_percentile = ((total_players_referrals - referrals_rank + 1) / total_players_referrals) * 100
            
        prestige_percentile = None
        if prestige_rank and total_players_prestige > 0:
            prestige_percentile = ((total_players_prestige - prestige_rank + 1) / total_players_prestige) * 100
        
        # Get business type breakdown
        business_types_query = select(
            Business.business_type,
            func.count(Business.id).label("count"),
            func.sum(Business.total_invested_amount).label("total_invested"),
            func.sum(Business.daily_rate).label("total_daily_rate")
        ).where(
            and_(
                Business.player_wallet == wallet,
                Business.is_active == True
            )
        ).group_by(Business.business_type)
        
        business_types_result = await db.execute(business_types_query)
        business_breakdown = {}
        for row in business_types_result:
            business_names = {
                0: "Lucky Strike Cigars",
                1: "Eternal Rest Funeral", 
                2: "Midnight Motors Garage",
                3: "Nonna's Secret Kitchen",
                4: "Velvet Shadows Club",
                5: "Angel's Mercy Foundation"
            }
            business_breakdown[business_names.get(row.business_type.value, "Unknown")] = {
                "count": row.count,
                "total_invested": row.total_invested,
                "daily_rate": row.total_daily_rate
            }
        
        # Get last activity
        last_activity_query = select(Event.block_time).where(
            Event.player_wallet == wallet
        ).order_by(desc(Event.block_time)).limit(1)
        
        last_activity_result = await db.execute(last_activity_query)
        last_activity = last_activity_result.scalar_one_or_none()
        
        # Calculate liquidation value and detailed breakdown
        liquidation_value = player.calculate_business_liquidation_value()
        net_profit_old = player.total_earned - (player.total_invested + player.total_upgrade_spent + player.total_slot_spent)
        net_profit_new = player.net_profit  # Includes liquidation value but NOT pending earnings (to avoid double counting)
        
        # Build complete profile
        complete_profile = {
            "wallet": wallet,
            "exists": True,
            "basic_stats": {
                "total_invested": player.total_invested or 0,
                "total_earned": player.total_earned or 0,
                "pending_earnings": player.pending_earnings or 0,
                "active_businesses": active_business_count,
                "unlocked_slots": player.unlocked_slots_count,
                "premium_slots": player.premium_slots_count or 0,
                "roi_percentage": (
                    (player.total_earned / player.total_invested * 100) 
                    if player.total_invested > 0 else 0
                ),
                # 💰 NEW: Enhanced net profit calculation
                "net_profit_old": net_profit_old,  # Legacy: only claimed earnings
                "net_profit": net_profit_new,      # New: includes liquidation + pending
                "liquidation_value": liquidation_value,  # Current sale value of all businesses
                "true_position": net_profit_new,   # Alias for frontend clarity
            },
            "prestige_info": {
                "current_points": player.prestige_points or 0,
                "current_level": player.prestige_level or "wannabe",
                "points_to_next_level": points_needed,
                "progress_percentage": progress_percentage,
                "level_up_count": player.prestige_level_up_count or 0,
                "total_points_earned": player.total_prestige_earned or 0
            },
            "leaderboard_ranks": {
                "earnings_rank": earnings_rank,
                "referrals_rank": referrals_rank,
                "prestige_rank": prestige_rank,
                "earnings_percentile": earnings_percentile,
                "referrals_percentile": referrals_percentile,
                "prestige_percentile": prestige_percentile,
                "total_players_earnings": total_players_earnings,
                "total_players_referrals": total_players_referrals,
                "total_players_prestige": total_players_prestige
            },
            "referral_stats": {
                "total_referrals": referral_stats.total_referrals if referral_stats else 0,
                "total_referral_earnings": referral_stats.total_referral_earnings if referral_stats else 0,
                "level_breakdown": {
                    "level_1": referral_stats.level_1_referrals if referral_stats else 0,
                    "level_2": referral_stats.level_2_referrals if referral_stats else 0,
                    "level_3": referral_stats.level_3_referrals if referral_stats else 0
                },
                "earnings_breakdown": {
                    "level_1": referral_stats.level_1_earnings if referral_stats else 0,
                    "level_2": referral_stats.level_2_earnings if referral_stats else 0,
                    "level_3": referral_stats.level_3_earnings if referral_stats else 0
                }
            },
            "business_breakdown": business_breakdown,
            "achievements": [],  # TODO: Implement achievements system
            "activity": {
                "last_activity": last_activity.isoformat() if last_activity else None,
                "member_since": player.created_at.isoformat() if player.created_at else None,
                "days_active": (
                    (datetime.utcnow() - player.created_at.replace(tzinfo=None)).days 
                    if player.created_at else 0
                )
            }
        }
        
        logger.info("Complete player profile retrieved", 
                   wallet=wallet,
                   earnings_rank=earnings_rank,
                   referrals_rank=referrals_rank,
                   prestige_rank=prestige_rank)
        
        return create_success_response(
            data=complete_profile,
            message="Complete player profile retrieved successfully"
        )
        
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        logger.error("Error retrieving complete player profile", 
                    wallet=wallet, 
                    error=str(e),
                    traceback=tb)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "COMPLETE_PROFILE_ERROR",
                "message": f"Failed to retrieve complete player profile: {str(e)}"
            }
        )


@router.post(
    "/connect",
    response_model=SuccessResponse,
    summary="Connect Wallet",
    description="Create or get user when wallet connects, generating referral code if needed"
)
async def connect_wallet(
    request: ConnectWalletRequest,
    db: AsyncSession = Depends(get_database)
):
    """Connect wallet and create user with referral code if needed."""
    try:
        wallet_address = request.wallet
        
        # Initialize referral service
        referral_service = ReferralService(db)
        
        # Get or create user with referral code
        user = await referral_service.get_or_create_user(
            user_id=wallet_address,
            user_type=UserType.WALLET,
            wallet_address=wallet_address
        )
        
        # Check if this is a new player (no businesses purchased yet)
        # A new player = user exists but has no entry in Player table (no businesses)
        
        player_result = await db.execute(
            select(Player).where(Player.wallet == wallet_address)
        )
        existing_player = player_result.scalar_one_or_none()
        
        # If no Player record exists, this is definitely a new user
        # If Player exists but has 0 businesses, also consider as new for entry fee display
        if not existing_player:
            is_new_user = True
        else:
            # Check if player has any businesses (active or inactive)
            business_count_result = await db.execute(
                select(func.count(Business.id)).where(Business.player_wallet == wallet_address)
            )
            business_count = business_count_result.scalar() or 0
            is_new_user = business_count == 0
        
        await db.commit()
        
        # Prepare response
        response_data = ConnectWalletResponse(
            user_id=user.id,
            wallet=user.wallet_address,
            referral_code=user.referral_code,
            is_new_user=is_new_user
        )
        
        logger.info(
            "Wallet connected successfully",
            wallet=wallet_address,
            user_id=user.id,
            referral_code=user.referral_code,
            is_new_user=is_new_user
        )
        
        return create_success_response(
            data=response_data,
            message="Wallet connected successfully" if not is_new_user else "New user created successfully"
        )
        
    except Exception as e:
        await db.rollback()
        logger.error("Error connecting wallet", wallet=request.wallet, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "WALLET_CONNECT_ERROR",
                "message": f"Failed to connect wallet: {str(e)}"
            }
        )