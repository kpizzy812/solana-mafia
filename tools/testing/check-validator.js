#!/usr/bin/env node

const { Connection } = require('@solana/web3.js');

async function checkValidator() {
  const connections = [
    { name: 'Localhost', url: 'http://127.0.0.1:8899' },
    { name: 'Devnet', url: 'https://api.devnet.solana.com' }
  ];

  for (const { name, url } of connections) {
    try {
      console.log(`\n🔍 Checking ${name} (${url})...`);
      
      const connection = new Connection(url, 'confirmed');
      const version = await connection.getVersion();
      const slot = await connection.getSlot();
      
      console.log(`✅ ${name} is running`);
      console.log(`   Version: ${version['solana-core']}`);
      console.log(`   Current slot: ${slot}`);
      
    } catch (error) {
      console.log(`❌ ${name} is not accessible: ${error.message}`);
    }
  }

  // Check program deployments
  console.log('\n🔍 Checking program deployments...');
  
  const programs = [
    { name: 'Localnet Program', id: '3Ly6bEWRfKyVGwrRN27gHhBogo1K4HbZyk69KHW9AUx7', connection: new Connection('http://127.0.0.1:8899', 'confirmed') },
    { name: 'Devnet Program', id: 'HifXYhFJapXPeBgKKZu8gmdc7cZvfERJ9aEkchHxyBLS', connection: new Connection('https://api.devnet.solana.com', 'confirmed') }
  ];

  for (const { name, id, connection } of programs) {
    try {
      const { PublicKey } = require('@solana/web3.js');
      const programId = new PublicKey(id);
      const accountInfo = await connection.getAccountInfo(programId);
      
      if (accountInfo) {
        console.log(`✅ ${name} deployed`);
        console.log(`   Program ID: ${id}`);
        console.log(`   Owner: ${accountInfo.owner.toString()}`);
        console.log(`   Executable: ${accountInfo.executable}`);
      } else {
        console.log(`❌ ${name} not found`);
      }
    } catch (error) {
      console.log(`❌ ${name} check failed: ${error.message}`);
    }
  }
}

checkValidator().catch(console.error);