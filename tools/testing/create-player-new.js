const anchor = require("@coral-xyz/anchor");
const { PublicKey, Connection, LAMPORTS_PER_SOL, Keypair } = require("@solana/web3.js");

// DEVNET конфигурация с новой программой
const PROGRAM_ID = new PublicKey("HifXYhFJapXPeBgKKZu8gmdc7cZvfERJ9aEkchHxyBLS");
const DEVNET_URL = "https://api.devnet.solana.com";

// Новый wallet для тестов
const NEW_WALLET = "9BA18LBbm3wL7Yt4YfumaHAqR7eGFriCLZkpZZMX28BF";

async function createPlayerForNewWallet() {
    console.log("👤 Создание игрока для нового wallet");
    console.log("=====================================");
    
    try {
        const connection = new Connection(DEVNET_URL, "confirmed");
        
        // Загружаем IDL и создаем программу
        const idl = require("../target/idl/solana_mafia.json");
        
        // Создаем фейковый wallet для вызова (admin wallet)
        const adminKeypair = Keypair.fromSecretKey(
            // Admin private key из .env (base58)
            anchor.utils.bytes.bs58.decode("5MBu1f5jjsUJK71fPwEhbVPKCzbJUmtVYdBPMAKrGWPiZpQUquU5D1rHhWpQSrcXYMYRYhAnQ1uoaMVForQEmiE")
        );
        
        const wallet = new anchor.Wallet(adminKeypair);
        const provider = new anchor.AnchorProvider(connection, wallet, {});
        const program = new anchor.Program(idl, PROGRAM_ID, provider);
        
        // Target wallet как pubkey
        const targetWallet = new PublicKey(NEW_WALLET);
        
        // Рассчитываем PDAs
        const [gameState] = await PublicKey.findProgramAddress([Buffer.from("game_state")], PROGRAM_ID);
        const [gameConfig] = await PublicKey.findProgramAddress([Buffer.from("game_config")], PROGRAM_ID);
        const [player] = await PublicKey.findProgramAddress([Buffer.from("player"), targetWallet.toBuffer()], PROGRAM_ID);
        
        console.log(`🎯 Target wallet: ${targetWallet}`);
        console.log(`🎯 Player PDA: ${player}`);
        console.log(`🎯 GameState: ${gameState}`);
        console.log(`🎯 GameConfig: ${gameConfig}`);
        
        // Проверим существует ли игрок
        const playerInfo = await connection.getAccountInfo(player);
        if (playerInfo) {
            console.log("ℹ️ Игрок уже существует!");
            return;
        }
        
        // Получаем treasury wallet из game state
        const gameStateAccount = await program.account.gameState.fetch(gameState);
        const treasuryWallet = gameStateAccount.treasuryWallet;
        
        console.log(`💰 Treasury wallet: ${treasuryWallet}`);
        
        // Проверяем баланс admin wallet для оплаты
        const adminBalance = await connection.getBalance(adminKeypair.publicKey);
        console.log(`💰 Admin balance: ${adminBalance / LAMPORTS_PER_SOL} SOL`);
        
        if (adminBalance < 0.1 * LAMPORTS_PER_SOL) {
            console.log("❌ Недостаточно средств на admin wallet");
            return;
        }
        
        // Создаем игрока
        console.log("🔨 Создание игрока...");
        const tx = await program.methods
            .createPlayer(null) // без referrer
            .accounts({
                owner: adminKeypair.publicKey, // admin платит
                player: player,
                gameConfig: gameConfig,
                gameState: gameState,
                treasuryWallet: treasuryWallet,
                systemProgram: anchor.web3.SystemProgram.programId,
            })
            .rpc();
            
        console.log(`✅ Игрок создан! TX: ${tx}`);
        console.log(`🎯 Теперь можно тестировать admin earnings update для: ${NEW_WALLET}`);
        
    } catch (error) {
        console.log(`❌ Ошибка: ${error.message}`);
        if (error.logs) {
            console.log("📋 Логи транзакции:");
            error.logs.forEach(log => console.log("  ", log));
        }
    }
}

createPlayerForNewWallet().catch(console.error);