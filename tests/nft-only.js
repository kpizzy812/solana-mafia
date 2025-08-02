// tests/nft-only.js
// NFT Functions Testing for Solana Mafia

const anchor = require("@coral-xyz/anchor");
const { PublicKey, Keypair, SystemProgram } = require("@solana/web3.js");
const { TOKEN_PROGRAM_ID, ASSOCIATED_TOKEN_PROGRAM_ID, getAssociatedTokenAddress } = require("@solana/spl-token");
const { expect } = require("chai");
const BN = anchor.BN;

describe("🖼️ Solana Mafia - NFT Functions", () => {
  // Configure for devnet or localnet
  const cluster = process.env.ANCHOR_PROVIDER_URL || "https://api.devnet.solana.com";
  const connection = new anchor.web3.Connection(cluster, "confirmed");
  const wallet = anchor.Wallet.local();
  const provider = new anchor.AnchorProvider(connection, wallet, {});
  anchor.setProvider(provider);

  const program = anchor.workspace.SolanaMafia;

  // Test accounts
  let gameStatePda;
  let gameConfigPda;
  let treasuryPda;
  let playerPda;
  let businessNftPda;
  let nftMint;
  let nftTokenAccount;
  let nftMetadata;
  let treasuryWallet; // Will be loaded from game_state
  const TOKEN_METADATA_PROGRAM_ID = new PublicKey("metaqbxxUerdq28cj1RbAWkYQm3ybzjb6a8bt518x1s");
  
  // Business types from constants
  const BUSINESS_TYPES = {
    TOBACCO_SHOP: 0,
    FUNERAL_SERVICE: 1,
    CAR_WORKSHOP: 2,
    ITALIAN_RESTAURANT: 3,
    GENTLEMEN_CLUB: 4,
    CHARITY_FUND: 5
  };

  before(async () => {
    console.log("🔧 Setting up NFT test environment...");

    // Find PDAs
    [gameStatePda] = await PublicKey.findProgramAddress(
      [Buffer.from("game_state")],
      program.programId
    );

    [gameConfigPda] = await PublicKey.findProgramAddress(
      [Buffer.from("game_config")],
      program.programId
    );

    [treasuryPda] = await PublicKey.findProgramAddress(
      [Buffer.from("treasury")],
      program.programId
    );

    [playerPda] = await PublicKey.findProgramAddress(
      [Buffer.from("player"), wallet.publicKey.toBuffer()],
      program.programId
    );

    console.log("📍 PDAs found:");
    console.log(`   Game State: ${gameStatePda}`);
    console.log(`   Player: ${playerPda}`);
  });

  describe("🏗️ Setup & Prerequisites", () => {
    it("should have sufficient SOL balance", async () => {
      const balance = await provider.connection.getBalance(wallet.publicKey);
      console.log(`💰 Current balance: ${balance / 1e9} SOL`);
      
      // Нужно минимум 5 SOL для всех операций
      if (balance < 5e9) {
        throw new Error(`❌ Insufficient balance: ${balance / 1e9} SOL. Need at least 5 SOL. Run: solana airdrop 20`);
      }
      
      console.log("✅ Sufficient balance for testing");
    });

    it("should initialize game if not exists", async () => {
      try {
        const gameState = await program.account.gameState.fetch(gameStatePda);
        console.log("✅ Game already initialized");
        treasuryWallet = gameState.treasuryWallet; // Load treasury wallet from game state
        console.log(`   Authority: ${gameState.authority}`);
        console.log(`   Treasury: ${treasuryWallet}`);
      } catch (error) {
        console.log("🚀 Initializing game...");
        
        // Create new treasury wallet for initialization
        treasuryWallet = Keypair.generate().publicKey;
        
        await program.methods
          .initialize(treasuryWallet)
          .accounts({
            authority: wallet.publicKey,
            gameState: gameStatePda,
            gameConfig: gameConfigPda,
            treasuryPda: treasuryPda,
            systemProgram: SystemProgram.programId,
          })
          .rpc();
          
        console.log("✅ Game initialized");
        console.log(`   Treasury: ${treasuryWallet}`);
      }
    });

    it("should create player if not exists", async () => {
      try {
        const existingPlayer = await program.account.player.fetch(playerPda);
        console.log("✅ Player already exists");
        console.log(`   Player: ${existingPlayer.owner}`);
        console.log(`   Businesses: ${existingPlayer.businesses.length}`);
      } catch (error) {
        console.log("👤 Creating player...");
        
        try {
          await program.methods
            .createPlayer(null) // no referrer
            .accounts({
              owner: wallet.publicKey,
              player: playerPda,
              gameConfig: gameConfigPda,
              gameState: gameStatePda,
              treasuryWallet: treasuryWallet,
              systemProgram: SystemProgram.programId,
            })
            .rpc();
            
          console.log("✅ Player created successfully");
          
          // Verify player was created
          const newPlayer = await program.account.player.fetch(playerPda);
          console.log(`   Player: ${newPlayer.owner}`);
          console.log(`   Entry paid: ${newPlayer.hasPaidEntry}`);
          
        } catch (createError) {
          console.error("❌ Failed to create player:", createError.message);
          if (createError.logs) {
            console.error("Logs:", createError.logs);
          }
          throw createError;
        }
      }
    });
  });

  describe("🖼️ Create Business with NFT", () => {
    it("should check Token Metadata Program availability", async () => {
      try {
        const accountInfo = await provider.connection.getAccountInfo(TOKEN_METADATA_PROGRAM_ID);
        if (accountInfo) {
          console.log("✅ Token Metadata Program found");
        } else {
          console.log("⚠️ Token Metadata Program not found - this may cause issues");
        }
      } catch (error) {
        console.log("⚠️ Could not check Token Metadata Program");
      }
    });

    it("should create business and mint NFT successfully", async () => {
      console.log("🏪 Creating business with NFT...");

      // Generate new mint for NFT
      nftMint = Keypair.generate();
      
      // Calculate associated token address instead of creating keypair
      nftTokenAccount = await getAssociatedTokenAddress(
        nftMint.publicKey,
        wallet.publicKey
      );

      console.log(`🎯 NFT Mint: ${nftMint.publicKey}`);
      console.log(`🪙 Token Account: ${nftTokenAccount}`);

      // Find BusinessNFT PDA
      [businessNftPda] = await PublicKey.findProgramAddress(
        [Buffer.from("business_nft"), nftMint.publicKey.toBuffer()],
        program.programId
      );

      // Find metadata PDA
      [nftMetadata] = await PublicKey.findProgramAddress(
        [
          Buffer.from("metadata"),
          TOKEN_METADATA_PROGRAM_ID.toBuffer(),
          nftMint.publicKey.toBuffer(),
        ],
        TOKEN_METADATA_PROGRAM_ID
      );

      console.log(`📋 BusinessNFT PDA: ${businessNftPda}`);
      console.log(`📜 Metadata PDA: ${nftMetadata}`);

      // Create business with NFT
      const businessType = BUSINESS_TYPES.TOBACCO_SHOP; // 0.1 SOL minimum
      const depositAmount = new BN(100_000_000); // 0.1 SOL in lamports as BN

      console.log(`💰 Deposit amount: ${depositAmount.toString()} lamports`);
      console.log(`🏪 Business type: ${businessType}`);

      try {
        const txSignature = await program.methods
          .createBusinessWithNft(businessType, depositAmount)
          .accounts({
            owner: wallet.publicKey,
            player: playerPda,
            gameConfig: gameConfigPda,
            gameState: gameStatePda,
            treasuryWallet: treasuryWallet,
            treasuryPda: treasuryPda,
            nftMint: nftMint.publicKey,
            nftTokenAccount: nftTokenAccount,
            businessNft: businessNftPda,
            nftMetadata: nftMetadata,
            tokenProgram: TOKEN_PROGRAM_ID,
            associatedTokenProgram: ASSOCIATED_TOKEN_PROGRAM_ID,
            tokenMetadataProgram: TOKEN_METADATA_PROGRAM_ID,
            systemProgram: SystemProgram.programId,
            rent: anchor.web3.SYSVAR_RENT_PUBKEY,
          })
          .signers([nftMint]) // Only nftMint needs to sign, not token account
          .rpc();

        console.log(`✅ Business NFT created! TX: ${txSignature}`);
      } catch (error) {
        console.error("❌ Failed to create business NFT:");
        console.error("Error message:", error.message);
        if (error.logs) {
          console.error("Transaction logs:", error.logs);
        }
        throw error;
      }

      // Verify NFT was created
      const businessNftAccount = await program.account.businessNft.fetch(businessNftPda);
      
      expect(businessNftAccount.player.toString()).to.equal(wallet.publicKey.toString());
      expect(businessNftAccount.mint.toString()).to.equal(nftMint.publicKey.toString());
      expect(businessNftAccount.investedAmount.toNumber()).to.equal(depositAmount.toNumber());
      expect(businessNftAccount.isBurned).to.be.false;
      expect(businessNftAccount.serialNumber.toNumber()).to.be.greaterThan(0);

      console.log("🎯 NFT Details:");
      console.log(`   Player: ${businessNftAccount.player}`);
      console.log(`   Business Type: ${businessNftAccount.businessType.tobaccoShop !== undefined ? 'TobaccoShop' : 'Other'}`);
      console.log(`   Invested: ${businessNftAccount.investedAmount} lamports`);
      console.log(`   Serial #: ${businessNftAccount.serialNumber}`);
      console.log(`   Daily Rate: ${businessNftAccount.dailyRate} bp`);
    });

    it("should verify player has the business", async () => {
      const playerAccount = await program.account.player.fetch(playerPda);
      
      expect(playerAccount.businesses.length).to.be.greaterThan(0);
      
      const lastBusiness = playerAccount.businesses[playerAccount.businesses.length - 1];
      expect(lastBusiness.nftMint.toString()).to.equal(nftMint.publicKey.toString());
      expect(lastBusiness.isActive).to.be.true;

      console.log("✅ Player has business with NFT linked");
    });
  });

  describe("📊 Get Business NFT Data", () => {
    it("should read NFT data successfully", async () => {
      console.log("📖 Reading NFT data...");

      await program.methods
        .getBusinessNftData()
        .accounts({
          businessNft: businessNftPda,
        })
        .rpc();

      console.log("✅ NFT data retrieved (check logs for details)");
    });
  });

  describe("🔥 Sell Business with NFT Burn", () => {
    it("should sell business and burn NFT", async () => {
      console.log("🔥 Selling business and burning NFT...");

      // Get player account to find business index
      const playerAccount = await program.account.player.fetch(playerPda);
      const businessIndex = playerAccount.businesses.length - 1; // Last business

      const txSignature = await program.methods
        .sellBusinessWithNftBurn(businessIndex)
        .accounts({
          playerOwner: wallet.publicKey,
          player: playerPda,
          treasuryPda: treasuryPda,
          gameState: gameStatePda,
          nftMint: nftMint.publicKey,
          nftTokenAccount: nftTokenAccount,
          businessNft: businessNftPda,
          tokenProgram: TOKEN_PROGRAM_ID,
          systemProgram: SystemProgram.programId,
        })
        .rpc();

      console.log(`✅ Business sold and NFT burned! TX: ${txSignature}`);

      // Verify NFT is marked as burned
      const businessNftAccount = await program.account.businessNft.fetch(businessNftPda);
      expect(businessNftAccount.isBurned).to.be.true;

      console.log("🔥 NFT marked as burned in BusinessNFT account");

      // Verify business is deactivated
      const updatedPlayerAccount = await program.account.player.fetch(playerPda);
      const soldBusiness = updatedPlayerAccount.businesses[businessIndex];
      expect(soldBusiness.isActive).to.be.false;

      console.log("✅ Business deactivated in player account");
    });
  });

  describe("📈 Game State Updates", () => {
    it("should verify NFT counters in game state", async () => {
      const gameState = await program.account.gameState.fetch(gameStatePda);
      
      expect(gameState.totalNftsMinted.toNumber()).to.be.greaterThan(0);
      expect(gameState.totalNftsBurned.toNumber()).to.be.greaterThan(0);
      
      console.log("📊 Game State NFT Counters:");
      console.log(`   Total Minted: ${gameState.totalNftsMinted}`);
      console.log(`   Total Burned: ${gameState.totalNftsBurned}`);
      console.log(`   Serial Counter: ${gameState.nftSerialCounter}`);
    });
  });

  describe("🧪 Edge Cases", () => {
    it("should handle multiple NFT creation", async () => {
      console.log("🔄 Testing multiple NFT creation...");

      // Create second NFT business
      const secondNftMint = Keypair.generate();
      const secondTokenAccount = await getAssociatedTokenAddress(
        secondNftMint.publicKey,
        wallet.publicKey
      );

      const [secondBusinessNftPda] = await PublicKey.findProgramAddress(
        [Buffer.from("business_nft"), secondNftMint.publicKey.toBuffer()],
        program.programId
      );

      const [secondNftMetadata] = await PublicKey.findProgramAddress(
        [
          Buffer.from("metadata"),
          TOKEN_METADATA_PROGRAM_ID.toBuffer(),
          secondNftMint.publicKey.toBuffer(),
        ],
        TOKEN_METADATA_PROGRAM_ID
      );

      await program.methods
        .createBusinessWithNft(BUSINESS_TYPES.FUNERAL_SERVICE, new BN(500_000_000)) // 0.5 SOL as BN
        .accounts({
          owner: wallet.publicKey,
          player: playerPda,
          gameConfig: gameConfigPda,
          gameState: gameStatePda,
          treasuryWallet: treasuryWallet,
          treasuryPda: treasuryPda,
          nftMint: secondNftMint.publicKey,
          nftTokenAccount: secondTokenAccount,
          businessNft: secondBusinessNftPda,
          nftMetadata: secondNftMetadata,
          tokenProgram: TOKEN_PROGRAM_ID,
          associatedTokenProgram: ASSOCIATED_TOKEN_PROGRAM_ID,
          tokenMetadataProgram: TOKEN_METADATA_PROGRAM_ID,
          systemProgram: SystemProgram.programId,
          rent: anchor.web3.SYSVAR_RENT_PUBKEY,
        })
        .signers([secondNftMint]) // Only mint needs to sign
        .rpc();

      console.log("✅ Second NFT business created successfully");

      // Verify different serial numbers
      const firstNft = await program.account.businessNft.fetch(businessNftPda);
      const secondNft = await program.account.businessNft.fetch(secondBusinessNftPda);
      
      expect(secondNft.serialNumber.toNumber()).to.be.greaterThan(firstNft.serialNumber.toNumber());
      
      console.log(`🔢 Serial numbers: ${firstNft.serialNumber} -> ${secondNft.serialNumber}`);
    });
  });
});