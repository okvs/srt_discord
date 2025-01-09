# -*- coding: utf-8 -*-
import time
import random
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.select import Select
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as ec
# from fake_useragent import UserAgent
from user_agent import generate_user_agent, generate_navigator
import json
import asyncio

with open("config.json") as f:
    conf = json.load(f)

import sys
import re
from datetime import datetime
from mylog import MyLog
log = MyLog("ktx", "INFO")


class Ktx():
    chain_list = []

    def __init__(self, thread_count=None):
        self.ktx_home = 'https://www.letskorail.com'
        self.payment_url = 'https://etk.srail.kr/hpg/hra/02/selectReservationList.do?pageId=TK0102010000'
        self.class_type_txt = {'2': "특실+일반실", '1': "특실", '0': "일반실"}
        self.start_time_txt = {'1': "지금바로", '0': "새벽3시"}
        self.class_type = {'2': [6, 7], '1': [6], '0': [7]}
        self.station_dic = {'수서': 0, '동탄': 1, '평택지제': 2, '광주송정': 5, '김천구미': 7, '대전': 10, '동대구': 11,
                            '목포': 13, '부산': 15, '신경주': 18, '오송': 21, '익산': 23, '전주': 24, '천안아산': 30, '포항': 31}
        self.id = conf["KTX_ID"]
        self.pw = conf["KTX_PW"]
        self.card_info = conf["CARD_INFO"]
        self.mobile = conf["MOBILE"]
        self.interval = 1
        self.macro_run_time = {'start': '0323', 'end': '0450'}
        self.start_time = []
        self.start_now = 1
        self.min_time = 1
        self.max_time = 1
        self.VIP = '0'
        self.depature = ''
        self.destination = ''
        self.seat_only = 1  # 좌석, 입석+좌석
        self.target_time = 0
        self.thread_count = thread_count
        self.is_finish = False
        self.quit_now = False
        self.waiting = 0
        self.info_txt_for_print = ''
        self.run_from_log = 0
        self.non_ktx_list = [["수원", "창원중앙"]]

    async def tprint(self, msg):
        log.logger.info(
            # f"(THREAD{self.thread_count}{str(id(self.thread_count))[-3:]})> {msg}")
            f"(THREAD{self.thread_count})> {msg}")

    async def waiting_click(self, click_xpath, txt='', quiet=1, max_cnt=999):
        cnt = 0
        while 1:
            cnt += 1
            if cnt > max_cnt:
                return 0
            try:
                self.driver.find_element(By.XPATH, click_xpath).click()
                break
            except:
                await asyncio.sleep(0.3)
            finally:
                if quiet == 0:
                    print(f'waiting... {txt}')
                pass

    async def start(self, trgt_date=None, deptime=None, dep_station=None, des_station=None):
        if trgt_date is not None:
            await self.get_info(trgt_date, deptime, dep_station, des_station)

        if self.start_now == 0:
            nowtime = int(datetime.now().strftime("%H%M"))
            while (nowtime > int(self.macro_run_time['end']) or nowtime < int(self.macro_run_time['start'])):
                if self.quit_now is True:
                    await self.tprint("종료합니다.")
                    return 0
                nowtime = int(datetime.now().strftime("%H%M"))
                if nowtime % 1 == 0:
                    await asyncio.sleep(self.thread_count+13)
                    print(f"({nowtime:04d}) KTX 대기중 {self.thread_count} : {self.info_txt_for_print}")
                    if len(Ktx.chain_list) > 0 and self.thread_count == 1:
                        await asyncio.sleep(4)
                        if nowtime < 300:  # 3시전이면
                            Ktx.chain_list = sorted(Ktx.chain_list, key=lambda x: datetime.strptime(x.date, "%Y%m%d"))
                        for k in Ktx.chain_list:
                            print(f"({nowtime:04d}) KTX 체인대기중 {k.thread_count} : {k.info_txt_for_print}")

                await asyncio.sleep(60)
                if self.quit_now is True:
                    await self.tprint("종료합니다.")
                    return 0
        options = Options()
        options.add_argument("--incognito")  # 시크릿모드

        userAgent = generate_user_agent(
            os=('win', 'mac'), device_type='desktop')

        options.add_argument(f'user-agent={userAgent}')
        self.driver = webdriver.Chrome(
            service=Service('chromedriver.exe'), options=options)
        self.driver.maximize_window()
        self.driver.get(self.ktx_home)

        # login
        await self.login()

        await self.select_menu()
        while (self.is_finish == False):
            is_success = await self.trying()
        while (len(Ktx.chain_list) > 0):
            if self == Ktx.chain_list[0]:
                break
            await self.close()
            await self.tprint(f"체인실행 {Ktx.chain_list[0].info_txt_for_print} (대기중인 체인 : {len(Ktx.chain_list)-1})")
            await Ktx.chain_list[0].start()
            await self.tprint(f"체인삭제 {Ktx.chain_list[0].info_txt_for_print}")
            del Ktx.chain_list[0]
        return is_success

    async def login(self):
        await asyncio.sleep(2)
        await self.waiting_click('//*[@id="header"]/div[1]/div/ul/li[2]/a/img', "로그인 버튼 클릭")
        WebDriverWait(self.driver, 10).until(
            ec.presence_of_element_located((By.XPATH, '//*[@id="txtMember"]')))
        self.driver.find_element(
            By.XPATH, '//*[@id="txtMember"]').send_keys(self.id)
        self.driver.find_element(
            By.XPATH, '//*[@id="txtPwd"]').send_keys(self.pw)
        await asyncio.sleep(1)
        await self.waiting_click('//*[@id="loginDisplay1"]/ul/li[3]/a/img', "로그인 시도")

    async def close(self):
        try:
            await self.driver.quit()
        except:
            pass

    async def screenshot(self, slp=1):
        await self.driver.save_screenshot("tmp_ktx.png")
        await asyncio.sleep(int(slp))

    async def get_info(self, dep_date, dep_time, dep, des):

        self.date = dep_date
        self.year = dep_date[0:4]
        self.month = dep_date[4:6]
        self.day = dep_date[6:8]
        self.time = dep_time
        self.dep_time = str(dep_time).zfill(2)
        self.target_time = dep_time
        self.dep = dep
        self.des = des
        self.info_txt_for_print = f"{dep}->{des}, {dep_date}, {self.start_time}시"
        if self.run_from_log:
            await self.tprint(f"재시도 : {self.info_txt_for_print}")
        else:
            await self.tprint(f"시도대기 : {self.info_txt_for_print}")

    async def select_menu(self):
        if self.quit_now is True:
            return 0
        await asyncio.sleep(2)
        await self.waiting_click('//*[@id="header"]/div[3]/div[1]/h3/a', "승차권 예약 클릭")
        await asyncio.sleep(2)
        only_ktx = 1
        for non in self.non_ktx_list:
            if self.dep in non and self.des in non:
                only_ktx = 0
                break
        if only_ktx:
            await self.waiting_click('//*[@id="selGoTrainRa00"]', "KTX 버튼 클릭")
        await self.waiting_click('//*[@id="adjcCheckYn"]', "인접역 체크해제 클릭")
        self.driver.find_element(By.XPATH, '//*[@id="start"]').clear()
        self.driver.find_element(By.XPATH, '//*[@id="get"]').clear()
        dep_station = self.driver.find_element(By.XPATH, '//*[@id="start"]').send_keys(self.dep)
        des_station = self.driver.find_element(By.XPATH, '//*[@id="get"]').send_keys(self.des)

        Select(self.driver.find_element(By.XPATH, '//*[@id="s_year"]')).select_by_value(self.year)
        await asyncio.sleep(0.5)
        Select(self.driver.find_element(By.XPATH, '//*[@id="s_month"]')).select_by_value(self.month)
        await asyncio.sleep(0.5)
        Select(self.driver.find_element(By.XPATH, '//*[@id="s_day"]')).select_by_value(self.day)
        await asyncio.sleep(0.5)
        Select(self.driver.find_element(By.XPATH, '//*[@id="s_hour"]')).select_by_value(self.dep_time)
        await self.waiting_click('//*[@id="center"]/form/div/p/a/img', "조회하기 버튼 클릭")
        await asyncio.sleep(5)
        try:
            self.driver.switch_to.alert.accept()
        except:
            pass

    async def print_info(self):
        await self.screenshot(0)
        await self.tprint(f"<{self.dep} => {self.des}>\n{self.date}, {self.time}시 이후 열차 시도중\
            \ninterval : {self.interval}~{self.interval+1}초\n객실타입 : {self.class_type_txt[self.VIP]}")

    async def restart(self, url):
        self.close()
        time.sleep(2)
        self.start(self.chat_id, url)
        time.sleep(1)
        self.select_menu()
        while (1):
            self.trying()

    async def success_process(self):
        # await asyncio.sleep(3)
        # await self.screenshot()
        # await asyncio.sleep(5)
        # await self.tprint("소멸자")
        self.is_finish = True
        # self.__del__()

    async def trying(self):
        elements = self.driver.find_elements(By.XPATH, f'//*[@id="tableResult"]/tbody/tr')
        # elements = self.driver.find_elements(By.XPATH, f'//*[@id="tableResult"]/tbody/tr[1]')
        if len(elements) < 1:
            await self.tprint(f"elements is none {elements}")
            print("메뉴선택부터 다시")
            self.driver.get(self.ktx_home)
            await self.select_menu()
            await asyncio.sleep(10)
            return 0
        for i in range(len(elements)):
            seat_info_list = elements[i].text.split()
            if len(seat_info_list) == 0:
                continue
            # elements = self.driver.find_elements(By.XPATH, f'//*[@id="tableResult"]/tbody/tr[{i}]')
            # seat_info_list = elements[0].text.split()
            if re.search(r'\d', seat_info_list[1]):
                seat_info_list.insert(1, "list 자리수 맞주기")
            elif 'SRT' in seat_info_list[1]:
                continue
            dep_time = seat_info_list[4][:2]
            if int(dep_time) not in self.start_time:
                continue
            try:
                # seat_status = self.driver.find_element(By.XPATH, f'//*[@id="tableResult"]/tbody/tr[{}]/td[6]').accessible_name
                grade = 5
                if int(self.VIP) == 0:
                    grade = 6
                status = self.driver.find_element(
                    By.XPATH, f'//*[@id="tableResult"]/tbody/tr[{i+1}]/td[{grade}]/a[1]/img').get_attribute('alt')
                if "예약하기" not in status:
                    continue
                self.driver.find_element(By.XPATH, f'//*[@id="tableResult"]/tbody/tr[{i+1}]/td[{grade}]/a[1]/img').click()
            except:
                # 매진
                # print(f'{seat_info_list[4]}는 매진입니다')
                continue

            await self.tprint(f"< 예매 성공 > {self.info_txt_for_print}")
            try:
                self.driver.switch_to.frame(0)
                await self.waiting_click('/html/body/div/div[2]/p[3]/a', "산천 팝업창", max_cnt=3)
                # print("산천팝업")
                self.driver.switch_to.default_content()
                # print("산천팝업 디폴트")
            except:
                # await self.tprint("산천 팝업창이 안떠서 팝업창해제를 스킵합니다")
                pass
            try:
                await asyncio.sleep(1)
                self.driver.switch_to.alert.accept()
                await asyncio.sleep(1)
                self.driver.switch_to.alert.accept()
                await asyncio.sleep(1)
                self.driver.switch_to.alert.accept()
            except:
                pass
            await asyncio.sleep(2)

            # 팝업창 클릭 만들어야함
            # self.driver.execute_script("document.body.style.zoom = '90%'")
            await self.waiting_click('//*[@id="btn_next"]', "결제하기")
            await self.waiting_click('//*[@id="tabStl1"]', "신용카드 탭 클릭")
            await asyncio.sleep(1)
            for i in range(1, 5):
                self.driver.find_element(
                    By.XPATH, f'//*[@id="Div_Card"]/table/tbody/tr[2]/td/input[{i}]').send_keys(self.card_info["card_num"][i - 1])
                await asyncio.sleep(0.3)
            await asyncio.sleep(0.3)
            sel_mon = Select(self.driver.find_element(
                By.XPATH, '//*[@id="month"]')).select_by_value(self.card_info["exp_month"])
            await asyncio.sleep(0.3)
            sel_year = Select(self.driver.find_element(
                By.XPATH, '//*[@id="year"]')).select_by_value(self.card_info["exp_year"])
            await asyncio.sleep(0.3)
            pw_box = self.driver.find_element(
                By.XPATH, '//*[@id="Div_Card"]/table/tbody/tr[5]/td/input').send_keys(self.card_info["pw"])
            await asyncio.sleep(0.3)
            verif_box = self.driver.find_element(
                By.XPATH, '//*[@id="Div_Card"]/table/tbody/tr[6]/td/input').send_keys(self.card_info['verif_code'])
            await asyncio.sleep(0.3)
            await self.waiting_click('//*[@id="chkAgree"]', "개인정보수집동의", max_cnt=10)
            await asyncio.sleep(0.3)
            await self.waiting_click('//*[@id="fnIssuing"]', "발권하기 버튼", max_cnt=10, quiet=0)
            await asyncio.sleep(0.3)
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            await asyncio.sleep(0.3)

            cur_frame = self.driver.switch_to.frame("mainframeSaleInfo")
            await self.waiting_click('//*[@id="btn_next2"]', "코레일톡 발권 버튼", max_cnt=10, quiet=0)
            await asyncio.sleep(2)
            self.driver.switch_to.alert.accept()
            await self.tprint(f"< 결제 완료 > {self.info_txt_for_print}")
            await asyncio.sleep(2)
            self.is_finish = True
            # self.driver.quit()
            return 1
        else:
            ran_time = float(str(random.randint(
                self.interval, self.interval+1)) + '.' + str(random.randint(1, 3)))
            await asyncio.sleep(ran_time)
            self.driver.refresh()
            await asyncio.sleep(0.1)
        if self.start_now == 0:
            nowtime = int(datetime.now().strftime("%H%M"))
            if (nowtime > int(self.macro_run_time['end'])):
                await self.tprint(f"{nowtime} : 새벽 매크로를 정지합니다... ")
                await asyncio.sleep(600)
                self.is_finish = True
                return 0


async def main():
    k = Ktx(0)
    if __name__ == "__main__":
        if len(sys.argv) > 1:
            k.start_now = int(sys.argv[1])
            await k.tprint(sys.argv[1:])
            is_success = await k.start(trgt_date=sys.argv[2], deptime=sys.argv[3], dep_station="서울", des_station="진주")
            # is_success = await k.start(trgt_date=sys.argv[2], deptime=sys.argv[3], dep_station=sys.argv[4], des_station=sys.argv[5])
        else:
            is_success = await k.start(trgt_date="20250115", deptime="08", dep_station="서울", des_station="진주")
    # is_success = await k.start(trgt_date="20240623", deptime="08", dep_station="서울", des_station="진주")

if __name__ == "__main__":
    asyncio.run(main())
