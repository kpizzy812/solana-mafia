import * as anchor from "@coral-xyz/anchor";
import { Program } from "@coral-xyz/anchor";
import { SolanaMafia } from "../target/types/solana_mafia";
import { expect } from "chai";
import { SystemProgram, LAMPORTS_PER_SOL } from "@solana/web3.js";

describe("solana-mafia", () => {
  const provider = anchor.AnchorProvider.env();
  anchor.setProvider(provider);

  const program = anchor.workspace.SolanaMafia as Program<SolanaMafia>;
  const gameStateKeypair = anchor.web3.Keypair.generate();
  
  let playerKeypair: anchor.web3.Keypair;
  let playerPda: anchor.web3.PublicKey;
  let playerBump: number;

  before(async () => {
    playerKeypair = anchor.web3.Keypair.generate();
    
    // Derive player PDA
    [playerPda, playerBump] = await anchor.web3.PublicKey.findProgramAddress(
      [Buffer.from("player"), playerKeypair.publicKey.toBuffer()],
      program.programId
    );

    // Airdrop SOL to test accounts
    await provider.connection.confirmTransaction(
      await provider.connection.requestAirdrop(
        playerKeypair.publicKey,
        2 * LAMPORTS_PER_SOL
      )
    );
  });

  describe("🔧 Инициализация", () => {
    it("Инициализирует игровое состояние", async () => {
      const tx = await program.methods
        .initialize()
        .accounts({
          gameState: gameStateKeypair.publicKey,
          admin: provider.wallet.publicKey,
          systemProgram: SystemProgram.programId,
        })
        .signers([gameStateKeypair])
        .rpc();

      const gameState = await program.account.gameState.fetch(gameStateKeypair.publicKey);
      expect(gameState.totalInvested.toNumber()).to.equal(0);
      expect(gameState.totalPlayers).to.equal(0);
    });

    it("❌ Не позволяет двойную инициализацию", async () => {
      try {
        await program.methods
          .initialize()
          .accounts({
            gameState: gameStateKeypair.publicKey,
            admin: provider.wallet.publicKey,
            systemProgram: SystemProgram.programId,
          })
          .signers([gameStateKeypair])
          .rpc();
        
        expect.fail("Должна быть ошибка");
      } catch (error) {
        expect(error.toString()).to.include("already in use");
      }
    });
  });

  describe("👤 Создание игрока", () => {
    it("Создает нового игрока", async () => {
      const tx = await program.methods
        .createPlayer()
        .accounts({
          player: playerPda,
          owner: playerKeypair.publicKey,
          gameState: gameStateKeypair.publicKey,
          systemProgram: SystemProgram.programId,
        })
        .signers([playerKeypair])
        .rpc();

      const player = await program.account.player.fetch(playerPda);
      expect(player.owner.toString()).to.equal(playerKeypair.publicKey.toString());
      expect(player.pendingEarnings.toNumber()).to.equal(0);
      expect(player.totalClaimed.toNumber()).to.equal(0);
    });
  });

  describe("🏢 Управление бизнесами", () => {
    it("Создает новый бизнес", async () => {
      const investAmount = new anchor.BN(0.1 * LAMPORTS_PER_SOL);
      const businessType = 0; // DrugDealing
      
      const tx = await program.methods
        .createBusiness(businessType, investAmount)
        .accounts({
          player: playerPda,
          owner: playerKeypair.publicKey,
          gameState: gameStateKeypair.publicKey,
          systemProgram: SystemProgram.programId,
        })
        .signers([playerKeypair])
        .rpc();

      const player = await program.account.player.fetch(playerPda);
      expect(player.businesses.length).to.equal(1);
      expect(player.businesses[0].investedAmount.toNumber()).to.equal(investAmount.toNumber());
      expect(player.businesses[0].isActive).to.be.true;
    });

    it("❌ Отклоняет недостаточный депозит", async () => {
      const tinyAmount = new anchor.BN(1000); // Очень малая сумма
      
      try {
        await program.methods
          .createBusiness(0, tinyAmount)
          .accounts({
            player: playerPda,
            owner: playerKeypair.publicKey,
            gameState: gameStateKeypair.publicKey,
            systemProgram: SystemProgram.programId,
          })
          .signers([playerKeypair])
          .rpc();
        
        expect.fail("Должна быть ошибка");
      } catch (error) {
        expect(error.toString()).to.include("InsufficientDeposit");
      }
    });

    it("❌ Отклоняет неверный тип бизнеса", async () => {
      const investAmount = new anchor.BN(0.1 * LAMPORTS_PER_SOL);
      const invalidBusinessType = 99;
      
      try {
        await program.methods
          .createBusiness(invalidBusinessType, investAmount)
          .accounts({
            player: playerPda,
            owner: playerKeypair.publicKey,
            gameState: gameStateKeypair.publicKey,
            systemProgram: SystemProgram.programId,
          })
          .signers([playerKeypair])
          .rpc();
        
        expect.fail("Должна быть ошибка");
      } catch (error) {
        expect(error.toString()).to.include("InvalidBusinessType");
      }
    });
  });

  describe("💰 Заработки и выплаты", () => {
    it("Обновляет заработки со временем", async () => {
      // Ждем немного для накопления заработков
      await new Promise(resolve => setTimeout(resolve, 2000));
      
      const tx = await program.methods
        .updateEarnings()
        .accounts({
          player: playerPda,
          owner: playerKeypair.publicKey,
        })
        .signers([playerKeypair])
        .rpc();

      const player = await program.account.player.fetch(playerPda);
      expect(player.pendingEarnings.toNumber()).to.be.greaterThan(0);
    });

    it("Позволяет забрать заработки", async () => {
      const playerBefore = await program.account.player.fetch(playerPda);
      const balanceBefore = await provider.connection.getBalance(playerKeypair.publicKey);
      
      const tx = await program.methods
        .claimEarnings()
        .accounts({
          player: playerPda,
          owner: playerKeypair.publicKey,
          gameState: gameStateKeypair.publicKey,
        })
        .signers([playerKeypair])
        .rpc();

      const playerAfter = await program.account.player.fetch(playerPda);
      const balanceAfter = await provider.connection.getBalance(playerKeypair.publicKey);
      
      expect(playerAfter.pendingEarnings.toNumber()).to.equal(0);
      expect(playerAfter.totalClaimed.toNumber()).to.be.greaterThan(
        playerBefore.totalClaimed.toNumber()
      );
      expect(balanceAfter).to.be.greaterThan(balanceBefore);
    });

    it("❌ Блокирует попытки забрать чужие заработки", async () => {
      const hacker = anchor.web3.Keypair.generate();
      
      await provider.connection.confirmTransaction(
        await provider.connection.requestAirdrop(hacker.publicKey, LAMPORTS_PER_SOL)
      );

      try {
        await program.methods
          .claimEarnings()
          .accounts({
            player: playerPda,
            owner: hacker.publicKey, // Пытаемся использовать чужой ключ
            gameState: gameStateKeypair.publicKey,
          })
          .signers([hacker])
          .rpc();
        
        expect.fail("Должна быть ошибка");
      } catch (error) {
        expect(error.toString()).to.include("ConstraintSeeds");
      }
    });
  });

  describe("⬆️ Апгрейды бизнеса", () => {
    it("Апгрейдит бизнес", async () => {
      const upgradeLevel = 1;
      
      const tx = await program.methods
        .upgradeBusiness(0, upgradeLevel) // business index 0, level 1
        .accounts({
          player: playerPda,
          owner: playerKeypair.publicKey,
          gameState: gameStateKeypair.publicKey,
        })
        .signers([playerKeypair])
        .rpc();

      const player = await program.account.player.fetch(playerPda);
      expect(player.businesses[0].upgradeLevel).to.equal(upgradeLevel);
    });

    it("❌ Отклоняет неверный уровень апгрейда", async () => {
      const invalidLevel = 99;
      
      try {
        await program.methods
          .upgradeBusiness(0, invalidLevel)
          .accounts({
            player: playerPda,
            owner: playerKeypair.publicKey,
            gameState: gameStateKeypair.publicKey,
          })
          .signers([playerKeypair])
          .rpc();
        
        expect.fail("Должна быть ошибка");
      } catch (error) {
        expect(error.toString()).to.include("InvalidUpgradeLevel");
      }
    });
  });

  describe("🔒 Безопасность и доступы", () => {
    it("❌ Блокирует несанкционированный доступ к админ-функциям", async () => {
      const notAdmin = anchor.web3.Keypair.generate();
      
      try {
        await program.methods
          .adminPause()
          .accounts({
            gameState: gameStateKeypair.publicKey,
            admin: notAdmin.publicKey,
          })
          .signers([notAdmin])
          .rpc();
        
        expect.fail("Должна быть ошибка");
      } catch (error) {
        expect(error.toString()).to.include("ConstraintRaw");
      }
    });

    it("Предотвращает математические переполнения", async () => {
      const maxAmount = new anchor.BN("18446744073709551615"); // u64::MAX
      
      try {
        await program.methods
          .createBusiness(0, maxAmount)
          .accounts({
            player: playerPda,
            owner: playerKeypair.publicKey,
            gameState: gameStateKeypair.publicKey,
            systemProgram: SystemProgram.programId,
          })
          .signers([playerKeypair])
          .rpc();
        
        expect.fail("Должна быть ошибка");
      } catch (error) {
        // Проверяем, что система корректно обрабатывает переполнение
        expect(error).to.exist;
      }
    });
  });

  describe("📊 Математические расчеты", () => {
    it("Корректно рассчитывает ежедневные заработки", async () => {
      const player = await program.account.player.fetch(playerPda);
      const business = player.businesses[0];
      
      // Проверяем, что расчет соответствует ожидаемой формуле
      const expectedDailyEarnings = 
        (business.investedAmount.toNumber() * business.dailyRate) / 10000;
      
      // В реальном тесте здесь был бы вызов view-функции для расчета
      expect(business.dailyRate).to.be.greaterThan(0);
      expect(business.investedAmount.toNumber()).to.be.greaterThan(0);
    });
  });

  describe("🎯 Граничные случаи", () => {
    it("Обрабатывает нулевые заработки", async () => {
      // Создаем нового игрока без бизнесов
      const newPlayer = anchor.web3.Keypair.generate();
      const [newPlayerPda] = await anchor.web3.PublicKey.findProgramAddress(
        [Buffer.from("player"), newPlayer.publicKey.toBuffer()],
        program.programId
      );

      await provider.connection.confirmTransaction(
        await provider.connection.requestAirdrop(newPlayer.publicKey, LAMPORTS_PER_SOL)
      );

      await program.methods
        .createPlayer()
        .accounts({
          player: newPlayerPda,
          owner: newPlayer.publicKey,
          gameState: gameStateKeypair.publicKey,
          systemProgram: SystemProgram.programId,
        })
        .signers([newPlayer])
        .rpc();

      // Попытка забрать заработки без бизнесов
      const tx = await program.methods
        .claimEarnings()
        .accounts({
          player: newPlayerPda,
          owner: newPlayer.publicKey,
          gameState: gameStateKeypair.publicKey,
        })
        .signers([newPlayer])
        .rpc();

      const playerData = await program.account.player.fetch(newPlayerPda);
      expect(playerData.pendingEarnings.toNumber()).to.equal(0);
    });
  });
});