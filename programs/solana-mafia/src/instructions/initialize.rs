use anchor_lang::prelude::*;

pub fn handler(ctx: Context<Initialize>, _treasury_wallet: Pubkey) -> Result<()> {
    msg!("Test initialize");
    Ok(())
}

#[derive(Accounts)]
pub struct Initialize<'info> {
    pub signer: Signer<'info>,
}