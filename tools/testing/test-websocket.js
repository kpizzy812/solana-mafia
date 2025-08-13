/**
 * Simple WebSocket connection test script
 * Usage: node test-websocket.js [wallet_address]
 */

const WebSocket = require('ws');

const WALLET_ADDRESS = process.argv[2] || 'test_wallet_address';
const WS_URL = `ws://localhost:8001/ws/${WALLET_ADDRESS}`;

console.log('🔌 Testing WebSocket connection to:', WS_URL);
console.log('👛 Using wallet address:', WALLET_ADDRESS);
console.log('');

const ws = new WebSocket(WS_URL);

ws.on('open', () => {
    console.log('✅ WebSocket connection established');
    
    // Subscribe to events
    const subscribeMessage = {
        type: 'subscribe',
        events: ['event', 'player_update', 'business_update', 'earnings_update'],
        filters: { wallet: WALLET_ADDRESS }
    };
    
    console.log('📡 Sending subscription:', subscribeMessage);
    ws.send(JSON.stringify(subscribeMessage));
    
    // Send a ping message every 30 seconds
    const pingInterval = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) {
            console.log('🏓 Sending ping...');
            ws.send(JSON.stringify({ type: 'ping' }));
        }
    }, 30000);
    
    // Stop after 2 minutes for testing
    setTimeout(() => {
        console.log('⏰ Test completed - closing connection');
        clearInterval(pingInterval);
        ws.close();
    }, 120000);
});

ws.on('message', (data) => {
    try {
        const message = JSON.parse(data.toString());
        
        console.log('📨 Received message:');
        console.log('  Type:', message.type);
        console.log('  Data:', JSON.stringify(message.data, null, 2));
        
        if (message.type === 'event' && message.data.type === 'signature_processing') {
            console.log('🎯 SIGNATURE PROCESSING EVENT:');
            console.log('  Signature:', message.data.signature);
            console.log('  Status:', message.data.status);
            console.log('  Context:', message.data.context);
        }
        
        console.log('');
    } catch (error) {
        console.error('❌ Error parsing message:', error);
        console.log('Raw message:', data.toString());
    }
});

ws.on('close', (code, reason) => {
    console.log('📡 WebSocket connection closed');
    console.log('  Code:', code);
    console.log('  Reason:', reason.toString());
});

ws.on('error', (error) => {
    console.error('❌ WebSocket error:', error.message);
});

// Handle process termination
process.on('SIGINT', () => {
    console.log('\n🛑 Received SIGINT - closing WebSocket connection');
    ws.close();
    process.exit(0);
});

console.log('Press Ctrl+C to stop the test');
console.log('Test will automatically stop after 2 minutes');
console.log('---');