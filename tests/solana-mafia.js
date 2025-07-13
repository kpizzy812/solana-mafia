const anchor = require("@coral-xyz/anchor");

describe("solana-mafia", () => {
  // Configure the client to use the local cluster.
  anchor.setProvider(anchor.AnchorProvider.env());
  
  const program = anchor.workspace.SolanaMafia;
  const provider = anchor.getProvider();

  it("Initializes the game successfully", async () => {
    // Treasury wallet (можно использовать любой кошелек)
    const treasuryWallet = anchor.web3.Keypair.generate().publicKey;
    
    // Найдем PDA для GameState, GameConfig и Treasury
    const [gameStatePda] = anchor.web3.PublicKey.findProgramAddressSync(
      [Buffer.from("game_state")],
      program.programId
    );
    
    const [gameConfigPda] = anchor.web3.PublicKey.findProgramAddressSync(
      [Buffer.from("game_config")], 
      program.programId
    );

    const [treasuryPda] = anchor.web3.PublicKey.findProgramAddressSync(
      [Buffer.from("treasury")],
      program.programId
    );

    console.log("Game State PDA:", gameStatePda.toString());
    console.log("Game Config PDA:", gameConfigPda.toString());
    console.log("Treasury PDA:", treasuryPda.toString());
    console.log("Treasury Wallet:", treasuryWallet.toString());

    // Вызываем инструкцию initialize
    try {
      const tx = await program.methods
        .initialize(treasuryWallet)
        .accounts({
          authority: provider.wallet.publicKey,
          gameState: gameStatePda,
          gameConfig: gameConfigPda,
          treasuryPda: treasuryPda,
          systemProgram: anchor.web3.SystemProgram.programId,
        })
        .rpc();

      console.log("✅ Initialize transaction signature:", tx);

      // Проверяем что аккаунты создались
      const gameState = await program.account.gameState.fetch(gameStatePda);
      const gameConfig = await program.account.gameConfig.fetch(gameConfigPda);

      console.log("🎮 Game State:", {
        authority: gameState.authority.toString(),
        treasuryWallet: gameState.treasuryWallet.toString(),
        totalPlayers: gameState.totalPlayers.toString(),
        totalInvested: gameState.totalInvested.toString(),
        isPaused: gameState.isPaused,
      });

      console.log("⚙️ Game Config:", {
        authority: gameConfig.authority.toString(),
        entryFee: gameConfig.entryFee.toString(),
        treasuryFeePercent: gameConfig.treasuryFeePercent,
        maxBusinessesPerPlayer: gameConfig.maxBusinessesPerPlayer,
        registrationsOpen: gameConfig.registrationsOpen,
      });

      // Проверяем корректность данных
      console.assert(gameState.authority.equals(provider.wallet.publicKey), "Authority должен совпадать");
      console.assert(gameState.treasuryWallet.equals(treasuryWallet), "Treasury wallet должен совпадать");
      console.assert(gameState.totalPlayers.eq(new anchor.BN(0)), "Начальное количество игроков должно быть 0");
      console.assert(!gameState.isPaused, "Игра не должна быть на паузе");
      
      console.log("🎯 Все проверки прошли успешно!");

    } catch (error) {
      console.error("❌ Ошибка при инициализации:", error);
      throw error;
    }
  });

  it("Creates a business successfully", async () => {
    const treasuryWallet = anchor.web3.Keypair.generate().publicKey;
    
    // Получаем PDA
    const [gameStatePda] = anchor.web3.PublicKey.findProgramAddressSync(
      [Buffer.from("game_state")],
      program.programId
    );
    
    const [gameConfigPda] = anchor.web3.PublicKey.findProgramAddressSync(
      [Buffer.from("game_config")], 
      program.programId
    );

    const [treasuryPda] = anchor.web3.PublicKey.findProgramAddressSync(
      [Buffer.from("treasury")],
      program.programId
    );

    const [playerPda] = anchor.web3.PublicKey.findProgramAddressSync(
      [Buffer.from("player"), provider.wallet.publicKey.toBuffer()],
      program.programId
    );

    try {
      // Создаем бизнес типа 0 (CryptoKiosk) с депозитом 0.1 SOL
      const businessType = 0;
      const depositAmount = new anchor.BN(100_000_000); // 0.1 SOL
      const referrer = null;

      const tx = await program.methods
        .createBusiness(businessType, depositAmount, referrer)
        .accounts({
          owner: provider.wallet.publicKey,
          player: playerPda,
          gameConfig: gameConfigPda,
          gameState: gameStatePda,
          treasuryWallet: treasuryWallet,
          treasuryPda: treasuryPda,
          systemProgram: anchor.web3.SystemProgram.programId,
        })
        .rpc();

      console.log("✅ Create business transaction signature:", tx);

      // Проверяем созданного игрока
      const player = await program.account.player.fetch(playerPda);
      const gameState = await program.account.gameState.fetch(gameStatePda);

      console.log("👤 Player:", {
        owner: player.owner.toString(),
        hasPaidEntry: player.hasPaidEntry,
        totalInvested: player.totalInvested.toString(),
        pendingEarnings: player.pendingEarnings.toString(),
        businessesCount: player.businesses.length,
      });

      console.log("📊 Game State:", {
        totalPlayers: gameState.totalPlayers.toString(),
        totalInvested: gameState.totalInvested.toString(),
        totalBusinesses: gameState.totalBusinesses.toString(),
      });

      // Проверки
      console.assert(player.hasPaidEntry, "Игрок должен заплатить вступительный взнос");
      console.assert(player.businesses.length === 1, "У игрока должен быть 1 бизнес");
      console.assert(gameState.totalPlayers.eq(new anchor.BN(1)), "Должен быть 1 игрок");
      
      console.log("🏪 Бизнес создан успешно!");

    } catch (error) {
      console.error("❌ Ошибка при создании бизнеса:", error);
      throw error;
    }
  });
});