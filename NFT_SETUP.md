# 🎨 Solana Mafia NFT Setup Guide

This guide explains how to set up real NFTs for your Solana Mafia game instead of placeholder URLs.

## 🚀 Quick Start

### Option 1: GitHub Raw URLs (Fastest)

1. **Update GitHub username** in the script:
   ```bash
   # Edit scripts/update-metadata-urls.js
   # Replace 'your-username' with your actual GitHub username
   ```

2. **Update URLs and build**:
   ```bash
   node scripts/update-metadata-urls.js
   anchor build
   ```

3. **Commit and push to GitHub**:
   ```bash
   git add metadata/
   git commit -m "Add NFT metadata and images"
   git push origin main
   ```

4. **Test NFT creation**:
   ```bash
   anchor test --skip-local-validator
   # or
   npm run test-nft
   ```

### Option 2: IPFS (Most Reliable)

1. **Install dependencies**:
   ```bash
   npm install pinata-sdk
   ```

2. **Sign up for Pinata** (free):
   - Go to https://pinata.cloud/
   - Get API keys from dashboard

3. **Set environment variables**:
   ```bash
   export PINATA_API_KEY="your-actual-key"
   export PINATA_SECRET_API_KEY="your-actual-secret"
   ```

4. **Upload to IPFS**:
   ```bash
   node scripts/upload-to-ipfs.js
   ```

5. **Update constants.rs** with generated IPFS URLs

6. **Build and test**:
   ```bash
   anchor build
   anchor test --skip-local-validator
   ```

## 📁 Generated Files

### Metadata Structure
```
metadata/
├── nft/
│   ├── lucky_strike_cigars_corner_stand.json
│   ├── lucky_strike_cigars_smoke_secrets.json
│   └── ... (24 total metadata files)
└── images/
    ├── lucky_strike_cigars_corner_stand.svg
    ├── lucky_strike_cigars_smoke_secrets.svg
    └── ... (24 total SVG images)
```

### NFT Features
- ✅ Proper Metaplex Token Metadata integration
- ✅ Dynamic names based on business type and level
- ✅ Unique serial numbers
- ✅ Level-based rarity attributes
- ✅ Business-specific imagery and themes
- ✅ Mafia-themed business names and descriptions

## 🔧 Business Types & Levels

| Business Type | Level 0 | Level 1 | Level 2 | Level 3 |
|---------------|---------|---------|---------|---------|
| **Lucky Strike Cigars** | Corner Stand | Smoke & Secrets | Cigar Lounge | Empire of Smoke |
| **Eternal Rest Funeral** | Quiet Departure | Silent Service | Final Solution | Legacy of Silence |
| **Midnight Motors Garage** | Street Repair | Custom Works | Underground Garage | Ghost Fleet |
| **Nonna's Secret Kitchen** | Family Recipe | Mama's Table | Don's Dining | Empire Feast |
| **Velvet Shadows Club** | Private Room | Exclusive Lounge | Shadow Society | Velvet Empire |
| **Angel's Mercy Foundation** | Helping Hand | Guardian Angel | Divine Intervention | Mercy Empire |

## 🧪 Testing

### Run NFT-specific tests:
```bash
# Test NFT creation and metadata
anchor test tests/nft-test.js --skip-local-validator

# Test on devnet
anchor test tests/nft-test.js --provider.cluster devnet
```

### Manual testing:
```bash
# Interactive testing toolkit
./manual-test.sh
```

## 🎨 Customizing NFT Images

The generated SVG images are placeholder designs. To create custom images:

1. **Replace SVG files** in `metadata/images/` with your designs
2. **Or convert to PNG**:
   ```bash
   # Install imagemagick or use online converter
   convert image.svg image.png
   ```
3. **Update file extensions** in metadata JSON files if needed
4. **Re-upload** to GitHub/IPFS

## 🔗 URL Structure

### GitHub Raw URLs:
```
https://raw.githubusercontent.com/USERNAME/REPO/main/metadata/nft/FILENAME.json
https://raw.githubusercontent.com/USERNAME/REPO/main/metadata/images/FILENAME.svg
```

### IPFS URLs:
```
https://gateway.pinata.cloud/ipfs/HASH/FILENAME.json
https://gateway.pinata.cloud/ipfs/HASH/FILENAME.svg
```

## 🚨 Important Notes

1. **Program Updates**: After changing URLs in `constants.rs`, you must rebuild and redeploy:
   ```bash
   anchor build
   anchor deploy --provider.cluster devnet
   ```

2. **Metadata Caching**: Some wallets/marketplaces cache metadata. Changes may take time to appear.

3. **IPFS Reliability**: IPFS is more reliable than GitHub Raw URLs for production use.

4. **Domain Migration**: When you get your domain, update all URLs in `constants.rs`.

## 🐛 Troubleshooting

### "Program failed to complete" errors:
- Check that Metaplex Token Metadata program is available
- Verify account sizes and rent exemption
- Ensure proper account derivations

### Metadata not loading:
- Check URL accessibility in browser
- Verify JSON format validity
- Confirm image URLs work independently

### NFT not appearing in wallets:
- Wait for metadata cache refresh
- Check if wallet supports Metaplex standard
- Verify token account has balance of 1

## 📚 Additional Resources

- [Metaplex Token Metadata Standard](https://docs.metaplex.com/programs/token-metadata/)
- [Solana NFT Guide](https://solanacookbook.com/guides/nfts.html)
- [Anchor Documentation](https://www.anchor-lang.com/)
- [Pinata IPFS Documentation](https://docs.pinata.cloud/)

## 🎯 Next Steps

After NFT setup is complete:

1. **Frontend Integration**: Update your frontend to display NFT images and metadata
2. **Marketplace Integration**: Ensure NFTs appear correctly on Solana NFT marketplaces
3. **Advanced Features**: Implement NFT staking, trading, or special utilities
4. **Analytics**: Track NFT creation, transfers, and marketplace activity