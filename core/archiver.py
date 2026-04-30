import discord
from discord import Message, Member, Thread, AllowedMentions, Webhook, File, Embed

import aiohttp

from core.models import getLogger

logger = getLogger(__name__)
  
class ArchiveThreadLogger:

    def __init__(self, bot):
        self.bot = bot

    async def log_note_message(self, thread: Thread, message: Message) -> Message:
        if thread is None:
            return None
        return await thread.send(f"**Note made by {message.author.name}:**\n> {message.content}")
    
    async def log_staff_message(self, thread: Thread, message: Message) -> Message:
        if thread is None:
            return None
        return await thread.send(message)
    
    async def log_internal_message(self, thread: Thread, message: Message) -> Message:
        if thread is None:
            return None
        try:
            if self.bot.config["archive_webhook"] is None:
                return None
            avatar_url = None if message.author.avatar is None else message.author.avatar.url

            webhook_message = None
            async with aiohttp.ClientSession() as session:
                webhook = Webhook.from_url(
                    url=f'{self.bot.config["archive_webhook"]}?thread_id={thread.id}',
                    session=session
                )

                # Handle reply preview
                if message.reference and message.reference.resolved:
                    ref = message.reference.resolved
                    if isinstance(ref, Message):
                        if ref.content:
                            preview = ref.content.replace('\n', ' ')[:100]
                            reply_text = f'***Replying to:***\n> {preview}'
                        elif ref.attachments or ref.embeds:
                            reply_text = '***Replying to a message with no text content.***'
                        else:
                            reply_text = '***Replying to an unknown message.***'

                        await webhook.send(
                            content=reply_text,
                            thread=thread,
                            username=f'{message.author.name}',
                            avatar_url=avatar_url,
                            allowed_mentions=AllowedMentions.none()
                        )

                files = await ArchiveThreadLogger.gather_attachments(message)
                
                main_content = message.content[:2000] if message is not None else None
                trailing_content = message.content[2000:] if main_content is not None and len(message.content) > 2000 else None

                webhook_message = await webhook.send(
                    content=main_content,
                    files=files if trailing_content is None else None,
                    thread=thread,
                    avatar_url=avatar_url,
                    username=f'{message.author.name}',
                    allowed_mentions=AllowedMentions.none())
                
                if trailing_content is not None:
                    webhook_message = await webhook.send(
                        content=trailing_content,
                        files=files,
                        thread=thread,
                        avatar_url=avatar_url,
                        username=f'{message.author.name}',
                        allowed_mentions=AllowedMentions.none())

            return webhook_message
        except discord.HTTPException as e:
            if e.code == 10003:
                return None
            raise e
            

    async def log_closing_message(self, thread: Thread, message_content: str, closer_name: str, silent: bool = False) -> Message:
        if thread is None:
          return None
        embed = Embed(
            title=f"Closed by **{closer_name}**",
            description="The thread closed silently" if silent else message_content,
            color=self.bot.error_color,
            timestamp=discord.utils.utcnow())
        try:
          await thread.send(embed=embed)
        except discord.NotFound:
            pass
    
    async def log_thread_start(self, recipient: Member, creator: Member, thread: Thread = None):
        if thread is None:
            return None
        await thread.send(f"Thread created by{' the recepient' if creator == recipient else ''} <@{creator.id}>", allowed_mentions=AllowedMentions.none())

    async def archive_message_copy(self, thread: Thread, message: Message):
        if thread is None:
            return None
        files = await ArchiveThreadLogger.gather_attachments(message)
        try:
          return await thread.send(
              content=message.content,
              embeds=message.embeds,
              files=files
          )
        except discord.NotFound:
            pass
    
    # Gather attachments
    async def gather_attachments(message: Message) -> list[File]:
        files = []
        if message.attachments is not None:
            for attachment in message.attachments:
                file = await attachment.to_file()
                files.append(file)
        return files
