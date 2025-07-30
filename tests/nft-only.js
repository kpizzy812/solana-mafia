const anchor = require("@coral-xyz/anchor");
const { SystemProgram, LAMPORTS_PER_SOL } = require("@solana/web3.js");
const assert = require("assert");

describe("🖼️ NFT TESTS ONLY", () => {
  const provider = anchor.AnchorProvider.env();
  anchor.setProvider(provider);

  const program = anchor.workspace.SolanaMafia;
  
  // 🏛️ ГЛОБАЛЬНЫЕ PDA
  let gameStatePda, gameConfigPda, treasuryPda;
  
  // 🧪 TEST PLAYERS
  let nftPlayer1;
  let player1Pda;
  
  // 🖼️ NFT DATA
  let nftMint1;
  let nftTokenAccount1;
  let businessNftPda1;
  let metadataPda1;

  before(async () => {
    console.log("🖼️ Starting NFT ONLY Tests...");
    console.log("Program ID:", program.programId.toString());

    // Global PDAs
    [gameStatePda] = await anchor.web3.PublicKey.findProgramAddress(
      [Buffer.from("game_state")],
      program.programId
    );
    [gameConfigPda] = await anchor.web3.PublicKey.findProgramAddress(
      [Buffer.from("game_config")],
      program.programId
    );
    [treasuryPda] = await anchor.web3.PublicKey.findProgramAddress(
      [Buffer.from("treasury")],
      program.programId
    );

    nftPlayer1 = anchor.web3.Keypair.generate();
    [player1Pda] = await anchor.web3.PublicKey.findProgramAddress(
      [Buffer.from("player"), nftPlayer1.publicKey.toBuffer()],
      program.programId
    );

    console.log("📍 PDAs:");
    console.log("Game State:", gameStatePda.toString());
    console.log("Player 1:", nftPlayer1.publicKey.toString());

    // 💰 Переводим SOL ВРУЧНУЮ (без airdrop)
    console.log("💰 MANUAL SOL TRANSFER NEEDED:");
    console.log(`Transfer 2 SOL to: ${nftPlayer1.publicKey.toString()}`);
    console.log("Use: solana transfer", nftPlayer1.publicKey.toString(), "2 --allow-unfunded-recipient");
    
    // Ждем 10 секунд для ручного перевода
    console.log("⏰ Waiting 10 seconds for manual transfer...");
    await new Promise(resolve => setTimeout(resolve, 10000));

    // Проверяем баланс
    const balance = await provider.connection.getBalance(nftPlayer1.publicKey);
    console.log(`Player balance: ${balance / LAMPORTS_PER_SOL} SOL`);
    
    if (balance < 1 * LAMPORTS_PER_SOL) {
      console.log("❌ Need more SOL! Please transfer manually and restart test.");
      return;
    }

    // 🎮 ИНИЦИАЛИЗАЦИЯ ИГРЫ (если еще не сделано)
    try {
      console.log("🎮 Checking if game exists...");
      await program.account.gameState.fetch(gameStatePda);
      console.log("✅ Game already exists");
    } catch (error) {
      console.log("🎮 Initializing game...");
      try {
        await program.methods
          .initialize(provider.wallet.publicKey) // Treasury wallet = current wallet
          .accounts({
            authority: provider.wallet.publicKey,
            gameState: gameStatePda,
            gameConfig: gameConfigPda,
            treasuryPda: treasuryPda,
            systemProgram: SystemProgram.programId,
          })
          .rpc();
        console.log("✅ Game initialized");
      } catch (initError) {
        console.log("⚠️ Game init error:", initError.message);
      }
    }

    // 👤 СОЗДАНИЕ ИГРОКА
    const gameState = await program.account.gameState.fetch(gameStatePda);
    try {
      await program.methods
        .createPlayer(null)
        .accounts({
          owner: nftPlayer1.publicKey,
          player: player1Pda,
          gameConfig: gameConfigPda,
          gameState: gameStatePda,
          treasuryWallet: gameState.treasuryWallet,
          systemProgram: SystemProgram.programId,
        })
        .signers([nftPlayer1])
        .rpc();
      
      console.log("✅ NFT Player created");
    } catch (error) {
      console.log("⚠️ Player creation error:", error.message);
    }
  });

  describe("🏭 NFT BUSINESS CREATION", () => {
    it("Создает Underground Pharmacy с NFT", async () => {
      console.log("🧪 Creating Underground Pharmacy NFT...");

      const gameState = await program.account.gameState.fetch(gameStatePda);
      const investment = new anchor.BN(0.1 * LAMPORTS_PER_SOL);
      const businessType = 0; // TobaccoShop

      // Generate NFT keypairs
      nftMint1 = anchor.web3.Keypair.generate();
      const nftTokenAccountKeypair1 = anchor.web3.Keypair.generate();
      nftTokenAccount1 = nftTokenAccountKeypair1.publicKey;

      // Business NFT PDA
      [businessNftPda1] = await anchor.web3.PublicKey.findProgramAddress(
        [Buffer.from("business_nft"), nftMint1.publicKey.toBuffer()],
        program.programId
      );

      // Metadata PDA
      const TOKEN_METADATA_PROGRAM_ID = new anchor.web3.PublicKey("metaqbxxUerdq28cj1RbAWkYQm3ybzjb6a8bt518x1s");
      [metadataPda1] = await anchor.web3.PublicKey.findProgramAddress(
        [
          Buffer.from("metadata"),
          TOKEN_METADATA_PROGRAM_ID.toBuffer(),
          nftMint1.publicKey.toBuffer(),
        ],
        TOKEN_METADATA_PROGRAM_ID
      );

      console.log("🔧 NFT Setup:");
      console.log("Mint:", nftMint1.publicKey.toString());
      console.log("Token Account:", nftTokenAccount1.toString());
      console.log("Business NFT PDA:", businessNftPda1.toString());

      try {
        const tx = await program.methods
          .createBusinessWithNft(businessType, investment)
          .accounts({
            owner: nftPlayer1.publicKey,
            player: player1Pda,
            gameConfig: gameConfigPda,
            gameState: gameStatePda,
            treasuryWallet: gameState.treasuryWallet,
            treasuryPda: treasuryPda,
            nftMint: nftMint1.publicKey,
            nftTokenAccount: nftTokenAccount1,
            businessNft: businessNftPda1,
            nftMetadata: metadataPda1,
            tokenProgram: anchor.utils.token.TOKEN_PROGRAM_ID,
            associatedTokenProgram: anchor.utils.token.ASSOCIATED_PROGRAM_ID,
            tokenMetadataProgram: TOKEN_METADATA_PROGRAM_ID,
            systemProgram: anchor.web3.SystemProgram.programId,
            rent: anchor.web3.SYSVAR_RENT_PUBKEY,
          })
          .signers([nftPlayer1, nftMint1, nftTokenAccountKeypair1])
          .rpc();

        console.log("✅ NFT Business creation SUCCESS:", tx);

        // Verify NFT data
        const businessNft = await program.account.businessNFT.fetch(businessNftPda1);
        console.log("🖼️ NFT Business data:", {
          player: businessNft.player.toString(),
          businessType: businessNft.businessType,
          mint: businessNft.mint.toString(),
          investedAmount: businessNft.investedAmount.toString(),
          serialNumber: businessNft.serialNumber.toString(),
          isBurned: businessNft.isBurned,
        });

        // Verify player state
        const player = await program.account.player.fetch(player1Pda);
        console.log("👤 Player state:", {
          businesses: player.businesses.length,
          totalInvested: player.totalInvested.toString(),
        });

        // Assertions
        assert.equal(businessNft.player.toString(), nftPlayer1.publicKey.toString());
        assert.equal(businessNft.investedAmount.toNumber(), investment.toNumber());
        assert.equal(businessNft.isBurned, false);
        assert(businessNft.serialNumber.toNumber() > 0);
        
        assert.equal(player.businesses.length, 1);
        assert.equal(player.businesses[0].investedAmount.toNumber(), investment.toNumber());

        console.log("🎉 NFT BUSINESS CREATION TEST PASSED!");

      } catch (error) {
        console.log("❌ NFT Business creation FAILED:");
        console.log("Error message:", error.message);
        if (error.logs) {
          console.log("Error logs:", error.logs);
        }
        throw error;
      }
    });
  });

  describe("📊 SIMPLE NFT STATUS", () => {
    it("Показывает статус NFT системы", async () => {
      try {
        const gameState = await program.account.gameState.fetch(gameStatePda);
        
        console.log("📊 NFT SYSTEM STATUS:");
        console.log("===================");
        console.log(`Total NFTs Minted: ${gameState.totalNftsMinted.toString()}`);
        console.log(`NFT Serial Counter: ${gameState.nftSerialCounter.toString()}`);
        console.log(`Total Businesses: ${gameState.totalBusinesses.toString()}`);
        console.log("===================");

        assert(gameState.totalNftsMinted.toNumber() >= 1, "Should have minted at least 1 NFT");
        
        console.log("✅ NFT STATUS CHECK PASSED!");
      } catch (error) {
        console.log("⚠️ Status check error:", error.message);
      }
    });
  });
});