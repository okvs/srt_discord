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


class Srt():
    def __init__(self, thread_count=None):
        self.srt_home = 'https://etk.srail.kr/main.do'
        self.payment_url = 'https://etk.srail.kr/hpg/hra/02/selectReservationList.do?pageId=TK0102010000'
        self.class_type_txt = {'2': "특실+일반실", '1': "특실", '0': "일반실"}
        self.start_time_txt = {'1': "지금바로", '0': "새벽3시"}
        self.class_type = {'2': [6, 7], '1': [6], '0': [7]}
        self.station_dic = {'수서': 0, '동탄': 1, '평택지제': 2, '천안아산': 3, '오송': 4, '대전': 5, '김천구미': 6, '서대구': 7, '동대구': 8,
                            '신경주': 9, '울산': 10, '부산': 11, '공주': 12, '익산': 13, '정읍': 14, '광주송정': 15, '나주': 16, '목포': 17}
        self.id = conf["SRT_ID"]
        self.pw = conf["SRT_PW"]
        self.card_info = conf["CARD_INFO"]
        self.mobile = conf["MOBILE"]
        self.interval = 1
        self.start_time = []
        self.start_now = 0
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

    async def tprint(self, msg):
        print(f"(THREAD{self.thread_count},{id(self.thread_count)})> {msg}")

    async def waiting_click(self, click_xpath, txt=''):
        while 1:
            try:
                self.driver.find_element(By.XPATH, click_xpath).click()
                break
            except:
                await asyncio.sleep(0.3)
            finally:
                # print(f'waiting... {txt}')
                pass

    async def start(self, url, trgt_date, deptime, dep_station, des_station):
        if self.start_now == 0:
            nowtime = int(datetime.now().strftime("%H%M"))
            while (nowtime > int("0425") or nowtime < int("0307")):
                nowtime = int(datetime.now().strftime("%H%M"))
                await self.tprint(f"대기중.. {nowtime}")
                await asyncio.sleep(60)
        options = Options()
        options.add_argument("--incognito")  # 시크릿모드

        userAgent = generate_user_agent(os=('win', 'mac'), device_type='desktop')

        options.add_argument(f'user-agent={userAgent}')
        self.driver = webdriver.Chrome(service=Service('chromedriver.exe'), options=options)
        self.driver.maximize_window()
        self.driver.get(url)
        WebDriverWait(self.driver, 10).until(ec.presence_of_element_located((By.XPATH, '//*[@id="wrap"]/div[3]/div[1]/div/a[2]')))

        # login
        await asyncio.sleep(2)
        self.driver.find_element(By.XPATH, '//*[@id="wrap"]/div[3]/div[1]/div/a[2]').click()
        WebDriverWait(self.driver, 10).until(ec.presence_of_element_located((By.XPATH, '//*[@id="srchDvNm01"]')))
        self.driver.find_element(By.XPATH, '//*[@id="srchDvNm01"]').send_keys(self.id)
        self.driver.find_element(By.XPATH, '//*[@id="hmpgPwdCphd01"]').send_keys(self.pw)
        self.driver.find_element(By.XPATH, '//*[@id="login-form"]/fieldset/div[1]/div[1]/div[2]/div/div[2]/input').click()

        if self.quit_now is True:
            return 0
        await self.get_info(trgt_date, deptime, dep_station, des_station)

    async def close(self):
        await self.driver.quit()

    async def screenshot(self, slp=1):
        await self.driver.save_screenshot("tmp_srt.png")
        await asyncio.sleep(int(slp))

    async def get_info(self, dep_date, dep_time, dep, des):

        self.date = dep_date
        self.time = dep_time[0:2]
        self.dep_time = dep_time
        self.target_time = dep_time
        self.dep = dep
        self.des = des

        for s in self.station_dic.keys():
            if dep in s:
                self.depature = self.station_dic[s] + 1
                self.dep = s
                break
        for s in self.station_dic.keys():
            if des in s:
                self.destination = self.station_dic[s] + 1
                self.des = s
                break
        await self.select_menu()

    async def select_menu(self):
        if self.quit_now is True:
            return 0
        Select(self.driver.find_element(By.XPATH, '//*[@id="dptRsStnCd"]')).select_by_index(self.depature)
        Select(self.driver.find_element(By.XPATH, '//*[@id="arvRsStnCd"]')).select_by_index(self.destination)
        self.driver.find_element(By.XPATH, '//*[@id="search-form"]/fieldset/a').click()
        WebDriverWait(self.driver, 10).until(lambda driver: driver.current_url ==
                                             "https://etk.srail.kr/hpg/hra/01/selectScheduleList.do?pageId=TK0101010000")
        only_srt = self.driver.find_element(By.XPATH, '//*[@id="trnGpCd300"]').send_keys(Keys.SPACE)
        Select(self.driver.find_element(By.XPATH, '//*[@id="dptDt"]')).select_by_value(self.date)
        Select(self.driver.find_element(By.XPATH, '//*[@id="dptTm"]')).select_by_value(self.dep_time)
        search_btn = self.driver.find_element(By.XPATH, '//*[@id="search_top_tag"]/input').click()
        await asyncio.sleep(1)
        while self.is_finish is False:
            await self.trying()

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

    async def fill_payment(self):
        await self.waiting_click('// *[ @ id = "list-form"] / fieldset / div[11] / a[1] / span', '"결제하기" 버튼')
        # await self.waiting_click('//*[@id="select-form"]/fieldset/div[2]/ul/li[1]/a', '신용카드')
        await self.waiting_click('// *[ @ id = "stlCrCrdNo14_tk_btn"] / label', '보안키패드1')
        await self.waiting_click('// *[ @ id = "vanPwd1_tk_btn"] / label', '보안키패드2')
        await asyncio.sleep(1)
        sel_mon = Select(self.driver.find_element(
            By.XPATH, '//*[@id="crdVlidTrm1M"]')).select_by_value(self.card_info["exp_month"])
        sel_year = Select(self.driver.find_element(
            By.XPATH, '//*[@id="crdVlidTrm1Y"]')).select_by_value(self.card_info["exp_year"])
        # await self.waiting_click('// *[ @ id = "agree1"]', '동의 체크박스')
        await self.waiting_click('// *[ @ id = "select-form"] / fieldset / div[11] / div[2] / ul / li[2] / a', '스마트폰 발권')
        self.driver.switch_to.alert.accept()
        await asyncio.sleep(5)
        for i in range(1, 5):
            self.driver.find_element(By.XPATH, f'// *[ @ id = "stlCrCrdNo1{i}"]').click()
            card_num = self.driver.find_element(
                By.XPATH, f'// *[ @ id = "stlCrCrdNo1{i}"]').send_keys(self.card_info["card_num"][i - 1])
            await asyncio.sleep(1)
        pw_box = self.driver.find_element(By.XPATH, '// *[ @ id = "vanPwd1"]').send_keys(self.card_info["pw"])
        verif_box = self.driver.find_element(By.XPATH, '//*[@id="athnVal1"]').send_keys(self.card_info['verif_code'])
        await asyncio.sleep(1)
        # await self.waiting_click('//*[@id="requestIssue1"]/span', "최종 결제 버튼")
        # self.final_txt = self.driver.switch_to.alert.text
        self.final_txt = "hi"
        # self.driver.switch_to.alert.accept() TODO

    async def success_process(self):
        await asyncio.sleep(3)
        await self.screenshot()
        # await asyncio.sleep(21000) TODO
        await self.tprint("소멸자")
        self.is_finish = True
        self.__del__()

    async def trying(self):
        room_type = self.class_type[self.VIP]
        row_list = self.driver.find_elements(
            By.CSS_SELECTOR, '#result-form > fieldset > div.tbl_wrap.th_thead > table > tbody > tr')
        if self.quit_now is True:
            return 0
        try:
            is_success = ''
            now_time = str(datetime.now().strftime("%H:%M"))
            for row in range(1, len(row_list)+2):
                cur_time = self.driver.find_element(
                    By.XPATH, f'//*[@id="result-form"]/fieldset/div[6]/table/tbody/tr[{str(row)}]/td[4]/em').text[0:2]
                is_in_trgt = False
                for st_time in list(self.start_time):
                    if str(st_time).zfill(2) == cur_time:
                        is_in_trgt = True
                        break
                if is_in_trgt is False:
                    await self.tprint(f"row:{row}, {cur_time}시는 {self.start_time}에 없어서 패스합니다.")
                    continue
                await self.tprint(f"row:{row}, {cur_time}시 도전")
                if "예약하기" in is_success:
                    break
                for cl in range(0, len(room_type)):
                    await self.tprint(f"  for loop : row:{row}, cl:{room_type[cl]}, (현재시간 {now_time})")
                    if "예약하기" in is_success:
                        continue
                    try:
                        if (self.seat_only):
                            remain_seat_type = self.driver.find_element(
                                By.XPATH, f'//*[@id="result-form"]/fieldset/div[6]/table/tbody/tr[{row}]/td[{room_type[cl]}]/a').text
                            # await self.tprint(f"  버튼명 : {remain_seat_type}")
                            if ('입석' in remain_seat_type):
                                continue
                            elif ('예약하기' in remain_seat_type or '신청하기' in remain_seat_type):
                                self.driver.find_element(
                                    By.XPATH, '//*[@id="result-form"]/fieldset/div[6]/table/tbody/tr[{}]/td[{}]/a'.format(row, room_type[cl])).click()
                        else:
                            self.driver.find_element(
                                By.XPATH, '//*[@id="result-form"]/fieldset/div[6]/table/tbody/tr[{}]/td[{}]/a'.format(row, room_type[cl])).click()
                        is_available_reserve_btn = self.driver.find_element(
                            By.CSS_SELECTOR, f'#result-form > fieldset > div.tbl_wrap.th_thead > table > tbody > tr:nth-child({row}) > td:nth-child(8)').text
                        # if ('-' not in is_available_reserve_btn):
                        if ('신청하기' in is_available_reserve_btn):
                            self.driver.find_element(
                                By.XPATH, '//*[@id="result-form"]/fieldset/div[6]/table/tbody/tr[{}]/td[{}]/a'.format(row, 8)).click()
                            is_success = self.driver.find_element(By.XPATH, '//*[@id="wrap"]/div[4]/div/div[1]/h2').text
                            await self.tprint("  예약대기 성공!")
                    except:
                        is_success = self.driver.find_element(By.XPATH, '//*[@id="wrap"]/div[4]/div/div[1]/h2').text
                        if "예약하기" in is_success:
                            await self.tprint("  예약하기 클릭 성공!")
                            break
        except:
            pass

        if "예약하기" in is_success:
            try:
                sold_out = self.driver.find_element(By.XPATH, '// *[ @ id = "wrap"] / div[4] / div / div[2] / div[5]').text
                if "잔여석없음" in sold_out:
                    await self.tprint(f'{sold_out} 으로 다시 홈페이지가서 새로고침(is_success : {is_success}')
                    self.driver.get(self.srt_home)
                    await self.select_menu()
                    await self.driver.refresh()
                    await asyncio.sleep(2)
                else:
                    await self.tprint("< 예매 성공 >")
                    await asyncio.sleep(2)
                    try:  # 예약대기팝업
                        self.driver.find_element(By.XPATH, '/html/body/div[2]/div[3]/div/button').click()
                        await self.tprint("예약대기 팝업 떠서 클릭함")
                    except:
                        pass
            except:
                await self.tprint("soldout html 못찾음")

            try:
                await asyncio.sleep(3)
                info_text = self.driver.find_element(By.XPATH, '//*[@id="wrap"]/div[4]/div/div[2]/div[4]').text
                await self.tprint(f'info_text : {info_text}')
                if "예약대기" in info_text:
                    await self.waiting_click('//*[@id="agree"]', "개인정보수집동의")
                    await self.waiting_click('//*[@id="smsY"]', "SMS동의")
                    await asyncio.sleep(1)
                    self.driver.switch_to.alert.accept()
                    self.driver.find_element(By.XPATH, '//*[@id="phoneNum1"]').send_keys(self.mobile[0])
                    self.driver.find_element(By.XPATH, '//*[@id="phoneNum2"]').send_keys(self.mobile[1])
                    await self.waiting_click('//*[@id="diffSeatY"]', "다른차실 동의")
                    await asyncio.sleep(1)
                    await self.waiting_click('//*[@id="moveTicketList"]', "확인")
                    self.driver.switch_to.alert.accept()
                    await self.success_process()
                elif "10분 내에 결제하지" in info_text:
                    await self.fill_payment()
                    while "카드번호" in self.final_txt:
                        await self.tprint(f"카드번호 입력불가로 재결제 시도합니다.")
                        await self.restart(self.payment_url)
                        WebDriverWait(self.driver, 10).until(
                            ec.presence_of_element_located((By.XPATH, '//*[@id="reserveTbl"]/tbody/tr[1]/td[10]/a')))
                        self.driver.find_element(By.XPATH, '//*[@id="reserveTbl"]/tbody/tr[1]/td[10]/a').click()
                        await self.fill_payment()
                    else:
                        await self.success_process()
            except:
                pass
            self.is_finish = True
        else:
            ran_time = float(str(random.randint(self.interval, self.interval+1)) + '.' + str(random.randint(1, 3)))
            await asyncio.sleep(ran_time)
            self.driver.refresh()
            await asyncio.sleep(0.5)
        # if self.start_now == 0:
        #     nowtime = int(datetime.now().strftime("%H%M"))
        #     if (nowtime > int("0425")):
        #         await self.tprint(f"{nowtime} : 새벽 매크로를 정지합니다... ")
        #         # await asyncio.sleep(21600) TODO
        #         del self
