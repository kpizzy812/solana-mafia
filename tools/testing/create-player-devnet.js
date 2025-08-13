const anchor = require("@coral-xyz/anchor");
const { PublicKey, Connection, LAMPORTS_PER_SOL, Keypair } = require("@solana/web3.js");

// DEVNET конфигурация
const PROGRAM_ID = new PublicKey("HifXYhFJapXPeBgKKZu8gmdc7cZvfERJ9aEkchHxyBLS");
const DEVNET_URL = "https://api.devnet.solana.com";

// Target player
const TARGET_PLAYER = new PublicKey("DfDkPhcm93C4JyXVRdz8M9B7cP8aeZKS9DNxS5cTxEmE");

async function testCreatePlayer() {
    console.log("👤 TESTING: Create Player на DEVNET");
    console.log("====================================");
    
    try {
        const connection = new Connection(DEVNET_URL, "confirmed");
        
        // Создаем wallet для target player (нужен private key)
        // НО для проверки аккаунта можем использовать публичный ключ
        
        // Проверим текущий аккаунт игрока
        const [playerPda, bump] = await PublicKey.findProgramAddress(
            [Buffer.from("player"), TARGET_PLAYER.toBuffer()],
            PROGRAM_ID
        );
        
        console.log(`🎯 Target player: ${TARGET_PLAYER}`);
        console.log(`🎯 Player PDA: ${playerPda}`);
        console.log(`🎯 PDA Bump: ${bump}`);
        
        // Проверим существует ли аккаунт
        const playerInfo = await connection.getAccountInfo(playerPda);
        
        if (playerInfo) {
            console.log("✅ Player account уже существует!");
            console.log(`- Size: ${playerInfo.data.length} bytes`);
            console.log(`- Owner: ${playerInfo.owner.toString()}`);
            console.log(`- Lamports: ${playerInfo.lamports}`);
            
            // Попробуем распарсить owner field правильно
            // Discriminator: 8 bytes, потом owner: 32 bytes
            const ownerBytes = playerInfo.data.slice(8, 40);
            const storedOwner = new PublicKey(ownerBytes);
            console.log(`- Stored owner: ${storedOwner.toString()}`);
            
            // Проверим PDA с stored owner
            const [testPda] = await PublicKey.findProgramAddress(
                [Buffer.from("player"), storedOwner.toBuffer()],
                PROGRAM_ID
            );
            console.log(`- PDA с stored owner: ${testPda.toString()}`);
            console.log(`- PDA совпадает: ${testPda.toString() === playerPda.toString()}`);
            
            if (storedOwner.toString() !== TARGET_PLAYER.toString()) {
                console.log("❌ ПРОБЛЕМА: Owner field неправильный!");
                console.log("💡 Возможно аккаунт создавался с багом");
                
                // Попробуем найти правильный PDA для stored owner
                console.log(`💡 Правильный PDA для stored owner был бы: ${testPda.toString()}`);
            }
            
        } else {
            console.log("❌ Player account не существует");
        }
        
        // Проверим game state PDAs для devnet
        const [gameStatePda] = await PublicKey.findProgramAddress([Buffer.from("game_state")], PROGRAM_ID);
        const [gameConfigPda] = await PublicKey.findProgramAddress([Buffer.from("game_config")], PROGRAM_ID);
        const [treasuryPda] = await PublicKey.findProgramAddress([Buffer.from("treasury")], PROGRAM_ID);
        
        console.log("\n📋 DEVNET PDAs:");
        console.log(`GameState: ${gameStatePda}`);
        console.log(`GameConfig: ${gameConfigPda}`);
        console.log(`Treasury: ${treasuryPda}`);
        
    } catch (error) {
        console.log(`❌ Error: ${error.message}`);
        console.log(error.stack);
    }
}

testCreatePlayer().catch(console.error);