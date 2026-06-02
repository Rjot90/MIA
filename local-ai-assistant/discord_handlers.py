import logging
import discord
from discord_bridge import APIBridge
from discord_context import DiscordContextManager

logger = logging.getLogger(__name__)

class MessageHandler:
    def __init__(self, bridge: APIBridge, context_manager: DiscordContextManager, prefix: str):
        self.bridge = bridge
        self.context = context_manager
        self.prefix = prefix

    async def handle_message(self, message: discord.Message, client: discord.Client):
        # Ignore messages from the bot itself
        if message.author == client.user:
            return

        # Check channel allowance
        if not self.context.is_channel_allowed(str(message.channel.id)):
            return

        content = message.content.strip()
        is_mention = client.user in message.mentions
        
        # Check if message is intended for the bot
        if not (content.startswith(self.prefix) or is_mention):
            # Allow DMs implicitly
            if not isinstance(message.channel, discord.DMChannel):
                return

        # Clean up the prompt
        prompt = content
        if prompt.startswith(self.prefix):
            prompt = prompt[len(self.prefix):].strip()
        elif is_mention:
            prompt = prompt.replace(f'<@{client.user.id}>', '').strip()

        if not prompt:
            await message.channel.send("Que puis-je faire pour toi ?")
            return

        # Concurrency check per user
        if not self.context.add_active_request(message.author.id):
            await message.channel.send("Veuillez patienter, je suis déjà en train de traiter votre requête précédente.")
            return

        try:
            # React to show we are processing
            await message.add_reaction("⏳")
            
            # Send typing indicator
            async with message.channel.typing():
                # Call the bridge
                response = await self.bridge.infer(
                    prompt=prompt,
                    user_id=str(message.author.id),
                    include_context=True
                )
                
                # Remove processing reaction
                try:
                    await message.remove_reaction("⏳", client.user)
                except:
                    pass

                if response is None:
                    await message.channel.send("❌ Désolé, une erreur de communication avec le serveur IA s'est produite.")
                    return
                
                if response.get("error") == "timeout":
                    await message.channel.send("⏱️ Le modèle met trop de temps à répondre (>45s). La requête a expirée.")
                    return
                
                text = response.get("text", "")
                if text:
                    import re
                    # Remove <think>...</think> blocks even if the closing tag is missing
                    text = re.sub(r'<think>.*?(</think>|$)', '', text, flags=re.DOTALL).strip()
                    # Remove any leftover tags just in case
                    text = text.replace('</think>', '').replace('<think>', '').strip()
                    
                    if not text:
                        text = "*(Le modèle a réfléchi mais n'a pas produit de réponse textuelle)*"
                        
                    # Discord limits message length to 2000 chars, so we chunk it if necessary
                    chunks = [text[i:i+1900] for i in range(0, len(text), 1900)]
                    for chunk in chunks:
                        await message.reply(chunk)
                else:
                    await message.channel.send("❌ La réponse générée est vide.")
                    
                # Mark as success
                await message.add_reaction("✅")

        except Exception as e:
            logger.error(f"Error handling message: {e}")
            await message.channel.send("❌ Une erreur interne est survenue.")
        finally:
            self.context.remove_active_request(message.author.id)
