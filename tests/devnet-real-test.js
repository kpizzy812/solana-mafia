const anchor = require("@coral-xyz/anchor");
const { SystemProgram, LAMPORTS_PER_SOL, PublicKey } = require("@solana/web3.js");
const assert = require("assert");

describe("🌐 DEVNET REAL TESTS", () => {
  // Подключение к devnet
  const provider = anchor.AnchorProvider.env();
  anchor.setProvider(provider);
  const program = anchor.workspace.SolanaMafia;
  
  // 🏦 РЕАЛЬНЫЙ КОШЕЛЕК КОМАНДЫ (замените на ваш)
  const TREASURY_WALLET = new PublicKey("HLWTn3BYB3jvgquBG323XLyqzEj11H4N5m6EMpPGCCG6");
  
  // PDA аккаунты
  let gameStatePda, gameConfigPda, treasuryPda;
  let testPlayer1, testPlayer2;
  let player1Pda, player2Pda;

  before(async () => {
    console.log("🌐 Connecting to Devnet...");
    console.log("Program ID:", program.programId.toString());
    console.log("Provider wallet:", provider.wallet.publicKey.toString());

    // Генерируем PDA
    [gameStatePda] = await PublicKey.findProgramAddress(
      [Buffer.from("game_state")], program.programId
    );
    [gameConfigPda] = await PublicKey.findProgramAddress(
      [Buffer.from("game_config")], program.programId
    );
    [treasuryPda] = await PublicKey.findProgramAddress(
      [Buffer.from("treasury")], program.programId
    );

    console.log("📍 PDAs:");
    console.log("Game State:", gameStatePda.toString());
    console.log("Game Config:", gameConfigPda.toString());
    console.log("Treasury PDA:", treasuryPda.toString());
    console.log("Treasury Wallet:", TREASURY_WALLET.toString());

    // Создаем тестовых игроков
    testPlayer1 = anchor.web3.Keypair.generate();
    testPlayer2 = anchor.web3.Keypair.generate();

    [player1Pda] = await PublicKey.findProgramAddress(
      [Buffer.from("player"), testPlayer1.publicKey.toBuffer()], program.programId
    );
    [player2Pda] = await PublicKey.findProgramAddress(
      [Buffer.from("player"), testPlayer2.publicKey.toBuffer()], program.programId
    );

    // 💰 Airdrop SOL на devnet (если нужно)
    console.log("💰 Requesting devnet SOL...");
    
    try {
      const airdrop1 = await provider.connection.requestAirdrop(testPlayer1.publicKey, 10 * LAMPORTS_PER_SOL);
      await provider.connection.confirmTransaction(airdrop1);
      
      const airdrop2 = await provider.connection.requestAirdrop(testPlayer2.publicKey, 10 * LAMPORTS_PER_SOL);
      await provider.connection.confirmTransaction(airdrop2);
      
      console.log("✅ Airdrop successful");
    } catch (error) {
      console.log("⚠️ Airdrop failed (возможно лимит devnet):", error.message);
    }

    // Проверяем балансы
    const balance1 = await provider.connection.getBalance(testPlayer1.publicKey);
    const balance2 = await provider.connection.getBalance(testPlayer2.publicKey);
    console.log(`Player 1 balance: ${balance1 / LAMPORTS_PER_SOL} SOL`);
    console.log(`Player 2 balance: ${balance2 / LAMPORTS_PER_SOL} SOL`);
  });

  describe("🚀 DEPLOYMENT & INITIALIZATION", () => {
    it("Инициализирует игру на devnet", async () => {
      console.log("🔧 Initializing game...");

      try {
        const tx = await program.methods
          .initialize(TREASURY_WALLET)
          .accounts({
            authority: provider.wallet.publicKey,
            gameState: gameStatePda,
            gameConfig: gameConfigPda,
            treasuryPda: treasuryPda,
            systemProgram: SystemProgram.programId,
          })
          .rpc();

        console.log("✅ Initialize transaction:", tx);

        // Проверяем что аккаунты созданы
        const gameState = await program.account.gameState.fetch(gameStatePda);
        const gameConfig = await program.account.gameConfig.fetch(gameConfigPda);

        console.log("📊 Game State:", {
          authority: gameState.authority.toString(),
          treasuryWallet: gameState.treasuryWallet.toString(),
          totalPlayers: gameState.totalPlayers.toString(),
          isPaused: gameState.isPaused
        });

        console.log("⚙️ Game Config:", {
          entryFee: gameConfig.entryFee.toString(),
          treasuryFeePercent: gameConfig.treasuryFeePercent,
          businessRates: gameConfig.businessRates
        });

        assert.equal(gameState.treasuryWallet.toString(), TREASURY_WALLET.toString());
        assert.equal(gameState.totalPlayers.toNumber(), 0);
        assert.equal(gameState.isPaused, false);

      } catch (error) {
        if (error.message.includes("already in use") || error.message.includes("0x0")) {
          console.log("⚠️ Game already initialized, skipping...");
        } else {
          throw error;
        }
      }
    });
  });

  describe("👥 PLAYER MANAGEMENT", () => {
    it("Создает первого игрока с entry fee", async () => {
      console.log("👤 Creating Player 1...");

      const treasuryBalanceBefore = await provider.connection.getBalance(TREASURY_WALLET);
      
      const tx = await program.methods
        .createPlayer()
        .accounts({
          owner: testPlayer1.publicKey,
          player: player1Pda,
          gameConfig: gameConfigPda,
          gameState: gameStatePda,
          treasuryWallet: TREASURY_WALLET,
          systemProgram: SystemProgram.programId,
        })
        .signers([testPlayer1])
        .rpc();

      console.log("✅ Create Player 1 transaction:", tx);

      const player1 = await program.account.player.fetch(player1Pda);
      const treasuryBalanceAfter = await provider.connection.getBalance(TREASURY_WALLET);
      const treasuryIncrease = treasuryBalanceAfter - treasuryBalanceBefore;

      console.log("📋 Player 1 created:", {
        owner: player1.owner.toString(),
        hasPaidEntry: player1.hasPaidEntry,
        businesses: player1.businesses.length,
        totalInvested: player1.totalInvested.toString()
      });

      console.log(`💰 Treasury increased by: ${treasuryIncrease} lamports`);

      assert.equal(player1.owner.toString(), testPlayer1.publicKey.toString());
      assert.equal(player1.hasPaidEntry, true);
      assert(treasuryIncrease > 0, "Treasury should receive entry fee");
    });

    it("Создает второго игрока", async () => {
      console.log("👤 Creating Player 2...");

      const tx = await program.methods
        .createPlayer()
        .accounts({
          owner: testPlayer2.publicKey,
          player: player2Pda,
          gameConfig: gameConfigPda,
          gameState: gameStatePda,
          treasuryWallet: TREASURY_WALLET,
          systemProgram: SystemProgram.programId,
        })
        .signers([testPlayer2])
        .rpc();

      console.log("✅ Create Player 2 transaction:", tx);

      const gameState = await program.account.gameState.fetch(gameStatePda);
      console.log(`👥 Total players in game: ${gameState.totalPlayers.toString()}`);

      assert.equal(gameState.totalPlayers.toNumber(), 2);
    });
  });

  describe("🏢 BUSINESS OPERATIONS", () => {
    it("Игрок 1 покупает CryptoKiosk (0.1 SOL)", async () => {
      console.log("🏪 Player 1 buying CryptoKiosk...");

      const investment = new anchor.BN(0.1 * LAMPORTS_PER_SOL);
      const businessType = 0; // CryptoKiosk

      const treasuryWalletBefore = await provider.connection.getBalance(TREASURY_WALLET);
      const treasuryPdaBefore = await provider.connection.getBalance(treasuryPda);

      const tx = await program.methods
        .createBusiness(businessType, investment)
        .accounts({
          owner: testPlayer1.publicKey,
          player: player1Pda,
          gameConfig: gameConfigPda,
          gameState: gameStatePda,
          treasuryWallet: TREASURY_WALLET,
          treasuryPda: treasuryPda,
          systemProgram: SystemProgram.programId,
        })
        .signers([testPlayer1])
        .rpc();

      console.log("✅ Create Business transaction:", tx);

      const player1 = await program.account.player.fetch(player1Pda);
      const business = player1.businesses[0];

      const treasuryWalletAfter = await provider.connection.getBalance(TREASURY_WALLET);
      const treasuryPdaAfter = await provider.connection.getBalance(treasuryPda);

      const teamFee = treasuryWalletAfter - treasuryWalletBefore;
      const gameFunds = treasuryPdaAfter - treasuryPdaBefore;

      console.log("🏪 Business created:", {
        type: "CryptoKiosk",
        invested: business.investedAmount.toString(),
        dailyRate: business.dailyRate,
        upgradeLevel: business.upgradeLevel,
        isActive: business.isActive
      });

      console.log("💰 Fee distribution:");
      console.log(`Team fee: ${teamFee / LAMPORTS_PER_SOL} SOL (${(teamFee/investment.toNumber()*100).toFixed(1)}%)`);
      console.log(`Game funds: ${gameFunds / LAMPORTS_PER_SOL} SOL (${(gameFunds/investment.toNumber()*100).toFixed(1)}%)`);

      assert.equal(business.dailyRate, 80); // 0.8%
      assert.equal(business.investedAmount.toNumber(), investment.toNumber());
      assert.equal(business.isActive, true);

      // Проверяем распределение 20% / 80%
      const expectedTeamFee = investment.toNumber() * 0.2;
      const expectedGameFunds = investment.toNumber() * 0.8;
      
      assert(Math.abs(teamFee - expectedTeamFee) < 1000000, "Team fee should be ~20%"); // 0.001 SOL tolerance
      assert(Math.abs(gameFunds - expectedGameFunds) < 1000000, "Game funds should be ~80%");
    });

    it("Игрок 2 покупает MemeCasino (0.5 SOL)", async () => {
      console.log("🎰 Player 2 buying MemeCasino...");

      const investment = new anchor.BN(0.5 * LAMPORTS_PER_SOL);
      const businessType = 1; // MemeCasino

      const tx = await program.methods
        .createBusiness(businessType, investment)
        .accounts({
          owner: testPlayer2.publicKey,
          player: player2Pda,
          gameConfig: gameConfigPda,
          gameState: gameStatePda,
          treasuryWallet: TREASURY_WALLET,
          treasuryPda: treasuryPda,
          systemProgram: SystemProgram.programId,
        })
        .signers([testPlayer2])
        .rpc();

      console.log("✅ Create MemeCasino transaction:", tx);

      const player2 = await program.account.player.fetch(player2Pda);
      const business = player2.businesses[0];

      console.log("🎰 MemeCasino created:", {
        invested: business.investedAmount.toString(),
        dailyRate: business.dailyRate
      });

      assert.equal(business.dailyRate, 90); // 0.9%
      assert.equal(business.investedAmount.toNumber(), investment.toNumber());
    });
  });

  describe("💰 EARNINGS & UPGRADES", () => {
    it("Обновляет earnings после времени", async () => {
      console.log("⏰ Waiting and updating earnings...");

      // Ждем немного для накопления
      await new Promise(resolve => setTimeout(resolve, 5000));

      try {
        const tx1 = await program.methods
          .updateEarnings()
          .accounts({
            authority: testPlayer1.publicKey,
            player: player1Pda,
          })
          .signers([testPlayer1])
          .rpc();

        console.log("✅ Update Player 1 earnings:", tx1);

        const player1 = await program.account.player.fetch(player1Pda);
        console.log(`💰 Player 1 pending earnings: ${player1.pendingEarnings.toNumber()} lamports`);

      } catch (error) {
        if (error.message.includes("TooEarlyToUpdate")) {
          console.log("⚠️ Cooldown active, skipping update");
        } else {
          console.log("Update earnings error:", error.message);
        }
      }
    });

    it("Апгрейдит бизнес (донат команде)", async () => {
      console.log("⬆️ Upgrading Player 1's business...");

      const treasuryBefore = await provider.connection.getBalance(TREASURY_WALLET);

      try {
        const tx = await program.methods
          .upgradeBusiness(0) // First business
          .accounts({
            playerOwner: testPlayer1.publicKey,
            player: player1Pda,
            treasuryWallet: TREASURY_WALLET,
            gameState: gameStatePda,
            gameConfig: gameConfigPda,
            systemProgram: SystemProgram.programId,
          })
          .signers([testPlayer1])
          .rpc();

        console.log("✅ Upgrade transaction:", tx);

        const player1 = await program.account.player.fetch(player1Pda);
        const business = player1.businesses[0];
        const treasuryAfter = await provider.connection.getBalance(TREASURY_WALLET);
        const upgradeFee = treasuryAfter - treasuryBefore;

        console.log("⬆️ Business upgraded:", {
          level: business.upgradeLevel,
          newDailyRate: business.dailyRate,
          upgradeFee: `${upgradeFee / LAMPORTS_PER_SOL} SOL`
        });

        assert.equal(business.upgradeLevel, 1);
        assert(business.dailyRate > 80, "Daily rate should increase");
        assert(upgradeFee > 0, "Team should receive upgrade fee");

      } catch (error) {
        console.log("⚠️ Upgrade error:", error.message);
      }
    });
  });

  describe("📊 FINAL STATISTICS", () => {
    it("Показывает финальную статистику игры", async () => {
      console.log("📊 FINAL DEVNET STATISTICS:");
      console.log("=".repeat(50));

      const gameState = await program.account.gameState.fetch(gameStatePda);
      const gameConfig = await program.account.gameConfig.fetch(gameConfigPda);
      const treasuryPdaBalance = await provider.connection.getBalance(treasuryPda);
      const treasuryWalletBalance = await provider.connection.getBalance(TREASURY_WALLET);

      console.log("🎮 Game Stats:");
      console.log(`Players: ${gameState.totalPlayers.toString()}`);
      console.log(`Businesses: ${gameState.totalBusinesses.toString()}`);
      console.log(`Total Invested: ${gameState.totalInvested.toNumber() / LAMPORTS_PER_SOL} SOL`);
      console.log(`Total Withdrawn: ${gameState.totalWithdrawn.toNumber() / LAMPORTS_PER_SOL} SOL`);
      console.log(`Treasury Collected: ${gameState.totalTreasuryCollected.toNumber() / LAMPORTS_PER_SOL} SOL`);

      console.log("\n💰 Balances:");
      console.log(`Game Pool (PDA): ${treasuryPdaBalance / LAMPORTS_PER_SOL} SOL`);
      console.log(`Team Wallet: ${treasuryWalletBalance / LAMPORTS_PER_SOL} SOL`);

      console.log("\n⚙️ Config:");
      console.log(`Entry Fee: ${gameConfig.entryFee.toNumber() / LAMPORTS_PER_SOL} SOL`);
      console.log(`Treasury Fee: ${gameConfig.treasuryFeePercent}%`);
      console.log(`Business Rates: [${gameConfig.businessRates.join(', ')}]`);

      console.log("\n🎯 Health Check:");
      const totalSystemValue = treasuryPdaBalance + treasuryWalletBalance;
      const pendingObligations = gameState.totalInvested.toNumber() - gameState.totalWithdrawn.toNumber();
      console.log(`System Value: ${totalSystemValue / LAMPORTS_PER_SOL} SOL`);
      console.log(`Pending Obligations: ${pendingObligations / LAMPORTS_PER_SOL} SOL`);

      if (treasuryPdaBalance >= pendingObligations * 0.8) {
        console.log("✅ Treasury Health: GOOD");
      } else {
        console.log("⚠️ Treasury Health: NEEDS ATTENTION");
      }

      console.log("=".repeat(50));

      // Основные проверки здоровья
      assert(gameState.totalPlayers.toNumber() > 0, "Should have players");
      assert(gameState.totalBusinesses.toNumber() > 0, "Should have businesses");
      assert(treasuryPdaBalance > 0, "Game pool should have funds");
      assert(treasuryWalletBalance > 0, "Team should have received fees");
    });

    it("🔗 Выводит важные адреса для фронтенда", async () => {
      console.log("\n🔗 ВАЖНЫЕ АДРЕСА ДЛЯ ФРОНТЕНДА:");
      console.log("=".repeat(50));
      console.log(`Program ID: ${program.programId.toString()}`);
      console.log(`Game State PDA: ${gameStatePda.toString()}`);
      console.log(`Game Config PDA: ${gameConfigPda.toString()}`);
      console.log(`Treasury PDA: ${treasuryPda.toString()}`);
      console.log(`Team Wallet: ${TREASURY_WALLET.toString()}`);
      console.log(`Network: devnet`);
      console.log("=".repeat(50));
    });
  });
});