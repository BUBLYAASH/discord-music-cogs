#! /usr/bin/env python
# -*- coding: utf-8 -*-

import discord, random, os, requests
from discord.ext import commands
import asyncio
import itertools
import sys
import traceback
from async_timeout import timeout
from functools import partial
from youtube_dl import YoutubeDL
from react import react
from bs4 import BeautifulSoup as bs

ytdlopts = {
    'format': 'bestaudio/best',
    'outtmpl': 'downloads/%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0'  # ipv6 addresses cause issues sometimes
}

ffmpegopts = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
}

headers = {
    'accept': '*/*',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.163 Safari/537.36'
}

ytdl = YoutubeDL(ytdlopts)


class VoiceConnectionError(commands.CommandError):
    """Custom Exception class for connection errors."""


class InvalidVoiceChannel(VoiceConnectionError):
    """Exception for cases of invalid Voice Channels."""


class YTDLSource(discord.PCMVolumeTransformer):

    def __init__(self, source, *, data, requester):
        super().__init__(source)
        self.requester = requester

        self.title = data.get('title')
        self.web_url = data.get('webpage_url')
        self.duration = data.get('duration')
        self.lost = 0

    def __getitem__(self, item: str):
        return self.__getattribute__(item)

    @classmethod
    async def create_source(cls, ctx, search: str, *, loop, download=False):
        loop = loop or asyncio.get_event_loop()

        to_run = partial(ytdl.extract_info, url=search, download=download)
        data = await loop.run_in_executor(None, to_run)

        if 'entries' in data:
            data = data['entries'][0]

        await ctx.send(f'```ini\n[{data["title"]} Added to queue.]\n```')

        if download:
            source = ytdl.prepare_filename(data)
        else:
            return {'webpage_url': data['webpage_url'], 'requester': ctx.author, 'title': data['title']}

        return cls(discord.FFmpegPCMAudio(source), data=data, requester=ctx.author)

    @classmethod
    async def search_method(cls, ctx, search: str, *, loop, download):
        if str(ctx.message.author.id) in react:
            await ctx.message.delete()
            # await ctx.send(f'You have any search. Press :x: reaction on the message to delete the search.')
            await ctx.send(f'You have any search. Send **cancel** to cancel current search.')
        else:
            loop = loop or asyncio.get_event_loop()

            waiting = await ctx.send("Wait... Finding search")

            to_run = partial(ytdl.extract_info, url=f"ytsearch10:{search}", download=False)
            data = await loop.run_in_executor(None, to_run)

            emb = discord.Embed(title=f'Search by **{ctx.message.author.name}**', colour=random.randint(0, 0xffffff)).set_author(name=f'{ctx.message.author.name}', icon_url=f'{ctx.message.author.avatar_url}')

            if 'entries' in data:
                for i in range(10):
                    emb.add_field(name=f'_ _', value=f'{int(i)+1}) [{data["entries"][i]["title"].replace("||", "|")}]({data["entries"][i]["webpage_url"]})', inline=False)
                emb.add_field(name='_ _', value=f'Use **cancel** to cancel this search', inline=False)

            await waiting.delete()
            message = await ctx.send(embed=emb)

            react.append(f'{str(ctx.message.author.id)}:wait')
            f = open('react.py', 'w')
            f.write(f'#! /usr/bin/env python\n# -*- coding: utf-8 -*-\nreact = {str(react)}')
            f.close()

            while True:
                for i in react:
                    splited = i.split(':')
                    reaction = str(splited[1])
                    uid = str(splited[0])
                    print(reaction)
                    if str(ctx.message.author.id) == str(uid):
                        if reaction == 'wait':
                            await asyncio.sleep(1)
                        elif reaction == 'cancel':
                            print('Cancel')
                            await ctx.send("Canceled! :thumbsup:", delete_after=15.0)
                            await message.delete()
                            react.remove(f'{str(ctx.message.author.id)}:cancel')
                            f = open('react.py', 'w')
                            f.write(f'#! /usr/bin/env python\n# -*- coding: utf-8 -*-\nreact = {str(react)}')
                            f.close()
                            return "End"
                        else:
                            if download:
                                data = data['entries'][int(reaction)-1]
                                print(data['title'], ':', data['webpage_url'])
                                run = partial(ytdl.extract_info, url=f"ytsearch:{data['webpage_url']}", download=True)
                                data = await loop.run_in_executor(None, run)
                                data = data['entries'][0]
                                print(data['title'])
                                source = ytdl.prepare_filename(data)
                                react.remove(f'{str(ctx.message.author.id)}:{str(reaction)}')
                                f = open('react.py', 'w')
                                f.write(f'#! /usr/bin/env python\n# -*- coding: utf-8 -*-\nreact = {str(react)}')
                                f.close()
                                await ctx.send(f'```ini\n[{data["title"]}] Added to queue.\n```')
                                await message.delete()
                            else:
                                react.remove(f'{str(ctx.message.author.id)}:{str(reaction)}')
                                f = open('react.py', 'w')
                                f.write(f'#! /usr/bin/env python\n# -*- coding: utf-8 -*-\nreact = {str(react)}')
                                f.close()
                                await ctx.send(f'```ini\n[{data["entries"][int(reaction)-1]["title"]}] Added to queue.\n```')
                                await message.delete()
                                return {'webpage_url': data['entries'][int(reaction)-1]['webpage_url'], 'requester': ctx.author, 'duration': data['entries'][int(reaction)-1]['duration'], 'title': data['entries'][int(reaction)-1]['title']}

                            return cls(discord.FFmpegPCMAudio(source), data=data, requester=ctx.author)
                    else:
                        await asyncio.sleep(1)
    @classmethod
    async def regather_stream(cls, data, *, loop):
        loop = loop or asyncio.get_event_loop()
        requester = data['requester']

        to_run = partial(ytdl.extract_info, url=data['webpage_url'], download=False)
        data = await loop.run_in_executor(None, to_run)

        return cls(discord.FFmpegPCMAudio(data['url']), data=data, requester=requester)


class MusicPlayer(commands.Cog):
    __slots__ = ('bot', '_voicec', '_guild', '_channel', '_cog', 'queue', 'next', 'current', 'np', 'volume', 'lost')

    def __init__(self, ctx):
        self.bot = ctx.bot
        self._guild = ctx.guild
        self._channel = ctx.channel
        self._cog = ctx.cog
        self._voicec = ctx.voice_client

        self.queue = asyncio.Queue()
        self.next = asyncio.Event()

        self.np = None  # Now playing message
        self.volume = .2
        self.current = None
        self.lost = 'name:0'

        ctx.bot.loop.create_task(self.player_loop())

    async def losting(self):
        source = await self.queue.get()
        while source.lost != 0:
            source.lost = int(source.duration)-1
            await asyncio.sleep(1)
        else:
            return 0

    async def player_loop(self):
        await self.bot.wait_until_ready()
        print("Этаче")
        vc = self._voicec
        while not self.bot.is_closed():
            self.next.clear()
            print("Closed")

            try:
                # Wait for the next song. If we timeout cancel the player and disconnect...
                async with timeout(600):  # 10 minutes...
                    source = await self.queue.get()
            except asyncio.TimeoutError:
                return self.destroy(self._guild)

            if not isinstance(source, YTDLSource):
                # Source was probably a stream (not downloaded)
                # So we should regather to prevent stream expiration
                try:
                    source = await YTDLSource.regather_stream(source, loop=self.bot.loop)
                except Exception:
                    continue

            source.volume = self.volume
            self.current = source

            durka = int(source.duration) / 60
            duration = int(source.duration) - int(int(durka) * 60)
            print(f"{int(durka)}:{duration}")
            self._guild.voice_client.play(source, after=lambda _: self.bot.loop.call_soon_threadsafe(self.next.set))
            emb = discord.Embed(title='**Now playing:**', colour=random.randint(0, 0xffffff))
            emb.add_field(name=f'Song by **{source.requester}**:', value=f'[{source.title}]({source.web_url}) - {int(durka)}:{duration}')
            self.np = await self._channel.send(embed=emb)
            await self.next.wait()
            # if self.lost == 'name:0':
            #     self.lost = f'{str(source.title)}:0'
            # else:
            #     pass
            # lost = str(self.lost).split(':')
            # for i in range(int(source.duration)):
            #     if not vc.is_playing():
            #         if str(lost[0]) == str(source.title):
            #             await asyncio.sleep(1)
            #             self.lost = f'{str(lost[0])}:{str(int(i) + 1)}'
            #             print(self.lost)
            #         else:
            #             print("Not this")
            #             return "Not this"
            #     else:
            #         print("Stopped")
            #         self.lost = 'name:0'
            #         return 'Stopped'
            # self.lost = 'name:0'

            # Make sure the FFmpeg process is cleaned up.
            source.cleanup()
            self.current = None

            try:
                # We are no longer playing this song...
                await self.np.delete()
            except discord.HTTPException:
                pass

    def qget(self, ctx):
        print(self.current)

    def destroy(self, guild):
        return self.bot.loop.create_task(self._cog.cleanup(guild))


class Music(commands.Cog):
    """Music related commands."""

    __slots__ = ('bot', 'players', 'loop', 'lost')

    def __init__(self, bot):
        self.bot = bot
        self.players = {}
        self.loop = False
        self.lost = 'name:0'

    async def cleanup(self, guild):
        vc = guild.voice_client
        vc.stop()
        del self.players[guild.id]


    async def __local_check(self, ctx):
        if not ctx.guild:
            raise commands.NoPrivateMessage
        return True

    async def __error(self, ctx, error):
        """A local error handler for all errors arising from commands in this cog."""
        if isinstance(error, commands.NoPrivateMessage):
            try:
                return await ctx.send('This command can not be used in Private Messages.')
            except discord.HTTPException:
                pass
        elif isinstance(error, InvalidVoiceChannel):
            await ctx.send('Error connecting to Voice Channel. '
                           'Please make sure you are in a valid channel or provide me with one')

        print('Ignoring exception in command {}:'.format(ctx.command), file=sys.stderr)
        traceback.print_exception(type(error), error, error.__traceback__, file=sys.stderr)

    def get_player(self, ctx):
        """Retrieve the guild player, or generate one."""
        try:
            player = self.players[ctx.guild.id]
        except KeyError:
            player = MusicPlayer(ctx)
            self.players[ctx.guild.id] = player

        return player

    # async def looping(self, ctx):
    #     vc = ctx.voice_client
    #     player = self.get_player(ctx)
    #     if self.loop == False:
    #         self.loop = True
    #         dur = int(vc.source.duration)
    #         del self.players[ctx.guild.id]
    #         await ctx.send("Enabled, queue has been cleared")
    #         while self.loop == True:
    #             source = await YTDLSource.create_source(ctx, vc.source.web_url, loop=self.bot.loop, download=True)
    #             await player.queue.put(source)
    #             await asyncio.sleep(dur)
    #     elif self.loop == True:
    #         self.loop = False
    #         await ctx.send("Disabled")
    #     else:
    #         print("Some error!")
    #         await ctx.send("Error")

    @commands.command()
    async def qgete(self, ctx):
        vc = ctx.voice_client
        player = self.get_player(ctx)
        print(player.queue._queue())

    @commands.command(name='connect', aliases=['join', 'come', 'follow'])
    async def connect_(self, ctx):
        try:
            channel = ctx.author.voice.channel
        except AttributeError:
            raise InvalidVoiceChannel('You\'re not in a voice channel')
        await channel.connect()
        await ctx.send(f'Joined to: **{channel}**', )

    @commands.command(name='leave', aliases=['disconnect'])
    async def leave_(self, ctx):
        vc = ctx.voice_client

        await vc.disconnect()

        await ctx.send(f'Disconnected :thumbsup:', )

    @commands.command(name='play', aliases=['sing', 'p'])
    async def play_(self, ctx, *, search: str):
        try:
            vc = ctx.voice_client
            try:
                vc.connect()
            except:
                pass
            if not vc:
                await ctx.invoke(self.connect_)

            player = self.get_player(ctx)

            source = await YTDLSource.create_source(ctx, search, loop=self.bot.loop, download=True)
            await player.queue.put(source)
        except InvalidVoiceChannel:
            await ctx.send("You're not in a voice channel")

    @commands.command(name='search', aliases=['find', 's'])
    async def search_(self, ctx, *, search: str):
        try:
            vc = ctx.voice_client
            try:
                vc.connect()
            except:
                pass
            if not vc:
                await ctx.invoke(self.connect_)

            player = self.get_player(ctx)

            source = await YTDLSource.search_method(ctx, search, loop=self.bot.loop, download=True)

            await player.queue.put(source)
        except InvalidVoiceChannel:
            await ctx.send("You're not in a voice channel")

    @commands.command(name='pause')
    async def pause_(self, ctx):
        vc = ctx.voice_client

        if not vc or not vc.is_playing():
            return await ctx.send('I don\'t play nothing!')
        elif vc.is_paused():
            return

        vc.pause()
        await ctx.send(f'**`{ctx.author}`**: Song paused!')

    @commands.command(name='resume')
    async def resume_(self, ctx):
        vc = ctx.voice_client

        if not vc or not vc.is_connected():
            return await ctx.send('I don\'t play nothing!', )
        elif not vc.is_paused():
            return

        vc.resume()
        await ctx.send(f'**`{ctx.author}`**: Song resumed!')

    @commands.command(name='skip', aliases=['next'])
    async def skip_(self, ctx):
        vc = ctx.voice_client
        # if str(ctx.message.author.name) in str(vc.channel.members):
        #     print("Da")
        # print(f'{vc.channel.members[1]}')

        if not vc or not vc.is_connected():
            return await ctx.send('I don\'t play nothing!')

        if vc.is_paused():
            pass
        elif not vc.is_playing():
            return

        name = str(vc.source.requester).split('#')
        for i in vc.channel.members:
            if str(vc.source.requester) == str(i):
                if str(ctx.message.author) == str(vc.source.requester):
                        vc.stop()
                        await ctx.send(f'**`{ctx.author}`**: Song skipped!')
                        return
                else:
                    await ctx.send("You can't skip this song")
                    return
            elif str(name) not in str(vc.channel.members):
                vc.stop()
                await ctx.send(f'**`{ctx.author}`**: Song skipped!')
                return
            else:
                pass
        else:
            await ctx.message.delete()
            await ctx.send("You can't skip **this** song")

    @commands.command(name='fs', aliases=['fasts', 'fskip'])
    @commands.has_permissions(administrator=True)
    async def fs_(self, ctx):
        vc = ctx.voice_client
        if vc.is_paused():
            pass
        elif not vc.is_playing():
            return
        vc.stop()
        await ctx.send(f"Skipped :thumbsup:")

    @commands.command(name='queue', aliases=['q', 'playlist'])
    async def queue_info(self, ctx):
        vc = ctx.voice_client

        if not vc or not vc.is_connected():
            return await ctx.send('I don\'t play nothing!')

        player = self.get_player(ctx)
        if player.queue.empty():
            return await ctx.send('Queue is empty')

        # Grab up to 10 entries from the queue
        upcoming = list(itertools.islice(player.queue._queue, 0, 10))
        fmt = '\n'.join(f'**`{_["title"]}`**' for _ in upcoming)
        embed = discord.Embed(title=f'In queue **{len(upcoming)}**', description=fmt, colour=random.randint(0, 0xffffff))

        await ctx.send(embed=embed)

    @commands.command(name='now_playing', aliases=['np', 'current', 'currentsong', 'playing'])
    async def now_playing_(self, ctx):
        vc = ctx.voice_client

        if not vc or not vc.is_connected():
            return await ctx.send('I\'m not in a voice channel', )

        player = self.get_player(ctx)
        if not player.current:
            return await ctx.send('I don\'t play nothing!')

        try:
            # Remove our previous now_playing message.
            await player.np.delete()
        except discord.HTTPException:
            pass
        durka = int(vc.source.duration) / 60
        duration = int(vc.source.duration) - int(int(durka) * 60)
        print(f"{int(durka)}:{duration}")
        emb = discord.Embed(title='**Now playing:**', colour=random.randint(0, 0xffffff))
        emb.add_field(name=f'_ _', value=f'[{vc.source.title}]({vc.source.web_url}) - {int(durka)}:{duration}')
        player.np = await ctx.send(embed=emb)

    @commands.command(pass_context=True)
    async def dur(self, ctx):
        vc = ctx.voice_client
        print(vc.source.title)
        print(vc.source.web_url)
        durka = int(vc.source.duration)/60
        duration = int(vc.source.duration)-int(int(durka)*60)
        print(f"{int(durka)}:{duration}")

    @commands.command(name='volume', aliases=['vol'])
    async def change_volume(self, ctx, *, vol: float):
        vc = ctx.voice_client

        if not vc or not vc.is_connected():
            return await ctx.send('I\'m not in a voice channel', )

        if not 0 < vol < 101:
            return await ctx.send('Set volume between 0 and 100')

        if vol == None:
            return await ctx.send(f'Current volume: {vol}%')

        player = self.get_player(ctx)

        if vc.source:
            vc.source.volume = vol / 100

        player.volume = vol / 100
        await ctx.send(f'**`{ctx.author}`** set volume to **{vol}%**')

    @commands.command(name='stop')
    async def stop_(self, ctx):
        vc = ctx.voice_client

        if not vc or not vc.is_connected():
            return await ctx.send('I don\'t play nothing')

        player = self.get_player(ctx)
        player.queue = asyncio.Queue()
        await self.cleanup(ctx.guild)
        await ctx.send("Stopped :thumbsup:")

    @commands.command(name='shuffle')
    async def shuffle_(self, ctx):
        player = self.get_player(ctx)
        if len(list(player.queue._queue)) < 1:
            print(player.queue._queue)
            songs = random.shuffle(list(player.queue._queue))
            print(songs)
            # await self.cleanup(ctx.guild)
            player.queue._queue = songs
            print(player.queue._queue)
            return await ctx.send('Queue is empty')
        else:
            # player.queue._queue = random.shuffle(list(player.queue._queue))
            return await ctx.send('**Shuffled**')

    @commands.command(name='loop', aliases=['repeat'])
    async def loop_(self, ctx):
        vc = ctx.voice_client
        await vc.loop()
        return await ctx.send(':repeat_one:Looped!')

    @commands.command(name='lyrics', aliases=['l', 'lyr'])
    async def lyrics_(self, *search: str):
        searching = str(search).replace(' ', '+')
        r = requests.Session().get(f'https://www.google.com/search?sxsrf=ALeKk03daz23Sko9CC4rkK4IhNOpG5I-ow%3A1613145872138&ei=EKcmYLndB8WSrgTv4IaIDw&q=lyrics+{searching}&oq=lyrics+{searching}&gs_lcp=Cgdnd3Mtd2l6EAMyBQghEKABMgUIIRCgAToICAAQsAMQkQI6BwgAELADEEM6CQgAELADEAcQHjoECAAQQzoCCAA6BAgAEAo6BwgAEIcCEBQ6BQgAEMsBOggILhDHARCvAToFCAAQyQM6BggAEBYQHjoICAAQFhAKEB5QqOkBWIzuAWCc8AFoAXAAeACAAX6IAb0EkgEDNC4ymAEAoAEBqgEHZ3dzLXdpesgBCsABAQ&sclient=gws-wiz&ved=0ahUKEwi5pbfV3OTuAhVFiYsKHW-wAfEQ4dUDCAw&uact=5', headers=headers)
        soup = bs(r.content, 'html.parser')
        print(soup)
        lyr = soup.find_all('div', attrs={'class': 'SALvLe'})
        print(lyr)

    @commands.command(pass_context=True)
    async def del_loads(self, ctx):
        if ctx.message.author.id == 454334260950859786:
            await ctx.message.delete()
            for i in os.listdir('downloads'):
                os.remove(os.path.join('downloads', i))

def setup(client):
    client.add_cog(Music(client))
