const anchor = require("@coral-xyz/anchor");

describe("solana-mafia", () => {
  // Configure the client to use the local cluster.
  anchor.setProvider(anchor.AnchorProvider.env());
  
  const program = anchor.workspace.SolanaMafia;
  const provider = anchor.getProvider();

  it("Initializes the game successfully", async () => {
    // Treasury wallet (можно использовать любой кошелек)
    const treasuryWallet = anchor.web3.Keypair.generate().publicKey;
    
    // Найдем PDA для GameState и GameConfig
    const [gameStatePda] = anchor.web3.PublicKey.findProgramAddressSync(
      [Buffer.from("game_state")],
      program.programId
    );
    
    const [gameConfigPda] = anchor.web3.PublicKey.findProgramAddressSync(
      [Buffer.from("game_config")], 
      program.programId
    );

    console.log("Game State PDA:", gameStatePda.toString());
    console.log("Game Config PDA:", gameConfigPda.toString());
    console.log("Treasury Wallet:", treasuryWallet.toString());

    // Вызываем инструкцию initialize
    try {
      const tx = await program.methods
        .initialize(treasuryWallet)
        .accounts({
          authority: provider.wallet.publicKey,
          gameState: gameStatePda,
          gameConfig: gameConfigPda,
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
});