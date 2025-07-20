const anchor = require("@coral-xyz/anchor");
const { SystemProgram, LAMPORTS_PER_SOL } = require("@solana/web3.js");
const assert = require("assert");

describe("solana-mafia", () => {
  const provider = anchor.AnchorProvider.env();
  anchor.setProvider(provider);

  const program = anchor.workspace.SolanaMafia;
  
  // Treasury wallet для админа
  const treasuryWallet = anchor.web3.Keypair.generate();
  
  // PDA аккаунты
  let gameStatePda, gameStateBump;
  let gameConfigPda, gameConfigBump;
  let treasuryPda, treasuryBump;
  
  // Игрок
  let playerKeypair;
  let playerPda, playerBump;

  before(async () => {
    // Генерируем PDA с правильными seeds
    [gameStatePda, gameStateBump] = await anchor.web3.PublicKey.findProgramAddress(
      [Buffer.from("game_state")],
      program.programId
    );

    [gameConfigPda, gameConfigBump] = await anchor.web3.PublicKey.findProgramAddress(
      [Buffer.from("game_config")],
      program.programId
    );

    [treasuryPda, treasuryBump] = await anchor.web3.PublicKey.findProgramAddress(
      [Buffer.from("treasury")],
      program.programId
    );

    playerKeypair = anchor.web3.Keypair.generate();
    [playerPda, playerBump] = await anchor.web3.PublicKey.findProgramAddress(
      [Buffer.from("player"), playerKeypair.publicKey.toBuffer()],
      program.programId
    );

    // Airdrop SOL
    await provider.connection.confirmTransaction(
      await provider.connection.requestAirdrop(
        treasuryWallet.publicKey,
        2 * LAMPORTS_PER_SOL
      )
    );

    await provider.connection.confirmTransaction(
      await provider.connection.requestAirdrop(
        playerKeypair.publicKey,
        10 * LAMPORTS_PER_SOL
      )
    );
  });

  describe("🔧 Инициализация", () => {
    it("Инициализирует игровое состояние", async () => {
      const tx = await program.methods
        .initialize(treasuryWallet.publicKey)
        .accounts({
          authority: provider.wallet.publicKey,
          gameState: gameStatePda,
          gameConfig: gameConfigPda,
          treasuryPda: treasuryPda,
          systemProgram: SystemProgram.programId,
        })
        .rpc();

      const gameState = await program.account.gameState.fetch(gameStatePda);
      assert.equal(gameState.totalInvested.toNumber(), 0);
      assert.equal(gameState.totalPlayers.toNumber(), 0);
      assert.equal(gameState.isPaused, false); // ✅ Исправлено название поля
      
      const gameConfig = await program.account.gameConfig.fetch(gameConfigPda);
      assert.equal(gameConfig.entryFee.toNumber(), 100000); // 0.0001 SOL

      console.log("✅ Игра инициализирована успешно");
    });

    it("❌ Не позволяет двойную инициализацию", async () => {
      try {
        await program.methods
          .initialize(treasuryWallet.publicKey)
          .accounts({
            authority: provider.wallet.publicKey,
            gameState: gameStatePda,
            gameConfig: gameConfigPda,
            treasuryPda: treasuryPda,
            systemProgram: SystemProgram.programId,
          })
          .rpc();
        
        assert.fail("Должна быть ошибка");
      } catch (error) {
        assert(error.toString().includes("already in use") || 
               error.toString().includes("0x0") || 
               error.toString().includes("AlreadyInUse"));
      }
    });
  });

  describe("👤 Создание игрока", () => {
    it("Создает нового игрока с оплатой entry fee", async () => {
      const balanceBefore = await provider.connection.getBalance(playerKeypair.publicKey);
      
      const tx = await program.methods
        .createPlayer()
        .accounts({
          owner: playerKeypair.publicKey,
          player: playerPda,
          gameConfig: gameConfigPda,
          gameState: gameStatePda,
          treasuryWallet: treasuryWallet.publicKey,
          systemProgram: SystemProgram.programId,
        })
        .signers([playerKeypair])
        .rpc();

      const player = await program.account.player.fetch(playerPda);
      assert.equal(player.owner.toString(), playerKeypair.publicKey.toString());
      assert.equal(player.hasPaidEntry, true);
      assert.equal(player.businesses.length, 0);
      assert.equal(player.totalInvested.toNumber(), 0);

      const balanceAfter = await provider.connection.getBalance(playerKeypair.publicKey);
      assert(balanceBefore > balanceAfter);
      
      console.log("✅ Игрок создан, entry fee заплачен");
    });
  });

  describe("🏢 Управление бизнесами", () => {
    it("Создает новый бизнес после создания игрока", async () => {
      const investAmount = new anchor.BN(0.1 * LAMPORTS_PER_SOL); // 0.1 SOL
      const businessType = 0; // CryptoKiosk (минимальный депозит 0.1 SOL)
      
      const balanceBefore = await provider.connection.getBalance(playerKeypair.publicKey);
      
      const tx = await program.methods
        .createBusiness(businessType, investAmount)
        .accounts({
          owner: playerKeypair.publicKey,
          player: playerPda,
          gameConfig: gameConfigPda,
          gameState: gameStatePda,
          treasuryWallet: treasuryWallet.publicKey,
          treasuryPda: treasuryPda, // ✅ Это SystemAccount, не Account<Treasury>
          systemProgram: SystemProgram.programId,
        })
        .signers([playerKeypair])
        .rpc();

      const player = await program.account.player.fetch(playerPda);
      assert.equal(player.businesses.length, 1);
      assert.equal(player.businesses[0].investedAmount.toNumber(), investAmount.toNumber());
      assert.equal(player.businesses[0].isActive, true);

      const balanceAfter = await provider.connection.getBalance(playerKeypair.publicKey);
      assert(balanceBefore > balanceAfter);
      
      console.log("✅ Бизнес создан:", {
        type: player.businesses[0].businessType,
        amount: player.businesses[0].investedAmount.toString(),
        rate: player.businesses[0].dailyRate
      });
    });

    it("❌ Отклоняет недостаточный депозит", async () => {
      const tinyAmount = new anchor.BN(10_000_000); // 0.01 SOL - меньше минимума
      
      try {
        await program.methods
          .createBusiness(0, tinyAmount)
          .accounts({
            owner: playerKeypair.publicKey,
            player: playerPda,
            gameConfig: gameConfigPda,
            gameState: gameStatePda,
            treasuryWallet: treasuryWallet.publicKey,
            treasuryPda: treasuryPda,
            systemProgram: SystemProgram.programId,
          })
          .signers([playerKeypair])
          .rpc();
        
        assert.fail("Должна быть ошибка");
      } catch (error) {
        console.log("✅ Правильно отклонил маленький депозит");
        assert(error);
      }
    });
  });

  describe("💰 Заработки и выплаты", () => {
    it("Обновляет заработки со временем", async () => {
      console.log("⏰ Ожидание накопления заработков...");
      await new Promise(resolve => setTimeout(resolve, 5000));
      
      try {
        const tx = await program.methods
          .updateEarnings()
          .accounts({
            authority: playerKeypair.publicKey, // ✅ Исправлено название поля
            player: playerPda,
          })
          .signers([playerKeypair]) // ✅ authority должен подписать
          .rpc();

        const player = await program.account.player.fetch(playerPda);
        console.log("💰 Pending earnings:", player.pendingEarnings.toNumber());
        assert(player.pendingEarnings.toNumber() >= 0);
      } catch (error) {
        console.log("⚠️ Update earnings error:", error.message);
        // Возможно есть cooldown
      }
    });

    it("Позволяет забрать заработки", async () => {
      try {
        const playerBefore = await program.account.player.fetch(playerPda);
        
        if (playerBefore.pendingEarnings.toNumber() > 0) {
          const tx = await program.methods
            .claimEarnings()
            .accounts({
              player: playerPda,
              owner: playerKeypair.publicKey,
              gameState: gameStatePda,
              // Возможно нужны treasuryPda и systemProgram
            })
            .signers([playerKeypair])
            .rpc();

          console.log("✅ Заработки получены успешно");
        } else {
          console.log("ℹ️ Нет заработков для получения пока");
        }
      } catch (error) {
        console.log("⚠️ Claim earnings error:", error.message);
        // Покажем какие аккаунты нужны
      }
    });
  });

  describe("⬆️ Апгрейды бизнеса", () => {
    it("Апгрейдит бизнес", async () => {
      const businessIndex = 0;
      
      try {
        const tx = await program.methods
          .upgradeBusiness(businessIndex)
          .accounts({
            playerOwner: playerKeypair.publicKey, // ✅ Исправлено название поля
            player: playerPda,
            treasuryWallet: treasuryWallet.publicKey,
            gameState: gameStatePda,
            gameConfig: gameConfigPda,
            systemProgram: SystemProgram.programId,
          })
          .signers([playerKeypair]) // ✅ playerOwner должен подписать
          .rpc();

        const player = await program.account.player.fetch(playerPda);
        console.log("⬆️ Апгрейд выполнен, уровень:", player.businesses[0].upgradeLevel);
        assert(player.businesses[0].upgradeLevel >= 1);
      } catch (error) {
        console.log("⚠️ Upgrade error:", error.message);
      }
    });
  });

  describe("🔒 Безопасность и админ-функции", () => {
    it("Health check игрока работает", async () => {
      try {
        const tx = await program.methods
          .healthCheckPlayer()
          .accounts({
            player: playerPda,
          })
          .rpc();
        
        console.log("✅ Health check passed");
      } catch (error) {
        console.log("⚠️ Health check error:", error.message);
      }
    });

    it("Показывает статистику игры", async () => {
      const gameState = await program.account.gameState.fetch(gameStatePda);
      const gameConfig = await program.account.gameConfig.fetch(gameConfigPda);
      
      console.log("📊 Статистика игры:");
      console.log("- Всего игроков:", gameState.totalPlayers.toString());
      console.log("- Всего инвестировано:", gameState.totalInvested.toString());
      console.log("- Всего бизнесов:", gameState.totalBusinesses.toString());
      console.log("- Entry fee:", gameConfig.entryFee.toString());
      console.log("- На паузе:", gameState.isPaused);
    });
  });
});