from bot.fmt import Formatter
from bot.manager import Manager, MessageContext
from bot.db import DB
import argparse
import json
import traceback
import asyncio
from bot import config as bc

class CommandProcessor:
    
    fmd: Formatter = Formatter()
    mng: Manager = None
    db: DB = None

    def __init__(self, bot, db):
        self.mng = Manager(bot, db=db)
        self.db = db
        
    async def command_chat(self, mc: MessageContext):
        """
        View edit and manage the current chat object and its settings 
        """
        parser = argparse.ArgumentParser(prog='Hal9003 `chat` command')
        parser.add_argument('--key', type=str, default=None)
        parser.add_argument('--set', type=str, default=None)
        

        async def _run_command(args):
            await self.mng.debugSend(f"Running chat command with subcommand: {args}", mc)
            
            if (not args.key) and (not args.set):
                chat_settings, _ = await self.db.getOrCreateChatSettings(mc.chat.uuid, mc=mc)
                pretty_settings_json = await self.fmd.wrap_code(json.dumps(chat_settings.to_dict(), indent=4))
                await self.mng.sendChatMessage(mc, f"Chat settings for `{mc.chat.uuid}`\n{pretty_settings_json}")
            elif args.key and (not args.set):
                chat_settings, _ = await self.db.getOrCreateChatSettings(mc.chat.uuid, mc=mc)
                cs = chat_settings.to_dict()
                keys = args.key.split('.')
                dictionary = cs
                try:
                    for key in keys:
                        dictionary = dictionary[key]
                    await self.mng.sendChatMessage(mc, f"Chat setting `{args.key}`: `{dictionary}`")
                except KeyError:
                    await self.mng.sendChatMessage(mc, f"Chat setting `{args.key}` not found")
            elif args.key and args.set:
                chat_settings, _ = await self.db.getOrCreateChatSettings(mc.chat.uuid, mc=mc)
                cs = chat_settings.to_dict()
                keys = args.key.split('.')
                dictionary = cs
                try:
                    assert len(keys) == 2 and (keys[0] == 'config'), "Only setting 'config' allowed"
                    cs, config = await self.db.updateChatSettingsConfigKey(mc.chat.uuid, keys[-1], args.set, mc=mc)
                    pretty_settings_json = await self.fmd.wrap_code(json.dumps(cs.to_dict(), indent=4))
                    await self.mng.sendChatMessage(mc, f"Chat setting `{args.key}` set to: `{args.set}`\n{pretty_settings_json}")
                except KeyError:
                    await self.mng.sendChatMessage(mc, f"Chat setting `{args.key}` not found")
        
        return parser, _run_command
    
    async def command_flush(self, mc: MessageContext):
        """
        Flushes the db
        """
        async def _run_command(args):
            await self.db.flush()
            await self.mng.sendChatMessage(mc, "DB flushed")
        
        parser = argparse.ArgumentParser(prog='Flush command')
        return parser, _run_command

    async def command_ping(self, mc: MessageContext):
        """
        Pings the chat with a simple message
        """
        async def _run_command(args):
            for i in range(args.loop):
                await self.mng.sendChatMessage(mc, f"Pong! {i+1}")
                await asyncio.sleep(1)

        parser = argparse.ArgumentParser(prog='Ping Command')
        parser.add_argument('--loop', type=int, default=1)
        
        return parser, _run_command

    async def command_intend(self, mc: MessageContext):
        """
        Intend 
        """
        
        async def _run_command(args):
            intend_model = "meta-llama/Meta-Llama-3-70B-Instruct"
            await self.mng.sendPartialMessage(mc, f"Checking Intend ...")
            await self.mng.debugSend(f"Running intend command with subcommand: {args}", mc)
            from agent.paralel_intend_and_extract import intend_extract_paralel_json
            res = intend_extract_paralel_json(
                prompt=args.query,
                models=[intend_model],
                batch_size=2
            )
            await self.mng.debugSend(f"Intend results: {res}", mc)
            tool_pick = res["tool_pick"]
            extraction_pick = res["extraction_pick"]
            pretty_res = await self.fmd.wrap_code(json.dumps(extraction_pick['parsed'], indent=4))
            await self.mng.sendChatMessage(mc, f"Intend check resulted in:\n - Tool pick: `{tool_pick}`\n - Extraction pick: \n{pretty_res}")

        parser = argparse.ArgumentParser(prog='Intend checker')
        parser.add_argument('--query', type=str, default="What is the meaning of life?")
        
        return parser, _run_command
    
    async def command_help(self, mc: MessageContext):
        async def _run_command(args):
            # gather parser help page for 'subcommand'
            if args.subcommand:
                if not hasattr(self, f'command_{args.subcommand}'):
                    await self.mng.sendChatMessage(mc, f"Command not found (No help page!): `{args.subcommand}`")
                else:
                    parser, _ = await getattr(self, f'command_{args.subcommand}')(mc)
                    docs = getattr(self, f'command_{args.subcommand}').__doc__
                    no_code = "\n".join([l.strip() for l in docs.split('\n')])
                    await self.mng.sendChatMessage(mc,"# Command `{0}`\n{1}\n{2}".format(args.subcommand, no_code, parser.format_help()))
            else:
                # gather help page for all subcommands
                help_text = "# Hal9003 commands\n"
                help_text += "Available commands:\n"
                for attr in dir(self):
                    if attr.startswith('command_'):
                        command = attr[8:]
                        up_first_letter = command[0].upper() + command[1:]
                        help_text += f"## {up_first_letter} (`/{command}`)\n"
                        if command != 'help':
                            help_text += f"- `/help {command}` for more info\n"
                            no_code = "\n".join([l.strip() for l in getattr(self, attr).__doc__.split('\n')])
                            help_text += f"{no_code}\n"
                        else:
                            parser, _ = await getattr(self, f'command_{command}')(mc)
                            help_text += f"{parser.format_help()}\n"
                await self.mng.sendChatMessage(mc, help_text)
        
        parser = argparse.ArgumentParser(prog='Help command')
        parser.add_argument('subcommand', type=str, nargs='?', default=None)
        
        return parser, _run_command
    
    async def run_command(self, command, args, mc: MessageContext):
        if not hasattr(self, f'command_{command}'):
            return await self.mng.sendChatMessage(mc, f"Command not found: `{command}`")
        else:
            parser, _run_command = await getattr(self, f'command_{command}')(mc)
            parsed_args = None
            try:
                parsed_args = parser.parse_args(args)
            except SystemExit as ex:
                trace = await self.fmd.wrap_code(traceback.format_exc())
                return await self.mng.sendChatMessage(mc, f"Error parsing arguments: `{args}`\n> {ex}\n{trace}")
            return await _run_command(parsed_args)