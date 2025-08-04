const fs = require('fs');
const path = require('path');

// Configuration - update with your GitHub username and repo name
const GITHUB_USERNAME = 'kpizzy812'; // ✅ Your GitHub username
const REPO_NAME = 'solana-mafia';

// Base URLs for GitHub Raw
const BASE_METADATA_URL = `https://raw.githubusercontent.com/${GITHUB_USERNAME}/${REPO_NAME}/main/metadata/nft/`;
const BASE_IMAGE_URL = `https://raw.githubusercontent.com/${GITHUB_USERNAME}/${REPO_NAME}/main/metadata/images/`;

function updateConstantsFile() {
    const constantsPath = path.join(__dirname, '..', 'programs', 'solana-mafia', 'src', 'constants.rs');
    let content = fs.readFileSync(constantsPath, 'utf8');
    
    // Generate new URIs array
    const newUris = [
        // Lucky Strike Cigars
        [
            `"${BASE_METADATA_URL}lucky_strike_cigars_corner_stand.json"`,
            `"${BASE_METADATA_URL}lucky_strike_cigars_smoke_secrets.json"`,
            `"${BASE_METADATA_URL}lucky_strike_cigars_cigar_lounge.json"`,
            `"${BASE_METADATA_URL}lucky_strike_cigars_empire_of_smoke.json"`
        ],
        // Eternal Rest Funeral
        [
            `"${BASE_METADATA_URL}eternal_rest_funeral_quiet_departure.json"`,
            `"${BASE_METADATA_URL}eternal_rest_funeral_silent_service.json"`,
            `"${BASE_METADATA_URL}eternal_rest_funeral_final_solution.json"`,
            `"${BASE_METADATA_URL}eternal_rest_funeral_legacy_of_silence.json"`
        ],
        // Midnight Motors Garage
        [
            `"${BASE_METADATA_URL}midnight_motors_garage_street_repair.json"`,
            `"${BASE_METADATA_URL}midnight_motors_garage_custom_works.json"`,
            `"${BASE_METADATA_URL}midnight_motors_garage_underground_garage.json"`,
            `"${BASE_METADATA_URL}midnight_motors_garage_ghost_fleet.json"`
        ],
        // Nonna's Secret Kitchen
        [
            `"${BASE_METADATA_URL}nonnas_secret_kitchen_family_recipe.json"`,
            `"${BASE_METADATA_URL}nonnas_secret_kitchen_mamas_table.json"`,
            `"${BASE_METADATA_URL}nonnas_secret_kitchen_dons_dining.json"`,
            `"${BASE_METADATA_URL}nonnas_secret_kitchen_empire_feast.json"`
        ],
        // Velvet Shadows Club
        [
            `"${BASE_METADATA_URL}velvet_shadows_club_private_room.json"`,
            `"${BASE_METADATA_URL}velvet_shadows_club_exclusive_lounge.json"`,
            `"${BASE_METADATA_URL}velvet_shadows_club_shadow_society.json"`,
            `"${BASE_METADATA_URL}velvet_shadows_club_velvet_empire.json"`
        ],
        // Angel's Mercy Foundation
        [
            `"${BASE_METADATA_URL}angels_mercy_foundation_helping_hand.json"`,
            `"${BASE_METADATA_URL}angels_mercy_foundation_guardian_angel.json"`,
            `"${BASE_METADATA_URL}angels_mercy_foundation_divine_intervention.json"`,
            `"${BASE_METADATA_URL}angels_mercy_foundation_mercy_empire.json"`
        ]
    ];

    // Replace the BUSINESS_NFT_URIS_BY_LEVEL array
    const oldPattern = /pub const BUSINESS_NFT_URIS_BY_LEVEL: \[\[&str; 4\]; 6\] = \[[\s\S]*?\];/;
    
    const newUrisString = `pub const BUSINESS_NFT_URIS_BY_LEVEL: [[&str; 4]; 6] = [
    // Lucky Strike Cigars - tobacco shop with secrets
    [
        ${newUris[0].join(',\n        ')},
    ],
    // Eternal Rest Funeral - funeral parlor for "disappearances"
    [
        ${newUris[1].join(',\n        ')},
    ],
    // Midnight Motors Garage - auto shop for untraceable vehicles
    [
        ${newUris[2].join(',\n        ')},
    ],
    // Nonna's Secret Kitchen - Italian restaurant for operation planning
    [
        ${newUris[3].join(',\n        ')},
    ],
    // Velvet Shadows Club - elite club for "family business"
    [
        ${newUris[4].join(',\n        ')},
    ],
    // Angel's Mercy Foundation - charity foundation for "assistance"
    [
        ${newUris[5].join(',\n        ')},
    ],
];`;

    content = content.replace(oldPattern, newUrisString);
    
    fs.writeFileSync(constantsPath, content);
    console.log('✅ Updated constants.rs with GitHub Raw URLs');
}

function updateMetadataFiles() {
    const metadataDir = path.join(__dirname, '..', 'metadata', 'nft');
    const files = fs.readdirSync(metadataDir).filter(f => f.endsWith('.json'));
    
    files.forEach(filename => {
        const filePath = path.join(metadataDir, filename);
        const metadata = JSON.parse(fs.readFileSync(filePath, 'utf8'));
        
        // Update image URLs
        const imageName = filename.replace('.json', '.svg');
        metadata.image = `${BASE_IMAGE_URL}${imageName}`;
        metadata.properties.files[0].uri = `${BASE_IMAGE_URL}${imageName}`;
        
        fs.writeFileSync(filePath, JSON.stringify(metadata, null, 2));
    });
    
    console.log('✅ Updated all metadata files with GitHub Raw image URLs');
}

// Main execution
if (GITHUB_USERNAME === 'your-username') {
    console.log('❌ Please update GITHUB_USERNAME in the script!');
    console.log('   Edit scripts/update-metadata-urls.js and replace "your-username" with your GitHub username');
    process.exit(1);
}

console.log(`🔄 Updating URLs for GitHub repository: ${GITHUB_USERNAME}/${REPO_NAME}`);
updateConstantsFile();
updateMetadataFiles();

console.log('\n📋 Next steps:');
console.log('1. Commit and push all metadata files to GitHub');
console.log('2. Test NFT creation on devnet');
console.log('3. Verify metadata is accessible via GitHub Raw URLs');