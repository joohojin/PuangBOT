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
import platform
import urllib.request
import zipfile
import shutil
import json
import math
from discord.ext import tasks
from mcrcon import MCRcon
# --- [수정: TTS 라이브러리 추가] ---
from gtts import gTTS
import uuid
import os

# TTS 기능을 켠 유저들을 추적하는 명부
tts_users = set()
# -----------------------------------

# ==========================================
# 🌟 [신규] FFmpeg 자동 다운로드 시스템
# ==========================================
def check_and_setup_env():
    print("🔄 [시스템 점검] 봇 구동 환경을 확인합니다...")

    sys_name = platform.system()
    ffmpeg_name = "ffmpeg.exe" if sys_name == "Windows" else "ffmpeg"

    # 1. 이미 다운받았는지 확인
    if os.path.exists(ffmpeg_name) or shutil.which("ffmpeg"):
        print("✅ FFmpeg가 이미 준비되어 있습니다.")
        return

    # 2. 없다면 자동으로 깃허브에서 다운로드하여 압축 풀기
    print(f"📥 FFmpeg가 없습니다! 깡통 서버를 위해 자동으로 다운로드합니다 (OS: {sys_name})...")
    try:
        if sys_name == "Windows":
            url = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip"
            zip_path = "ffmpeg_temp.zip"
            urllib.request.urlretrieve(url, zip_path)
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                for file in zip_ref.namelist():
                    if file.endswith("ffmpeg.exe"):
                        with zip_ref.open(file) as source, open(ffmpeg_name, "wb") as target:
                            target.write(source.read())
            os.remove(zip_path)
            print("🎉 FFmpeg 자동 설치 완료!")
    except Exception as e:
        print(f"❌ FFmpeg 다운로드 실패: {e}")

# 봇이 켜질 때 무조건 환경 세팅 먼저 실행
check_and_setup_env()

# 다운받은 FFmpeg의 절대 경로 저장 (재생 오류 원천 차단)
FFMPEG_PATH = os.path.abspath("ffmpeg.exe" if platform.system() == "Windows" else "ffmpeg")
# ==========================================


# [설정] 봇 기본 설정
intents = discord.Intents.all()
bot = commands.Bot(command_prefix='!', intents=intents)

OWNER_ID = 495511094434201600  # ⚠️ 오너 ID 유지됨

# [설정] server.properties에 적었던 비밀번호
RCON_PASSWORD = "puang6974"

# 🌟 경험치 데이터 저장용 파일 이름
XP_FILE = "puang_xp.json"

# ==========================================
# 🛠️ 서버 관리 경로 설정 (상대 경로 기준 - 수정됨)
# ==========================================
# 봇 위치: Desktop\ET\PuangBOT\puang.py
# .. 를 통해 Desktop\ET 폴더로 이동합니다.
BASE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# 🌟 중요: 스크린샷에 맞춰 'serve'를 'server'로 수정했습니다!
MC_ROOT_DIR = os.path.join(BASE_PATH, "server", "mc")  # Desktop\ET\server\mc
PLAYIT_DIR = os.path.join(BASE_PATH, "server")        # Desktop\ET\server
PLAYIT_LINK = "playit.gg.lnk"                         # 바로가기 파일명

# [디버깅용] 봇이 켜질 때 실제 경로를 콘솔에 출력해서 확인하게 합니다.
print(f"📂 [경로 확인] 마크 루트: {MC_ROOT_DIR}")
print(f"📂 [경로 확인] Playit 폴더: {PLAYIT_DIR}")

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
        self.controller_msg = None 
        self.skip_votes = set() 
        # --- [수정: TTS 큐 시스템 추가] ---
        self.tts_queue = asyncio.Queue()
        self.tts_task = None
        # -----------------------------------

guild_states = {}

def load_xp():
    try:
        with open(XP_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_xp(data):
    with open(XP_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

def get_required_xp(level):
    # 레벨이 오를수록 기하급수적으로 증가하는 요구 경험치 곡선
    return int(100 * (level ** 1.5))

async def add_xp(user: discord.Member, amount: int, channel: discord.TextChannel = None):
    if user.bot: return

    data = load_xp()
    uid = str(user.id)

    # 신규 유저 초기화
    if uid not in data:
        data[uid] = {"xp": 0, "level": 1}

    data[uid]["xp"] += amount
    current_level = data[uid]["level"]
    required_xp = get_required_xp(current_level)

    # 레벨업 판정
    if data[uid]["xp"] >= required_xp:
        data[uid]["level"] += 1
        data[uid]["xp"] -= required_xp  # 초과 경험치 이월
        new_level = data[uid]["level"]
        save_xp(data)

        # 레벨업 축하 메시지 출력
        if channel:
            await channel.send(f"🎉 빰빠밤! {user.mention}님이 **레벨 {new_level}**(으)로 올랐습니다! 푸앙푸앙!")
            
        # 💡 [역할 부여 로직] 디스코드 서버에 'Lv.10', 'Lv.20' 같은 역할이 미리 만들어져 있어야 합니다.
        # role_name = f"Lv.{new_level}"
        # role = discord.utils.get(user.guild.roles, name=role_name)
        # if role:
        #     try: await user.add_roles(role)
        #     except: pass
    else:
        save_xp(data)

# --- [수정: TTS 처리 백그라운드 엔진] ---
async def process_tts_queue(guild: discord.Guild):
    state = get_state(guild.id)
    vc = guild.voice_client
    
    while not state.tts_queue.empty():
        text = await state.tts_queue.get()
        
        if not vc or not vc.is_connected():
            break

        try:
            # 1. 텍스트를 mp3 파일로 변환 (고유 이름 부여)
            tts = gTTS(text=text, lang='ko')
            filename = f"tts_{uuid.uuid4().hex}.mp3"
            tts.save(filename)
            
            # 2. 음악 재생 중첩 문제 해결 (음악 임시 정지)
            was_playing_music = False
            if vc.is_playing():
                was_playing_music = True
                vc.pause() # 음악 멈춰!
            
            # 3. 재생 완료 후 파일을 지우는 정리 함수
            def cleanup(error):
                try: os.remove(filename)
                except: pass

            # 4. TTS 재생
            tts_source = discord.FFmpegPCMAudio(filename, executable=FFMPEG_PATH)
            # 볼륨을 약간 키워줍니다
            tts_source = discord.PCMVolumeTransformer(tts_source, volume=1.0) 
            vc.play(tts_source, after=cleanup)
            
            # 5. TTS가 끝날 때까지 대기
            while vc.is_playing():
                await asyncio.sleep(0.5)
                
            # 6. 아까 음악이 재생 중이었다면 다시 재생 (Resume)
            if was_playing_music:
                vc.resume()

        except Exception as e:
            print(f"TTS 에러: {e}")
            try: os.remove(filename)
            except: pass
# -----------------------------------

def get_state(guild_id):
    if guild_id not in guild_states:
        guild_states[guild_id] = GuildState()
    return guild_states[guild_id]

def format_time(seconds):
    return str(datetime.timedelta(seconds=int(seconds))) if seconds else "실시간"

@bot.event
async def on_voice_state_update(member, before, after):
    if member == bot.user and before.channel and not after.channel:
        guild_id = before.channel.guild.id
        if guild_id in guild_states:
            del guild_states[guild_id] 
            
    if member != bot.user and before.channel:
        if bot.user in before.channel.members:
            if len([m for m in before.channel.members if not m.bot]) == 0:
                vc = before.channel.guild.voice_client
                if vc and vc.is_connected():
                    await vc.disconnect()

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
        if state.controller_msg:
            try: await state.controller_msg.delete()
            except: pass
        await interaction.response.send_message("⏹️ **정지 및 대기열 초기화 완료!**", ephemeral=True)

    @discord.ui.button(emoji="⏭️", style=discord.ButtonStyle.success, row=0)
    async def skip(self, interaction: discord.Interaction, button: discord.ui.Button):
        vc = interaction.guild.voice_client
        if not vc or not (vc.is_playing() or vc.is_paused()):
            await interaction.response.send_message("스킵할 노래가 없어요.", ephemeral=True)
            return

        state = get_state(self.guild_id)
        user = interaction.user

        # 1. DJ 권한 확인 (오너이거나, 이름이 'DJ'인 역할을 가졌거나)
        is_dj = (user.id == OWNER_ID) or any(role.name.upper() == "DJ" for role in user.roles)

        if is_dj:
            vc.stop()
            await interaction.response.send_message("👑 **DJ 권한으로 강제 스킵했습니다!**")
            return

        # 2. 일반 유저 투표 로직 (봇 제외 현재 채널 인원의 절반 이상 필요)
        channel_members = [m for m in user.voice.channel.members if not m.bot]
        required_votes = max(1, (len(channel_members) + 1) // 2)

        state.skip_votes.add(user.id)

        if len(state.skip_votes) >= required_votes:
            vc.stop()
            await interaction.response.send_message(f"⏭️ **투표 가결 ({len(state.skip_votes)}/{required_votes})!** 스킵합니다.")
        else:
            await interaction.response.send_message(f"🗳️ **스킵 투표:** {len(state.skip_votes)} / {required_votes} (절반 이상 찬성 시 스킵)")

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
        if state.controller_msg:
            try: await state.controller_msg.delete()
            except: pass
        await interaction_channel.send(embed=discord.Embed(description="🎵 모든 노래가 끝났어요!", color=discord.Color.dark_gray()))
        return

    song = state.queue.pop(0)
    state.current_song = song
    state.skip_votes.clear()  # 새 노래가 시작되면 투표 초기화
    state.is_playing = True
    state.start_time = time.time()

    filter_str = FFMPEG_FILTERS.get(state.filter, '')
    ffmpeg_opts = {
        'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
        'options': f'-vn -filter:a "{filter_str}"' if filter_str else '-vn'
    }

    def after_playing(error):
        if error: print(f"Error: {error}")
        coro = play_next(guild_id, interaction_channel)
        fut = asyncio.run_coroutine_threadsafe(coro, bot.loop)
        try: fut.result()
        except: pass

    try:
        # 🌟 이제 절대 경로를 사용하여 ffmpeg를 무조건 찾아냅니다.
        source = discord.FFmpegPCMAudio(song.url, executable=FFMPEG_PATH, **ffmpeg_opts)
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
        
        if state.controller_msg:
            try: await state.controller_msg.delete()
            except: pass
            
        state.controller_msg = await interaction_channel.send(embed=embed, view=view)

    except Exception as e:
        print(f"재생 오류: {e}")
        await play_next(guild_id, interaction_channel)

@bot.event
async def on_ready():
    await bot.tree.sync()
    voice_xp_loop.start() # 봇이 켜지면 음성 채널 경험치 지급 루프 시작
    await bot.change_presence(status=discord.Status.online, activity=discord.Game("🎵 서버 무중단 운영 중"))
    print(f'✅ 푸앙봇 V4.0 로그인 완료! 푸앙푸앙: {bot.user}')

# 💡 채팅을 치면 경험치 획득 (글자 수에 비례하되 최대 20 제한)
@bot.event
async def on_message(message: discord.Message):
    if message.author.bot: return

    # --- [수정: TTS 감지 로직 추가] ---
    if message.author.id in tts_users and message.author.voice:
        guild_id = message.guild.id
        state = get_state(guild_id)
        
        # 봇이 음성 채널에 없으면 유저가 있는 곳으로 먼저 들어감
        if not message.guild.voice_client:
            await message.author.voice.channel.connect(timeout=20.0, self_deaf=True)
            state.voice_client = message.guild.voice_client
            
        # "닉네임님이 말합니다"를 붙여서 큐에 삽입
        text_to_read = f"{message.author.display_name}님의 말. {message.content}"
        await state.tts_queue.put(text_to_read)
        
        # 엔진이 안 돌아가고 있다면 시동 걸기
        if state.tts_task is None or state.tts_task.done():
            state.tts_task = asyncio.create_task(process_tts_queue(message.guild))
    # -----------------------------------

    gained_xp = min(20, max(5, len(message.content)))
    await add_xp(message.author, gained_xp, message.channel)

    await bot.process_commands(message)

# 💡 음성 채널에 머물면 경험치 획득 (5분마다 실행되는 백그라운드 태스크)
@tasks.loop(minutes=5.0)
async def voice_xp_loop():
    for guild in bot.guilds:
        for vc in guild.voice_channels:
            # 음성 채널에 봇을 제외하고 사람이 있다면
            members = [m for m in vc.members if not m.bot]
            if members:
                for member in members:
                    # 음악을 듣거나 통화 중인 유저에게 꾸준히 30 XP 지급
                    # (여기서는 채팅창 도배 방지를 위해 채널 객체를 넘기지 않아 레벨업 메시지는 생략됩니다)
                    await add_xp(member, 30)

# ==========================================
# 🤖 서버 관제 명령어 (자동 완성 포함)
# ==========================================

# 1. mc 폴더 내의 폴더 리스트를 실시간으로 불러오는 자동 완성 함수
async def server_list_autocomplete(
    interaction: discord.Interaction,
    current: str,
) -> list[app_commands.Choice[str]]:
    # 1. 경로가 실제로 존재하는지 먼저 검사
    if not os.path.exists(MC_ROOT_DIR):
        return [app_commands.Choice(name="⚠️ 경로 오류 (server/mc 폴더 없음)", value="error")]
    
    try:
        # 2. 폴더 목록 가져오기
        folders = [f for f in os.listdir(MC_ROOT_DIR) if os.path.isdir(os.path.join(MC_ROOT_DIR, f))]
        
        # 3. 검색어 필터링
        choices = [
            app_commands.Choice(name=folder, value=folder)
            for folder in folders if current.lower() in folder.lower()
        ]
        
        return choices[:25] # 디스코드 최대 25개 제한
    except Exception as e:
        print(f"❌ 자동 완성 오류: {e}")
        return []

@bot.tree.command(name="서버켜기", description="[관리자] mc 폴더 내의 서버를 선택하여 실행합니다.")
@app_commands.autocomplete(server_name=server_list_autocomplete)
async def start_selected_server(interaction: discord.Interaction, server_name: str):
    if interaction.user.id != OWNER_ID:
        await interaction.response.send_message("❌ 오너만 사용할 수 있습니다.", ephemeral=True)
        return

    target_dir = os.path.join(MC_ROOT_DIR, server_name)
    bat_path = os.path.join(target_dir, "start.bat")

    if not os.path.exists(bat_path):
        await interaction.response.send_message(f"❌ `{server_name}` 폴더에 `start.bat`이 없습니다!", ephemeral=True)
        return

    await interaction.response.send_message(f"🚀 **{server_name}** 서버의 `start.bat`을 백그라운드에서 실행합니다...")
    
    try:
        # 윈도우에서 독립된 프로세스로 실행 (서버가 켜져도 봇이 멈추지 않음)
        subprocess.Popen(
            ["start.bat"],
            cwd=target_dir,
            creationflags=0x00000008, # DETACHED_PROCESS
            shell=True
        )
    except Exception as e:
        await interaction.followup.send(f"❌ 실행 에러: {e}")

@bot.tree.command(name="통로열기", description="[관리자] playit.gg 바로가기를 실행합니다.")
async def open_tunnel(interaction: discord.Interaction):
    if interaction.user.id != OWNER_ID:
        await interaction.response.send_message("❌ 권한이 없습니다.", ephemeral=True)
        return

    target_path = os.path.join(PLAYIT_DIR, PLAYIT_LINK)
    
    if not os.path.exists(target_path):
        await interaction.response.send_message(f"❌ `{target_path}` 파일을 찾을 수 없습니다. 이름(playit.gg.lnk)을 확인해주세요.", ephemeral=True)
        return

    await interaction.response.send_message("🌐 **Playit.gg 통로를 개방합니다...**")
    try:
        os.startfile(target_path) # 윈도우 바로가기 실행
    except Exception as e:
        await interaction.followup.send(f"❌ 실행 에러: {e}")

@bot.tree.command(name="시스템재부팅", description="[관리자] 컴퓨터 시스템을 즉시 재시작합니다.")
async def reboot_system(interaction: discord.Interaction):
    if interaction.user.id != OWNER_ID:
        await interaction.response.send_message("❌ 위험한 명령어입니다. 오너만 가능합니다.", ephemeral=True)
        return

    await interaction.response.send_message("⚠️ **10초 뒤 컴퓨터를 재부팅합니다.** 저장되지 않은 작업은 종료됩니다.")
    await asyncio.sleep(10)
    
    try:
        if platform.system() == "Windows":
            os.system("shutdown /r /t 1") # 1초 뒤 재부팅 명령
        else:
            await interaction.followup.send("❌ 윈도우 시스템이 아닙니다.")
    except Exception as e:
        await interaction.followup.send(f"❌ 명령 실패: {e}")

@bot.tree.command(name="서버끄기", description="[관리자] 현재 켜져 있는 마인크래프트 서버를 안전하게 종료합니다.")
async def stop_server(interaction: discord.Interaction):
    if interaction.user.id != OWNER_ID:
        await interaction.response.send_message("❌ 오너만 사용할 수 있습니다.", ephemeral=True)
        return

    await interaction.response.send_message("🛑 **서버를 안전하게 종료하고 맵 데이터를 저장합니다...**")
    
    try:
        # RCON을 통해 서버에 공식 종료 명령(stop)을 전송합니다.
        with MCRcon("127.0.0.1", RCON_PASSWORD, port=25575) as mcr:
            # 학생들에게 5초의 대피 시간을 줍니다!
            mcr.command("say [푸앙봇] 5초 뒤 서버가 종료됩니다! 데이터가 저장됩니다.")
            await asyncio.sleep(5)
            mcr.command("stop")
            
        await interaction.followup.send("✅ **서버 종료 명령 전송 완료!** (완전히 꺼질 때까지 잠시 대기해주세요)")
    except Exception as e:
        await interaction.followup.send(f"❌ **종료 실패:** 서버가 켜져 있지 않거나 RCON이 연결되지 않았습니다.\n`{e}`")

@bot.tree.command(name="통로끊기", description="[관리자] Playit.gg 터널링 프로세스를 종료합니다.")
async def close_tunnel(interaction: discord.Interaction):
    if interaction.user.id != OWNER_ID:
        await interaction.response.send_message("❌ 오너만 사용할 수 있습니다.", ephemeral=True)
        return

    await interaction.response.send_message("🔌 **Playit.gg 터널링 연결을 강제로 끊습니다...**")
    
    try:
        if platform.system() == "Windows":
            # 윈도우의 taskkill 명령어로 이름에 playit이 들어간 모든 프로세스를 강제(/F) 종료합니다.
            os.system("taskkill /F /IM playit* /T")
            await interaction.followup.send("✅ **통로가 성공적으로 닫혔습니다.**")
        else:
            await interaction.followup.send("❌ 윈도우 환경에서만 지원되는 명령어입니다.")
    except Exception as e:
        await interaction.followup.send(f"❌ 프로세스 종료 실패: {e}")

# --- [수정: TTS 제어 명령어 추가] ---
@bot.tree.command(name="tts켜기", description="[전체 유저] 채팅을 치면 푸앙이가 음성 채널에서 대신 읽어줍니다.")
async def tts_on(interaction: discord.Interaction):
    if not interaction.user.voice:
        await interaction.response.send_message("❌ 음성 채널에 먼저 접속한 상태에서 사용해주세요!", ephemeral=True)
        return
        
    tts_users.add(interaction.user.id)
    await interaction.response.send_message("🎙️ **TTS 모드 ON!**\n지금부터 이 채널에 채팅을 치면 푸앙이가 목소리로 읽어줄게요!", ephemeral=True)

@bot.tree.command(name="tts끄기", description="[전체 유저] TTS 기능을 끕니다.")
async def tts_off(interaction: discord.Interaction):
    tts_users.discard(interaction.user.id)
    await interaction.response.send_message("🔇 **TTS 모드 OFF!**", ephemeral=True)
# -----------------------------------

@bot.tree.command(name="업데이트", description="[개발자 전용] 깃허브에서 코드를 받아오고 봇을 재시작합니다.")
async def update_bot(interaction: discord.Interaction):
    if interaction.user.id != OWNER_ID:
        await interaction.response.send_message("❌ 오너(개발자)만 사용할 수 있는 명령어입니다.", ephemeral=True)
        return

    await interaction.response.send_message("🔄 **원격 업데이트를 시작합니다...**\n(서버에서 `git pull` 중...)")
    try:
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, lambda: subprocess.run(["git", "pull"], check=True, capture_output=True, text=True))
        
        await interaction.followup.send("✅ **업데이트 완료!** 봇을 재시작합니다.\n```\n" + result.stdout + "\n```")
        
        # 🌟 해결 1: 디스코드에 메시지가 완전히 전송될 수 있도록 1초 대기합니다.
        await asyncio.sleep(1)
        
        # 🌟 해결 2: 현재 실행 중인 파이썬과 파일의 절대 경로를 추적하여 강제로 완벽하게 재실행합니다.
        os.execv(sys.executable, [sys.executable, os.path.abspath(sys.argv[0])])
        
    except subprocess.CalledProcessError as e:
        await interaction.followup.send(f"❌ **Git Pull 실패:**\n```\n{e.stderr}\n```")
    except FileNotFoundError:
        await interaction.followup.send("❌ **[WinError 2] Git이 설치되어 있지 않거나 환경 변수에 없습니다!**")
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
            del guild_states[guild_id] 
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
        'no_warnings': True,
        'default_search': 'auto',
        'source_address': '0.0.0.0',
        'extractor_args': {'youtube': {'player_client': ['android']}}
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

@bot.tree.command(name="미니푸앙", description="푸앙봇의 시그니처 텍스트 아트를 출력합니다.")
async def print_ascii_mini(interaction: discord.Interaction):
    try:
        # puang.txt 파일을 읽어옵니다. (인코딩 에러 방지를 위해 utf-8 지정)
        with open("puang.txt", "r", encoding="utf-8") as f:
            content = f.read()
        
        # 디스코드 메시지 제한을 고려하여 안전하게 출력 (글꼴 깨짐 방지용 코드블록)
        await interaction.response.send_message(f"```{content}```")
        
    except FileNotFoundError:
        await interaction.response.send_message("❌ puang.txt 파일을 찾을 수 없습니다.")
    except Exception as e:
        await interaction.response.send_message(f"❌ 오류 발생: {e}")

@bot.tree.command(name="빅푸앙", description="푸앙봇의 빅-시그니처 텍스트 아트를 출력합니다.")
async def print_ascii_big(interaction: discord.Interaction):
    try:
        # puang-art.txt 파일을 읽어옵니다. (인코딩 에러 방지를 위해 utf-8 지정)
        with open("puang-art.txt", "r", encoding="utf-8") as f:
            content = f.read()
        
        # 디스코드 메시지 제한을 고려하여 안전하게 출력 (글꼴 깨짐 방지용 코드블록)
        await interaction.response.send_message(f"```{content}```")
        
    except FileNotFoundError:
        await interaction.response.send_message("❌ puang-art.txt 파일을 찾을 수 없습니다.")
    except Exception as e:
        await interaction.response.send_message(f"❌ 오류 발생: {e}")

@bot.tree.command(name="내정보", description="현재 나의 레벨과 경험치를 확인합니다.")
async def my_info(interaction: discord.Interaction):
    data = load_xp()
    uid = str(interaction.user.id)

    if uid not in data:
        await interaction.response.send_message("📊 아직 획득한 경험치가 없습니다. 채팅을 치거나 음악을 들어보세요!", ephemeral=True)
        return

    level = data[uid]["level"]
    xp = data[uid]["xp"]
    req_xp = get_required_xp(level)

    # 시각적인 진행률 바(Progress Bar) 계산
    progress = xp / req_xp
    bars = 15
    filled = int(progress * bars)
    bar_str = "🟩" * filled + "⬜" * (bars - filled)

    embed = discord.Embed(title=f"📈 {interaction.user.display_name}님의 프로필", color=discord.Color.blue())
    embed.set_thumbnail(url=interaction.user.display_avatar.url)
    embed.add_field(name="현재 레벨", value=f"**Lv.{level}**", inline=True)
    embed.add_field(name="경험치 (XP)", value=f"`{xp} / {req_xp}`", inline=True)
    embed.add_field(name="다음 레벨까지", value=f"{bar_str} ({int(progress*100)}%)", inline=False)

    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="마크명령", description="[관리자] 마인크래프트 서버에 명령어를 전송합니다.")
@app_commands.describe(command="실행할 명령어 (예: list, stop, say Hello)")
async def mc_command(interaction: discord.Interaction, command: str):
    if interaction.user.id != OWNER_ID:
        await interaction.response.send_message("❌ 관리자만 가능합니다.", ephemeral=True)
        return

    try:
        # 마크 서버(RCON)에 접속해서 명령어를 쏘고 대답을 받아옵니다.
        with MCRcon("127.0.0.1", RCON_PASSWORD, port=25575) as mcr:
            response = mcr.command(command)
            await interaction.response.send_message(f"💻 **서버 응답:**\n```\n{response}\n```")
    except Exception as e:
        await interaction.response.send_message(f"❌ 서버 연결 실패: {e}", ephemeral=True)

# 봇 실행
with open('token.txt', 'r') as f:
    TOKEN = f.read().strip()

bot.run(TOKEN)