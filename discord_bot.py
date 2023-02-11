import discord
from discord.ui import Button, View
from discord.ext import commands, tasks
from discord.utils import get
import json
import datetime
import asyncio
import time
from srt.srt import Srt

with open("config.json") as f:
    conf = json.load(f)

now = datetime.datetime.now()
intents = discord.Intents.all()
intents.members = True
bot = commands.Bot(command_prefix='/', help_command=None, intents=intents)


c = {'dep_station': None, 'des_station': None, 'trgt_date': None, 'start_time_min': None, 'start_time_max': None}
station_dict = {'수서': 0, '동탄': 1, '평택지제': 2, '천안아산': 3, '오송': 4, '대전': 5, '김천구미': 6, '서대구': 7, '동대구': 8,
                '신경주': 9, '울산': 10, '부산': 11, '공주': 12, '익산': 13, '정읍': 14, '광주송정': 15, '나주': 16, '목포': 17}
short_station_dict = {'수서': 0, '동탄': 1, '평택지제': 2, '천안아산': 3, '대전': 5,
                      '김천구미': 6, '동대구': 8, '신경주': 9, '울산': 10, '부산': 11, '익산': 13, '광주송정': 15}


is_running = False
thread_cnt = 0


def get_helpmsg():
    embed = discord.Embed(color=0xe6492d)
    embed.add_field(name="매크로 실행방법", value="/srt", inline=False)
    embed.add_field(name="이 메세지를 다시보려면?", value="/help", inline=False)
    return embed


class ExitView(View):
    def __init__(self, timeout: float = 86400, msg: str = ''):
        super().__init__(timeout=timeout)
        self.msg = msg

        btn = MyBtn(label="종료", style=discord.ButtonStyle.danger, msg=self.msg)
        self.add_item(btn)
        # self.stop()


class MyBtn(Button):
    def __init__(self, style, label, msg: str = "", row: int = None, disabled: bool = False, ctx=None):
        super().__init__(style=style, label=label, row=row)
        self.label = label
        self.msg = msg
        self.disabled = disabled
        self.ctx = ctx
        self.s = None

    def is_finished_select():
        global c

        if None in c.values():
            return 0
        return 1

    def print_selected_info():
        global c
        station = f"{c['dep_station']}->{c['des_station']}"
        time = f"{c['start_time_min']}~{c['start_time_max']}시"

        embed = discord.Embed(title="SRT Macro를 실행중입니다.", color=0x5572b4)
        embed.add_field(name="역", value=station, inline=False)
        embed.add_field(name="날짜", value=c['trgt_date_txt'], inline=False)
        embed.add_field(name="출발시간", value=time, inline=False)
        return embed

    async def callback(self, interaction: discord.Interaction):
        p_label = None
        tview = None
        global c, is_running, thread_cnt
        if self.msg == '출발':
            if c['dep_station'] is None:
                c['dep_station'] = self.label
                p_label = self.label
                tview = StationView(msg="출발", station=short_station_dict, ctx=self.ctx)
                await interaction.response.edit_message(content=f"출발역 : {p_label}\n도착역을 선택해주세요.", view=tview)
            else:
                c['des_station'] = self.label
                p_label = self.label
                tview = StationView(msg="도착", station=short_station_dict, ctx=self.ctx)
                await interaction.response.edit_message(content=f"목적지 선택완료", view=tview)
                calendar_view = CalendarView(timeout=180, msg="날짜", ctx=self.ctx)
                await self.ctx.send("날짜를 선택해주세요", view=calendar_view)
        elif self.msg == "종료":
            thread_cnt -= 1
            await interaction.response.edit_message(content=f"매크로가 종료되었습니다.", view=None, embed=None)
            self.s.quit_now = True
        elif self.msg == '날짜':
            c['trgt_date'] = self.label
            p_label = self.label
            tview = CalendarView(msg="날짜", ctx=self.ctx)
            await interaction.response.edit_message(content=f"날짜 선택완료", view=tview)
            mintime_view = TimeView(timeout=180, msg="min시간", ctx=self.ctx)
            await self.ctx.send("최소~최대 출발시간을 차례로 선택해주세요", view=mintime_view)
        elif self.msg == 'min시간':
            if c['start_time_min'] is None:
                c['start_time_min'] = self.label
                p_label = self.label
                tview = TimeView(msg="min시간", ctx=self.ctx)
                await interaction.response.edit_message(content=f"최소출발시간 : {p_label}, 최대출발시간을 선택해주세요.", view=tview)
            else:
                c['start_time_max'] = self.label
                p_label = "max시간"
                tview = TimeView(msg="max시간", ctx=self.ctx)
                await interaction.response.edit_message(content=f"시간 선택완료", view=tview)
                is_running = False
        if exit is not True and self.is_finished_select():
            exitview = ExitView(msg="종료")
            await interaction.channel.send(embed=self.print_selected_info(), view=exitview)
            self.s = Srt(thread_cnt)
            self.s.min_time = int(c['start_time_min'])
            deptime = str(self.s.min_time - (self.s.min_time % 2)).zfill(2) + '0000'
            self.s.start_time = list(range(self.s.min_time, int(c['start_time_max'])+1))
            self.s.interval = 1
            self.s.VIP = "0"  # '2':"특실+일반실", '1':"특실", '0':"일반실"
            self.s.start_now = 0

            await self.s.start(self.s.srt_home, c['trgt_date'], deptime, c['dep_station'], c['des_station'])
            thread_cnt -= 1


class TimeView(View):
    def __init__(self, timeout: float = 180, msg: str = '', ctx=None):
        super().__init__(timeout=timeout)
        self.msg = msg
        global c
        self.ctx = ctx

        if c['start_time_max'] is not None:
            btn = MyBtn(label=f"{c['start_time_min']} ~ {c['start_time_max']}시",
                        style=discord.ButtonStyle.green,  disabled=True, ctx=self.ctx)
            self.add_item(btn)
        else:
            for x in range(8, 23):
                if c['start_time_min'] == str(x):
                    btn = MyBtn(label=x, style=discord.ButtonStyle.green, msg=self.msg, ctx=self.ctx)
                elif c['start_time_min'] is not None and int(c['start_time_min']) >= x:
                    btn = MyBtn(label=x, style=discord.ButtonStyle.grey, msg=self.msg, disabled=True, ctx=self.ctx)
                else:
                    btn = MyBtn(label=x, style=discord.ButtonStyle.grey, msg=self.msg, ctx=self.ctx)
                self.add_item(btn)


class CalendarView(View):
    def __init__(self, timeout: float = 180, msg: str = '', ctx=None):
        super().__init__(timeout=timeout)
        self.msg = msg
        global c
        self.ctx = ctx

        if c['trgt_date'] is not None:
            c['trgt_date_txt'] = str(now.strftime("%m"))+"월 "+c['trgt_date']
            trgt_date = c['trgt_date'].split("일")[0]
            c['trgt_date'] = str(now.strftime("%Y%m"))+trgt_date
            btn = MyBtn(label=c['trgt_date_txt'], style=discord.ButtonStyle.green, msg=self.msg, disabled=True, ctx=self.ctx)
            self.add_item(btn)
        else:
            prev_month = 0
            day_offset = 1
            for x in range(0, 12):
                cur_time = (now + datetime.timedelta(days=day_offset))
                cur_month = int(cur_time.strftime("%m"))
                if prev_month < cur_month:
                    btn = MyBtn(label=str(cur_month)+"월", style=discord.ButtonStyle.green,
                                msg=self.msg, row=int(x/3), disabled=True, ctx=self.ctx)
                else:
                    day = cur_time.strftime("%d일(%a)")
                    day_offset += 1
                    btn = MyBtn(label=day, style=discord.ButtonStyle.grey, msg=self.msg, row=int(x/3), ctx=self.ctx)
                prev_month = cur_month
                self.add_item(btn)


class StationView(View):
    def __init__(self, timeout: float = 180, msg: str = '', station: dict = {}, ctx=None):
        super().__init__(timeout=timeout)
        self.station_dict = station
        self.msg = msg
        global c
        self.ctx = ctx

        if c['des_station'] is not None:
            btn = MyBtn(label=f"{c['dep_station']} -> {c['des_station']}",
                        style=discord.ButtonStyle.green,  disabled=True, ctx=self.ctx)
            self.add_item(btn)
        else:
            rows = 0
            cnt = 0
            for x in self.station_dict.keys():
                rows = int(cnt / 4)
                cnt += 1
                if c['dep_station'] == str(x):
                    btn = MyBtn(label=x, style=discord.ButtonStyle.green, msg=self.msg, row=rows, disabled=True, ctx=self.ctx)
                else:
                    btn = MyBtn(label=x, style=discord.ButtonStyle.grey, msg=self.msg, row=rows, ctx=self.ctx)
                self.add_item(btn)


@ bot.event
async def on_ready():
    print(f'서버 구동중... {bot.user.name}')
    await bot.change_presence(status=discord.Status.online, activity=discord.Game("서버구동"))


@ bot.event
async def on_member_join(member):
    channel = bot.get_channel(conf['CH_ID'])
    await channel.send(content=f"{member}님, {member.server}에 오신것을 환영합니다.", embed=get_helpmsg())


@ bot.command()
async def help(ctx):
    await ctx.send(embed=get_helpmsg(), view=None)


@ bot.command()
async def srt(ctx):
    global c, is_running, thread_cnt
    if is_running:
        await ctx.reply("다른분의 메뉴선택이 끝날때까지 기다렸다 다시 시도해주세요.", view=None)
    elif thread_cnt > 2:
        await ctx.reply("이미 3개의 매크로가 실행중입니다.\n나중에 다시 시도해주세요", view=None)
    else:
        for k in c.keys():
            c[k] = None
        is_running = True
        thread_cnt += 1

        departure_view = StationView(timeout=180, msg="출발", station=short_station_dict, ctx=ctx)
        await ctx.reply("SRT 매크로를 시작합니다.\n출발, 도착역을 차례로선택해주세요", view=departure_view)

bot.run(conf['TOKEN'])
