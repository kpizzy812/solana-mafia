// state/player.rs - ULTRA-OPTIMIZED СТРУКТУРА
use anchor_lang::prelude::*;
use crate::constants::*;
use crate::state::business::Business;
use crate::error::SolanaMafiaError;

/// 🚀 ULTRA-OPTIMIZED: Битовые флаги для слотов
#[derive(AnchorSerialize, AnchorDeserialize, Clone, Copy, Debug)]
pub struct BusinessSlotCompact {
    /// Упакованные флаги (32 бита):
    /// - Биты 0-1: SlotType (0=Basic, 1=Premium, 2=VIP, 3=Legendary)
    /// - Бит 2: is_unlocked (ВСЕГДА true в новой системе)
    /// - Бит 3: has_business
    /// - Бит 4: is_paid (оплачен ли слот)
    /// - Биты 5-31: зарезервировано
    pub flags: u32,
    
    /// Бизнес в слоте (если есть)
    pub business: Option<Business>,
    
    /// Стоимость слота при первой оплате (u64 - Legendary slot = 5 SOL > u32 limit)  
    pub slot_cost_paid: u64,
}

impl BusinessSlotCompact {
    pub const SIZE: usize = 
        4 +  // flags (u32)
        1 + Business::SIZE + // business Option<Business>
        8;   // slot_cost_paid (u64) ← УВЕЛИЧЕНО для Legendary slot

    // Битовые маски
    const SLOT_TYPE_MASK: u32 = 0x03;      // Биты 0-1
    const UNLOCKED_FLAG: u32 = 0x04;       // Бит 2 (всегда true)
    const HAS_BUSINESS_FLAG: u32 = 0x08;   // Бит 3
    const IS_PAID_FLAG: u32 = 0x10;        // Бит 4

    /// Создать новый базовый бесплатный слот (0-2)
    pub fn new_basic_free() -> Self {
        Self {
            flags: Self::UNLOCKED_FLAG | Self::IS_PAID_FLAG, // unlocked + paid = true
            business: None,
            slot_cost_paid: 0,
        }
    }

    /// Создать новый базовый платный слот (3-5)
    pub fn new_basic_paid() -> Self {
        Self {
            flags: Self::UNLOCKED_FLAG, // unlocked = true, paid = false
            business: None,
            slot_cost_paid: 0,
        }
    }

    /// Создать премиум слот (6-8) - неоплаченный
    pub fn new_premium_unpaid(slot_type: SlotType) -> Self {
        let slot_type_bits = match slot_type {
            SlotType::Basic => 0,
            SlotType::Premium => 1,
            SlotType::VIP => 2,
            SlotType::Legendary => 3,
        };
        
        Self {
            flags: slot_type_bits | Self::UNLOCKED_FLAG, // unlocked = true, paid = false
            business: None,
            slot_cost_paid: 0,
        }
    }

    /// Создать премиум слот оплаченный (только для совместимости)
    pub fn new_premium(slot_type: SlotType, cost: u64) -> Self {
        let slot_type_bits = match slot_type {
            SlotType::Basic => 0,
            SlotType::Premium => 1,
            SlotType::VIP => 2,
            SlotType::Legendary => 3,
        };
        
        Self {
            flags: slot_type_bits | Self::UNLOCKED_FLAG | Self::IS_PAID_FLAG,
            business: None,
            slot_cost_paid: cost,
        }
    }

    // Геттеры
    pub fn slot_type(&self) -> SlotType {
        match self.flags & Self::SLOT_TYPE_MASK {
            0 => SlotType::Basic,
            1 => SlotType::Premium,
            2 => SlotType::VIP,
            3 => SlotType::Legendary,
            _ => SlotType::Basic, // fallback
        }
    }

    pub fn is_unlocked(&self) -> bool {
        (self.flags & Self::UNLOCKED_FLAG) != 0
    }

    pub fn has_business(&self) -> bool {
        (self.flags & Self::HAS_BUSINESS_FLAG) != 0
    }

    pub fn is_paid(&self) -> bool {
        (self.flags & Self::IS_PAID_FLAG) != 0
    }

    // Сеттеры
    pub fn set_unlocked(&mut self, unlocked: bool) {
        if unlocked {
            self.flags |= Self::UNLOCKED_FLAG;
        } else {
            self.flags &= !Self::UNLOCKED_FLAG;
        }
    }

    pub fn set_has_business(&mut self, has_business: bool) {
        if has_business {
            self.flags |= Self::HAS_BUSINESS_FLAG;
        } else {
            self.flags &= !Self::HAS_BUSINESS_FLAG;
        }
    }

    pub fn set_paid(&mut self, paid: bool) {
        if paid {
            self.flags |= Self::IS_PAID_FLAG;
        } else {
            self.flags &= !Self::IS_PAID_FLAG;
        }
    }

    /// Оплатить слот при первом использовании
    pub fn pay_slot(&mut self, cost: u64) -> Result<()> {
        if self.is_paid() {
            return Err(SolanaMafiaError::SlotAlreadyPaid.into());
        }
        
        self.set_paid(true);
        self.slot_cost_paid = cost;
        Ok(())
    }
    
    /// Получить стоимость слота для первой оплаты
    pub fn get_slot_cost(&self, business_price: u64) -> u64 {
        match self.slot_type() {
            SlotType::Basic => {
                // Слоты 0-2 бесплатные, слоты 3-5 = 10% от цены бизнеса
                if self.is_paid() {
                    0 // Уже оплачен
                } else {
                    business_price * 10 / 100 // 10%
                }
            },
            SlotType::Premium => if self.is_paid() { 0 } else { PREMIUM_SLOT_COSTS[0] },
            SlotType::VIP => if self.is_paid() { 0 } else { PREMIUM_SLOT_COSTS[1] },
            SlotType::Legendary => if self.is_paid() { 0 } else { PREMIUM_SLOT_COSTS[2] },
        }
    }

    /// Поместить бизнес в слот (слоты всегда разблокированы в новой системе)
    pub fn place_business(&mut self, business: Business) -> Result<()> {
        if self.has_business() {
            return Err(SolanaMafiaError::SlotOccupied.into());
        }
        
        self.business = Some(business);
        self.set_has_business(true);
        Ok(())
    }

    /// Удалить бизнес из слота
    pub fn remove_business(&mut self) -> Option<Business> {
        let business = self.business.take();
        self.set_has_business(false);
        business
    }

    /// Получить бонус доходности слота
    pub fn get_yield_bonus(&self) -> u16 {
        match self.slot_type() {
            SlotType::Basic => 0,
            SlotType::Premium => PREMIUM_SLOT_YIELD_BONUSES[0],  // +1.5%
            SlotType::VIP => PREMIUM_SLOT_YIELD_BONUSES[1],      // +3%
            SlotType::Legendary => PREMIUM_SLOT_YIELD_BONUSES[2], // +5%
        }
    }

    /// Получить скидку на комиссию продажи
    pub fn get_sell_fee_discount(&self) -> u8 {
        match self.slot_type() {
            SlotType::Basic => 0,
            SlotType::Premium => PREMIUM_SLOT_SELL_FEE_DISCOUNTS[0],  // 0%
            SlotType::VIP => PREMIUM_SLOT_SELL_FEE_DISCOUNTS[1],      // -50%
            SlotType::Legendary => PREMIUM_SLOT_SELL_FEE_DISCOUNTS[2], // -100%
        }
    }

    /// Рассчитать доходность с учетом бонуса слота
    pub fn calculate_earnings(&self, base_earnings: u64) -> u64 {
        if let Some(_business) = &self.business {
            let slot_bonus = self.get_yield_bonus();
            let bonus_earnings = (base_earnings as u128 * slot_bonus as u128) / 10000;
            base_earnings + bonus_earnings as u64
        } else {
            0
        }
    }
}

/// 🚀 ULTRA-OPTIMIZED Player структура
#[account]
pub struct PlayerCompact {
    pub owner: Pubkey,
    
    /// 🆕 ФИКСИРОВАННЫЙ МАССИВ вместо Vec - экономия 24 байта overhead!
    pub business_slots: [BusinessSlotCompact; MAX_REGULAR_SLOTS as usize],
    
    /// 🆕 УПАКОВАННЫЕ СЧЕТЧИКИ (u8 вместо отдельных полей)
    pub unlocked_slots_count: u8,
    pub premium_slots_count: u8,
    
    /// 🆕 УПАКОВАННЫЕ ФЛАГИ В ОДИН u32:
    /// - Бит 0: has_paid_entry
    /// - Биты 1-31: зарезервированы для будущих флагов
    pub flags: u32,
    
    /// 🚨 ИСПРАВЛЕНО: Критические поля u64 для больших сумм, остальные u32
    pub total_invested: u64,        // u64 - может быть > 4.29 SOL (CharityFund 50 SOL)
    pub total_upgrade_spent: u64,   // u64 - CharityFund level 3 upgrade = 50 SOL 
    pub total_slot_spent: u64,      // u64 - max possible: 3×50SOL×10% + 1+2+5 = 23 SOL > 4.29 limit  
    pub total_earned: u64,          // u64 - накопленные earnings могут быть большими
    pub pending_earnings: u64,      // u64 - может накопиться много earnings
    
    /// 🆕 u32 TIMESTAMPS вместо i64 (до 2106 года)
    pub created_at: u32,
    pub next_earnings_time: u32,
    pub earnings_interval: u32,
    pub first_business_time: u32,
    pub last_auto_update: u32,
    
    pub bump: u8,
}

impl PlayerCompact {
    // Флаги
    const HAS_PAID_ENTRY_FLAG: u32 = 0x01;

    /// 🚨 ОБНОВЛЕННЫЙ размер после u64 исправлений и удаления referrals
    pub const SIZE: usize = 8 + // discriminator
        32 + // owner (Pubkey)
        (BusinessSlotCompact::SIZE * 9) + // фиксированный массив 9 слотов
        1 + // unlocked_slots_count
        1 + // premium_slots_count
        4 + // flags (упакованные)
        8 + // total_invested (u64) ← УВЕЛИЧЕНО
        8 + // total_upgrade_spent (u64) ← УВЕЛИЧЕНО
        8 + // total_slot_spent (u64) ← УВЕЛИЧЕНО
        8 + // total_earned (u64) ← УВЕЛИЧЕНО
        8 + // pending_earnings (u64) ← УВЕЛИЧЕНО
        4 + // created_at (u32)
        4 + // next_earnings_time (u32)
        4 + // earnings_interval (u32)
        4 + // first_business_time (u32)
        4 + // last_auto_update (u32)
        1; // bump

    pub fn has_paid_entry(&self) -> bool {
        (self.flags & Self::HAS_PAID_ENTRY_FLAG) != 0
    }

    pub fn set_has_paid_entry(&mut self, has_paid: bool) {
        if has_paid {
            self.flags |= Self::HAS_PAID_ENTRY_FLAG;
        } else {
            self.flags &= !Self::HAS_PAID_ENTRY_FLAG;
        }
    }

    /// Конвертация i64 timestamp в u32 (безопасно до 2106 года)
    pub fn timestamp_to_u32(timestamp: i64) -> u32 {
        (timestamp as u32).max(1) // Минимум 1, чтобы 0 означал "не установлено"
    }

    /// Конвертация u32 обратно в i64
    pub fn u32_to_timestamp(compact_time: u32) -> i64 {
        if compact_time == 0 {
            0
        } else {
            compact_time as i64
        }
    }

    /// НОВАЯ Инициализация - все 9 слотов разблокированы сразу
    pub fn new(owner: Pubkey, bump: u8, current_time: i64) -> Self {
        let mut slots = [BusinessSlotCompact::new_basic_free(); 9];
        
        // Слоты 0-2: Basic бесплатные (уже оплачены)
        for i in 0..3 {
            slots[i] = BusinessSlotCompact::new_basic_free();
        }
        
        // Слоты 3-5: Basic платные (10% при первом использовании)
        for i in 3..6 {
            slots[i] = BusinessSlotCompact::new_basic_paid();
        }
        
        // Слоты 6-8: Premium/VIP/Legendary (неоплаченные)
        slots[6] = BusinessSlotCompact::new_premium_unpaid(SlotType::Premium);
        slots[7] = BusinessSlotCompact::new_premium_unpaid(SlotType::VIP);
        slots[8] = BusinessSlotCompact::new_premium_unpaid(SlotType::Legendary);
        
        Self {
            owner,
            business_slots: slots,
            unlocked_slots_count: 9, // Все 9 слотов разблокированы
            premium_slots_count: 3, // 3 premium слота доступны (но неоплачены)
            flags: 0, // has_paid_entry = false
            total_invested: 0,
            total_upgrade_spent: 0,
            total_slot_spent: 0,
            total_earned: 0,
            pending_earnings: 0,
            created_at: Self::timestamp_to_u32(current_time),
            next_earnings_time: Self::timestamp_to_u32(current_time + EARNINGS_INTERVAL),
            earnings_interval: EARNINGS_INTERVAL as u32,
            first_business_time: 0,
            last_auto_update: Self::timestamp_to_u32(current_time),
            bump,
        }
    }

    /// Проверить, пора ли обновлять earnings
    pub fn is_earnings_due(&self, current_time: i64) -> bool {
        Self::u32_to_timestamp(self.next_earnings_time) <= current_time
    }

    /// Автообновление earnings
    pub fn auto_update_earnings(&mut self, current_time: i64) -> Result<u64> {
        if !self.is_earnings_due(current_time) {
            return Ok(0);
        }

        let mut total_earnings = 0u64;
        
        // Рассчитываем доходы от всех активных бизнесов с учетом бонусов слотов
        for slot in &self.business_slots {
            if let Some(business) = &slot.business {
                // Рассчитываем базовые earnings за период EARNINGS_INTERVAL
                let base_earnings = business.calculate_earnings_for_period(EARNINGS_INTERVAL);
                // 🏪 ИСПРАВЛЕНИЕ: Применяем бонус доходности слота
                let slot_earnings = slot.calculate_earnings(base_earnings);
                total_earnings += slot_earnings;
            }
        }

        // Обновляем pending_earnings (теперь u64 - без overflow риска)
        self.pending_earnings = self.pending_earnings.saturating_add(total_earnings);
        
        // Обновляем время следующего начисления
        self.next_earnings_time = Self::timestamp_to_u32(current_time + EARNINGS_INTERVAL);
        self.last_auto_update = Self::timestamp_to_u32(current_time);

        Ok(total_earnings)
    }

    /// Получить количество активных бизнесов
    pub fn get_active_businesses_count(&self) -> u8 {
        self.business_slots.iter()
            .filter(|slot| slot.has_business())
            .count() as u8
    }

    /// Найти свободный слот (все слоты разблокированы)
    pub fn find_free_slot(&self) -> Option<usize> {
        self.business_slots.iter()
            .position(|slot| !slot.has_business())
    }

    /// Поместить бизнес в слот
    pub fn place_business_in_slot(&mut self, slot_index: usize, business: Business) -> Result<()> {
        if slot_index >= self.business_slots.len() {
            return Err(SolanaMafiaError::InvalidSlotIndex.into());
        }

        self.business_slots[slot_index].place_business(business)?;
        Ok(())
    }

    /// Установить расписание earnings
    pub fn set_earnings_schedule(&mut self, current_time: i64, _seed: u64) -> Result<()> {
        self.next_earnings_time = Self::timestamp_to_u32(current_time + EARNINGS_INTERVAL);
        self.earnings_interval = EARNINGS_INTERVAL as u32;
        Ok(())
    }

    /// Улучшить бизнес в слоте
    pub fn upgrade_business_in_slot(&mut self, slot_index: usize, upgrade_cost: u64, new_business: Business) -> Result<()> {
        if slot_index >= self.business_slots.len() {
            return Err(SolanaMafiaError::InvalidSlotIndex.into());
        }

        self.business_slots[slot_index].business = Some(new_business);
        self.total_upgrade_spent = self.total_upgrade_spent.saturating_add(upgrade_cost);
        Ok(())
    }

    /// Продать бизнес из слота
    pub fn sell_business_from_slot(&mut self, slot_index: usize) -> Result<(Business, u8)> {
        if slot_index >= self.business_slots.len() {
            return Err(SolanaMafiaError::InvalidSlotIndex.into());
        }

        let business = self.business_slots[slot_index].remove_business()
            .ok_or(SolanaMafiaError::SlotEmpty)?;
        let discount = self.business_slots[slot_index].get_sell_fee_discount();
        
        Ok((business, discount))
    }

    /// Обновить pending earnings
    pub fn update_pending_earnings(&mut self, current_time: i64) -> Result<()> {
        self.auto_update_earnings(current_time)?;
        Ok(())
    }

    /// Получить сумму для клейма
    pub fn get_claimable_amount(&self) -> Result<u64> {
        Ok(self.pending_earnings)
    }

    /// Забрать все earnings
    pub fn claim_all_earnings(&mut self) -> Result<()> {
        let claimed = self.pending_earnings;
        self.total_earned = self.total_earned.saturating_add(claimed);
        self.pending_earnings = 0;
        Ok(())
    }

    /// Health check
    pub fn health_check(&self, _current_time: i64) -> Result<()> {
        // Simplified health check
        Ok(())
    }

    /// Получить все бизнесы
    pub fn get_all_businesses(&self) -> Vec<&Business> {
        self.business_slots.iter()
            .filter_map(|slot| slot.business.as_ref())
            .collect()
    }

    /// 🏪 Получить стоимость слота для бизнеса (новая система)
    pub fn get_slot_cost_for_business(&self, slot_index: usize, business_price: u64) -> u64 {
        if slot_index >= self.business_slots.len() {
            return 0;
        }
        
        self.business_slots[slot_index].get_slot_cost(business_price)
    }

    /// 🏪 Оплатить слот при первом использовании (новая система)
    pub fn pay_slot_if_needed(&mut self, slot_index: usize, business_price: u64) -> Result<u64> {
        if slot_index >= self.business_slots.len() {
            return Err(SolanaMafiaError::InvalidSlotIndex.into());
        }
        
        let slot_cost = self.business_slots[slot_index].get_slot_cost(business_price);
        
        if slot_cost > 0 {
            self.business_slots[slot_index].pay_slot(slot_cost)?;
            self.total_slot_spent = self.total_slot_spent.saturating_add(slot_cost);
        }
        
        Ok(slot_cost)
    }
}

/// Alias для обратной совместимости
pub type BusinessSlot = BusinessSlotCompact;
pub type Player = PlayerCompact;