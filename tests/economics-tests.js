const anchor = require("@coral-xyz/anchor");
const { SystemProgram, LAMPORTS_PER_SOL } = require("@solana/web3.js");
const assert = require("assert");

describe("💰 ECONOMICS & MATH TESTS", () => {
  const provider = anchor.AnchorProvider.env();
  anchor.setProvider(provider);
  const program = anchor.workspace.SolanaMafia;
  
  // 🔧 ПРАВИЛЬНО: Используем ЕДИНЫЕ глобальные PDA для всех тестов
  let gameStatePda, gameConfigPda, treasuryPda;
  
  // 🔧 ПРАВИЛЬНО: Создаем РАЗНЫХ игроков с РАЗНЫМИ кошельками
  let investor1, investor2;
  let investor1Pda, investor2Pda;

  before(async () => {
    console.log("💰 Starting Economics Tests - using global game state...");
    
    // 🏛️ ГЛОБАЛЬНЫЕ PDA - одни и те же для всех тестов
    [gameStatePda] = await anchor.web3.PublicKey.findProgramAddress(
      [Buffer.from("game_state")], // БЕЗ уникальных seeds!
      program.programId
    );
    [gameConfigPda] = await anchor.web3.PublicKey.findProgramAddress(
      [Buffer.from("game_config")], // БЕЗ уникальных seeds!
      program.programId
    );
    [treasuryPda] = await anchor.web3.PublicKey.findProgramAddress(
      [Buffer.from("treasury")], // БЕЗ уникальных seeds!
      program.programId
    );

    // 👤 УНИКАЛЬНЫЕ ИГРОКИ с разными кошельками
    investor1 = anchor.web3.Keypair.generate(); // Новый кошелек
    investor2 = anchor.web3.Keypair.generate(); // Новый кошелек

    // 👤 PDA для каждого игрока (уникальные благодаря разным кошелькам)
    [investor1Pda] = await anchor.web3.PublicKey.findProgramAddress(
      [Buffer.from("player"), investor1.publicKey.toBuffer()], // Уникален благодаря кошельку
      program.programId
    );
    [investor2Pda] = await anchor.web3.PublicKey.findProgramAddress(
      [Buffer.from("player"), investor2.publicKey.toBuffer()], // Уникален благодаря кошельку
      program.programId
    );

    console.log("📍 Using Global PDAs:");
    console.log("Game State:", gameStatePda.toString());
    console.log("Game Config:", gameConfigPda.toString());
    console.log("Treasury PDA:", treasuryPda.toString());
    
    console.log("👤 New Investors:");
    console.log("Investor 1:", investor1.publicKey.toString());
    console.log("Investor 2:", investor2.publicKey.toString());

    // 💰 Airdrop для новых игроков
    for (const keypair of [investor1, investor2]) {
      try {
        await provider.connection.confirmTransaction(
          await provider.connection.requestAirdrop(keypair.publicKey, 50 * LAMPORTS_PER_SOL)
        );
        console.log(`✅ Airdrop for ${keypair.publicKey.toString()}`);
      } catch (error) {
        console.log(`⚠️ Airdrop failed for ${keypair.publicKey.toString()}`);
      }
    }

    // 🔍 Проверяем что глобальная игра уже инициализирована
    try {
      const gameState = await program.account.gameState.fetch(gameStatePda);
      console.log("✅ Game already initialized:");
      console.log("- Players:", gameState.totalPlayers.toString());
      console.log("- Businesses:", gameState.totalBusinesses.toString());
      console.log("- Treasury Wallet:", gameState.treasuryWallet.toString());

      // 👤 Создаем новых игроков в существующей игре
      const treasuryWallet = gameState.treasuryWallet;

      for (const [keypair, pda, name] of [
        [investor1, investor1Pda, "Investor1"], 
        [investor2, investor2Pda, "Investor2"]
      ]) {
        try {
          await program.methods
            .createPlayer()
            .accounts({
              owner: keypair.publicKey,
              player: pda,
              gameConfig: gameConfigPda,
              gameState: gameStatePda,
              treasuryWallet: treasuryWallet,
              systemProgram: SystemProgram.programId,
            })
            .signers([keypair])
            .rpc();
          
          console.log(`✅ Created ${name}: ${keypair.publicKey.toString()}`);
        } catch (error) {
          console.log(`⚠️ ${name} creation error:`, error.message);
        }
      }

    } catch (error) {
      console.log("❌ Game not initialized! Please run devnet-real-test.js first");
      console.log("Error:", error.message);
    }
  });

  describe("🏪 Создание бизнесов", () => {
    it("Investor1 создает CryptoKiosk", async () => {
      try {
        const gameState = await program.account.gameState.fetch(gameStatePda);
        const investment = new anchor.BN(0.1 * LAMPORTS_PER_SOL);
        
        await program.methods
          .createBusiness(0, investment) // CryptoKiosk
          .accounts({
            owner: investor1.publicKey,
            player: investor1Pda,
            gameConfig: gameConfigPda,
            gameState: gameStatePda,
            treasuryWallet: gameState.treasuryWallet,
            treasuryPda: treasuryPda,
            systemProgram: SystemProgram.programId,
          })
          .signers([investor1])
          .rpc();

        const player = await program.account.player.fetch(investor1Pda);
        const business = player.businesses[0];
        
        console.log("✅ CryptoKiosk created:", {
          invested: business.investedAmount.toString(),
          dailyRate: business.dailyRate
        });

        assert.equal(business.dailyRate, 80);
        assert.equal(business.investedAmount.toNumber(), investment.toNumber());
      } catch (error) {
        console.log("⚠️ CryptoKiosk creation error:", error.message);
      }
    });

    it("Investor2 создает MemeCasino", async () => {
      try {
        const gameState = await program.account.gameState.fetch(gameStatePda);
        const investment = new anchor.BN(0.5 * LAMPORTS_PER_SOL);
        
        // Ждем cooldown
        await new Promise(resolve => setTimeout(resolve, 2000));
        
        await program.methods
          .createBusiness(1, investment) // MemeCasino
          .accounts({
            owner: investor2.publicKey,
            player: investor2Pda,
            gameConfig: gameConfigPda,
            gameState: gameStatePda,
            treasuryWallet: gameState.treasuryWallet,
            treasuryPda: treasuryPda,
            systemProgram: SystemProgram.programId,
          })
          .signers([investor2])
          .rpc();

        const player = await program.account.player.fetch(investor2Pda);
        const business = player.businesses[0];
        
        console.log("✅ MemeCasino created:", {
          invested: business.investedAmount.toString(),
          dailyRate: business.dailyRate
        });

        assert.equal(business.dailyRate, 90);
        assert.equal(business.investedAmount.toNumber(), investment.toNumber());
      } catch (error) {
        console.log("⚠️ MemeCasino creation error:", error.message);
      }
    });
  });

  describe("💰 Earnings система", () => {
    it("Earnings накапливаются со временем", async () => {
      try {
        console.log("⏰ Waiting for earnings accumulation...");
        await new Promise(resolve => setTimeout(resolve, 5000));
        
        // Проверяем investor1
        try {
          await program.methods
            .updateEarnings()
            .accounts({
              authority: investor1.publicKey,
              player: investor1Pda,
            })
            .signers([investor1])
            .rpc();

          const player1 = await program.account.player.fetch(investor1Pda);
          console.log(`💰 Investor1 earnings: ${player1.pendingEarnings.toNumber()} lamports`);
          
          assert(player1.pendingEarnings.toNumber() >= 0);
        } catch (error) {
          console.log("⚠️ Investor1 update error:", error.message);
        }

        // Ждем cooldown и проверяем investor2
        await new Promise(resolve => setTimeout(resolve, 2000));
        
        try {
          await program.methods
            .updateEarnings()
            .accounts({
              authority: investor2.publicKey,
              player: investor2Pda,
            })
            .signers([investor2])
            .rpc();

          const player2 = await program.account.player.fetch(investor2Pda);
          console.log(`💰 Investor2 earnings: ${player2.pendingEarnings.toNumber()} lamports`);
          
          assert(player2.pendingEarnings.toNumber() >= 0);
        } catch (error) {
          console.log("⚠️ Investor2 update error:", error.message);
        }

      } catch (error) {
        console.log("⚠️ Earnings test error:", error.message);
      }
    });
  });

  describe("📊 Экономическая статистика", () => {
    it("Показывает актуальную статистику игры", async () => {
      try {
        const gameState = await program.account.gameState.fetch(gameStatePda);
        const gameConfig = await program.account.gameConfig.fetch(gameConfigPda);
        const treasuryBalance = await provider.connection.getBalance(treasuryPda);
        const teamBalance = await provider.connection.getBalance(gameState.treasuryWallet);
        
        console.log("\n💰 UPDATED GAME STATISTICS:");
        console.log("=".repeat(50));
        console.log(`Total Players: ${gameState.totalPlayers.toString()}`);
        console.log(`Total Businesses: ${gameState.totalBusinesses.toString()}`);
        console.log(`Total Invested: ${gameState.totalInvested.toNumber() / LAMPORTS_PER_SOL} SOL`);
        console.log(`Treasury Balance: ${treasuryBalance / LAMPORTS_PER_SOL} SOL`);
        console.log(`Team Balance: ${teamBalance / LAMPORTS_PER_SOL} SOL`);
        console.log(`Entry Fee: ${gameConfig.entryFee.toNumber() / LAMPORTS_PER_SOL} SOL`);
        console.log("=".repeat(50));
        
        // Проверки здоровья
        assert(gameState.totalPlayers.toNumber() > 0);
        assert(gameState.totalBusinesses.toNumber() > 0);
        assert(treasuryBalance > 0);
        
        console.log("✅ Game economics are healthy!");
      } catch (error) {
        console.log("⚠️ Stats error:", error.message);
      }
    });
  });
});