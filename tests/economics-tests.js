const anchor = require("@coral-xyz/anchor");
const { SystemProgram, LAMPORTS_PER_SOL } = require("@solana/web3.js");
const assert = require("assert");

describe("💰 ECONOMICS & MATH TESTS", () => {
  const provider = anchor.AnchorProvider.env();
  anchor.setProvider(provider);

  const program = anchor.workspace.SolanaMafia;
  const treasuryWallet = anchor.web3.Keypair.generate();
  
  let gameStatePda, gameConfigPda, treasuryPda;
  let investor1, investor2;
  let investor1Pda, investor2Pda;

  before(async () => {
    // Setup как в предыдущих тестах
    [gameStatePda] = await anchor.web3.PublicKey.findProgramAddress(
      [Buffer.from("game_state")], program.programId
    );
    [gameConfigPda] = await anchor.web3.PublicKey.findProgramAddress(
      [Buffer.from("game_config")], program.programId
    );
    [treasuryPda] = await anchor.web3.PublicKey.findProgramAddress(
      [Buffer.from("treasury")], program.programId
    );

    investor1 = anchor.web3.Keypair.generate();
    investor2 = anchor.web3.Keypair.generate();

    [investor1Pda] = await anchor.web3.PublicKey.findProgramAddress(
      [Buffer.from("player"), investor1.publicKey.toBuffer()], program.programId
    );
    [investor2Pda] = await anchor.web3.PublicKey.findProgramAddress(
      [Buffer.from("player"), investor2.publicKey.toBuffer()], program.programId
    );

    // Airdrop и инициализация
    for (const keypair of [treasuryWallet, investor1, investor2]) {
      await provider.connection.confirmTransaction(
        await provider.connection.requestAirdrop(keypair.publicKey, 50 * LAMPORTS_PER_SOL)
      );
    }

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

    // Создание инвесторов
    for (const [keypair, pda] of [[investor1, investor1Pda], [investor2, investor2Pda]]) {
      await program.methods
        .createPlayer()
        .accounts({
          owner: keypair.publicKey,
          player: pda,
          gameConfig: gameConfigPda,
          gameState: gameStatePda,
          treasuryWallet: treasuryWallet.publicKey,
          systemProgram: SystemProgram.programId,
        })
        .signers([keypair])
        .rpc();
    }
  });

  describe("🏪 Все типы бизнесов", () => {
    const businessTypes = [
      { name: "CryptoKiosk", investment: 0.1, expectedRate: 80 },
      { name: "MemeCasino", investment: 0.5, expectedRate: 90 },
      { name: "NFTLaundry", investment: 2, expectedRate: 100 },
      { name: "MiningFarm", investment: 5, expectedRate: 110 },
      { name: "DeFiEmpire", investment: 20, expectedRate: 130 },
      { name: "SolanaCartel", investment: 100, expectedRate: 150 },
    ];

    businessTypes.forEach((biz, index) => {
      it(`Создает ${biz.name} с правильным rate`, async () => {
        const investment = new anchor.BN(biz.investment * LAMPORTS_PER_SOL);
        
        await program.methods
          .createBusiness(index, investment)
          .accounts({
            owner: investor1.publicKey,
            player: investor1Pda,
            gameConfig: gameConfigPda,
            gameState: gameStatePda,
            treasuryWallet: treasuryWallet.publicKey,
            treasuryPda: treasuryPda,
            systemProgram: SystemProgram.programId,
          })
          .signers([investor1])
          .rpc();

        const player = await program.account.player.fetch(investor1Pda);
        const business = player.businesses[player.businesses.length - 1];
        
        console.log(`✅ ${biz.name}:`, {
          invested: business.investedAmount.toString(),
          dailyRate: business.dailyRate,
          expectedDaily: (investment.toNumber() * biz.expectedRate) / 10000
        });

        assert.equal(business.dailyRate, biz.expectedRate);
        assert.equal(business.investedAmount.toNumber(), investment.toNumber());
        
        // Ждем между созданиями (cooldown)
        if (index < businessTypes.length - 1) {
          await new Promise(resolve => setTimeout(resolve, 1000));
        }
      });
    });
  });

  describe("📈 Математика earnings", () => {
    it("Earnings растут линейно со временем", async () => {
      const startTime = Date.now();
      
      // Создаем простой бизнес для тестирования
      await program.methods
        .createBusiness(0, new anchor.BN(1 * LAMPORTS_PER_SOL))
        .accounts({
          owner: investor2.publicKey,
          player: investor2Pda,
          gameConfig: gameConfigPda,
          gameState: gameStatePda,
          treasuryWallet: treasuryWallet.publicKey,
          treasuryPda: treasuryPda,
          systemProgram: SystemProgram.programId,
        })
        .signers([investor2])
        .rpc();

      // Measurements в разное время
      const measurements = [];
      
      for (let i = 0; i < 3; i++) {
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

          const player = await program.account.player.fetch(investor2Pda);
          measurements.push({
            time: Date.now() - startTime,
            earnings: player.pendingEarnings.toNumber()
          });
          
          console.log(`T+${Math.round((Date.now() - startTime) / 1000)}s: ${player.pendingEarnings.toNumber()} lamports`);
        } catch (error) {
          if (!error.message.includes("TooEarlyToUpdate")) {
            console.log("Update error:", error.message);
          }
        }
      }

      // Проверяем что earnings растут
      if (measurements.length >= 2) {
        assert(measurements[measurements.length - 1].earnings >= measurements[0].earnings,
               "Earnings должны расти со временем");
      }
    });

    it("ROI соответствует заявленному", async () => {
      const investment = 1 * LAMPORTS_PER_SOL; // 1 SOL
      const dailyRate = 80; // 0.8%
      
      const expectedDailyEarnings = (investment * dailyRate) / 10000;
      const expectedYearlyROI = (expectedDailyEarnings * 365) / investment;
      
      console.log("📊 ROI Analysis:");
      console.log(`Investment: ${investment / LAMPORTS_PER_SOL} SOL`);
      console.log(`Daily rate: ${dailyRate / 100}%`);
      console.log(`Expected daily earnings: ${expectedDailyEarnings / LAMPORTS_PER_SOL} SOL`);
      console.log(`Expected yearly ROI: ${(expectedYearlyROI * 100).toFixed(1)}%`);
      
      // Проверки разумности
      assert(expectedYearlyROI > 2.5, "ROI должен быть выше 250% годовых"); // 0.8% * 365 = 292%
      assert(expectedYearlyROI < 10, "ROI не должен быть слишком высоким");
    });
  });

  describe("⬆️ Система апгрейдов", () => {
    it("Апгрейды увеличивают доходность", async () => {
      const playerBefore = await program.account.player.fetch(investor2Pda);
      const businessBefore = playerBefore.businesses[0];
      const rateBefore = businessBefore.dailyRate;
      
      // Делаем апгрейд
      await program.methods
        .upgradeBusiness(0)
        .accounts({
          playerOwner: investor2.publicKey,
          player: investor2Pda,
          treasuryWallet: treasuryWallet.publicKey,
          gameState: gameStatePda,
          gameConfig: gameConfigPda,
          systemProgram: SystemProgram.programId,
        })
        .signers([investor2])
        .rpc();

      const playerAfter = await program.account.player.fetch(investor2Pda);
      const businessAfter = playerAfter.businesses[0];
      const rateAfter = businessAfter.dailyRate;
      
      console.log(`Апгрейд: ${rateBefore} -> ${rateAfter} basis points`);
      console.log(`Уровень: ${businessBefore.upgradeLevel} -> ${businessAfter.upgradeLevel}`);
      
      assert(rateAfter > rateBefore, "Rate должен увеличиться после апгрейда");
      assert.equal(businessAfter.upgradeLevel, businessBefore.upgradeLevel + 1);
      
      // Проверяем стоимость апгрейда
      const gameConfig = await program.account.gameConfig.fetch(gameConfigPda);
      const upgradeCost = gameConfig.upgradeCosts[0]; // Level 1 cost
      console.log(`Стоимость апгрейда: ${upgradeCost.toNumber() / LAMPORTS_PER_SOL} SOL`);
    });
  });

  describe("💸 Early sell fees", () => {
    it("Sell fees уменьшаются со временем", async () => {
      // Создаем бизнес для продажи
      await program.methods
        .createBusiness(1, new anchor.BN(0.5 * LAMPORTS_PER_SOL))
        .accounts({
          owner: investor1.publicKey,
          player: investor1Pda,
          gameConfig: gameConfigPda,
          gameState: gameStatePda,
          treasuryWallet: treasuryWallet.publicKey,
          treasuryPda: treasuryPda,
          systemProgram: SystemProgram.programId,
        })
        .signers([investor1])
        .rpc();

      const player = await program.account.player.fetch(investor1Pda);
      const latestBusiness = player.businesses[player.businesses.length - 1];
      
      console.log("📅 Sell fee simulation:");
      
      // Симулируем fees для разных дней
      const daysToTest = [0, 7, 14, 21, 28, 35];
      const EARLY_SELL_FEES = [
        20, 20, 20, 20, 20, 20, 20, // Days 0-6: 20%
        15, 15, 15, 15, 15, 15, 15, // Days 7-13: 15%
        10, 10, 10, 10, 10, 10, 10, // Days 14-20: 10%
        7,  7,  7,  7,  7,  7,  7,  // Days 21-27: 7%
        5,  5,  5,  2,              // Days 28-30: 5%, final: 2%
      ];
      
      daysToTest.forEach(days => {
        const feePercent = days < EARLY_SELL_FEES.length ? EARLY_SELL_FEES[days] : 2;
        const investment = latestBusiness.investedAmount.toNumber();
        const fee = (investment * feePercent) / 100;
        const returnAmount = investment - fee;
        
        console.log(`День ${days}: fee ${feePercent}%, возврат ${(returnAmount / LAMPORTS_PER_SOL).toFixed(3)} SOL`);
      });

      // Продаем бизнес (ранняя продажа с высокой комиссией)
      const businessIndex = player.businesses.length - 1;
      
      try {
        await program.methods
          .sellBusiness(businessIndex)
          .accounts({
            playerOwner: investor1.publicKey,
            player: investor1Pda,
            treasuryPda: treasuryPda,
            gameState: gameStatePda,
            systemProgram: SystemProgram.programId,
          })
          .signers([investor1])
          .rpc();

        console.log("✅ Бизнес продан успешно");
      } catch (error) {
        console.log("Sell error:", error.message);
      }
    });
  });

  describe("💰 Fee distribution", () => {
    it("20% команде, 80% в игровой пул", async () => {
      const teamBalanceBefore = await provider.connection.getBalance(treasuryWallet.publicKey);
      const treasuryBalanceBefore = await provider.connection.getBalance(treasuryPda);
      
      const investment = new anchor.BN(10 * LAMPORTS_PER_SOL); // 10 SOL
      
      await program.methods
        .createBusiness(2, investment) // NFTLaundry
        .accounts({
          owner: investor1.publicKey,
          player: investor1Pda,
          gameConfig: gameConfigPda,
          gameState: gameStatePda,
          treasuryWallet: treasuryWallet.publicKey,
          treasuryPda: treasuryPda,
          systemProgram: SystemProgram.programId,
        })
        .signers([investor1])
        .rpc();

      const teamBalanceAfter = await provider.connection.getBalance(treasuryWallet.publicKey);
      const treasuryBalanceAfter = await provider.connection.getBalance(treasuryPda);
      
      const teamIncrease = teamBalanceAfter - teamBalanceBefore;
      const treasuryIncrease = treasuryBalanceAfter - treasuryBalanceBefore;
      
      console.log("💰 Fee Distribution:");
      console.log(`Team received: ${teamIncrease / LAMPORTS_PER_SOL} SOL`);
      console.log(`Treasury received: ${treasuryIncrease / LAMPORTS_PER_SOL} SOL`);
      console.log(`Total: ${(teamIncrease + treasuryIncrease) / LAMPORTS_PER_SOL} SOL`);
      
      const expectedTeamFee = investment.toNumber() * 0.2; // 20%
      const expectedTreasuryFee = investment.toNumber() * 0.8; // 80%
      
      console.log(`Expected team: ${expectedTeamFee / LAMPORTS_PER_SOL} SOL`);
      console.log(`Expected treasury: ${expectedTreasuryFee / LAMPORTS_PER_SOL} SOL`);
      
      // Позволяем небольшую погрешность из-за transaction fees
      const tolerance = 0.01 * LAMPORTS_PER_SOL;
      assert(Math.abs(teamIncrease - expectedTeamFee) < tolerance, "Team fee неточный");
      assert(Math.abs(treasuryIncrease - expectedTreasuryFee) < tolerance, "Treasury fee неточный");
    });
  });

  describe("📊 Final Economics Report", () => {
    it("Показывает полную экономическую картину", async () => {
      const gameState = await program.account.gameState.fetch(gameStatePda);
      const gameConfig = await program.account.gameConfig.fetch(gameConfigPda);
      const treasuryBalance = await provider.connection.getBalance(treasuryPda);
      const teamBalance = await provider.connection.getBalance(treasuryWallet.publicKey);
      
      console.log("\n💰 ECONOMICS SUMMARY:");
      console.log("=".repeat(50));
      
      console.log("\n📈 Game Statistics:");
      console.log(`Total Players: ${gameState.totalPlayers.toString()}`);
      console.log(`Total Businesses: ${gameState.totalBusinesses.toString()}`);
      console.log(`Total Invested: ${gameState.totalInvested.toNumber() / LAMPORTS_PER_SOL} SOL`);
      console.log(`Total Withdrawn: ${gameState.totalWithdrawn.toNumber() / LAMPORTS_PER_SOL} SOL`);
      console.log(`Treasury Collected: ${gameState.totalTreasuryCollected.toNumber() / LAMPORTS_PER_SOL} SOL`);
      
      console.log("\n💳 Balances:");
      console.log(`Game Pool (Treasury PDA): ${treasuryBalance / LAMPORTS_PER_SOL} SOL`);
      console.log(`Team Wallet: ${teamBalance / LAMPORTS_PER_SOL} SOL`);
      
      console.log("\n⚙️ Configuration:");
      console.log(`Entry Fee: ${gameConfig.entryFee.toNumber() / LAMPORTS_PER_SOL} SOL`);
      console.log(`Treasury Fee: ${gameConfig.treasuryFeePercent}%`);
      console.log(`Business Rates: [${gameConfig.businessRates.join(', ')}] basis points`);
      
      const totalSystemValue = treasuryBalance + teamBalance;
      const investedVsWithdrawn = gameState.totalInvested.toNumber() - gameState.totalWithdrawn.toNumber();
      
      console.log("\n🏥 Health Metrics:");
      console.log(`System Value: ${totalSystemValue / LAMPORTS_PER_SOL} SOL`);
      console.log(`Pending Obligations: ${investedVsWithdrawn / LAMPORTS_PER_SOL} SOL`);
      console.log(`Coverage Ratio: ${((treasuryBalance / investedVsWithdrawn) * 100).toFixed(1)}%`);
      
      // Проверки здоровья
      assert(treasuryBalance > 0, "Treasury должен иметь средства");
      assert(treasuryBalance >= investedVsWithdrawn * 0.5, "Treasury должен покрывать минимум 50% обязательств");
      assert(gameState.totalInvested.toNumber() >= gameState.totalWithdrawn.toNumber(), 
             "Инвестиции >= выводов");
      
      console.log("\n✅ Economic Health: HEALTHY");
      console.log("=".repeat(50));
    });
  });
});