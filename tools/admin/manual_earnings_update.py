#!/usr/bin/env python3
"""
Manual earnings update script for debugging and maintenance.
Updated for new blockchain-first architecture.
"""

import asyncio
import sys
from datetime import datetime

from app.core.database import get_async_session
from app.services.resilient_earnings_processor import get_resilient_earnings_processor
from app.services.transaction_service import get_transaction_service
from app.models.player import Player
from sqlalchemy import select, update


async def update_player_earnings(wallet: str):
    """Manually update earnings for a specific player using new architecture."""
    print(f"ultrathink: Обновляем доходы для игрока {wallet} (новая архитектура)")
    
    try:
        # Send permissionless blockchain transaction
        transaction_service = await get_transaction_service()
        result = await transaction_service.update_player_earnings_permissionless(wallet)
        
        if result.success:
            print(f"✅ Транзакция отправлена: {result.signature}")
            
            # Wait a bit for blockchain to process
            await asyncio.sleep(3)
            
            # Sync database with blockchain state
            processor = await get_resilient_earnings_processor()
            updated_states = await processor._get_all_player_states_batch([wallet])
            
            if wallet in updated_states:
                state = updated_states[wallet]
                async with get_async_session() as db:
                    await db.execute(
                        update(Player)
                        .where(Player.wallet == wallet)
                        .values(
                            pending_earnings=state.pending_earnings,
                            last_earnings_update=datetime.fromtimestamp(state.last_auto_update),
                            updated_at=datetime.utcnow()
                        )
                    )
                    await db.commit()
                
                print(f"✅ База данных синхронизирована с блокчейном")
            else:
                print(f"⚠️ Не удалось получить обновленное состояние из блокчейна")
                
        else:
            print(f"❌ Транзакция не удалась: {result.error}")
        
    except Exception as e:
        print(f"❌ Ошибка при обновлении: {e}")
        import traceback
        traceback.print_exc()


async def show_player_stats(wallet: str):
    """Show player statistics."""
    async with get_async_session() as db:
        # Get player info
        result = await db.execute(
            select(Player).where(Player.wallet == wallet)
        )
        player = result.scalar_one_or_none()
        
        if not player:
            print(f"❌ Игрок {wallet} не найден")
            return
            
        print(f"📊 Статистика игрока {wallet}:")
        print(f"   pending_earnings: {player.pending_earnings} ({player.pending_earnings/1e9:.9f} SOL)")
        print(f"   total_earned: {player.total_earned} ({player.total_earned/1e9:.9f} SOL)")
        print(f"   last_earnings_update: {player.last_earnings_update}")
        print(f"   next_earnings_time: {player.next_earnings_time}")
        print(f"   daily_earnings_estimate: {player.daily_earnings_estimate} ({player.daily_earnings_estimate/1e9:.9f} SOL)")
        
        # Get businesses
        from app.models.business import Business
        business_result = await db.execute(
            select(Business).where(
                Business.player_wallet == wallet,
                Business.is_active == True
            )
        )
        businesses = business_result.scalars().all()
        
        print(f"   активных бизнесов: {len(businesses)}")
        total_daily_rate = sum(b.daily_rate for b in businesses)
        print(f"   общая дневная доходность: {total_daily_rate} ({total_daily_rate/1e9:.9f} SOL)")


async def trigger_full_earnings_process():
    """Trigger full earnings process for all players."""
    print(f"ultrathink: Запускаем полное начисление доходов для всех игроков")
    
    try:
        processor = await get_resilient_earnings_processor()
        stats = await processor.run_daily_earnings_process()
        
        print(f"✅ Процесс завершен:")
        print(f"   Найдено игроков: {stats.total_players_found}")
        print(f"   Нуждались в обновлении: {stats.players_needing_update}")
        print(f"   Успешно обновлено: {stats.successful_updates}")
        print(f"   Ошибок: {stats.failed_updates}")
        print(f"   Время обработки: {stats.total_processing_time:.2f}s")
        print(f"   Успешность: {stats.success_rate * 100:.1f}%")
                
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()


async def main():
    """Main function."""
    if len(sys.argv) < 2:
        print("Использование:")
        print("  python manual_earnings_update.py <wallet> [action]")
        print("")
        print("Действия:")
        print("  update - обновить доходы (по умолчанию)")  
        print("  stats - показать статистику")
        print("  fix-schedule - исправить расписание")
        print("")
        print("Пример:")
        print("  python manual_earnings_update.py DfDkPhcm93C4JyXVRdz8M9B7cP8aeZKS9DNxS5cTxEmE update")
        return
        
    wallet = sys.argv[1]
    action = sys.argv[2] if len(sys.argv) > 2 else "update"
    
    if action == "stats":
        await show_player_stats(wallet)
    elif action == "fix-schedule":
        await trigger_full_earnings_process()
    elif action == "update":
        await show_player_stats(wallet)
        print("\n" + "="*50)
        await update_player_earnings(wallet)
        print("="*50)
        await show_player_stats(wallet)
    else:
        print(f"❌ Неизвестное действие: {action}")


if __name__ == "__main__":
    asyncio.run(main())