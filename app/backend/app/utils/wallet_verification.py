"""
Solana wallet signature verification utilities.
Validates wallet ownership through cryptographic signatures.
"""

import base58
import json
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

import nacl.signing
import nacl.encoding
import structlog

logger = structlog.get_logger(__name__)


class WalletVerificationService:
    """Service for verifying Solana wallet signatures."""
    
    @staticmethod
    def verify_wallet_signature(
        wallet_address: str,
        signature: str,
        message: str,
        max_age_minutes: int = 10
    ) -> Dict[str, Any]:
        """
        Verify a wallet signature for authentication.
        
        Args:
            wallet_address: Solana wallet address (base58)
            signature: Base58 encoded signature
            message: Original message that was signed
            max_age_minutes: Maximum age of the message in minutes
            
        Returns:
            Dict with verification result and details
        """
        try:
            # Parse message if it's JSON
            try:
                message_data = json.loads(message)
                if isinstance(message_data, dict):
                    # Check timestamp if present
                    if 'timestamp' in message_data:
                        timestamp = datetime.fromtimestamp(message_data['timestamp'])
                        max_age = timedelta(minutes=max_age_minutes)
                        
                        if datetime.now() - timestamp > max_age:
                            return {
                                "valid": False,
                                "error": "Message timestamp is too old",
                                "details": f"Message older than {max_age_minutes} minutes"
                            }
                    
                    # Check wallet address in message
                    if 'wallet' in message_data and message_data['wallet'] != wallet_address:
                        return {
                            "valid": False,
                            "error": "Wallet address mismatch",
                            "details": "Message wallet doesn't match provided address"
                        }
                    
                    # Use the original message for verification
                    message_to_verify = message
                else:
                    message_to_verify = message
            except json.JSONDecodeError:
                message_to_verify = message
            
            # Decode the signature
            try:
                signature_bytes = base58.b58decode(signature)
            except Exception as e:
                return {
                    "valid": False,
                    "error": "Invalid signature format",
                    "details": f"Cannot decode signature: {str(e)}"
                }
            
            # Decode the wallet address to get public key
            try:
                public_key_bytes = base58.b58decode(wallet_address)
            except Exception as e:
                return {
                    "valid": False,
                    "error": "Invalid wallet address format",
                    "details": f"Cannot decode wallet address: {str(e)}"
                }
            
            # Verify the signature
            try:
                verify_key = nacl.signing.VerifyKey(public_key_bytes)
                message_bytes = message_to_verify.encode('utf-8')
                
                # Verify signature
                verify_key.verify(message_bytes, signature_bytes)
                
                return {
                    "valid": True,
                    "wallet_address": wallet_address,
                    "message": message_to_verify,
                    "verified_at": datetime.now().isoformat()
                }
                
            except nacl.exceptions.BadSignatureError:
                return {
                    "valid": False,
                    "error": "Invalid signature",
                    "details": "Signature verification failed"
                }
            except Exception as e:
                return {
                    "valid": False,
                    "error": "Verification error",
                    "details": f"Unexpected error during verification: {str(e)}"
                }
                
        except Exception as e:
            logger.error("Wallet verification failed", error=str(e))
            return {
                "valid": False,
                "error": "Verification failed",
                "details": f"Internal error: {str(e)}"
            }
    
    @staticmethod
    def generate_verification_message(
        wallet_address: str,
        purpose: str = "wallet_verification",
        additional_data: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generate a verification message for signing.
        
        Args:
            wallet_address: Solana wallet address
            purpose: Purpose of verification
            additional_data: Additional data to include
            
        Returns:
            JSON string to be signed
        """
        message_data = {
            "wallet": wallet_address,
            "purpose": purpose,
            "timestamp": int(datetime.now().timestamp()),
            "nonce": base58.b58encode(nacl.utils.random(16)).decode('utf-8')
        }
        
        if additional_data:
            message_data.update(additional_data)
        
        return json.dumps(message_data, sort_keys=True)
    
    @staticmethod
    def verify_wallet_linking_signature(
        wallet_address: str,
        signature: str,
        message: str,
        telegram_user_id: int
    ) -> Dict[str, Any]:
        """
        Verify wallet signature specifically for linking with Telegram account.
        
        Args:
            wallet_address: Solana wallet address
            signature: Base58 encoded signature
            message: Signed message
            telegram_user_id: Telegram user ID for linking
            
        Returns:
            Dict with verification result
        """
        try:
            # First, verify the basic signature
            verification = WalletVerificationService.verify_wallet_signature(
                wallet_address=wallet_address,
                signature=signature,
                message=message,
                max_age_minutes=10
            )
            
            if not verification["valid"]:
                return verification
            
            # Parse message to check linking-specific requirements
            try:
                message_data = json.loads(message)
                
                # Check purpose
                if message_data.get("purpose") != "link_telegram_account":
                    return {
                        "valid": False,
                        "error": "Invalid purpose",
                        "details": "Message purpose must be 'link_telegram_account'"
                    }
                
                # Check telegram user ID
                if message_data.get("telegram_user_id") != telegram_user_id:
                    return {
                        "valid": False,
                        "error": "Telegram user ID mismatch",
                        "details": "Message telegram_user_id doesn't match"
                    }
                
                return {
                    "valid": True,
                    "wallet_address": wallet_address,
                    "telegram_user_id": telegram_user_id,
                    "verified_at": datetime.now().isoformat(),
                    "linking_approved": True
                }
                
            except json.JSONDecodeError:
                return {
                    "valid": False,
                    "error": "Invalid message format",
                    "details": "Message must be valid JSON for wallet linking"
                }
                
        except Exception as e:
            logger.error("Wallet linking verification failed", error=str(e))
            return {
                "valid": False,
                "error": "Verification failed",
                "details": f"Internal error: {str(e)}"
            }
    
    @staticmethod
    def generate_linking_message(
        wallet_address: str,
        telegram_user_id: int,
        app_name: str = "Solana Mafia"
    ) -> str:
        """
        Generate a message for linking wallet to Telegram account.
        
        Args:
            wallet_address: Solana wallet address
            telegram_user_id: Telegram user ID
            app_name: Application name
            
        Returns:
            JSON string to be signed for linking
        """
        return WalletVerificationService.generate_verification_message(
            wallet_address=wallet_address,
            purpose="link_telegram_account",
            additional_data={
                "telegram_user_id": telegram_user_id,
                "app_name": app_name,
                "action": "link_accounts"
            }
        )


def verify_wallet_signature(
    wallet_address: str,
    signature: str,
    message: str,
    max_age_minutes: int = 10
) -> Dict[str, Any]:
    """
    Convenience function for wallet signature verification.
    
    Args:
        wallet_address: Solana wallet address
        signature: Base58 encoded signature
        message: Original message that was signed
        max_age_minutes: Maximum age of the message in minutes
        
    Returns:
        Dict with verification result
    """
    return WalletVerificationService.verify_wallet_signature(
        wallet_address=wallet_address,
        signature=signature,
        message=message,
        max_age_minutes=max_age_minutes
    )


def verify_linking_signature(
    wallet_address: str,
    signature: str,
    message: str,
    telegram_user_id: int
) -> Dict[str, Any]:
    """
    Convenience function for wallet linking verification.
    
    Args:
        wallet_address: Solana wallet address
        signature: Base58 encoded signature
        message: Signed message
        telegram_user_id: Telegram user ID
        
    Returns:
        Dict with verification result
    """
    return WalletVerificationService.verify_wallet_linking_signature(
        wallet_address=wallet_address,
        signature=signature,
        message=message,
        telegram_user_id=telegram_user_id
    )