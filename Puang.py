import discord
from discord import app_commands
from discord.ext import commands
import yt_dlp as youtube_dl
import asyncio
import random
import time
import datetime
import os
import sys
import subprocess

# [설정] 봇 기본 설정
intents = discord.Intents.all()
bot = commands.Bot(command_prefix='!', intents=intents)

# [권한 설정] 개발자(오너) ID 설정 (원격 업데이트용)
# 디스코드 설정 -> 고급 -> 개발자 모드 켜기 후, 본인 프로필 우클릭 -> ID 복사
OWNER_ID = 495511094434201600  # ⚠️ 여기에 본인의 진짜 ID 숫자를 넣으세요!

# [상수] 이펙트 필터 설정
FFMPEG_FILTERS = {
    'normal': '',
    'bassboost': 'bass=g=20,dynaudnorm=f=200',
    'nightcore': 'asetrate=44100*1.25,aresample=44100,atempo=1.0',
    'slowed': 'asetrate=44100*0.8,aresample=44100,atempo=1.0',
    '8d': 'apulsator=hz=0.08',
    'vaporwave': 'aresample=48000,asetrate=48000*0.8'
}

class Song:
    def __init__(self, url, title, duration, thumbnail, requester):
        self.url = url
        self.title = title
        self.duration = duration
        self.thumbnail = thumbnail
        self.requester = requester

class GuildState:
    def __init__(self):
        self.queue = []          
        self.is_playing = False
        self.volume = 0.5        
        self.loop_mode = 0       
        self.current_song = None
        self.voice_client = None
        self.filter = 'normal'   
        self.start_time = 0      
        self.controller_msg = None # 🌟 24/7 최적화: 채팅창 도배 방지용 UI 메시지 추적

guild_states = {}

def get_state(guild_id):
    if guild_id not in guild_states:
        guild_states[guild_id] = GuildState()
    return guild_states[guild_id]

def format_time(seconds):
    return str(datetime.timedelta(seconds=int(seconds))) if seconds else "실시간"

# [이벤트] 🌟 24/7 최적화: 메모리 관리 및 자동 퇴장
@bot.event
async def on_voice_state_update(member, before, after):
    # 1. 봇이 강제로 통화방에서 쫓겨나거나 끊겼을 때 메모리(상태) 초기화
    if member == bot.user and before.channel and not after.channel:
        guild_id = before.channel.guild.id
        if guild_id in guild_states:
            del guild_states[guild_id] # 찌꺼기 메모리 삭제
            
    # 2. 통화방에 봇 혼자 남았을 때 자동 퇴장 (서버 트래픽 절약)
    if member != bot.user and before.channel:
        if bot.user in before.channel.members:
            # 봇을 제외한 실제 사람이 0명이면
            if len([m for m in before.channel.members if not m.bot]) == 0:
                vc = before.channel.guild.voice_client
                if vc and vc.is_connected():
                    await vc.disconnect()

# [UI] 고급 뮤직 컨트롤러
class MusicController(discord.ui.View):
    def __init__(self, guild_id):
        super().__init__(timeout=None)
        self.guild_id = guild_id

    @discord.ui.button(emoji="⏯️", style=discord.ButtonStyle.primary, row=0)
    async def pause_resume(self, interaction: discord.Interaction, button: discord.ui.Button):
        vc = interaction.guild.voice_client
        if vc:
            if vc.is_playing():
                vc.pause()
                await interaction.response.send_message("⏸️ **일시정지!**", ephemeral=True)
            elif vc.is_paused():
                vc.resume()
                await interaction.response.send_message("▶️ **재생!**", ephemeral=True)
        else:
            await interaction.response.send_message("재생 중인 노래가 없어요.", ephemeral=True)

    @discord.ui.button(emoji="⏹️", style=discord.ButtonStyle.danger, row=0)
    async def stop(self, interaction: discord.Interaction, button: discord.ui.Button):
        state = get_state(self.guild_id)
        state.queue.clear()
        state.loop_mode = 0
        if interaction.guild.voice_client:
            interaction.guild.voice_client.stop()
        
        # UI 플레이어 메시지도 깔끔하게 지워줌
        if state.controller_msg:
            try: await state.controller_msg.delete()
            except: pass
        await interaction.response.send_message("⏹️ **정지 및 대기열 초기화 완료!**", ephemeral=True)

    @discord.ui.button(emoji="⏭️", style=discord.ButtonStyle.success, row=0)
    async def skip(self, interaction: discord.Interaction, button: discord.ui.Button):
        vc = interaction.guild.voice_client
        if vc and (vc.is_playing() or vc.is_paused()):
            vc.stop()
            await interaction.response.send_message("⏭️ **스킵!**", ephemeral=True)
        else:
            await interaction.response.send_message("스킵할 노래가 없어요.", ephemeral=True)

    @discord.ui.button(label="반복: 끔", emoji="🔁", style=discord.ButtonStyle.secondary, row=1)
    async def loop_toggle(self, interaction: discord.Interaction, button: discord.ui.Button):
        state = get_state(self.guild_id)
        state.loop_mode = (state.loop_mode + 1) % 3
        modes = ["끔", "한 곡", "전체"]
        button.label = f"반복: {modes[state.loop_mode]}"
        
        if state.loop_mode == 0: button.style = discord.ButtonStyle.secondary
        elif state.loop_mode == 1: button.style = discord.ButtonStyle.primary
        else: button.style = discord.ButtonStyle.success
        
        await interaction.response.edit_message(view=self)

    @discord.ui.button(label="대기열", emoji="📜", style=discord.ButtonStyle.gray, row=1)
    async def show_queue(self, interaction: discord.Interaction, button: discord.ui.Button):
        state = get_state(self.guild_id)
        if not state.queue:
            await interaction.response.send_message("대기열이 텅 비었어요!", ephemeral=True)
            return
        desc = ""
        for i, song in enumerate(state.queue[:10]):
            desc += f"**{i+1}.** {song.title} `[{format_time(song.duration)}]`\n"
        if len(state.queue) > 10:
            desc += f"\n...외 {len(state.queue)-10}곡 더 있음"
        embed = discord.Embed(title="📜 현재 대기열", description=desc, color=discord.Color.gold())
        await interaction.response.send_message(embed=embed, ephemeral=True)

# [로직] 다음 곡 재생
async def play_next(guild_id, interaction_channel):
    state = get_state(guild_id)
    voice = state.voice_client

    if state.current_song and state.loop_mode == 1:
        state.queue.insert(0, state.current_song)
    elif state.current_song and state.loop_mode == 2:
        state.queue.append(state.current_song)

    if not state.queue:
        state.is_playing = False
        state.current_song = None
        # 끝났을 때 이전 UI 삭제
        if state.controller_msg:
            try: await state.controller_msg.delete()
            except: pass
        await interaction_channel.send(embed=discord.Embed(description="🎵 모든 노래가 끝났어요!", color=discord.Color.dark_gray()))
        return

    song = state.queue.pop(0)
    state.current_song = song
    state.is_playing = True
    state.start_time = time.time()

    filter_str = FFMPEG_FILTERS.get(state.filter, '')
    ffmpeg_opts = {
        'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
        'options': f'-vn -filter:a "{filter_str}"' if filter_str else '-vn'
        # ⚠️ 만약 서버 환경에 ffmpeg가 환경 변수로 잡혀있다면 executable 옵션은 지우는게 좋습니다!
    }

    def after_playing(error):
        if error: print(f"Error: {error}")
        coro = play_next(guild_id, interaction_channel)
        fut = asyncio.run_coroutine_threadsafe(coro, bot.loop)
        try: fut.result()
        except: pass

    try:
        import os
        ffmpeg_path = os.path.abspath("ffmpeg.exe")
        source = discord.FFmpegPCMAudio(song.url, executable=ffmpeg_path, **ffmpeg_opts)
        source = discord.PCMVolumeTransformer(source, volume=state.volume)
        voice.play(source, after=after_playing)

        embed = discord.Embed(title=song.title, url=song.url, color=discord.Color.from_rgb(255, 105, 180))
        embed.set_author(name=f"Now Playing - {state.filter.upper()} Mode", icon_url=bot.user.display_avatar.url)
        embed.set_thumbnail(url=song.thumbnail)
        embed.add_field(name="⏳ 시간", value=f"`{format_time(song.duration)}`", inline=True)
        embed.add_field(name="👤 신청자", value=song.requester.mention, inline=True)
        embed.add_field(name="🎚️ 볼륨", value=f"{int(state.volume*100)}%", inline=True)
        
        if state.queue: embed.set_footer(text=f"다음 곡: {state.queue[0].title}")

        view = MusicController(guild_id)
        
        # 🌟 24/7 최적화: 도배 방지 로직 (이전 플레이어가 있으면 지우고 새로 띄움)
        if state.controller_msg:
            try: await state.controller_msg.delete()
            except: pass
            
        state.controller_msg = await interaction_channel.send(embed=embed, view=view)

    except Exception as e:
        print(f"재생 오류: {e}")
        await play_next(guild_id, interaction_channel)

# ------------------------------------------------------------
# [명령어] Slash Commands
# ------------------------------------------------------------

@bot.event
async def on_ready():
    await bot.tree.sync()
    await bot.change_presence(status=discord.Status.online, activity=discord.Game("🎵 서버 무중단 운영 중"))
    print(f'✅ 푸앙봇 V4.0 (24/7 에디션) 로그인 완료: {bot.user}')

@bot.tree.command(name="업데이트", description="[개발자 전용] 깃허브에서 코드를 받아오고 봇을 재시작합니다.")
async def update_bot(interaction: discord.Interaction):
    # 권한 검사
    if interaction.user.id != OWNER_ID:
        await interaction.response.send_message("❌ 오너(개발자)만 사용할 수 있는 명령어입니다.", ephemeral=True)
        return

    # 먼저 대답을 해서 10062 에러 방지
    await interaction.response.send_message("🔄 **원격 업데이트를 시작합니다...**\n(서버에서 `git pull` 중...)")
    
    try:
        # 비동기로 시스템 명령어(git) 실행 (봇이 멈추지 않게 함)
        loop = asyncio.get_event_loop()
        # 오류 상세 내용을 보기 위해 capture_output=True 추가
        result = await loop.run_in_executor(
            None, 
            lambda: subprocess.run(["git", "pull"], check=True, capture_output=True, text=True)
        )
        
        await interaction.followup.send("✅ **업데이트 완료!** 봇을 재시작합니다.\n```\n" + result.stdout + "\n```")
        
        # 봇 재시작 로직 (경로 문제 방지)
        os.execv(sys.executable, ['python', 'Puang.py'])
        
    except subprocess.CalledProcessError as e:
        await interaction.followup.send(f"❌ **Git Pull 실패 (코드 충돌 또는 권한 문제):**\n```\n{e.stderr}\n```")
    except FileNotFoundError:
        await interaction.followup.send("❌ **[WinError 2] Git이 설치되어 있지 않거나 환경 변수에 없습니다!**\nGit을 설치하고 PC를 재부팅해주세요.")
    except Exception as e:
        await interaction.followup.send(f"❌ **알 수 없는 에러 발생:**\n```\n{e}\n```")

@bot.tree.command(name="입장", description="봇을 현재 음성 채널로 부릅니다.")
async def join(interaction: discord.Interaction):
    if interaction.user.voice:
        channel = interaction.user.voice.channel
        if interaction.guild.voice_client:
            await interaction.guild.voice_client.move_to(channel)
        else:
            await channel.connect(timeout=20.0, self_deaf=True)
        state = get_state(interaction.guild_id)
        state.voice_client = interaction.guild.voice_client
        await interaction.response.send_message("🔊 **스피커 연결 완료!**")
    else:
        await interaction.response.send_message("❌ 음성 채널에 먼저 들어가주세요!", ephemeral=True)

@bot.tree.command(name="퇴장", description="봇을 내보냅니다.")
async def leave(interaction: discord.Interaction):
    if interaction.guild.voice_client:
        guild_id = interaction.guild_id
        if guild_id in guild_states:
            del guild_states[guild_id] # 퇴장 시 깔끔하게 메모리 정리
        await interaction.guild.voice_client.disconnect()
        await interaction.response.send_message("👋 **빠이빠이!**")
    else:
        await interaction.response.send_message("❌ 들어와 있지도 않아요!", ephemeral=True)

@bot.tree.command(name="재생", description="유튜브 노래를 재생합니다.")
@app_commands.describe(search="노래 제목 또는 URL")
async def play(interaction: discord.Interaction, search: str):
    await interaction.response.defer() 

    if not interaction.user.voice:
        await interaction.followup.send("❌ 음성 채널에 먼저 들어가주세요!", ephemeral=True)
        return

    state = get_state(interaction.guild_id)

    try:
        if not interaction.guild.voice_client:
            await interaction.user.voice.channel.connect(timeout=20.0, self_deaf=True)
        elif not interaction.guild.voice_client.is_connected():
            await interaction.guild.voice_client.move_to(interaction.user.voice.channel)
    except Exception as e:
        await interaction.followup.send("❌ 음성 채널 연결에 실패했어요.")
        return

    state.voice_client = interaction.guild.voice_client

    ydl_opts = {
        'format': 'bestaudio/best',
        'noplaylist': True,
        'quiet': True,
        'default_search': 'auto',
        'source_address': '0.0.0.0'
    }

    try:
        loop = bot.loop
        if search.startswith("http://") or search.startswith("https://"):
            extract_query = search
        else:
            extract_query = f"ytsearch:{search}"
            
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            info = await loop.run_in_executor(None, lambda: ydl.extract_info(extract_query, download=False))
        
        if 'entries' in info: info = info['entries'][0]
        
        song = Song(
            url=info['url'],
            title=info['title'],
            duration=info.get('duration'),
            thumbnail=info.get('thumbnail'),
            requester=interaction.user
        )
        
        state.queue.append(song)
        
        if not interaction.guild.voice_client.is_playing():
            await play_next(interaction.guild_id, interaction.channel)
            await interaction.followup.send(f"🔎 **{song.title}** 재생을 시작합니다!")
        else:
            embed = discord.Embed(title="✅ 대기열 추가됨", description=f"**{song.title}**", color=discord.Color.green())
            embed.set_thumbnail(url=song.thumbnail)
            embed.add_field(name="대기 순서", value=f"{len(state.queue)}번째", inline=True)
            await interaction.followup.send(embed=embed)
            
    except Exception as e:
        print(f"재생 에러: {e}")
        await interaction.followup.send("❌ 노래를 찾을 수 없거나 오류가 발생했어요.")

@bot.tree.command(name="대기열", description="대기열의 노래를 확인, 이동, 셔플, 삭제합니다.")
async def queue_manage(interaction: discord.Interaction):
    # 이 부분은 뷰(버튼)에서 이미 지원하므로 안내 메시지로 대체
    await interaction.response.send_message("💡 팁: 재생 중인 플레이어 UI의 `📜 대기열` 버튼을 누르면 편하게 볼 수 있습니다!", ephemeral=True)

# 봇 실행
with open('token.txt', 'r') as f:
    TOKEN = f.read().strip()

bot.run(TOKEN)