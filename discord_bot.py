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
import chromedriver_autoinstaller
import requests
from bs4 import BeautifulSoup
import re
import subprocess
from to_notion import *

with open("config.json") as f:
    conf = json.load(f)

api_key = conf["NOTION_API_KEY"]  # Notion  API 키
db_id = conf["NOTION_DB_ID"]
now = datetime.datetime.now()
log = MyLog("discord", "INFO")
intents = discord.Intents.all()
intents.members = True
bot = commands.Bot(command_prefix='/', help_command=None, intents=intents)

c = {'dep_station': None, 'des_station': None, 'trgt_date': None,
     'start_time_min': None, 'start_time_max': None}
srt_short_station_dict = {'수서': 0, '동탄': 1, '평택지제': 2, '창원': 28, '광주송정': 6,  '김천구미': 8,
                          '대전': 11, '동대구': 12,   '부산': 16, '전주': 24,
                          '오송': 21, '익산': 23, '울산(통도사)': 22,  '천안아산': 30, '포항': 31,
                          '목포': 14, '진영': 26, '경주': 3, '진주': 27, '나주': 9}

ktx_station_dict = {'서울': 0, '용산': 1, '영등포': 2, '광명': 3,  '수원': 4,
                    '천안아산': 5, '오송': 6, '대전': 7, '김천구미': 9,
                    '동대구': 10, '경주': 11, '포항': 12, '부산': 13, '강릉': 14,
                    '익산': 15, '울산': 16, '광주송정': 17, '전주': 18, '순천': 19,
                    '여수': 20}
is_running = False
srt_thread_cnt = 0
ktx_thread_cnt = 0
srt_dict = {}
ktx_dict = {}
default_timeout = None
cur_mode = None
admin_mode = False
user_name = None
tasks = []
start_now = 0
max_window = 4  # 한번에 띄우는 최대 창 수


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
        global c, is_running, srt_thread_cnt, ktx_thread_cnt, srt_dict, admin_mode, max_window, user_name

        async def exit_select_menu(done=0):
            global is_running, srt_thread_cnt, ktx_thread_cnt, srt_dict
            if srt_thread_cnt in srt_dict:
                srt_dict[self.cur_thread].quit_now = True
            if ktx_thread_cnt in ktx_dict:
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
            disabled_early = False
            if c['trgt_date'] == tomorrow_str and admin_mode == False:
                print("당장 내일 표 예매라 아침시간을 제외합니다.")
                disabled_early = True
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
                if "srt" in cur_mode:
                    log.logger.info(
                        f"Srt Thread Count : {srt_thread_cnt}, {c['dep_station']} ~ {c['des_station']},  {c['trgt_date']}, {c['start_time_min']}~{c['start_time_max']}")
                else:
                    log.logger.info(
                        f"Ktx Thread Count : {ktx_thread_cnt}, {c['dep_station']} ~ {c['des_station']},  {c['trgt_date']}, {c['start_time_min']}~{c['start_time_max']}")
                tview.disable_timeout()
                is_running = False

        if self.exit is not True and self.is_finished_select():
            if 'srt' in cur_mode:
                exitview = ExitView(msg="취소", th_cnt=srt_thread_cnt)
            else:
                exitview = ExitView(msg="취소", th_cnt=ktx_thread_cnt)
            await interaction.channel.send(embed=self.print_selected_info(), view=exitview)
            if "srt" in cur_mode:
                srt_dict[self.cur_thread] = Srt(srt_thread_cnt)
                srt_dict[self.cur_thread].min_time = int(c['start_time_min'])
                deptime = str(srt_dict[self.cur_thread].min_time -
                              (srt_dict[self.cur_thread].min_time % 2)).zfill(2) + '0000'
                srt_dict[self.cur_thread].start_time = list(
                    range(srt_dict[self.cur_thread].min_time, int(c['start_time_max'])+1))
                srt_dict[self.cur_thread].interval = 1
                # '2':"특실+일반실", '1':"특실", '0':"일반실"
                srt_dict[self.cur_thread].VIP = "0"
                srt_dict[self.cur_thread].start_now = start_now
                if len(srt_dict[self.cur_thread].start_time) > 1:
                    notion_time = f"{srt_dict[self.cur_thread].start_time[0]}-{srt_dict[self.cur_thread].start_time[-1]}"
                else:
                    notion_time = f"{srt_dict[self.cur_thread].start_time[0]}"
                to_notion_data = {'이름': user_name,
                                  '출발역': c['dep_station'],
                                  '도착역': c['des_station'],
                                  '날짜': f"{c['trgt_date'][:4]}-{c['trgt_date'][4:6]}-{c['trgt_date'][6:]}",
                                  '시간': notion_time,
                                  '타입': 'srt',
                                  '좌석수': 1,
                                  '정산': "발권 전",
                                  '비고': '디스코드'}

                create_result = await create_page(api_key, db_id, to_notion_data)
                if create_result == 200:
                    log.logger.info(f"노션 등록 완료 : {to_notion_data}")
                    srt_dict[self.cur_thread].notion_data = {'num_id': num_id, 'status': status,
                                                             'page_id': d['page_id'], 'name': d['name'], 'seats': d['seats']}
                if srt_thread_cnt <= max_window:
                    log.logger.info(f"Srt Thread Count : {self.cur_thread}")
                    is_success = await srt_dict[self.cur_thread].start(c['trgt_date'], deptime, c['dep_station'], c['des_station'])
                else:
                    log.logger.info(
                        f"Thread Count : {self.cur_thread}라서 체인으로 실행")
                    await srt_dict[self.cur_thread].get_info(c['trgt_date'], deptime, c['dep_station'], c['des_station'])
                    Srt.chain_list.append(srt_dict[self.cur_thread])

            else:
                ktx_dict[self.cur_thread] = Ktx(ktx_thread_cnt)
                ktx_dict[self.cur_thread].min_time = int(c['start_time_min'])
                deptime = str(ktx_dict[self.cur_thread].min_time)

                ktx_dict[self.cur_thread].start_time = list(
                    range(ktx_dict[self.cur_thread].min_time, int(c['start_time_max'])+1))
                ktx_dict[self.cur_thread].interval = 1
                # '2':"특실+일반실", '1':"특실", '0':"일반실"
                ktx_dict[self.cur_thread].VIP = "0"
                ktx_dict[self.cur_thread].start_now = start_now
                if c['start_time_min'] == c['start_time_max']:
                    notion_time = c['start_time_min']
                else:
                    notion_time = f"{c['start_time_min']}-{c['start_time_max']}"
                to_notion_data = {'이름': user_name,
                                  '출발역': c['dep_station'],
                                  '도착역': c['des_station'],
                                  '날짜': f"{c['trgt_date'][:4]}-{c['trgt_date'][4:6]}-{c['trgt_date'][6:]}",
                                  '시간': notion_time,
                                  '타입': 'ktx',
                                  '좌석수': 1,
                                  '정산': "발권 전",
                                  '비고': "디스코드"}
                create_result = create_page(api_key, db_id, to_notion_data)
                if create_result == 200:
                    log.logger.info(f"노션 등록 완료 : {to_notion_data}")
                    ktx_dict[self.cur_thread].notion_data = {'num_id': num_id, 'status': status,
                                                             'page_id': d['page_id'], 'name': d['name'], 'seats': d['seats']}
                if ktx_thread_cnt <= max_window:
                    log.logger.info(f"Ktx Thread Count : {self.cur_thread}")
                    is_success = await ktx_dict[self.cur_thread].start(c['trgt_date'], deptime, c['dep_station'], c['des_station'])
                else:
                    log.logger.info(
                        f"Ktx Thread Count : {self.cur_thread}라서 체인으로 실행")
                    await ktx_dict[self.cur_thread].get_info(c['trgt_date'], deptime, c['dep_station'], c['des_station'])
                    Ktx.chain_list.append(ktx_dict[self.cur_thread])


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
        global c, srt_thread_cnt, ktx_thread_cnt
        self.ctx = ctx
        tcnt = srt_thread_cnt
        if 'ktx' in cur_mode:
            tcnt = ktx_thread_cnt

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
                                msg=self.msg, ctx=self.ctx, cur_thread=tcnt)
                elif c['start_time_min'] is not None and int(c['start_time_min']) >= x:
                    btn = MyBtn(label=x, style=discord.ButtonStyle.grey,
                                msg=self.msg, disabled=True, ctx=self.ctx, cur_thread=tcnt)
                else:
                    btn = MyBtn(label=x, style=discord.ButtonStyle.grey,
                                msg=self.msg, ctx=self.ctx, cur_thread=tcnt)
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
        global c, start_now, admin_mode
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
            if admin_mode:
                day_offset = 0
                start_now = 1
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
    await bot.change_presence(status=discord.Status.online, activity=discord.Activity(type=discord.ActivityType.listening, name="매크로 실행은 /srt 또는 /ktx를 입력하세요."))


@ bot.command()
async def help(ctx):
    await ctx.send(embed=get_helpmsg(), view=None)


@ bot.command()
async def srt(ctx):
    global c, is_running, srt_thread_cnt, cur_mode, user_name
    author = ctx.author
    author_name = author.name
    user_name = author.display_name

    if is_running:
        await ctx.reply("다른분의 메뉴선택이 끝날때까지 기다렸다 다시 시도해주세요.", view=None)
    else:
        for k in c.keys():
            c[k] = None
        is_running = True
        srt_thread_cnt += 1
        cur_mode = "srt"

        departure_view = StationView(
            timeout=None, msg="출발", station=srt_short_station_dict, ctx=ctx)
        await ctx.reply("SRT 매크로를 시작합니다.\n출발, 도착역을 차례로선택해주세요", view=departure_view)


@ bot.command()
async def srtx(ctx):
    global c, is_running, srt_thread_cnt, cur_mode, admin_mode, user_name
    author = ctx.author
    author_name = author.name
    user_name = author.display_name
    admin_mode = 0
    print(f"이름 : {author_name}")

    if str(author_name) == 'smin312':
        admin_mode = 1
        print("관리자 모드로 실행합니다.")
    else:
        return 0
    if is_running:
        await ctx.reply("다른분의 메뉴선택이 끝날때까지 기다렸다 다시 시도해주세요.", view=None)
    else:
        for k in c.keys():
            c[k] = None
        is_running = True
        srt_thread_cnt += 1
        cur_mode = "srt"

        departure_view = StationView(
            timeout=None, msg="출발", station=srt_short_station_dict, ctx=ctx)
        await ctx.reply("SRT 매크로를 시작합니다.\n출발, 도착역을 차례로선택해주세요", view=departure_view)


@ bot.command()
async def ktx(ctx):
    global c, is_running, ktx_thread_cnt, cur_mode, admin_mode, user_name
    author = ctx.author
    author_name = author.name
    user_name = author.display_name

    if is_running:
        await ctx.reply("다른분의 메뉴선택이 끝날때까지 기다렸다 다시 시도해주세요.", view=None)
    elif ktx_thread_cnt > 4:
        await ctx.reply("이미 4개의 매크로가 실행중입니다.\n나중에 다시 시도해주세요", view=None)
    else:
        for k in c.keys():
            c[k] = None
        is_running = True
        ktx_thread_cnt += 1
        cur_mode = "ktx"

        departure_view = StationView(
            timeout=None, msg="출발", station=ktx_station_dict, ctx=ctx)
        await ctx.reply("KTX 매크로를 시작합니다.\n출발, 도착역을 차례로선택해주세요", view=departure_view)


@ bot.command()
async def ktxx(ctx):
    global c, is_running, ktx_thread_cnt, cur_mode, admin_mode, user_name
    author = ctx.author
    author_name = author.name
    user_name = author.display_name
    admin_mode = 0
    print(f"이름 : {author_name}")
    if str(author_name) == 'smin312':
        admin_mode = 1
        print("관리자 모드로 실행합니다.")
    else:
        return 0
    if is_running:
        await ctx.reply("다른분의 메뉴선택이 끝날때까지 기다렸다 다시 시도해주세요.", view=None)
    elif ktx_thread_cnt > 4:
        await ctx.reply("이미 4개의 매크로가 실행중입니다.\n나중에 다시 시도해주세요", view=None)
    else:
        for k in c.keys():
            c[k] = None
        is_running = True
        ktx_thread_cnt += 1
        cur_mode = "ktx"

        departure_view = StationView(
            timeout=None, msg="출발", station=ktx_station_dict, ctx=ctx)
        await ctx.reply("KTX 매크로를 시작합니다.\n출발, 도착역을 차례로선택해주세요", view=departure_view)


def check_chrome_ver():
    latest_chrome_ver_url = "https://googlechromelabs.github.io/chrome-for-testing/"
    response = requests.get(latest_chrome_ver_url)
    soup = BeautifulSoup(response.content, "html.parser")
    latest_chrome_ver = re.search(r"Stable\S+<code>([\d\.]+)</code>", str(soup)).group(1)

    import os
    current_dir = os.path.dirname(os.path.abspath(__file__))
    print(f"c:\Workspace\chromedriver.exe")
    result = subprocess.run([f"chromedriver.exe", "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    cur_chrome_ver = result.stdout.strip().split()[-2]

    if cur_chrome_ver[:3] != latest_chrome_ver[:3]:
        print("@"*1000)
        print(f"Plz Update Chrome Version {cur_chrome_ver} -> {latest_chrome_ver}")
        print("@"*1000)
    else:
        print("크롬드라이버 버전 체크 완료")


async def main():
    await asyncio.gather(
        # bot.run(conf['TOKEN']),
        bot.start(conf['TOKEN']),
        *tasks
    )


if __name__ == "__main__":
    check_chrome_ver()

    if len(sys.argv) > 1:
        start_now = int(sys.argv[1])

    # srt_from_log_dict = {}
    # ktx_from_log_dict = {}
    # with open("srt.log", "r", encoding="utf-8") as file:
    #     for line in file:
    #         if "시도대기" in line:
    #             matches = re.findall(r"시도대기 : (.*)시", line.strip())
    #             if matches[0] not in srt_from_log_dict:
    #                 srt_from_log_dict[matches[0]] = {'try': 1, 'success': 0, 'cancel': 0, 'finish': 0}
    #             else:
    #                 srt_from_log_dict[matches[0]]['try'] += 1
    #         elif "< 결제 완료 >" in line or "일반실 예약대기 완료 >" in line:
    #             matches = re.findall(r"완료 > (.*)시", line.strip())
    #             srt_from_log_dict[matches[0]]['finish'] += 1
    #         elif "< 취소 >" in line:
    #             matches = re.findall(r"취소 > (.*)시", line.strip())
    #             srt_from_log_dict[matches[0]]['cancel'] += 1

    # with open("ktx.log", "r", encoding="utf-8") as file:
    #     for line in file:
    #         if "시도대기" in line:
    #             matches = re.findall(r"시도대기 : (.*)시", line.strip())
    #             if matches[0] not in ktx_from_log_dict:
    #                 ktx_from_log_dict[matches[0]] = {'try': 1, 'success': 0, 'cancel': 0, 'finish': 0}
    #             else:
    #                 ktx_from_log_dict[matches[0]]['try'] += 1
    #         elif "< 결제 완료 >" in line or "일반실 예약대기 완료 >" in line:
    #             matches = re.findall(r"완료 > (.*)시", line.strip())
    #             ktx_from_log_dict[matches[0]]['finish'] += 1
    #         elif "< 취소 >" in line:
    #             matches = re.findall(r"취소 > (.*)시", line.strip())
    #             ktx_from_log_dict[matches[0]]['cancel'] += 1

    # with open("srt.log", "r", encoding="utf-8") as file:
    #     for line in file:
    #         if "< 예매 성공 > " in line:
    #             matches = re.findall(r"< 예매 성공 > (.*)시", line.strip())
    #             srt_from_log_dict[matches[0]]['success'] += 1

    # with open("ktx.log", "r", encoding="utf-8") as file:
    #     for line in file:
    #         if "< 예매 성공 > " in line:
    #             matches = re.findall(r"< 예매 성공 > (.*)시", line.strip())
    #             ktx_from_log_dict[matches[0]]['success'] += 1

    # for k, v in srt_from_log_dict.items():
    #     run_cnt = 0
    #     if v['try'] - v['cancel'] > v['finish']:
    #         run_cnt = v['try'] - v['finish']
    #         if v['finish']-v['success'] != 0:
    #             log.logger.info(f"(SRT) 총 {v['try']}건의 시도중 {v['finish']}건 성공(결제실패 {v['success']-v['finish']}건)했으므로 다시 시도합니다 {k}")
    #         else:
    #             log.logger.info(f"(SRT) 총 {v['try']}건의 시도중 {v['finish']}건 성공했으므로 다시 시도합니다 {k}")
    #         matches = re.findall(r"(\S+)->(\S+), (\d+), (\[[\d, ]+\])", k)[0]
    #         dep = matches[0]
    #         des = matches[1]
    #         dep_date = matches[2]
    #         trgt_time_list = json.loads(matches[3])
    #         for _ in range(run_cnt):
    #             srt_thread_cnt += 1
    #             dep_time = str(trgt_time_list[0] - (trgt_time_list[0] % 2)).zfill(2) + '0000'
    #             srt_dict[srt_thread_cnt] = Srt(srt_thread_cnt)
    #             srt_dict[srt_thread_cnt].start_time = trgt_time_list
    #             srt_dict[srt_thread_cnt].start_now = start_now
    #             srt_dict[srt_thread_cnt].run_from_log = 1

    #             if srt_thread_cnt <= max_window:
    #                 tasks.append(srt_dict[srt_thread_cnt].start(dep_date, dep_time, dep, des))
    #             else:
    #                 log.logger.info(
    #                     f"(SRT)   Thread Count : {srt_thread_cnt}라서 체인으로 실행(run_from_log) {k}")
    #                 tasks.insert(0, srt_dict[srt_thread_cnt].get_info(dep_date, dep_time, dep, des))
    #                 Srt.chain_list.append(srt_dict[srt_thread_cnt])
    #     elif v['try'] > 0:
    #         print(f"(SRT INFO) {k}는 {v['try']}번 발권내역이 있습니다.")

    # for k, v in ktx_from_log_dict.items():
    #     run_cnt = 0
    #     if v['try'] - v['cancel'] > v['finish']:
    #         run_cnt = v['try'] - v['finish']
    #         if v['finish']-v['success'] != 0:
    #             log.logger.info(f"(KTX) 총 {v['try']}건의 시도중 {v['finish']}건 성공(결제실패 {v['success']-v['finish']}건)했으므로 다시 시도합니다 {k}")
    #         else:
    #             log.logger.info(f"(KTX) 총 {v['try']}건의 시도중 {v['finish']}건 성공했으므로 다시 시도합니다 {k}")
    #         matches = re.findall(r"(\S+)->(\S+), (\d+), (\[[\d, ]+\])", k)[0]
    #         dep = matches[0]
    #         des = matches[1]
    #         dep_date = matches[2]
    #         trgt_time_list = json.loads(matches[3])
    #         for _ in range(run_cnt):
    #             ktx_thread_cnt += 1
    #             dep_time = str(trgt_time_list[0])
    #             ktx_dict[ktx_thread_cnt] = Ktx(ktx_thread_cnt)
    #             ktx_dict[ktx_thread_cnt].start_time = trgt_time_list
    #             ktx_dict[ktx_thread_cnt].start_now = start_now
    #             ktx_dict[ktx_thread_cnt].run_from_log = 1

    #             if ktx_thread_cnt <= max_window:
    #                 tasks.append(ktx_dict[ktx_thread_cnt].start(dep_date, dep_time, dep, des))
    #             else:
    #                 log.logger.info(
    #                     f"(KTX)   Thread Count : {ktx_thread_cnt}라서 체인으로 실행(run_from_log) {k}")
    #                 tasks.insert(0, ktx_dict[ktx_thread_cnt].get_info(dep_date, dep_time, dep, des))
    #                 Ktx.chain_list.append(ktx_dict[ktx_thread_cnt])
    #     elif v['try'] > 0:
    #         print(f"(KTX INFO) {k}는 {v['try']}번 발권내역이 있습니다.")

    need_conf_update = False
    with open("srt.log", "r", encoding="utf-8") as file:
        for line in file:
            if "예약대기 완료" in line:
                exceuted_time = line.split()[1]
                if conf['SRT_RES_MIN'] > exceuted_time:
                    log.logger.info(f"(SRT 예약대기 history) Min : {conf['SRT_RES_MIN']} -> {exceuted_time}")
                    conf['SRT_RES_MIN'] = exceuted_time
                    need_conf_update = True
                if conf['SRT_RES_MAX'] < exceuted_time and exceuted_time < '05:55:55,555':
                    log.logger.info(f"(SRT 예약대기 history) Max : {conf['SRT_RES_MAX']} -> {exceuted_time}")
                    conf['SRT_RES_MAX'] = exceuted_time
                    need_conf_update = True
            elif "결제 완료" in line:
                exceuted_time = line.split()[1]
                if conf['SRT_BUY_MIN'] > exceuted_time:
                    log.logger.info(f"(SRT 취소표 history) Min : {conf['SRT_BUY_MIN']} -> {exceuted_time}")
                    conf['SRT_BUY_MIN'] = exceuted_time
                    need_conf_update = True
                if conf['SRT_BUY_MAX'] < exceuted_time and exceuted_time < '05:55:55,555':
                    log.logger.info(f"(SRT 취소표 history) Max : {conf['SRT_BUY_MAX']} -> {exceuted_time}")
                    conf['SRT_BUY_MAX'] = exceuted_time
                    need_conf_update = True
    with open("ktx.log", "r", encoding="utf-8") as file:
        for line in file:
            if "결제 완료" in line:
                exceuted_time = line.split()[1]
                if conf['KTX_BUY_MIN'] > exceuted_time:
                    log.logger.info(f"(KTX 취소표 history) Min : {conf['KTX_BUY_MIN']} -> {exceuted_time}")
                    conf['KTX_BUY_MIN'] = exceuted_time
                    need_conf_update = True
                if conf['KTX_BUY_MAX'] < exceuted_time and exceuted_time < '05:55:55,555':
                    log.logger.info(f"(KTX 취소표 history) Max : {conf['KTX_BUY_MAX']} -> {exceuted_time}")
                    conf['KTX_BUY_MAX'] = exceuted_time
                    need_conf_update = True
    if need_conf_update:
        with open("config.json", "w") as f:
            json.dump(conf, f, indent=4)

    notion_data_pre = read_database(api_key, db_id)
    notion_data_pre = sorted(notion_data_pre.items(),        key=lambda x: (x[1]['date'], x[1]['type']))
    import random
    random.shuffle(notion_data_pre)

    notion_data = []
    latest_date = None
    multiple_seat_list = []
    ktx_start_num = sum(1 for item in notion_data_pre if item[1]['type'] == 'srt')
    for i, d_tup in enumerate(notion_data_pre):
        num_id = d_tup[0]
        d = d_tup[1]
        status = d['status']
        if i == ktx_start_num:
            latest_date = None
            if len(multiple_seat_list) > 0:
                notion_data.extend(multiple_seat_list.copy())
                multiple_seat_list = []

        if status == '발권 전' or status == '부분발권':
            dep_date = d['date'].replace('-', '')
            if latest_date is None:
                latest_date = dep_date

            if d['seats'] > 1:
                for k in range(d['seats']-1-(d['status'] == '부분발권')):
                    multiple_seat_list.append(d_tup)
            elif (latest_date < dep_date) and len(multiple_seat_list) > 0:
                notion_data.extend(multiple_seat_list.copy())
                multiple_seat_list = []

            if i == len(notion_data_pre)-1 and len(multiple_seat_list) > 0:
                notion_data.extend(multiple_seat_list.copy())
            notion_data.append(d_tup)
            latest_date = dep_date

    high_priority_list = []
    for i, d_tup in enumerate(notion_data):
        if 'memo' not in d_tup[1]:
            continue
        if '우선' in d_tup[1]['memo']:
            high_priority_list.append(d_tup)
    for h in high_priority_list:
        notion_data.remove(h)  # 기존 위치에서 제거
        notion_data.insert(0, h)  # 맨 앞에 삽입

    for i, d_tup in enumerate(notion_data):
        num_id = d_tup[0]
        d = d_tup[1]
        status = d['status']

        if status == '발권 전' or status == '부분발권':
            # print(d)
            dep = d['dep']
            des = d['des']
            dep_date = d['date'].replace('-', '')
            if '-' in d['time'] or '~' in d['time']:
                start, end = map(int, d['time'].split('-'))
                trgt_time_list = list(range(start, end + 1))
            else:
                trgt_time_list = [int(d['time'])]
            cur_notion_data = {'num_id': num_id, 'status': status, 'page_id': d['page_id'], 'name': d['name'], 'seats': d['seats']}
            if 'memo' in d:
                cur_notion_data['memo'] = d['memo']

            if d['type'] == 'srt':
                srt_thread_cnt += 1
                dep_time = str(trgt_time_list[0] - (trgt_time_list[0] % 2)).zfill(2) + '0000'
                srt_dict[srt_thread_cnt] = Srt(srt_thread_cnt)
                srt_dict[srt_thread_cnt].start_time = trgt_time_list
                srt_dict[srt_thread_cnt].start_now = start_now
                srt_dict[srt_thread_cnt].notion_data = cur_notion_data

                if srt_thread_cnt <= max_window:
                    tasks.append(srt_dict[srt_thread_cnt].start(dep_date, dep_time, dep, des))
                    log.logger.info(
                        f"(SRT)   Thread Count : {srt_thread_cnt}, 매크로 등록 {num_id} : {d['name']}, {d['dep']}->{d['des']}, {d['date']}, {trgt_time_list}시")
                else:
                    log.logger.info(
                        f"(SRT)   Thread Count : {srt_thread_cnt}, 체인으로 등록 {num_id} : {d['name']}, {d['dep']}->{d['des']}, {d['date']}, {trgt_time_list}시")
                    tasks.insert(0, srt_dict[srt_thread_cnt].get_info(dep_date, dep_time, dep, des))
                    Srt.chain_list.append(srt_dict[srt_thread_cnt])
            else:
                ktx_thread_cnt += 1
                dep_time = str(trgt_time_list[0])
                ktx_dict[ktx_thread_cnt] = Ktx(ktx_thread_cnt)
                ktx_dict[ktx_thread_cnt].start_time = trgt_time_list
                ktx_dict[ktx_thread_cnt].start_now = start_now
                ktx_dict[ktx_thread_cnt].notion_data = cur_notion_data

                if ktx_thread_cnt <= max_window:
                    tasks.append(ktx_dict[ktx_thread_cnt].start(dep_date, dep_time, dep, des))
                    log.logger.info(
                        f"(KTX)   Thread Count : {ktx_thread_cnt}, 매크로 등록 {num_id} : {d['name']}, {d['dep']}->{d['des']}, {d['date']}, {trgt_time_list}시")
                else:
                    log.logger.info(
                        f"(KTX)   Thread Count : {ktx_thread_cnt}, 체인으로 등록 {num_id} : {d['name']}, {d['dep']}->{d['des']}, {d['date']}, {trgt_time_list}시")
                    tasks.insert(0, ktx_dict[ktx_thread_cnt].get_info(dep_date, dep_time, dep, des))
                    Ktx.chain_list.append(ktx_dict[ktx_thread_cnt])

    asyncio.run(main())


# if __name__ == "__main__":
#     check_chrome_ver()

#     if len(sys.argv) > 1:
#         start_now = int(sys.argv[1])

#     # bot.run(conf['TOKEN'])

#     asyncio.run(main())
