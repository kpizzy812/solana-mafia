// IPFS Upload Script using Pinata (free tier available)
// Install: npm install pinata-sdk
// Get API keys from: https://pinata.cloud/

const pinataSDK = require('pinata-sdk');
const fs = require('fs');
const path = require('path');

// Configuration - get these from Pinata dashboard
const PINATA_API_KEY = process.env.PINATA_API_KEY || 'your-pinata-api-key';
const PINATA_SECRET_API_KEY = process.env.PINATA_SECRET_API_KEY || 'your-pinata-secret-key';

const pinata = new pinataSDK(PINATA_API_KEY, PINATA_SECRET_API_KEY);

async function uploadToIPFS() {
    try {
        // Test authentication
        const result = await pinata.testAuthentication();
        console.log('✅ Pinata authentication successful:', result);

        // Upload images folder
        console.log('📤 Uploading images to IPFS...');
        const imagesPath = path.join(__dirname, '..', 'metadata', 'images');
        const imagesResult = await pinata.pinFromFS(imagesPath, {
            pinataMetadata: {
                name: 'Solana Mafia NFT Images'
            }
        });
        
        const imagesIPFSHash = imagesResult.IpfsHash;
        console.log(`✅ Images uploaded to IPFS: https://gateway.pinata.cloud/ipfs/${imagesIPFSHash}`);

        // Update metadata files with IPFS image URLs
        console.log('🔄 Updating metadata files with IPFS URLs...');
        const metadataDir = path.join(__dirname, '..', 'metadata', 'nft');
        const metadataFiles = fs.readdirSync(metadataDir).filter(f => f.endsWith('.json'));
        
        for (const filename of metadataFiles) {
            const filePath = path.join(metadataDir, filename);
            const metadata = JSON.parse(fs.readFileSync(filePath, 'utf8'));
            
            const imageName = filename.replace('.json', '.svg');
            const ipfsImageUrl = `https://gateway.pinata.cloud/ipfs/${imagesIPFSHash}/${imageName}`;
            
            metadata.image = ipfsImageUrl;
            metadata.properties.files[0].uri = ipfsImageUrl;
            
            fs.writeFileSync(filePath, JSON.stringify(metadata, null, 2));
        }

        // Upload metadata folder
        console.log('📤 Uploading metadata to IPFS...');
        const metadataPath = path.join(__dirname, '..', 'metadata', 'nft');
        const metadataResult = await pinata.pinFromFS(metadataPath, {
            pinataMetadata: {
                name: 'Solana Mafia NFT Metadata'
            }
        });
        
        const metadataIPFSHash = metadataResult.IpfsHash;
        console.log(`✅ Metadata uploaded to IPFS: https://gateway.pinata.cloud/ipfs/${metadataIPFSHash}`);

        // Generate new constants.rs content
        console.log('🔄 Generating updated constants.rs...');
        generateUpdatedConstants(metadataIPFSHash);

        console.log('\n🎉 IPFS Upload Complete!');
        console.log(`📁 Images IPFS Hash: ${imagesIPFSHash}`);
        console.log(`📄 Metadata IPFS Hash: ${metadataIPFSHash}`);
        console.log('\n📋 Next steps:');
        console.log('1. Update your constants.rs file with the new IPFS URLs');
        console.log('2. Rebuild and deploy your program');
        console.log('3. Test NFT creation');

    } catch (error) {
        console.error('❌ IPFS upload failed:', error);
        
        if (PINATA_API_KEY === 'your-pinata-api-key') {
            console.log('\n💡 Setup instructions:');
            console.log('1. Sign up for free at https://pinata.cloud/');
            console.log('2. Get your API keys from the dashboard');
            console.log('3. Set environment variables:');
            console.log('   export PINATA_API_KEY="your-actual-key"');
            console.log('   export PINATA_SECRET_API_KEY="your-actual-secret"');
            console.log('4. Or update the keys directly in this script');
        }
    }
}

function generateUpdatedConstants(metadataIPFSHash) {
    const baseUrl = `https://gateway.pinata.cloud/ipfs/${metadataIPFSHash}`;
    
    const filenames = [
        // Lucky Strike Cigars
        ['lucky_strike_cigars_corner_stand.json', 'lucky_strike_cigars_smoke_secrets.json', 'lucky_strike_cigars_cigar_lounge.json', 'lucky_strike_cigars_empire_of_smoke.json'],
        // Eternal Rest Funeral
        ['eternal_rest_funeral_quiet_departure.json', 'eternal_rest_funeral_silent_service.json', 'eternal_rest_funeral_final_solution.json', 'eternal_rest_funeral_legacy_of_silence.json'],
        // Midnight Motors Garage
        ['midnight_motors_garage_street_repair.json', 'midnight_motors_garage_custom_works.json', 'midnight_motors_garage_underground_garage.json', 'midnight_motors_garage_ghost_fleet.json'],
        // Nonna's Secret Kitchen
        ['nonnas_secret_kitchen_family_recipe.json', 'nonnas_secret_kitchen_mamas_table.json', 'nonnas_secret_kitchen_dons_dining.json', 'nonnas_secret_kitchen_empire_feast.json'],
        // Velvet Shadows Club
        ['velvet_shadows_club_private_room.json', 'velvet_shadows_club_exclusive_lounge.json', 'velvet_shadows_club_shadow_society.json', 'velvet_shadows_club_velvet_empire.json'],
        // Angel's Mercy Foundation
        ['angels_mercy_foundation_helping_hand.json', 'angels_mercy_foundation_guardian_angel.json', 'angels_mercy_foundation_divine_intervention.json', 'angels_mercy_foundation_mercy_empire.json']
    ];

    const constantsUpdate = `
// UPDATED IPFS URLs - Replace in your constants.rs file
pub const BUSINESS_NFT_URIS_BY_LEVEL: [[&str; 4]; 6] = [
    // Lucky Strike Cigars
    [
        "${baseUrl}/${filenames[0][0]}",
        "${baseUrl}/${filenames[0][1]}",
        "${baseUrl}/${filenames[0][2]}",
        "${baseUrl}/${filenames[0][3]}",
    ],
    // Eternal Rest Funeral
    [
        "${baseUrl}/${filenames[1][0]}",
        "${baseUrl}/${filenames[1][1]}",
        "${baseUrl}/${filenames[1][2]}",
        "${baseUrl}/${filenames[1][3]}",
    ],
    // Midnight Motors Garage
    [
        "${baseUrl}/${filenames[2][0]}",
        "${baseUrl}/${filenames[2][1]}",
        "${baseUrl}/${filenames[2][2]}",
        "${baseUrl}/${filenames[2][3]}",
    ],
    // Nonna's Secret Kitchen
    [
        "${baseUrl}/${filenames[3][0]}",
        "${baseUrl}/${filenames[3][1]}",
        "${baseUrl}/${filenames[3][2]}",
        "${baseUrl}/${filenames[3][3]}",
    ],
    // Velvet Shadows Club
    [
        "${baseUrl}/${filenames[4][0]}",
        "${baseUrl}/${filenames[4][1]}",
        "${baseUrl}/${filenames[4][2]}",
        "${baseUrl}/${filenames[4][3]}",
    ],
    // Angel's Mercy Foundation
    [
        "${baseUrl}/${filenames[5][0]}",
        "${baseUrl}/${filenames[5][1]}",
        "${baseUrl}/${filenames[5][2]}",
        "${baseUrl}/${filenames[5][3]}",
    ],
];`;

    fs.writeFileSync(path.join(__dirname, 'ipfs-constants-update.txt'), constantsUpdate);
    console.log('📝 Generated ipfs-constants-update.txt with new URLs');
}

// Check if pinata-sdk is installed
try {
    require.resolve('pinata-sdk');
    uploadToIPFS();
} catch (e) {
    console.log('📦 Installing pinata-sdk...');
    console.log('Run: npm install pinata-sdk');
    console.log('Then run this script again.');
}