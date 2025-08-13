const fs = require('fs');
const { Keypair } = require('@solana/web3.js');
const bs58 = require('bs58');

// Read the keypair file
const keypairArray = JSON.parse(fs.readFileSync('/Users/a1/.config/solana/id.json', 'utf8'));

// Create keypair from array
const keypair = Keypair.fromSecretKey(new Uint8Array(keypairArray));

// Convert to base58
const base58PrivateKey = bs58.encode(keypair.secretKey);

console.log('Public Key:', keypair.publicKey.toBase58());
console.log('Private Key (base58):', base58PrivateKey);
console.log('');
console.log('For Phantom wallet, use this base58 private key:');
console.log(base58PrivateKey);