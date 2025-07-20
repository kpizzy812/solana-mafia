const anchor = require("@coral-xyz/anchor");
const { SystemProgram, LAMPORTS_PER_SOL } = require("@solana/web3.js");
const assert = require("assert");

describe("⚡ QUICK ECONOMICS TEST", () => {
  const provider = anchor.AnchorProvider.env();
  anchor.setProvider(provider);
  const treasuryWallet = anchor.web3.Keypair.generate();
  
  let gameStatePda, gameConfigPda, treasuryPda;
  let testPlayer;
  let testPlayerPda;

  before(async () => {
    // Уникальные PDA для этого теста
    const testSeed = Date.now().toString();
    
    [gameStatePda] = await anchor.web3.PublicKey.findProgramAddress(
      [Buffer.from("game_state"), Buffer.from(testSeed)], program.programId
    );
    [gameConfigPda] = await anchor.web3.PublicKey.findProgramAddress(
      [Buffer.from("game_config"), Buffer.from(testSeed)], program.programId
    );
    [treasuryPda] = await anchor.web3.PublicKey.findProgramAddress(
      [Buffer.from("treasury"), Buffer.from(testSeed)], program.programId
    );

    testPlayer = anchor.web3.Keypair.generate();
    [testPlayerPda] = await anchor.web3.PublicKey.findProgramAddress(
      [Buffer.from("player"), testPlayer.publicKey.toBuffer()], program.programId
    );

    // Airdrop
    for (const keypair of [treasuryWallet, testPlayer]) {
      await provider.connection.confirmTransaction(
        await provider.connection.requestAirdrop(keypair.publicKey, 20 * LAMPORTS_PER_SOL)
      );
    }

    // Инициализация
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

    // Создание игрока
    await program.methods
      .createPlayer()
      .accounts({
        owner: testPlayer.publicKey,
        player: testPlayerPda,
        gameConfig: gameConfigPda,
        gameState: gameStatePda,
        treasuryWallet: treasuryWallet.publicKey,
        systemProgram: SystemProgram.programId,
      })
      .signers([testPlayer])
      .rpc();
  });

  it("Создает CryptoKiosk и проверяет экономику", async () => {
    const investment = new anchor.BN(1 * LAMPORTS_PER_SOL);
    
    await program.methods
      .createBusiness(0, investment)
      .accounts({
        owner: testPlayer.publicKey,
        player: testPlayerPda,
        gameConfig: gameConfigPda,
        gameState: gameStatePda,
        treasuryWallet: treasuryWallet.publicKey,
        treasuryPda: treasuryPda,
        systemProgram: SystemProgram.programId,
      })
      .signers([testPlayer])
      .rpc();

    const player = await program.account.player.fetch(testPlayerPda);
    const business = player.businesses[0];
    
    console.log("✅ Бизнес создан:", {
      type: "CryptoKiosk",
      invested: business.investedAmount.toString(),
      dailyRate: business.dailyRate,
      expectedDailyEarnings: (investment.toNumber() * 80) / 10000
    });

    assert.equal(business.dailyRate, 80);
    assert.equal(business.investedAmount.toNumber(), investment.toNumber());
  });

  it("Тестирует апгрейд", async () => {
    await program.methods
      .upgradeBusiness(0)
      .accounts({
        playerOwner: testPlayer.publicKey,
        player: testPlayerPda,
        treasuryWallet: treasuryWallet.publicKey,
        gameState: gameStatePda,
        gameConfig: gameConfigPda,
        systemProgram: SystemProgram.programId,
      })
      .signers([testPlayer])
      .rpc();

    const player = await program.account.player.fetch(testPlayerPda);
    const business = player.businesses[0];
    
    console.log("⬆️ После апгрейда:", {
      level: business.upgradeLevel,
      dailyRate: business.dailyRate
    });

    assert.equal(business.upgradeLevel, 1);
    assert(business.dailyRate > 80); // Должен увеличиться
  });

  it("Показывает экономическую статистику", async () => {
    const gameState = await program.account.gameState.fetch(gameStatePda);
    const treasuryBalance = await provider.connection.getBalance(treasuryPda);
    const teamBalance = await provider.connection.getBalance(treasuryWallet.publicKey);
    
    console.log("📊 ECONOMICS SUMMARY:");
    console.log(`Players: ${gameState.totalPlayers.toString()}`);
    console.log(`Businesses: ${gameState.totalBusinesses.toString()}`);
    console.log(`Invested: ${gameState.totalInvested.toNumber() / LAMPORTS_PER_SOL} SOL`);
    console.log(`Treasury: ${treasuryBalance / LAMPORTS_PER_SOL} SOL`);
    console.log(`Team: ${teamBalance / LAMPORTS_PER_SOL} SOL`);
    
    assert(gameState.totalInvested.toNumber() > 0);
    assert(treasuryBalance > 0);
  });
});
