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
import chromedriver_autoinstaller


class Ktx():
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
        self.log = MyLog("ktx", "INFO")
        self.waiting = 0
        self.row_list = [1]

    async def tprint(self, msg):
        self.log.logger.info(
            f"(THREAD{self.thread_count}{str(id(self.thread_count))[-3:]})> {msg}")

    async def waiting_and_click(self, click_xpath, txt='', quiet=1, max_cnt=99):
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

    async def start(self, trgt_date, deptime, dep_station, des_station):
        chrome_ver = chromedriver_autoinstaller.get_chrome_version()
        print("current chrome version: {}".format(chrome_ver))
        chromedriver_autoinstaller.install()

        if self.start_now == 0:
            nowtime = int(datetime.now().strftime("%H%M"))
            while (nowtime > int("0455") or nowtime < int("0300")):
                if self.quit_now is True:
                    await self.tprint("종료합니다.")
                    return 0
                nowtime = int(datetime.now().strftime("%H%M"))
                if nowtime % 3 == 0:
                    print(f"대기중.. {nowtime:04d}")
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

        await self.get_info(trgt_date, deptime, dep_station, des_station)
        await self.select_menu()
        cnt = 0
        while (self.is_finish == False):
            if cnt % 300 == 299:
                self.driver.get(self.ktx_home)
                await self.select_menu()
                await self.tprint("처음부터 다시 시작")
            is_success = 0
            for row in self.row_list:
                if is_success == 1:
                    break
                is_success = await self.trying(row)
            cnt += 1
        return is_success

    async def login(self):
        await asyncio.sleep(2)
        await self.waiting_and_click('//*[@id="header"]/div[1]/div/ul/li[2]/a/img', "로그인 버튼 클릭")
        WebDriverWait(self.driver, 10).until(
            ec.presence_of_element_located((By.XPATH, '//*[@id="txtMember"]')))
        self.driver.find_element(
            By.XPATH, '//*[@id="txtMember"]').send_keys(self.id)
        self.driver.find_element(
            By.XPATH, '//*[@id="txtPwd"]').send_keys(self.pw)
        await asyncio.sleep(1)
        await self.waiting_and_click('//*[@id="loginDisplay1"]/ul/li[3]/a/img', "로그인 시도")

    async def close(self):
        await self.driver.quit()

    async def screenshot(self, slp=1):
        await self.driver.save_screenshot("tmp_ktx.png")
        await asyncio.sleep(int(slp))

    async def get_info(self, dep_date, dep_time, dep, des):

        self.date = dep_date
        self.year = dep_date[0:4]
        self.month = dep_date[4:6]
        self.day = dep_date[6:8]
        self.time = dep_time
        self.dep_time = dep_time
        self.target_time = dep_time
        self.dep = dep
        self.des = des

    async def select_menu(self):
        if self.quit_now is True:
            return 0
        await asyncio.sleep(2)
        await self.waiting_and_click('//*[@id="header"]/div[3]/div[1]/h3/a', "승차권 예약 클릭")
        await asyncio.sleep(2)
        await self.waiting_and_click('//*[@id="selGoTrainRa00"]', "KTX 버튼 클릭")
        await self.waiting_and_click('//*[@id="adjcCheckYn"]', "인접역 체크해제 클릭")
        self.driver.find_element(By.XPATH, '//*[@id="start"]').clear()
        self.driver.find_element(By.XPATH, '//*[@id="get"]').clear()
        dep_station = self.driver.find_element(By.XPATH, '//*[@id="start"]').send_keys(self.dep)
        des_station = self.driver.find_element(By.XPATH, '//*[@id="get"]').send_keys(self.des)

        Select(self.driver.find_element(By.XPATH, '//*[@id="s_year"]')).select_by_value(self.year)
        Select(self.driver.find_element(By.XPATH, '//*[@id="s_month"]')).select_by_value(self.month)
        Select(self.driver.find_element(By.XPATH, '//*[@id="s_day"]')).select_by_value(self.day)
        Select(self.driver.find_element(By.XPATH, '//*[@id="s_hour"]')).select_by_value(self.dep_time)
        await self.waiting_and_click('//*[@id="center"]/form/div/p/a/img', "조회하기 버튼 클릭")
        await asyncio.sleep(7)
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

    async def fill_payment1(self):
        await self.waiting_and_click('// *[ @ id = "list-form"] / fieldset / div[11] / a[1] / span', '"결제하기" 버튼')
        # await self.waiting_click('//*[@id="select-form"]/fieldset/div[2]/ul/li[1]/a', '신용카드')
        await asyncio.sleep(1)
        await self.waiting_and_click('// *[ @ id = "stlCrCrdNo14_tk_btn"] / label', '보안키패드1 해제')
        await self.waiting_and_click('// *[ @ id = "vanPwd1_tk_btn"] / label', '보안키패드2 해제')
        await asyncio.sleep(1)
        sel_mon = Select(self.driver.find_element(
            By.XPATH, '//*[@id="crdVlidTrm1M"]')).select_by_value(self.card_info["exp_month"])
        sel_year = Select(self.driver.find_element(
            By.XPATH, '//*[@id="crdVlidTrm1Y"]')).select_by_value(self.card_info["exp_year"])
        # await self.waiting_click('// *[ @ id = "agree1"]', '동의 체크박스')
        await self.waiting_and_click('// *[ @ id = "select-form"] / fieldset / div[11] / div[2] / ul / li[2] / a', '스마트폰 발권')
        await asyncio.sleep(1)
        self.driver.switch_to.alert.accept()
        await asyncio.sleep(1)
        for i in range(1, 5):
            self.driver.find_element(
                By.XPATH, f'// *[ @ id = "stlCrCrdNo1{i}"]').click()
            card_num = self.driver.find_element(
                By.XPATH, f'// *[ @ id = "stlCrCrdNo1{i}"]').send_keys(self.card_info["card_num"][i - 1])
            await asyncio.sleep(1)
        pw_box = self.driver.find_element(
            By.XPATH, '// *[ @ id = "vanPwd1"]').send_keys(self.card_info["pw"])
        await asyncio.sleep(1)
        verif_box = self.driver.find_element(
            By.XPATH, '//*[@id="athnVal1"]').send_keys(self.card_info['verif_code'])
        await asyncio.sleep(1)
        await self.waiting_and_click('//*[@id="Div_Card"]/table/tbody/tr[6]/td/input', "결제조건동의", max_cnt=3)
        await asyncio.sleep(2)
        await self.waiting_and_click('/html/body/div[1]/div[4]/div/div[2]/form/fieldset/div[11]/div[11]/input[1]', "최종 결제 버튼", quiet=0)
        await asyncio.sleep(1)
        self.driver.switch_to.alert.accept()
        # print("최종결제2")
        # await asyncio.sleep(10)
        # self.final_txt = self.driver.switch_to.alert.text
        # print(self.final_txt)
        # self.driver.switch_to.alert.accept()

    async def success_process(self):
        await asyncio.sleep(3)
        await self.screenshot()
        await asyncio.sleep(5)
        await self.tprint("소멸자")
        self.is_finish = True
        self.__del__()

    async def trying(self, row):
        elements = self.driver.find_elements(By.XPATH, f'//*[@id="tableResult"]/tbody/tr[{row}]')
        if len(elements) < 1:
            await self.tprint(f"elements is none {elements}")
            return 0
        seat_info_list = elements[0].text.split()
        is_ktx = 1 if 'KTX' in seat_info_list[1] else 0
        dep_time = seat_info_list[4]
        seat_status = self.driver.find_element(By.XPATH, f'//*[@id="tableResult"]/tbody/tr[{row}]/td[6]').accessible_name
        if "매진" not in seat_status:  # TODO del
            await self.tprint(seat_status)
        else:
            print(datetime.now(), seat_status)
        if "예약하기" in seat_status:
            await self.waiting_and_click(f'//*[@id="tableResult"]/tbody/tr[{row}]/td[6]/a[1]/img', f"{row}열예매버튼")
            await self.tprint("예매 버튼 클릭!!!")
            try:
                self.driver.switch_to.frame(0)
                await self.waiting_and_click('/html/body/div/div[2]/p[3]/a', "산천 팝업창", max_cnt=3)
                # self.driver.switch_to.default_content()
            except:
                await self.tprint("산천 팝업창이 안떠서 팝업창해제를 스킵합니다")
                pass
            try:
                self.driver.switch_to.alert.accept()
                self.driver.switch_to.alert.accept()
            except:
                pass
            await asyncio.sleep(2)

            # 팝업창 클릭 만들어야함
            # self.driver.execute_script("document.body.style.zoom = '90%'")
            await self.waiting_and_click('//*[@id="btn_next"]', "결제하기")
            await self.waiting_and_click('//*[@id="tabStl1"]', "신용카드 탭 클릭")
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
            await self.waiting_and_click('//*[@id="chkAgree"]', "개인정보수집동의", max_cnt=10)
            await asyncio.sleep(0.3)
            await self.waiting_and_click('//*[@id="fnIssuing"]', "발권하기 버튼", max_cnt=10, quiet=0)
            await asyncio.sleep(0.3)
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            await asyncio.sleep(0.3)

            cur_frame = self.driver.switch_to.frame("mainframeSaleInfo")
            await self.waiting_and_click('//*[@id="btn_next2"]', "코레일톡 발권 버튼", max_cnt=10, quiet=0)
            await asyncio.sleep(2)
            self.driver.switch_to.alert.accept()
            await self.tprint("< 예매 성공 >")
            await asyncio.sleep(2)
            self.is_finish = True
            self.driver.quit()
            return 1
        else:
            ran_time = f"{random.uniform(1.0, 2.0):.1f}"
            # ran_time = float(str(random.randint(
            #     self.interval, self.interval+2)) + '.' + str(random.randint(1, 3)))
            await asyncio.sleep(float(ran_time))
            self.driver.refresh()
            await asyncio.sleep(0.1)
        return 0
        # await asyncio.sleep(2)
        # try:  # 예약대기팝업
        #     self.driver.find_element(
        #         By.XPATH, '/html/body/div[2]/div[3]/div/button').click()
        #     await self.tprint("예약대기 팝업 떠서 클릭함")
        # except:
        #     pass

        #    try:
        #         await asyncio.sleep(3)
        #         info_text = self.driver.find_element(
        #             By.XPATH, '//*[@id="wrap"]/div[4]/div/div[2]/div[4]').text
        #         await self.tprint(f'info_text : {info_text}')
        #         if "예약대기" in info_text:
        #             await self.waiting_and_click('//*[@id="agree"]', "개인정보수집동의")
        #             await self.waiting_and_click('//*[@id="smsY"]', "SMS동의")
        #             await asyncio.sleep(1)
        #             self.driver.switch_to.alert.accept()
        #             self.driver.find_element(
        #                 By.XPATH, '//*[@id="phoneNum1"]').send_keys(self.mobile[0])
        #             self.driver.find_element(
        #                 By.XPATH, '//*[@id="phoneNum2"]').send_keys(self.mobile[1])
        #             await self.waiting_and_click('//*[@id="diffSeatY"]', "다른차실 동의")
        #             await asyncio.sleep(1)
        #             await self.waiting_and_click('//*[@id="moveTicketList"]', "확인")
        #             self.driver.switch_to.alert.accept()
        #             await self.success_process()
        #         elif "10분 내에 결제하지" in info_text:
        #             await self.fill_payment1()
        #             await asyncio.sleep(3)
        #             while "카드번호" in self.final_txt:
        #                 await self.tprint(f"카드번호 입력불가로 재결제 시도합니다.")
        #                 await self.restart(self.payment_url)
        #                 WebDriverWait(self.driver, 10).until(
        #                     ec.presence_of_element_located((By.XPATH, '//*[@id="reserveTbl"]/tbody/tr[1]/td[10]/a')))
        #                 self.driver.find_element(
        #                     By.XPATH, '//*[@id="reserveTbl"]/tbody/tr[1]/td[10]/a').click()
        #                 await self.fill_payment1()
        #             else:
        #                 await self.success_process()
        #                 self.waiting = 0
        #     except:
        #         pass
        #     self.is_finish = True
        #     return 1
        # else:
        #     ran_time = float(str(random.randint(
        #         self.interval, self.interval+1)) + '.' + str(random.randint(1, 3)))
        #     await asyncio.sleep(ran_time)
        #     self.driver.refresh()
        #     await asyncio.sleep(0.1)
        # if self.start_now == 0:
        #     nowtime = int(datetime.now().strftime("%H%M"))
        #     if (nowtime > int("0455")):
        #         await self.tprint(f"{nowtime} : 새벽 매크로를 정지합니다... ")
        #         await asyncio.sleep(600)
        #         self.is_finish = True
        #         return 0
        #         await asyncio.sleep(21600)


async def main():
    k = Ktx(0)
    if __name__ == "__main__":
        if len(sys.argv) > 1:
            k.start_now = int(sys.argv[1])
            await k.tprint(sys.argv[1:])
            is_success = await k.start(trgt_date=sys.argv[2], deptime=sys.argv[3], dep_station="서울", des_station="진주")
            # is_success = await k.start(trgt_date=sys.argv[2], deptime=sys.argv[3], dep_station=sys.argv[4], des_station=sys.argv[5])
        else:
            is_success = await k.start(trgt_date="20240622", deptime="08", dep_station="서울", des_station="진주")
    # is_success = await k.start(trgt_date="20240623", deptime="08", dep_station="서울", des_station="진주")

if __name__ == "__main__":
    asyncio.run(main())
