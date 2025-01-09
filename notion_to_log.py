import pyperclip
from datetime import datetime
import re

# 현재 시간 가져오기
now = datetime.now()


# 입력 데이터 예제
input_data = """
동탄	동대구	2025년 1월 11일	10	srt	2
동대구	동탄	2025년 1월 12일	13	srt	2
대전	동탄	2025년 1월 12일	19-21	srt	1
대전	동탄	2025년 1월 17일	19	srt	1
동탄	광주	2025년 1월 17일	19	srt	1
동탄	진주	2025년 1월 17일	19	srt	2
동탄	전주	2025년 1월 17일	19	srt	1
동탄	대전	2025년 1월 18일	9	srt	1
광주	동탄	2025년 1월 18일	10	srt	1
평택지제	경주	2025년 1월 18일	8	srt	2
동탄	경주	2025년 1월 18일	9	srt	2
동탄	부산	2025년 1월 18일	9-11	srt	1
"""

# 원하는 포맷으로 시간 출력
now_time = now.strftime("%Y-%m-%d %H:%M:%S")
srt_log_name = 'srt.log'
ktx_log_name = 'ktx.log'
srt_result = []
ktx_result = []


def parse_schedule(input_data):
    for line in input_data.strip().split("\n"):
        line = line.strip()
        # 탭(\t)으로 구분하여 분리
        departure, arrival, date, time_range, train_name, cnt = line.split('\t')

        # 날짜 포맷 변경 (YYYY년 MM월 DD일 -> YYYYMMDD)
        match = re.match(r"(\d+)년 (\d+)월 (\d+)일", date)
        year, month, day = match.groups()
        date_formatted = year+month.zfill(2)+day.zfill(2)

        # 시간 범위를 리스트로 변환
        if "-" in time_range:
            start, end = map(int, time_range.split("-"))
            time_list = list(range(start, end + 1))
        else:
            time_list = [int(time_range)]

        # 결과에 추가
        for i in range(int(cnt)):
            if train_name == 'srt':
                srt_result.append(f"{now_time} - 노션으로부터 시도대기 : {departure}->{arrival}, {date_formatted}, {time_list}시")
            else:
                ktx_result.append(f"{now_time} - 노션으로부터 시도대기 : {departure}->{arrival}, {date_formatted}, {time_list}시")

    return srt_result, ktx_result


# 변환된 데이터 출력
# for parsed_line in parse_schedule(input_data):
    # print(parsed_line)
parse_schedule(input_data)
srt_cmd_txt = "\n".join(srt_result)
ktx_cmd_txt = "\n".join(ktx_result)

if len(srt_cmd_txt) > 3:
    print(srt_cmd_txt)
    with open(srt_log_name, "a", encoding="utf-8") as file:  # "a" 모드로 열기
        file.write(srt_cmd_txt + "\n")  # 텍스트를 이어붙이고 줄바꿈 추가
        print(f"{srt_log_name}에 추가하였습니다!")

if len(ktx_cmd_txt) > 3:
    print(ktx_cmd_txt)
    with open(ktx_log_name, "a", encoding="utf-8") as file:  # "a" 모드로 열기
        file.write(ktx_cmd_txt + "\n")  # 텍스트를 이어붙이고 줄바꿈 추가
        print(f"{ktx_log_name}에 추가하였습니다!")
# pyperclip.copy(str_for_clipboard+'\n')
# print("클립보드에 복사되었습니다!")
