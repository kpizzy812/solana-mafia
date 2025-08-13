"""
🔗 Реальный парсер данных блокчейна для earnings

Заменяет mock парсер на реальное чтение данных Anchor аккаунтов
"""

import struct
from datetime import datetime, timezone
from solders.pubkey import Pubkey

from app.services.earnings.core.types import PlayerAccountData


class RealDataParser:
    """
    Парсер реальных данных Player аккаунтов из блокчейна.
    
    Структура PlayerCompact аккаунта (из Rust):
    - discriminator: [u8; 8] 
    - pending_earnings: u64
    - next_earnings_time: u32  
    - last_auto_update: u32
    - businesses_slots: [BusinessSlotCompact; 15]
    - ... другие поля
    """
    
    def parse_player_account_data(self, wallet: str, pda: Pubkey, data: bytes) -> PlayerAccountData:
        """Парсит реальные данные Player аккаунта из блокчейна."""
        try:
            if len(data) < 1400:  # PlayerCompact минимум ~1350+ байт
                raise ValueError(f"Account data too small: {len(data)} bytes")
            
            # Правильные offset'ы для структуры PlayerCompact:
            # 1. discriminator (8 bytes)
            # 2. owner: Pubkey (32 bytes)  
            # 3. business_slots: [BusinessSlotCompact; 15] (15 * 83 = 1245 bytes)
            # 4. unlocked_slots_count: u8 (1 byte)
            # 5. premium_slots_count: u8 (1 byte)
            # 6. flags: u32 (4 bytes)
            # 7. total_invested: u64 (8 bytes)
            # 8. total_upgrade_spent: u64 (8 bytes)
            # 9. total_slot_spent: u64 (8 bytes)
            # 10. total_earned: u64 (8 bytes)
            # 11. pending_earnings: u64 (8 bytes) ← ЭТО НАМ НУЖНО
            
            pending_earnings_offset = 8 + 32 + 1245 + 1 + 1 + 4 + 8 + 8 + 8 + 8  # = 1323
            next_earnings_offset = pending_earnings_offset + 8 + 4  # +pending_earnings, +created_at = 1335
            last_auto_update_offset = next_earnings_offset + 4 + 4 + 4  # +next_earnings_time, +earnings_interval, +first_business_time = 1347
            
            # Читаем основные поля (little-endian)
            pending_earnings = struct.unpack('<Q', data[pending_earnings_offset:pending_earnings_offset+8])[0]
            next_earnings_time = struct.unpack('<I', data[next_earnings_offset:next_earnings_offset+4])[0]
            last_auto_update = struct.unpack('<I', data[last_auto_update_offset:last_auto_update_offset+4])[0]
            
            # Проверка пределов PostgreSQL BIGINT (max = 9,223,372,036,854,775,807)
            MAX_BIGINT = 9_223_372_036_854_775_807
            if pending_earnings > MAX_BIGINT:
                print(f"⚠️ Warning: pending_earnings {pending_earnings} exceeds PostgreSQL BIGINT, capping to {MAX_BIGINT}")
                pending_earnings = MAX_BIGINT
            
            # Подсчет бизнесов (упрощенно - проверяем слоты)
            businesses_count = 0
            try:
                # Каждый слот BusinessSlotCompact = 4 байта
                # 15 слотов = 60 байт
                if offset + 60 <= len(data):
                    slots_data = data[offset:offset+60]
                    # Подсчитываем непустые слоты (упрощенная логика)
                    for i in range(0, 60, 4):
                        slot_value = struct.unpack('<I', slots_data[i:i+4])[0]
                        if slot_value > 0:  # Непустой слот
                            businesses_count += 1
            except:
                businesses_count = 1  # Default если не удалось прочитать
            
            # Определяем нужно ли обновление
            current_time = int(datetime.now(timezone.utc).timestamp())
            needs_update = next_earnings_time <= current_time
            
            return PlayerAccountData(
                wallet=wallet,
                pubkey=pda,
                pending_earnings=pending_earnings,
                next_earnings_time=next_earnings_time,
                last_auto_update=last_auto_update,
                businesses_count=businesses_count,
                needs_update=needs_update,
                raw_data=data
            )
            
        except Exception as e:
            # Fallback в случае ошибки парсинга
            print(f"⚠️ Error parsing real data for {wallet}: {e}")
            print(f"   Data size: {len(data)} bytes")
            
            # Возвращаем безопасные значения
            current_time = int(datetime.now(timezone.utc).timestamp())
            
            return PlayerAccountData(
                wallet=wallet,
                pubkey=pda,
                pending_earnings=0,
                next_earnings_time=current_time + 86400,  # Next day
                last_auto_update=current_time - 3600,     # 1 hour ago
                businesses_count=1,
                needs_update=False,  # Безопасно - не обновляем при ошибке
                raw_data=data
            )