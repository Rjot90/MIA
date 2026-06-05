import os
import logging
import discord
from dotenv import load_dotenv
from discord_bridge import APIBridge
from discord_context import DiscordContextManager
from discord_handlers import MessageHandler

# Setup simple logging for the bot
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("discord_bot")

def main():
    # Load phase 2 environment variables if present
    load_dotenv('.env.phase2')
    # Fallback to .env if not found
    load_dotenv('.env')
    
    TOKEN = os.getenv("DISCORD_TOKEN")
    if not TOKEN or TOKEN == "your_token_here":
        logger.error("DISCORD_TOKEN is not set or invalid. Please check your .env.phase2 file.")
        return

    CHANNEL_ID = os.getenv("DISCORD_CHANNEL_ID", "")
    ADMIN_USERS = os.getenv("DISCORD_ADMIN_USERS", "")
    PREFIX = os.getenv("DISCORD_PREFIX", "!")
    API_URL = os.getenv("PHASE1_API_URL", "http://localhost:8000")
    ENDPOINT = os.getenv("PHASE1_INFER_ENDPOINT", "/api/infer")
    TIMEOUT = int(os.getenv("DISCORD_LATENCY_TIMEOUT", "45"))

    # Parse lists
    allowed_channels = [c.strip() for c in CHANNEL_ID.split(",") if c.strip()]
    admin_users = [u.strip() for u in ADMIN_USERS.split(",") if u.strip()]

    # Initialize components
    bridge = APIBridge(api_url=API_URL, endpoint=ENDPOINT, timeout=TIMEOUT)
    context_manager = DiscordContextManager(allowed_channels=allowed_channels, admin_users=admin_users)
    handler = MessageHandler(bridge=bridge, context_manager=context_manager, prefix=PREFIX)

    # Setup Discord Client
    intents = discord.Intents.default()
    intents.message_content = True  # Required to read message content
    
    client = discord.Client(intents=intents)

    @client.event
    async def on_ready():
        logger.info("=" * 50)
        logger.info(f"Bot connecté en tant que {client.user}")
        logger.info(f"Prefixe: {PREFIX}")
        logger.info(f"API Target: {API_URL}{ENDPOINT}")
        logger.info("=" * 50)

    @client.event
    async def on_message(message: discord.Message):
        await handler.handle_message(message, client)

    logger.info("Starting Discord bot...")
    try:
        client.run(TOKEN)
    except discord.errors.LoginFailure:
        logger.error("Impossible de se connecter à Discord. Vérifiez votre DISCORD_TOKEN.")
    except Exception as e:
        logger.error(f"Erreur inattendue: {e}")

if __name__ == "__main__":
    main()
