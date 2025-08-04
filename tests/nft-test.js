const anchor = require("@coral-xyz/anchor");
const { PublicKey, Keypair, LAMPORTS_PER_SOL } = anchor.web3;
const { TOKEN_PROGRAM_ID, ASSOCIATED_TOKEN_PROGRAM_ID, getAssociatedTokenAddress } = require("@solana/spl-token");
const { Metadata } = require("@metaplex-foundation/mpl-token-metadata");

describe("solana-mafia-nft", () => {
  // Configure the client to use the local cluster
  anchor.setProvider(anchor.AnchorProvider.env());
  const program = anchor.workspace.SolanaMafia;
  const provider = anchor.getProvider();

  // Test accounts
  let gameStateAccount;
  let gameConfigAccount;
  let treasuryAccount;
  let playerAccount;
  let businessNFTAccount;
  let admin;

  before(async () => {
    admin = Keypair.generate();
    
    // Airdrop SOL to admin
    await provider.connection.requestAirdrop(admin.publicKey, 5 * LAMPORTS_PER_SOL);
    await new Promise(resolve => setTimeout(resolve, 1000));

    // Derive PDAs
    [gameStateAccount] = PublicKey.findProgramAddressSync(
      [Buffer.from("game_state")],
      program.programId
    );

    [gameConfigAccount] = PublicKey.findProgramAddressSync(
      [Buffer.from("game_config")],
      program.programId
    );

    [treasuryAccount] = PublicKey.findProgramAddressSync(
      [Buffer.from("treasury")],
      program.programId
    );

    [playerAccount] = PublicKey.findProgramAddressSync(
      [Buffer.from("player"), admin.publicKey.toBuffer()],
      program.programId
    );

    console.log("🔑 Test accounts prepared");
  });

  it("Initialize game", async () => {
    try {
      await program.methods
        .initializeGame()
        .accounts({
          gameState: gameStateAccount,
          gameConfig: gameConfigAccount,
          treasury: treasuryAccount,
          authority: admin.publicKey,
          systemProgram: anchor.web3.SystemProgram.programId,
        })
        .signers([admin])
        .rpc();

      console.log("✅ Game initialized");
    } catch (error) {
      console.log("ℹ️ Game already initialized or error:", error.message);
    }
  });

  it("Create player", async () => {
    try {
      await program.methods
        .createPlayer()
        .accounts({
          player: playerAccount,
          gameState: gameStateAccount,
          authority: admin.publicKey,
          systemProgram: anchor.web3.SystemProgram.programId,
        })
        .signers([admin])
        .rpc();

      console.log("✅ Player created");
    } catch (error) {
      console.log("ℹ️ Player already exists or error:", error.message);
    }
  });

  it("Create business with NFT", async () => {
    // Generate NFT mint keypair
    const nftMint = Keypair.generate();
    const nftTokenAccount = await getAssociatedTokenAddress(
      nftMint.publicKey,
      admin.publicKey
    );

    // Derive business NFT PDA
    [businessNFTAccount] = PublicKey.findProgramAddressSync(
      [Buffer.from("business_nft"), nftMint.publicKey.toBuffer()],
      program.programId
    );

    // Derive metadata PDA for Metaplex
    const [nftMetadata] = PublicKey.findProgramAddressSync(
      [
        Buffer.from("metadata"),
        new PublicKey("metaqbxxUerdq28cj1RbAWkYQm3ybzjb6a8bt518x1s").toBuffer(), // Metaplex program ID
        nftMint.publicKey.toBuffer(),
      ],
      new PublicKey("metaqbxxUerdq28cj1RbAWkYQm3ybzjb6a8bt518x1s")
    );

    const businessType = 0; // Lucky Strike Cigars
    const depositAmount = new anchor.BN(100_000_000); // 0.1 SOL
    const slotIndex = 0;

    try {
      const tx = await program.methods
        .createBusiness(businessType, depositAmount, slotIndex)
        .accounts({
          player: playerAccount,
          gameState: gameStateAccount,
          gameConfig: gameConfigAccount,
          treasuryWallet: treasuryAccount,
          businessNft: businessNFTAccount,
          nftMint: nftMint.publicKey,
          nftTokenAccount: nftTokenAccount,
          nftMetadata: nftMetadata,
          authority: admin.publicKey,
          tokenProgram: TOKEN_PROGRAM_ID,
          associatedTokenProgram: ASSOCIATED_TOKEN_PROGRAM_ID,
          tokenMetadataProgram: new PublicKey("metaqbxxUerdq28cj1RbAWkYQm3ybzjb6a8bt518x1s"),
          systemProgram: anchor.web3.SystemProgram.programId,
          rent: anchor.web3.SYSVAR_RENT_PUBKEY,
        })
        .signers([admin, nftMint])
        .rpc();

      console.log("✅ Business created with NFT!");
      console.log("📋 Transaction:", tx);
      console.log("🎨 NFT Mint:", nftMint.publicKey.toString());
      console.log("🏪 Business NFT Account:", businessNFTAccount.toString());

      // Wait for confirmation
      await provider.connection.confirmTransaction(tx);

      // Check NFT data
      const businessNFTData = await program.account.businessNft.fetch(businessNFTAccount);
      console.log("📊 Business NFT Data:", {
        player: businessNFTData.player.toString(),
        mint: businessNFTData.mint.toString(),
        businessType: businessNFTData.businessType,
        upgradeLevel: businessNFTData.upgradeLevel,
        dailyRate: businessNFTData.dailyRate,
        serialNumber: businessNFTData.serialNumber.toString(),
        isBurned: businessNFTData.isBurned,
      });

      // Check if NFT token exists
      const tokenAccountInfo = await provider.connection.getAccountInfo(nftTokenAccount);
      if (tokenAccountInfo) {
        console.log("✅ NFT token account created successfully");
        
        // Check token balance
        const tokenBalance = await provider.connection.getTokenAccountBalance(nftTokenAccount);
        console.log("🪙 NFT Balance:", tokenBalance.value.amount);
      }

      // Check metadata account
      const metadataAccountInfo = await provider.connection.getAccountInfo(nftMetadata);
      if (metadataAccountInfo) {
        console.log("✅ NFT metadata account created successfully");
        console.log("📄 Metadata account size:", metadataAccountInfo.data.length);
      }

    } catch (error) {
      console.error("❌ Failed to create business with NFT:", error);
      throw error;
    }
  });

  it("Get NFT data", async () => {
    try {
      // Use the business NFT account from previous test
      await program.methods
        .getBusinessNftData()
        .accounts({
          businessNft: businessNFTAccount,
        })
        .rpc();

      console.log("✅ NFT data retrieved successfully");
    } catch (error) {
      console.error("❌ Failed to get NFT data:", error);
    }
  });

  it("Upgrade business NFT", async () => {
    try {
      const slotIndex = 0;
      
      const tx = await program.methods
        .upgradeBusinessInSlot(slotIndex)
        .accounts({
          player: playerAccount,
          gameState: gameStateAccount,
          gameConfig: gameConfigAccount,
          businessNft: businessNFTAccount,
          authority: admin.publicKey,
          systemProgram: anchor.web3.SystemProgram.programId,
        })
        .signers([admin])
        .rpc();

      console.log("✅ Business NFT upgraded!");
      console.log("📋 Transaction:", tx);

      // Check updated NFT data
      const businessNFTData = await program.account.businessNft.fetch(businessNFTAccount);
      console.log("📊 Updated Business NFT Data:", {
        upgradeLevel: businessNFTData.upgradeLevel,
        dailyRate: businessNFTData.dailyRate,
      });

    } catch (error) {
      console.error("❌ Failed to upgrade business NFT:", error);
    }
  });
});

// Helper function to check NFT metadata via RPC
async function checkNFTMetadata(connection, metadataPDA) {
  try {
    const metadataAccount = await connection.getAccountInfo(metadataPDA);
    if (metadataAccount) {
      // Parse metadata using Metaplex library
      const metadata = Metadata.deserialize(metadataAccount.data);
      console.log("🎨 NFT Metadata:", {
        name: metadata[0].data.name,
        symbol: metadata[0].data.symbol,
        uri: metadata[0].data.uri,
        creators: metadata[0].data.creators,
      });
      return metadata[0];
    }
  } catch (error) {
    console.log("⚠️ Could not parse metadata:", error.message);
  }
}