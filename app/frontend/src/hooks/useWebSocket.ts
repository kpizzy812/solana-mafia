/**
 * WebSocket hook for real-time notifications using react-use-websocket
 */

import { useEffect, useCallback, useMemo } from 'react';
import useWebSocketLib, { ReadyState } from 'react-use-websocket';
import { toast } from 'react-hot-toast';

interface WebSocketMessage {
  type: string;
  timestamp: string;
  data: any;
}

interface SignatureProcessingEvent {
  type: 'signature_processing';
  signature: string;
  status: 'processing' | 'completed' | 'failed';
  timestamp: string;
  context?: {
    slot_index?: number;
    business_level?: number;
  };
  result?: any;
}

interface UseWebSocketProps {
  wallet: string | null;
  onSignatureProcessingUpdate?: (event: SignatureProcessingEvent) => void;
  onBusinessUpdate?: (data: any) => void;
  onEarningsUpdate?: (data: any) => void;
  onPlayerUpdate?: (data: any) => void;
  onPrestigeUpdate?: (data: any) => void;
  refetchData?: () => Promise<void>;
  enabled?: boolean;
}

interface UseWebSocketReturn {
  isConnected: boolean;
  isConnecting: boolean;
  connectionError: string | null;
  lastMessage: WebSocketMessage | null;
  sendMessage: (message: any) => void;
  reconnect: () => void;
}

const WS_URL = process.env.NEXT_PUBLIC_WS_URL || (
  process.env.NODE_ENV === 'production' 
    ? 'wss://your-domain.com/ws' 
    : 'ws://localhost:8000/ws'
);

export const useWebSocket = ({
  wallet,
  onSignatureProcessingUpdate,
  onBusinessUpdate,
  onEarningsUpdate,
  onPlayerUpdate,
  onPrestigeUpdate,
  refetchData,
  enabled = true
}: UseWebSocketProps): UseWebSocketReturn => {

  // Construct WebSocket URL
  const socketUrl = useMemo(() => {
    if (!enabled || !wallet) return null;
    // Ensure URL has /ws path before wallet address
    const baseUrl = WS_URL.endsWith('/ws') ? WS_URL : `${WS_URL}/ws`;
    return `${baseUrl}/${wallet}`;
  }, [wallet, enabled]);

  // Handle incoming messages
  const handleMessage = useCallback((event: MessageEvent) => {
    try {
      const message: WebSocketMessage = JSON.parse(event.data);
      
      console.log('📡 WebSocket message received:', message.type, message.data);
      
      // Handle different message types
      switch (message.type) {
        case 'event':
          const eventData = message.data;
          
          // Handle signature processing events
          if (eventData.type === 'signature_processing') {
            const signatureEvent: SignatureProcessingEvent = eventData;
            console.log('🎯 Signature processing event:', signatureEvent);
            
            onSignatureProcessingUpdate?.(signatureEvent);
            
            // Show completion notifications
            if (signatureEvent.status === 'completed') {
              toast.success(`Transaction completed! ${signatureEvent.signature.slice(0, 8)}...`);
              
              // Trigger data refetch on completion
              if (refetchData) {
                console.log('🔄 Triggering data refetch after WebSocket completion...');
                setTimeout(() => {
                  refetchData().catch(console.error);
                }, 1000);
              }
              
            } else if (signatureEvent.status === 'failed') {
              toast.error(`Transaction failed! ${signatureEvent.signature.slice(0, 8)}...`);
            }
          }
          break;
          
        case 'player_update':
          console.log('👤 Player update received:', message.data);
          onPlayerUpdate?.(message.data);
          break;
          
        case 'business_update':
          console.log('🏢 Business update received:', message.data);
          onBusinessUpdate?.(message.data);
          break;
          
        case 'earnings_update':
          console.log('💰 Earnings update received:', message.data);
          onEarningsUpdate?.(message.data);
          break;
          
        case 'prestige_update':
          console.log('💎 Prestige update received:', message.data);
          onPrestigeUpdate?.(message.data);
          break;
          
        case 'connection_status':
          if (message.data.status === 'connected') {
            console.log('✅ WebSocket connection confirmed');
          }
          break;
          
        case 'error':
          console.error('❌ WebSocket error message:', message.data);
          break;
          
        default:
          console.log('🔍 Unhandled WebSocket message type:', message.type);
      }
    } catch (error) {
      console.error('❌ Error parsing WebSocket message:', error);
    }
  }, [onSignatureProcessingUpdate, onBusinessUpdate, onEarningsUpdate, onPlayerUpdate, onPrestigeUpdate, refetchData]);

  // Configure WebSocket options
  const {
    sendMessage: sendMessageRaw,
    lastMessage,
    readyState,
    getWebSocket
  } = useWebSocketLib(
    socketUrl,
    {
      onOpen: () => {
        console.log('✅ WebSocket connected successfully');
        
        // Subscribe to relevant events after connection
        if (wallet) {
          sendMessageRaw(JSON.stringify({
            type: 'subscribe',
            events: ['event', 'player_update', 'business_update', 'earnings_update'],
            filters: { wallet }
          }));
        }
      },
      onClose: (event: CloseEvent) => {
        console.log('📡 WebSocket connection closed:', event.code, event.reason);
      },
      onError: (error: Event) => {
        console.error('❌ WebSocket error:', error);
      },
      onMessage: handleMessage,
      shouldReconnect: (closeEvent: CloseEvent) => {
        // Reconnect on all close events unless manually closed
        return enabled && closeEvent.code !== 1000;
      },
      reconnectAttempts: 5,
      reconnectInterval: (attemptNumber: number) => 
        Math.min(Math.pow(2, attemptNumber) * 1000, 10000), // Exponential backoff capped at 10s
      heartbeat: {
        message: JSON.stringify({ type: 'ping' }),
        returnMessage: JSON.stringify({ type: 'pong' }),
        timeout: 60000, // 1 minute timeout
        interval: 25000, // Ping every 25 seconds
      },
    },
    Boolean(enabled && wallet) // Ensure boolean value, always defined
  );

  // Enhanced sendMessage that handles JSON stringification
  const sendMessage = useCallback((message: any) => {
    if (readyState === ReadyState.OPEN) {
      sendMessageRaw(JSON.stringify(message));
    } else {
      console.warn('WebSocket is not connected, cannot send message:', message);
    }
  }, [sendMessageRaw, readyState]);

  // Connection state mapping
  const isConnected = readyState === ReadyState.OPEN;
  const isConnecting = readyState === ReadyState.CONNECTING;
  
  const connectionError = useMemo(() => {
    switch (readyState) {
      case ReadyState.CLOSED:
        return enabled && wallet ? 'Connection closed' : null;
      case ReadyState.UNINSTANTIATED:
        return enabled && wallet ? 'Connection failed to initialize' : null;
      default:
        return null;
    }
  }, [readyState, enabled, wallet]);

  // Manual reconnect function
  const reconnect = useCallback(() => {
    const ws = getWebSocket();
    if (ws && ws.readyState !== WebSocket.CONNECTING) {
      ws.close();
      // react-use-websocket will automatically reconnect
    }
  }, [getWebSocket]);

  // Parse and return last message as our interface expects
  const parsedLastMessage: WebSocketMessage | null = useMemo(() => {
    if (!lastMessage?.data) return null;
    
    try {
      if (typeof lastMessage.data === 'string') {
        return JSON.parse(lastMessage.data);
      }
      return lastMessage.data;
    } catch {
      return null;
    }
  }, [lastMessage]);

  return {
    isConnected,
    isConnecting,
    connectionError,
    lastMessage: parsedLastMessage,
    sendMessage,
    reconnect
  };
};