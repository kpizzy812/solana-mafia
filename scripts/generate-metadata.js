const fs = require('fs');
const path = require('path');

// Business configuration from your constants
const BUSINESS_NAMES = [
    "Lucky Strike Cigars",
    "Eternal Rest Funeral", 
    "Midnight Motors Garage",
    "Nonna's Secret Kitchen",
    "Velvet Shadows Club",
    "Angel's Mercy Foundation"
];

const BUSINESS_DESCRIPTIONS = [
    "A tobacco shop that serves as the perfect cover for family business operations.",
    "A funeral parlor providing discreet services for those who need to 'disappear'.",
    "An auto shop specializing in untraceable vehicle modifications.",
    "An Italian restaurant where important family meetings take place.",
    "An elite club for conducting exclusive 'family business'.",
    "A charity foundation providing 'assistance' to those in need."
];

const UPGRADE_NAMES = [
    ["Corner Stand", "Smoke & Secrets", "Cigar Lounge", "Empire of Smoke"],
    ["Quiet Departure", "Silent Service", "Final Solution", "Legacy of Silence"],
    ["Street Repair", "Custom Works", "Underground Garage", "Ghost Fleet"],
    ["Family Recipe", "Mama's Table", "Don's Dining", "Empire Feast"],
    ["Private Room", "Exclusive Lounge", "Shadow Society", "Velvet Empire"],
    ["Helping Hand", "Guardian Angel", "Divine Intervention", "Mercy Empire"]
];

const BASE_RATES = [80, 90, 100, 80, 90, 100]; // basis points
const RARITIES = ["Common", "Uncommon", "Rare", "Legendary"];

// Generate metadata for all businesses and levels
function generateAllMetadata() {
    const metadataDir = path.join(__dirname, '..', 'metadata', 'nft');
    
    if (!fs.existsSync(metadataDir)) {
        fs.mkdirSync(metadataDir, { recursive: true });
    }

    BUSINESS_NAMES.forEach((businessName, businessIndex) => {
        UPGRADE_NAMES[businessIndex].forEach((levelName, levelIndex) => {
            const filename = businessName.toLowerCase()
                .replace(/[^a-z0-9\s]/g, '')
                .replace(/\s+/g, '_') + '_' + 
                levelName.toLowerCase()
                .replace(/[^a-z0-9\s]/g, '')
                .replace(/\s+/g, '_') + '.json';

            const rate = (BASE_RATES[businessIndex] + (levelIndex * 10)) / 100; // Convert to percentage
            
            const metadata = {
                name: `${levelName} ${businessName} #{{SERIAL}}`,
                symbol: "MAFIA",
                description: `${BUSINESS_DESCRIPTIONS[businessIndex]} Level ${levelIndex} business in the Solana Mafia game.`,
                image: `https://raw.githubusercontent.com/your-username/solana-mafia/main/metadata/images/${filename.replace('.json', '.png')}`,
                attributes: [
                    {
                        trait_type: "Business Type",
                        value: businessName
                    },
                    {
                        trait_type: "Level",
                        value: levelName
                    },
                    {
                        trait_type: "Upgrade Level",
                        value: levelIndex
                    },
                    {
                        trait_type: "Daily Rate",
                        value: `${rate}%`
                    },
                    {
                        trait_type: "Rarity",
                        value: RARITIES[levelIndex]
                    },
                    {
                        trait_type: "Game",
                        value: "Solana Mafia"
                    }
                ],
                properties: {
                    category: "image",
                    files: [
                        {
                            uri: `https://raw.githubusercontent.com/your-username/solana-mafia/main/metadata/images/${filename.replace('.json', '.png')}`,
                            type: "image/png"
                        }
                    ]
                }
            };

            const filePath = path.join(metadataDir, filename);
            fs.writeFileSync(filePath, JSON.stringify(metadata, null, 2));
            console.log(`Generated: ${filename}`);
        });
    });

    console.log('\n✅ All metadata files generated!');
    console.log('\n📋 Next steps:');
    console.log('1. Create placeholder images for each NFT');
    console.log('2. Upload to GitHub or IPFS');
    console.log('3. Update constants.rs with correct URLs');
}

generateAllMetadata();