import sys
import discord
from discord.ui import Button, View
from discord.ext import commands, tasks
from discord.utils import get
import json
import datetime
import asyncio
import time
from srt import Srt
from ktx import Ktx
from mylog import MyLog


with open("config.json") as f:
    conf = json.load(f)

now = datetime.datetime.now()
log = MyLog("discord", "INFO")
intents = discord.Intents.all()
intents.members = True
bot = commands.Bot(command_prefix='/', help_command=None, intents=intents)

c = {'dep_station': None, 'des_station': None, 'trgt_date': None,
     'start_time_min': None, 'start_time_max': None}
srt_short_station_dict = {'수서': 0, '동탄': 1, '평택지제': 2, '광주송정': 5,  '김천구미': 7,
                          '대전': 10, '동대구': 11,   '부산': 15, '전주': 24,
                          '오송': 21, '익산': 23, '울산(통도사)': 22,'신경주': 18, '천안아산': 30, '포항': 31}
ktx_station_dict = {'서울': 0, '용산': 1, '영등포': 2, '광명': 3,  '수원': 4,
                    '천안아산': 5, '오송': 6, '대전': 7, '김천구미': 9,
                    '동대구': 10, '경주': 11, '포항': 12, '부산': 13, '강릉': 14,
                    '익산': 15, '울산': 16, '광주송정': 17, '전주': 18, '순천': 19,
                    '여수': 20}
is_running = False
thread_cnt = 0
srt_dict = {}
ktx_dict = {}
default_timeout = None
start_now = 0
cur_mode = None


def get_helpmsg():
    embed = discord.Embed(color=0xe6492d)
    embed.add_field(name="매크로 실행방법", value="/srt", inline=False)
    embed.add_field(name="이 메세지를 다시보려면?", value="/help", inline=False)
    return embed


class MyBtn(Button):
    def __init__(self, style, label, msg: str = "", row: int = None, disabled: bool = False, ctx=None, cur_thread=None):
        super().__init__(style=style, label=label, row=row)
        self.label = label
        self.msg = msg
        self.disabled = disabled
        self.ctx = ctx
        self.exit = False
        self.cur_thread = cur_thread

    def is_finished_select(self):
        global c

        if None in c.values():
            return 0
        return 1

    def print_selected_info(self):
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
        global c, is_running, thread_cnt, srt_dict

        async def exit_select_menu(done=0):
            global is_running, thread_cnt, srt_dict
            if thread_cnt in srt_dict:
                srt_dict[self.cur_thread].quit_now = True
            if thread_cnt in ktx_dict:
                ktx_dict[self.cur_thread].quit_now = True
            log.logger.info(f"Thread Count : {self.cur_thread} 종료")
            if done == 999:  # TODO
                # TODO response말고 그냥 edit메세지로 해야됨
                await interaction.response.edit_message(content=f"매크로 진행이 완료되었습니다.", view=None, embed=None)
            else:
                await interaction.response.edit_message(content=f"매크로가 종료되었습니다.", view=None, embed=None)
            self.exit = True
            is_running = False

        if self.msg == '출발':
            if c['dep_station'] is None:
                c['dep_station'] = self.label
                p_label = self.label
                if "srt" in cur_mode:
                    tview = StationView(msg="출발", station=srt_short_station_dict, ctx=self.ctx)
                else:
                    tview = StationView(msg="출발", station=ktx_station_dict, ctx=self.ctx)
                await interaction.response.edit_message(content=f"출발역 : {p_label}\n도착역을 선택해주세요.", view=tview)
                tview.disable_timeout()
            else:
                c['des_station'] = self.label
                p_label = self.label
                if "srt" in cur_mode:
                    tview = StationView(msg="도착", station=srt_short_station_dict, ctx=self.ctx)
                else:
                    tview = StationView(msg="도착", station=ktx_station_dict, ctx=self.ctx)

                await interaction.response.edit_message(content=f"목적지 선택완료", view=tview)
                tview.disable_timeout()
                calendar_view = CalendarView(msg="날짜", ctx=self.ctx, next=0)
                await self.ctx.send("날짜를 선택해주세요", view=calendar_view)
        elif self.msg == "취소":
            await exit_select_menu()
        elif self.msg == 'next':
            tview = CalendarView(msg="날짜", ctx=self.ctx, next=1)
            await interaction.response.edit_message(content=f"다음날짜선택", view=tview)
            tview.disable_timeout()
        elif self.msg == '날짜':
            c['trgt_date'] = self.label
            today = datetime.datetime.today()
            tomorrow = today + datetime.timedelta(days=1)
            tomorrow_str = tomorrow.strftime("%Y%m%d")
            p_label = self.label
            tview = CalendarView(msg="날짜", ctx=self.ctx, next=0)
            await interaction.response.edit_message(content=f"날짜 선택완료", view=tview)
            disabled_early=False
            if c['trgt_date'] == tomorrow_str:
                print("당장 내일 표 예매라 아침시간을 제외합니다.")
                disabled_early=True
            tview.disable_timeout()
            mintime_view = TimeView(timeout=100, msg="min시간", ctx=self.ctx, disabled_early=disabled_early)
            await self.ctx.send("최소~최대 출발시간을 차례로 선택해주세요", view=mintime_view)
        elif self.msg == 'min시간':
            if c['start_time_min'] is None:
                c['start_time_min'] = self.label
                p_label = self.label
                tview = TimeView(msg="min시간", ctx=self.ctx)
                await interaction.response.edit_message(content=f"최소출발시간 : {p_label}, 최대출발시간을 선택해주세요.", view=tview)
                tview.disable_timeout()
            else:
                c['start_time_max'] = self.label
                p_label = "max시간"
                tview = TimeView(msg="max시간", ctx=self.ctx)
                await interaction.response.edit_message(content=f"시간 선택완료", view=tview)
                log.logger.info(
                    f"Thread Count : {thread_cnt}, {c['dep_station']} ~ {c['des_station']},  {c['trgt_date']}, {c['start_time_min']}~{c['start_time_max']}")
                tview.disable_timeout()
                is_running = False
                
        if self.exit is not True and self.is_finished_select():
            exitview = ExitView(msg="취소", th_cnt=thread_cnt)
            await interaction.channel.send(embed=self.print_selected_info(), view=exitview)
            if "srt" in cur_mode:
                srt_dict[self.cur_thread] = Srt(thread_cnt)
                srt_dict[self.cur_thread].min_time = int(c['start_time_min'])
                deptime = str(srt_dict[self.cur_thread].min_time -
                              (srt_dict[self.cur_thread].min_time % 2)).zfill(2) + '0000'
                srt_dict[self.cur_thread].start_time = list(
                    range(srt_dict[self.cur_thread].min_time, int(c['start_time_max'])+1))
                srt_dict[self.cur_thread].interval = 1
                # '2':"특실+일반실", '1':"특실", '0':"일반실"
                srt_dict[self.cur_thread].VIP = "0"
                srt_dict[self.cur_thread].start_now = start_now
                log.logger.info(
                    f"DONE> srt_dict : {srt_dict}, Thread Count : {self.cur_thread}")
        
                is_success = await srt_dict[self.cur_thread].start(srt_dict[self.cur_thread].srt_home, c['trgt_date'], deptime, c['dep_station'], c['des_station'])

            else:
                ktx_dict[self.cur_thread] = Ktx(thread_cnt)
                ktx_dict[self.cur_thread].min_time = int(c['start_time_min'])
                deptime = str(ktx_dict[self.cur_thread].min_time)

                ktx_dict[self.cur_thread].start_time = list(
                    range(ktx_dict[self.cur_thread].min_time, int(c['start_time_max'])+1))
                ktx_dict[self.cur_thread].interval = 1
                # '2':"특실+일반실", '1':"특실", '0':"일반실"
                ktx_dict[self.cur_thread].VIP = "0"
                ktx_dict[self.cur_thread].start_now = start_now
                print(c['trgt_date'], deptime, c['dep_station'], c['des_station'])

                is_success = await ktx_dict[self.cur_thread].start(c['trgt_date'], deptime, c['dep_station'], c['des_station'])
                log.logger.info(
                    f"DONE> ktx_dict : {ktx_dict}, Thread Count : {self.cur_thread}")


class ExitView(View):
    def __init__(self, timeout=None, msg: str = '', th_cnt=None):
        super().__init__(timeout=timeout)
        self.msg = msg

        btn = MyBtn(label="취소", style=discord.ButtonStyle.danger, msg=self.msg, cur_thread=th_cnt)
        self.add_item(btn)


class TimeView(View):
    def __init__(self, timeout: float = default_timeout, msg: str = '', ctx=None, disabled_early=None):
        super().__init__(timeout=timeout)
        self.msg = msg
        global c, thread_cnt
        self.ctx = ctx

        if c['start_time_max'] is not None:
            btn = MyBtn(label=f"{c['start_time_min']} ~ {c['start_time_max']}시",
                        style=discord.ButtonStyle.green,  disabled=True, ctx=self.ctx)
            self.add_item(btn)
        else:
            for x in range(6, 24):
                if disabled_early and x < 10:
                    continue
                if c['start_time_min'] == str(x):
                    btn = MyBtn(label=x, style=discord.ButtonStyle.green,
                                msg=self.msg, ctx=self.ctx, cur_thread=thread_cnt)
                elif c['start_time_min'] is not None and int(c['start_time_min']) >= x:
                    btn = MyBtn(label=x, style=discord.ButtonStyle.grey,
                                msg=self.msg, disabled=True, ctx=self.ctx, cur_thread=thread_cnt)
                else:
                    btn = MyBtn(label=x, style=discord.ButtonStyle.grey,
                                msg=self.msg, ctx=self.ctx, cur_thread=thread_cnt)
                self.add_item(btn)

    def disable_timeout(self):
        self.timeout = None

    # async def on_timeout(self) -> None:
    #     await self.ctx.send(content=f"시간초과로 매크로가 종료되었습니다. /srt를 다시 입력하세요.", view=None, embed=None)
    #     global is_running
    #     self.disable_timeout()
    #     is_running = False
    #     return await super().on_timeout()


class CalendarView(View):
    def __init__(self, timeout: float = default_timeout, msg: str = '', next=0, ctx=None):
        super().__init__(timeout=timeout)
        self.msg = msg
        global c, start_now
        self.ctx = ctx

        now = datetime.datetime.now()
        if next:
            now = now + datetime.timedelta(days=9)

        if c['trgt_date'] is not None:
            t_offset = 0
            if now.strftime("%d") > c['trgt_date']:
                t_offset = 20  # for next month
            cur_time = (now + datetime.timedelta(days=t_offset))
            c['trgt_date_txt'] = str(
                cur_time.strftime("%m"))+"월 "+c['trgt_date']
            trgt_date = c['trgt_date'].split("일")[0]
            c['trgt_date'] = str(cur_time.strftime("%Y%m"))+trgt_date
            btn = MyBtn(label=c['trgt_date_txt'], style=discord.ButtonStyle.green,
                        msg=self.msg, disabled=True, ctx=self.ctx)
            self.add_item(btn)
        else:
            prev_month = 0
            day_offset = 1 - start_now
            for x in range(0, 12):
                cur_time = (now + datetime.timedelta(days=day_offset))
                cur_month = int(cur_time.strftime("%m"))
                if prev_month < cur_month:
                    btn = MyBtn(label=str(cur_month)+"월", style=discord.ButtonStyle.green,
                                msg=self.msg, row=int(x/3), disabled=True, ctx=self.ctx)
                else:
                    day = cur_time.strftime("%d일(%a)")
                    day_offset += 1
                    if x < 11:
                        btn = MyBtn(label=day, style=discord.ButtonStyle.grey,
                                    msg=self.msg, row=int(x/3), ctx=self.ctx)
                    if next == 0 and x == 11:
                        btn = MyBtn(
                            label="다음", style=discord.ButtonStyle.grey, msg="next", row=3, ctx=self.ctx)
                    else:
                        btn = MyBtn(label=day, style=discord.ButtonStyle.grey,
                                    msg=self.msg, row=int(x/3), ctx=self.ctx)

                prev_month = cur_month
                self.add_item(btn)

    def disable_timeout(self):
        self.timeout = None

    # async def on_timeout(self) -> None:
    #     await self.ctx.send(content=f"시간초과로 매크로가 종료되었습니다. /srt를 다시 입력하세요.", view=None, embed=None)
    #     global is_running
    #     self.disable_timeout()
    #     is_running = False
    #     return await super().on_timeout()


class StationView(View):
    def __init__(self, timeout: float = default_timeout, msg: str = '', station: dict = {}, ctx=None):
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
                    btn = MyBtn(label=x, style=discord.ButtonStyle.green,
                                msg=self.msg, row=rows, disabled=True, ctx=self.ctx)
                else:
                    btn = MyBtn(label=x, style=discord.ButtonStyle.grey,
                                msg=self.msg, row=rows, ctx=self.ctx)
                self.add_item(btn)

    def disable_timeout(self):
        self.timeout = None

    # async def on_timeout(self) -> None:
    #     await self.ctx.send(content=f"시간초과로 매크로가 종료되었습니다. /srt를 다시 입력하세요.", view=None, embed=None)
    #     global is_running
    #     is_running = False
    #     self.disable_timeout()
    #     return await super().on_timeout()


@ bot.event
async def on_ready():
    print(f'서버 구동중... {bot.user.name}')
    await bot.change_presence(status=discord.Status.online, activity=discord.Activity(type=discord.ActivityType.listening, name="매크로 실행은 /srt 를 입력하세요."))


@ bot.command()
async def help(ctx):
    await ctx.send(embed=get_helpmsg(), view=None)


@ bot.command()
async def srt(ctx):
    global c, is_running, thread_cnt, cur_mode
    if is_running:
        await ctx.reply("다른분의 메뉴선택이 끝날때까지 기다렸다 다시 시도해주세요.", view=None)
    elif thread_cnt > 4:
        await ctx.reply("이미 4개의 매크로가 실행중입니다.\n나중에 다시 시도해주세요", view=None)
    else:
        for k in c.keys():
            c[k] = None
        is_running = True
        thread_cnt += 1
        cur_mode = "srt"

        departure_view = StationView(
            timeout=None, msg="출발", station=srt_short_station_dict, ctx=ctx)
        await ctx.reply("SRT 매크로를 시작합니다.\n출발, 도착역을 차례로선택해주세요", view=departure_view)


@ bot.command()
async def ktx(ctx):
    global c, is_running, thread_cnt, cur_mode
    if is_running:
        await ctx.reply("다른분의 메뉴선택이 끝날때까지 기다렸다 다시 시도해주세요.", view=None)
    elif thread_cnt > 4:
        await ctx.reply("이미 4개의 매크로가 실행중입니다.\n나중에 다시 시도해주세요", view=None)
    else:
        for k in c.keys():
            c[k] = None
        is_running = True
        thread_cnt += 1
        cur_mode = "ktx"

        departure_view = StationView(
            timeout=None, msg="출발", station=ktx_station_dict, ctx=ctx)
        await ctx.reply("KTX 매크로를 시작합니다.\n출발, 도착역을 차례로선택해주세요", view=departure_view)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        start_now = int(sys.argv[1])
    bot.run(conf['TOKEN'])
