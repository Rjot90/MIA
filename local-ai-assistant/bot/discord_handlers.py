import logging
import discord
import re
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
        
        # Enlever toutes les mentions du bot proprement
        mention_pattern = f"<@!?{client.user.id}>"
        prompt = re.sub(mention_pattern, '', prompt).strip()

        if not prompt:
            await message.channel.send("Que puis-je faire pour toi ?")
            return
        
        if prompt.lower() in ["reset", "clear", "oublie tout"]:
            await message.channel.typing()
            success = await self.bridge.clear_history(str(message.author.id))
            if success:
                await message.reply("🧹 **Lavage de cerveau terminé !** J'ai tout oublié, on repart de zéro.")
            else:
                await message.reply("❌ Oups, impossible d'effacer ma mémoire. L'API est injoignable.")
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
                # Call the bridge to get AI response
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
                
                # --- AFFICHAGE DANS LE TERMINAL POUR DÉBUGGER ---
                print("\n" + "="*50)
                print(f"REQUÊTE DE {message.author.name} : {prompt}")
                print(f"RÉPONSE BRUTE DE L'IA :\n{text}")
                print("="*50 + "\n")
                
                if text:
                    # --- NETTOYAGE INTELLIGENT ---
                    if "<think>" in text:
                        if "</think>" in text:
                            # S'il a fini de réfléchir, on enlève la réflexion pour ne garder que la réponse
                            text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL).strip()
                        else:
                            # S'il n'a pas fini (coupé en plein milieu par manque de place)
                            # On retire juste la balise d'ouverture et on affiche ses pensées sur Discord !
                            text = text.replace("<think>", "⚠️ *[Réflexion inachevée - Manque de tokens]*\n").strip()
                    
                    if not text:
                        text = "*(Le modèle a réfléchi mais n'a pas produit de réponse finale)*"
                        
                    # Discord limits message length to 2000 chars. Smart chunking to avoid cutting words.
                    max_chunk_size = 1900
                    chunks = []
                    
                    # Split by lines first to try and keep formatting intact
                    lines = text.split('\n')
                    current_chunk = ""
                    
                    for line in lines:
                        # If a single line is too long, we have to hard-split it
                        if len(line) > max_chunk_size:
                            if current_chunk:
                                chunks.append(current_chunk)
                                current_chunk = ""
                            # Hard split the long line
                            for i in range(0, len(line), max_chunk_size):
                                chunks.append(line[i:i+max_chunk_size])
                        elif len(current_chunk) + len(line) + 1 > max_chunk_size:
                            chunks.append(current_chunk)
                            current_chunk = line + "\n"
                        else:
                            current_chunk += line + "\n"
                            
                    if current_chunk.strip():
                        chunks.append(current_chunk.strip())

                    for chunk in chunks:
                        if chunk:
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