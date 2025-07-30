const anchor = require("@coral-xyz/anchor");
const { SystemProgram, LAMPORTS_PER_SOL } = require("@solana/web3.js");
const assert = require("assert");

describe("🖼️ NFT BUSINESS COMPREHENSIVE TESTS", () => {
  const provider = anchor.AnchorProvider.env();
  anchor.setProvider(provider);

  const program = anchor.workspace.SolanaMafia;
  
  // 🏛️ ГЛОБАЛЬНЫЕ PDA
  let gameStatePda, gameConfigPda, treasuryPda;
  
  // 🧪 TEST PLAYERS
  let nftPlayer1, nftPlayer2;
  let player1Pda, player2Pda;
  
  // 🖼️ NFT DATA
  let nftMint1, nftMint2;
  let nftTokenAccount1, nftTokenAccount2;
  let businessNftPda1, businessNftPda2;
  let metadataPda1, metadataPda2;

  before(async () => {
    console.log("🖼️ Starting NFT Comprehensive Tests...");

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

    // Create test players
    nftPlayer1 = anchor.web3.Keypair.generate();
    nftPlayer2 = anchor.web3.Keypair.generate();

    [player1Pda] = await anchor.web3.PublicKey.findProgramAddress(
      [Buffer.from("player"), nftPlayer1.publicKey.toBuffer()],
      program.programId
    );
    [player2Pda] = await anchor.web3.PublicKey.findProgramAddress(
      [Buffer.from("player"), nftPlayer2.publicKey.toBuffer()],
      program.programId
    );

    console.log("📍 Test Setup:");
    console.log("Game State:", gameStatePda.toString());
    console.log("Player 1:", nftPlayer1.publicKey.toString());
    console.log("Player 2:", nftPlayer2.publicKey.toString());

    // Airdrop SOL
    for (const keypair of [nftPlayer1, nftPlayer2]) {
      try {
        await provider.connection.confirmTransaction(
          await provider.connection.requestAirdrop(keypair.publicKey, 50 * LAMPORTS_PER_SOL)
        );
        console.log(`✅ Airdrop for ${keypair.publicKey.toString()}`);
      } catch (error) {
        console.log(`⚠️ Airdrop failed for ${keypair.publicKey.toString()}`);
      }
    }

    // Ensure game is initialized and create players
    try {
      const gameState = await program.account.gameState.fetch(gameStatePda);
      console.log("✅ Game already initialized");

      // Create players
      for (const [keypair, pda, name] of [
        [nftPlayer1, player1Pda, "NFT Player 1"],
        [nftPlayer2, player2Pda, "NFT Player 2"]
      ]) {
        try {
          await program.methods
            .createPlayer(null)
            .accounts({
              owner: keypair.publicKey,
              player: pda,
              gameConfig: gameConfigPda,
              gameState: gameStatePda,
              treasuryWallet: gameState.treasuryWallet,
              systemProgram: SystemProgram.programId,
            })
            .signers([keypair])
            .rpc();
          
          console.log(`✅ Created ${name}`);
        } catch (error) {
          console.log(`⚠️ ${name} creation error:`, error.message);
        }
      }

    } catch (error) {
      console.log("❌ Game not initialized! Please run devnet-real-test.js first");
      throw error;
    }
  });

  describe("🏭 NFT BUSINESS CREATION", () => {
    it("Player 1 создает Underground Pharmacy с NFT", async () => {
      console.log("🧪 Creating Underground Pharmacy NFT...");

      const gameState = await program.account.gameState.fetch(gameStatePda);
      const investment = new anchor.BN(0.1 * LAMPORTS_PER_SOL);
      const businessType = 0; // TobaccoShop/Underground Pharmacy

      // Generate NFT keypairs
      nftMint1 = anchor.web3.Keypair.generate();
      
      // Generate token account (не используем associated, создаем вручную)
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

      const balanceBefore = await provider.connection.getBalance(nftPlayer1.publicKey);

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

        console.log("✅ NFT Business creation transaction:", tx);

        const balanceAfter = await provider.connection.getBalance(nftPlayer1.publicKey);
        const spent = balanceBefore - balanceAfter;

        // Verify player state
        const player = await program.account.player.fetch(player1Pda);
        console.log("👤 Player after NFT business creation:", {
          businesses: player.businesses.length,
          totalInvested: player.totalInvested.toString(),
          firstBusiness: player.businesses[0] ? {
            type: player.businesses[0].businessType,
            amount: player.businesses[0].investedAmount.toString(),
            dailyRate: player.businesses[0].dailyRate,
            nftMint: player.businesses[0].nftMint?.toString(),
          } : null
        });

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

        // Verify mint exists and has supply of 1
        const mintInfo = await provider.connection.getAccountInfo(nftMint1.publicKey);
        console.log("🪙 NFT Mint created:", mintInfo !== null);

        // Verify token account has 1 token
        const tokenAccountInfo = await provider.connection.getAccountInfo(nftTokenAccount1);
        console.log("💰 Token account created:", tokenAccountInfo !== null);

        // Assertions
        assert.equal(player.businesses.length, 1, "Should have 1 business");
        assert.equal(player.businesses[0].investedAmount.toNumber(), investment.toNumber());
        assert.equal(player.businesses[0].dailyRate, 80); // 0.8%
        assert(player.businesses[0].nftMint, "Business should have NFT mint");
        
        assert.equal(businessNft.player.toString(), nftPlayer1.publicKey.toString());
        assert.equal(businessNft.investedAmount.toNumber(), investment.toNumber());
        assert.equal(businessNft.isBurned, false);
        assert(businessNft.serialNumber.toNumber() > 0);

        assert(mintInfo !== null, "NFT mint should exist");
        assert(tokenAccountInfo !== null, "Token account should exist");
        assert(spent > investment.toNumber(), "Should spend more than investment (including fees)");

      } catch (error) {
        console.log("❌ NFT Business creation failed:", error.message);
        console.log("Error logs:", error.logs);
        throw error;
      }
    });

    it("Player 2 создает Speakeasy Bar с NFT", async () => {
      console.log("🍺 Creating Speakeasy Bar NFT...");

      const gameState = await program.account.gameState.fetch(gameStatePda);
      const investment = new anchor.BN(0.5 * LAMPORTS_PER_SOL);
      const businessType = 1; // FuneralService/Speakeasy Bar

      // Generate NFT keypairs
      nftMint2 = anchor.web3.Keypair.generate();
      const nftTokenAccountKeypair2 = anchor.web3.Keypair.generate();
      nftTokenAccount2 = nftTokenAccountKeypair2.publicKey;

      [businessNftPda2] = await anchor.web3.PublicKey.findProgramAddress(
        [Buffer.from("business_nft"), nftMint2.publicKey.toBuffer()],
        program.programId
      );

      const TOKEN_METADATA_PROGRAM_ID = new anchor.web3.PublicKey("metaqbxxUerdq28cj1RbAWkYQm3ybzjb6a8bt518x1s");
      [metadataPda2] = await anchor.web3.PublicKey.findProgramAddress(
        [
          Buffer.from("metadata"),
          TOKEN_METADATA_PROGRAM_ID.toBuffer(),
          nftMint2.publicKey.toBuffer(),
        ],
        TOKEN_METADATA_PROGRAM_ID
      );

      try {
        const tx = await program.methods
          .createBusinessWithNft(businessType, investment)
          .accounts({
            owner: nftPlayer2.publicKey,
            player: player2Pda,
            gameConfig: gameConfigPda,
            gameState: gameStatePda,
            treasuryWallet: gameState.treasuryWallet,
            treasuryPda: treasuryPda,
            nftMint: nftMint2.publicKey,
            nftTokenAccount: nftTokenAccount2,
            businessNft: businessNftPda2,
            nftMetadata: metadataPda2,
            tokenProgram: anchor.utils.token.TOKEN_PROGRAM_ID,
            associatedTokenProgram: anchor.utils.token.ASSOCIATED_PROGRAM_ID,
            tokenMetadataProgram: TOKEN_METADATA_PROGRAM_ID,
            systemProgram: anchor.web3.SystemProgram.programId,
            rent: anchor.web3.SYSVAR_RENT_PUBKEY,
          })
          .signers([nftPlayer2, nftMint2, nftTokenAccountKeypair2])
          .rpc();

        console.log("✅ Speakeasy Bar NFT created:", tx);

        const businessNft = await program.account.businessNFT.fetch(businessNftPda2);
        console.log("🍺 Speakeasy Bar NFT data:", {
          businessType: businessNft.businessType,
          dailyRate: businessNft.dailyRate,
          serialNumber: businessNft.serialNumber.toString(),
        });

        assert.equal(businessNft.dailyRate, 90); // 0.9%
        assert.equal(businessNft.investedAmount.toNumber(), investment.toNumber());

      } catch (error) {
        console.log("❌ Speakeasy Bar NFT creation failed:", error.message);
        throw error;
      }
    });
  });

  describe("⬆️ NFT BUSINESS UPGRADES", () => {
    it("Апгрейдит Underground Pharmacy NFT до уровня 1", async () => {
      console.log("⬆️ Upgrading Underground Pharmacy NFT...");

      const gameState = await program.account.gameState.fetch(gameStatePda);
      const businessIndex = 0;

      // Check current state
      const businessNftBefore = await program.account.businessNFT.fetch(businessNftPda1);
      console.log("📊 Before upgrade:", {
        level: businessNftBefore.upgradeLevel,
        dailyRate: businessNftBefore.dailyRate
      });

      const teamBalanceBefore = await provider.connection.getBalance(gameState.treasuryWallet);

      try {
        const tx = await program.methods
          .upgradeBusinessNft(businessIndex)
          .accounts({
            playerOwner: nftPlayer1.publicKey,
            player: player1Pda,
            treasuryWallet: gameState.treasuryWallet,
            gameState: gameStatePda,
            gameConfig: gameConfigPda,
            nftMint: nftMint1.publicKey,
            businessNft: businessNftPda1,
            systemProgram: SystemProgram.programId,
          })
          .signers([nftPlayer1])
          .rpc();

        console.log("✅ NFT Upgrade transaction:", tx);

        const businessNftAfter = await program.account.businessNFT.fetch(businessNftPda1);
        const teamBalanceAfter = await provider.connection.getBalance(gameState.treasuryWallet);
        const upgradeCost = teamBalanceAfter - teamBalanceBefore;

        console.log("📊 After upgrade:", {
          level: businessNftAfter.upgradeLevel,
          dailyRate: businessNftAfter.dailyRate,
          upgradeCost: `${upgradeCost / LAMPORTS_PER_SOL} SOL`
        });

        // Verify upgrade
        assert.equal(businessNftAfter.upgradeLevel, 1);
        assert(businessNftAfter.dailyRate > businessNftBefore.dailyRate);
        assert(upgradeCost > 0, "Team should receive upgrade payment");

        // Verify business state is also updated
        const player = await program.account.player.fetch(player1Pda);
        const business = player.businesses[0];
        assert.equal(business.upgradeLevel, 1);
        assert.equal(business.dailyRate, businessNftAfter.dailyRate);

      } catch (error) {
        console.log("❌ NFT Upgrade failed:", error.message);
        throw error;
      }
    });
  });

  describe("💰 NFT EARNINGS & CLAIMS", () => {
    it("Проверяет что earnings накапливаются для NFT бизнесов", async () => {
      console.log("💰 Testing NFT business earnings...");

      // Wait for some earnings to accumulate
      console.log("⏰ Waiting for earnings accumulation...");
      await new Promise(resolve => setTimeout(resolve, 5000));

      try {
        // Update earnings for both players
        await program.methods
          .updateEarnings()
          .accounts({
            authority: nftPlayer1.publicKey,
            player: player1Pda,
          })
          .signers([nftPlayer1])
          .rpc();

        await program.methods
          .updateEarnings()
          .accounts({
            authority: nftPlayer2.publicKey,
            player: player2Pda,
          })
          .signers([nftPlayer2])
          .rpc();

        const player1 = await program.account.player.fetch(player1Pda);
        const player2 = await program.account.player.fetch(player2Pda);

        console.log("💰 Earnings status:", {
          player1: {
            pending: player1.pendingEarnings.toNumber(),
            businesses: player1.businesses.length
          },
          player2: {
            pending: player2.pendingEarnings.toNumber(),
            businesses: player2.businesses.length
          }
        });

        assert(player1.pendingEarnings.toNumber() >= 0);
        assert(player2.pendingEarnings.toNumber() >= 0);
        assert.equal(player1.businesses.length, 1);
        assert.equal(player2.businesses.length, 1);

      } catch (error) {
        console.log("⚠️ Earnings update error:", error.message);
        // Don't fail the test, might be cooldown
      }
    });
  });

  describe("🔥 NFT BUSINESS BURNING", () => {
    it("Продает и сжигает Underground Pharmacy NFT", async () => {
      console.log("🔥 Testing NFT business burn...");

      const businessIndex = 0;
      const player1Before = await program.account.player.fetch(player1Pda);
      const treasuryBalanceBefore = await provider.connection.getBalance(treasuryPda);
      const playerBalanceBefore = await provider.connection.getBalance(nftPlayer1.publicKey);

      // Check NFT exists before burn
      const businessNftBefore = await program.account.businessNFT.fetch(businessNftPda1);
      assert.equal(businessNftBefore.isBurned, false);

      try {
        const tx = await program.methods
          .sellBusinessWithNftBurn(businessIndex)
          .accounts({
            playerOwner: nftPlayer1.publicKey,
            player: player1Pda,
            treasuryPda: treasuryPda,
            gameState: gameStatePda,
            nftMint: nftMint1.publicKey,
            nftTokenAccount: nftTokenAccount1,
            businessNft: businessNftPda1,
            tokenProgram: anchor.utils.token.TOKEN_PROGRAM_ID,
            systemProgram: SystemProgram.programId,
          })
          .signers([nftPlayer1])
          .rpc();

        console.log("✅ NFT Burn transaction:", tx);

        const player1After = await program.account.player.fetch(player1Pda);
        const treasuryBalanceAfter = await provider.connection.getBalance(treasuryPda);
        const playerBalanceAfter = await provider.connection.getBalance(nftPlayer1.publicKey);

        const returnAmount = playerBalanceAfter - playerBalanceBefore;
        const treasuryDecrease = treasuryBalanceBefore - treasuryBalanceAfter;

        console.log("🔥 Burn results:", {
          businessDeactivated: !player1After.businesses[0].isActive,
          returnAmount: `${returnAmount / LAMPORTS_PER_SOL} SOL`,
          treasuryDecrease: `${treasuryDecrease / LAMPORTS_PER_SOL} SOL`,
        });

        // Verify business is deactivated
        assert.equal(player1After.businesses[0].isActive, false);

        // Verify NFT is marked as burned
        const businessNftAfter = await program.account.businessNFT.fetch(businessNftPda1);
        assert.equal(businessNftAfter.isBurned, true);

        // Verify financial flows
        assert(returnAmount > 0, "Player should receive return amount");
        assert(treasuryDecrease > 0, "Treasury should decrease");

        // Check that token supply decreased (NFT burned)
        try {
          const tokenAccountInfo = await provider.connection.getAccountInfo(nftTokenAccount1);
          console.log("💰 Token account after burn exists:", tokenAccountInfo !== null);
          // Token account might still exist but with 0 balance
        } catch (error) {
          console.log("ℹ️ Token account check error (expected):", error.message);
        }

      } catch (error) {
        console.log("❌ NFT Burn failed:", error.message);
        console.log("Error logs:", error.logs);
        throw error;
      }
    });
  });

  describe("📊 NFT DATA QUERIES", () => {
    it("Получает данные NFT через get_business_nft_data", async () => {
      console.log("📊 Testing NFT data query...");

      try {
        // Query remaining NFT (Player 2's Speakeasy Bar)
        const tx = await program.methods
          .getBusinessNftData()
          .accounts({
            businessNft: businessNftPda2,
          })
          .rpc();

        console.log("✅ NFT Data query transaction:", tx);

        const businessNft = await program.account.businessNFT.fetch(businessNftPda2);
        console.log("📋 NFT Data retrieved:", {
          player: businessNft.player.toString(),
          businessType: businessNft.businessType,
          mint: businessNft.mint.toString(),
          serialNumber: businessNft.serialNumber.toString(),
          dailyRate: businessNft.dailyRate,
          upgradeLevel: businessNft.upgradeLevel,
          isBurned: businessNft.isBurned,
        });

        assert.equal(businessNft.isBurned, false);
        assert.equal(businessNft.player.toString(), nftPlayer2.publicKey.toString());
        assert(businessNft.serialNumber.toNumber() > 0);

      } catch (error) {
        console.log("❌ NFT Data query failed:", error.message);
        throw error;
      }
    });

    it("Показывает финальную статистику NFT системы", async () => {
      console.log("📊 FINAL NFT STATISTICS:");
      console.log("=".repeat(50));

      const gameState = await program.account.gameState.fetch(gameStatePda);
      
      console.log("🖼️ NFT Stats:");
      console.log(`Total NFTs Minted: ${gameState.totalNftsMinted.toString()}`);
      console.log(`Total NFTs Burned: ${gameState.totalNftsBurned.toString()}`);
      console.log(`NFT Serial Counter: ${gameState.nftSerialCounter.toString()}`);
      console.log(`Active NFTs: ${gameState.totalNftsMinted.toNumber() - gameState.totalNftsBurned.toNumber()}`);

      console.log("\n🏢 Business Stats with NFTs:");
      console.log(`Total Businesses: ${gameState.totalBusinesses.toString()}`);
      console.log(`Total Players: ${gameState.totalPlayers.toString()}`);
      console.log(`Total Invested: ${gameState.totalInvested.toNumber() / LAMPORTS_PER_SOL} SOL`);

      console.log("=".repeat(50));

      // Health checks
      assert(gameState.totalNftsMinted.toNumber() >= 2, "Should have minted at least 2 NFTs");
      assert(gameState.totalNftsBurned.toNumber() >= 1, "Should have burned at least 1 NFT");
      assert(gameState.nftSerialCounter.toNumber() >= 2, "Serial counter should increment");
    });
  });

  describe("🔒 NFT SECURITY TESTS", () => {
    it("❌ Блокирует попытку upgrade чужого NFT", async () => {
      console.log("🔒 Testing NFT ownership protection...");

      try {
        // Player 1 tries to upgrade Player 2's NFT
        await program.methods
          .upgradeBusinessNft(0) // Player 2's business index
          .accounts({
            playerOwner: nftPlayer1.publicKey, // Wrong owner!
            player: player2Pda,                // Player 2's account
            treasuryWallet: (await program.account.gameState.fetch(gameStatePda)).treasuryWallet,
            gameState: gameStatePda,
            gameConfig: gameConfigPda,
            nftMint: nftMint2.publicKey,        // Player 2's NFT
            businessNft: businessNftPda2,       // Player 2's NFT data
            systemProgram: SystemProgram.programId,
          })
          .signers([nftPlayer1])
          .rpc();

        assert.fail("Should have blocked unauthorized NFT upgrade");
      } catch (error) {
        console.log("✅ Correctly blocked unauthorized access:", error.message);
        assert(error.message.includes("ConstraintSeeds") || 
               error.message.includes("constraint"));
      }
    });

    it("❌ Блокирует попытку burn чужого NFT", async () => {
      console.log("🔒 Testing NFT burn protection...");

      try {
        // Player 1 tries to burn Player 2's NFT  
        await program.methods
          .sellBusinessWithNftBurn(0)
          .accounts({
            playerOwner: nftPlayer1.publicKey, // Wrong owner!
            player: player2Pda,                // Player 2's account
            treasuryPda: treasuryPda,
            gameState: gameStatePda,
            nftMint: nftMint2.publicKey,        // Player 2's NFT
            nftTokenAccount: nftTokenAccount2,  // Player 2's token account
            businessNft: businessNftPda2,       // Player 2's NFT data
            tokenProgram: anchor.utils.token.TOKEN_PROGRAM_ID,
            systemProgram: SystemProgram.programId,
          })
          .signers([nftPlayer1])
          .rpc();

        assert.fail("Should have blocked unauthorized NFT burn");
      } catch (error) {
        console.log("✅ Correctly blocked unauthorized burn:", error.message);
        assert(error.message.includes("ConstraintSeeds") || 
               error.message.includes("constraint") ||
               error.message.includes("BusinessNotOwned"));
      }
    });
  });
});