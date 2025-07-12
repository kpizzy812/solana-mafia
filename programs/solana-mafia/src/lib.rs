use anchor_lang::prelude::*;

declare_id!("93zp2Qtgaiud9NTG1fYb4qqDddSi98AAx9Px7Gyv3CnM");

#[program]
pub mod solana_mafia {
    use super::*;

    pub fn initialize(ctx: Context<Initialize>) -> Result<()> {
        msg!("Greetings from: {:?}", ctx.program_id);
        Ok(())
    }
}

#[derive(Accounts)]
pub struct Initialize {}
