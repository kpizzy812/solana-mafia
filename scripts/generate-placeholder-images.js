const fs = require('fs');
const path = require('path');

// Business configuration
const BUSINESS_INFO = [
    { name: "Lucky Strike Cigars", emoji: "🚬", color: "#8B4513" },
    { name: "Eternal Rest Funeral", emoji: "⚰️", color: "#2F2F2F" },
    { name: "Midnight Motors Garage", emoji: "🔧", color: "#FF4500" },
    { name: "Nonna's Secret Kitchen", emoji: "🍝", color: "#DC143C" },
    { name: "Velvet Shadows Club", emoji: "🥃", color: "#4B0082" },
    { name: "Angel's Mercy Foundation", emoji: "👼", color: "#FFD700" }
];

const UPGRADE_NAMES = [
    ["Corner Stand", "Smoke & Secrets", "Cigar Lounge", "Empire of Smoke"],
    ["Quiet Departure", "Silent Service", "Final Solution", "Legacy of Silence"],
    ["Street Repair", "Custom Works", "Underground Garage", "Ghost Fleet"],
    ["Family Recipe", "Mama's Table", "Don's Dining", "Empire Feast"],
    ["Private Room", "Exclusive Lounge", "Shadow Society", "Velvet Empire"],
    ["Helping Hand", "Guardian Angel", "Divine Intervention", "Mercy Empire"]
];

const LEVEL_COLORS = ["#808080", "#C0C0C0", "#FFD700", "#FF6B35"];

function generateSVG(businessInfo, levelName, levelIndex) {
    const bgColor = LEVEL_COLORS[levelIndex];
    const businessColor = businessInfo.color;
    
    return `<svg width="400" height="400" xmlns="http://www.w3.org/2000/svg">
    <defs>
        <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" style="stop-color:${bgColor};stop-opacity:1" />
            <stop offset="100%" style="stop-color:${businessColor};stop-opacity:0.8" />
        </linearGradient>
        <filter id="shadow">
            <feDropShadow dx="2" dy="2" stdDeviation="3" flood-opacity="0.3"/>
        </filter>
    </defs>
    
    <!-- Background -->
    <rect width="400" height="400" fill="url(#bg)" rx="20"/>
    
    <!-- Border -->
    <rect x="10" y="10" width="380" height="380" fill="none" stroke="${businessColor}" stroke-width="4" rx="15"/>
    
    <!-- Business emoji/icon -->
    <text x="200" y="150" text-anchor="middle" font-size="80" fill="${businessColor}">${businessInfo.emoji}</text>
    
    <!-- Business name -->
    <text x="200" y="220" text-anchor="middle" font-family="Arial, sans-serif" font-size="18" font-weight="bold" fill="white" filter="url(#shadow)">${businessInfo.name}</text>
    
    <!-- Level name -->
    <text x="200" y="250" text-anchor="middle" font-family="Arial, sans-serif" font-size="16" fill="white" filter="url(#shadow)">${levelName}</text>
    
    <!-- Level indicator -->
    <text x="200" y="280" text-anchor="middle" font-family="Arial, sans-serif" font-size="14" fill="white" opacity="0.8">Level ${levelIndex}</text>
    
    <!-- Decorative elements based on level -->
    ${levelIndex >= 1 ? `<circle cx="50" cy="50" r="8" fill="${businessColor}" opacity="0.6"/>` : ''}
    ${levelIndex >= 2 ? `<circle cx="350" cy="50" r="8" fill="${businessColor}" opacity="0.6"/>` : ''}
    ${levelIndex >= 3 ? `<circle cx="50" cy="350" r="8" fill="${businessColor}" opacity="0.6"/>
                        <circle cx="350" cy="350" r="8" fill="${businessColor}" opacity="0.6"/>` : ''}
    
    <!-- Mafia symbol -->
    <text x="200" y="350" text-anchor="middle" font-family="Arial, sans-serif" font-size="12" fill="white" opacity="0.7">SOLANA MAFIA</text>
</svg>`;
}

function generateAllImages() {
    const imagesDir = path.join(__dirname, '..', 'metadata', 'images');
    
    if (!fs.existsSync(imagesDir)) {
        fs.mkdirSync(imagesDir, { recursive: true });
    }

    BUSINESS_INFO.forEach((businessInfo, businessIndex) => {
        UPGRADE_NAMES[businessIndex].forEach((levelName, levelIndex) => {
            const filename = businessInfo.name.toLowerCase()
                .replace(/[^a-z0-9\s]/g, '')
                .replace(/\s+/g, '_') + '_' + 
                levelName.toLowerCase()
                .replace(/[^a-z0-9\s]/g, '')
                .replace(/\s+/g, '_') + '.svg';

            const svg = generateSVG(businessInfo, levelName, levelIndex);
            const filePath = path.join(imagesDir, filename);
            
            fs.writeFileSync(filePath, svg);
            console.log(`Generated: ${filename}`);
        });
    });

    console.log('\n✅ All placeholder images generated!');
    console.log('\n📋 Next steps:');
    console.log('1. Convert SVG to PNG if needed (or use SVG directly)');
    console.log('2. Upload to GitHub repository');
    console.log('3. Update metadata JSON files with correct image URLs');
}

generateAllImages();