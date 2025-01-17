from pprint import pprint

import requests
import json

with open("config.json") as f:
    conf = json.load(f)

# API 키와 데이터베이스 ID
api_key = conf["NOTION_API_KEY"]  # Notion  API 키
db_id = '1631f0291d2980de988bd6d131448157'  # 기차표 노션 페이지
# DATABASE_ID = '1761f0291d298065a616d5309d2b63f7'  # 새페이지


def read_database(api_key, db_id):
    headers = {
        "Authorization": "Bearer " + api_key,
        "Notion-Version": "2022-02-22"
    }
    readUrl = f"https://api.notion.com/v1/databases/{db_id}/query"

    res = requests.post(readUrl, headers=headers)
    print(res.status_code)

    data = res.json()
    d = {}
    for result in data["results"]:
        if result["properties"]["날짜"]["date"] is not None:
            id = result["properties"]["ID"]['unique_id']['prefix']+'-'+str(result["properties"]["ID"]['unique_id']['number'])
            d[id] = {}
            d[id]['order'] = result["properties"]["ID"]['unique_id']['number']
            d[id]['memo'] = ''
            d[id]['page_id'] = result['id']
            d[id]['date'] = result["properties"]["날짜"]["date"]["start"]
            d[id]['dep'] = result["properties"]["출발역"]['rich_text'][0]['text']['content']
            d[id]['des'] = result["properties"]["도착역"]['rich_text'][0]['text']['content']
            d[id]['seats'] = result["properties"]["좌석수"]['number']
            d[id]['status'] = result["properties"]["정산"]['status']['name']
            d[id]['time'] = result["properties"]["시간"]['rich_text'][0]['text']['content']
            d[id]['type'] = result["properties"]["타입"]['select']['name']
            d[id]['name'] = result["properties"]["이름"]['title'][0]['text']['content']
            if len(result["properties"]["비고"]['rich_text']) > 0:
                d[id]['memo'] = result["properties"]["비고"]['rich_text'][0]['text']['content']
            # print(d[id])
    pretty_data = json.dumps(data, indent=4, ensure_ascii=False)

    with open("./db.json", "w", encoding="utf8") as f:
        f.write(pretty_data)
    return d


async def async_read_database(api_key, db_id):
    headers = {
        "Authorization": "Bearer " + api_key,
        "Notion-Version": "2022-02-22"
    }
    readUrl = f"https://api.notion.com/v1/databases/{db_id}/query"

    res = requests.post(readUrl, headers=headers)
    print(res.status_code)

    data = res.json()
    d = {}
    for result in data["results"]:
        if result["properties"]["날짜"]["date"] is not None:
            id = result["properties"]["ID"]['unique_id']['prefix']+'-'+str(result["properties"]["ID"]['unique_id']['number'])
            d[id] = {}
            d[id]['order'] = result["properties"]["ID"]['unique_id']['number']
            d[id]['memo'] = ''
            d[id]['page_id'] = result['id']
            d[id]['date'] = result["properties"]["날짜"]["date"]["start"]
            d[id]['dep'] = result["properties"]["출발역"]['rich_text'][0]['text']['content']
            d[id]['des'] = result["properties"]["도착역"]['rich_text'][0]['text']['content']
            d[id]['seats'] = result["properties"]["좌석수"]['number']
            d[id]['status'] = result["properties"]["정산"]['status']['name']
            d[id]['time'] = result["properties"]["시간"]['rich_text'][0]['text']['content']
            d[id]['type'] = result["properties"]["타입"]['select']['name']
            d[id]['name'] = result["properties"]["이름"]['title'][0]['text']['content']
            if len(result["properties"]["비고"]['rich_text']) > 0:
                d[id]['memo'] = result["properties"]["비고"]['rich_text'][0]['text']['content']
            # print(d[id])
    pretty_data = json.dumps(data, indent=4, ensure_ascii=False)

    with open("./db.json", "w", encoding="utf8") as f:
        f.write(pretty_data)
    return d


async def create_page(api_key, db_id, page_values):
    headers = {
        "Authorization": "Bearer " + api_key,
        "Content-Type": "application/json",
        "Notion-Version": "2022-02-22"
    }
    createdUrl = "https://api.notion.com/v1/pages"

    newPageData = {
        "parent": {"database_id": db_id},
        "properties": {
            "날짜": {
                "date": {
                    "start": page_values["날짜"]
                }
            },
            "좌석수": {
                "number": int(page_values["좌석수"])
            },
            "타입": {
                "select": {
                    "name": page_values["타입"]
                }
            },
            "도착역": {
                "rich_text": [
                    {
                        "text": {
                            "content": page_values["도착역"]
                        }
                    }
                ]
            },
            "비고": {
                "rich_text":   [
                    {
                        "text": {
                            "content": page_values["비고"]
                        }
                    }
                ]
            },
            "정산": {
                "status": {
                    "name": page_values["정산"]
                }
            },
            "시간": {
                "rich_text": [
                    {
                        "text": {
                            "content": page_values["시간"]
                        }
                    }
                ]
            },
            "출발역": {
                "rich_text": [
                    {
                        "text": {
                            "content": page_values["출발역"]
                        },
                    }
                ]
            },
            "이름": {
                "title": [
                    {
                        "text": {
                            "content": page_values["이름"]
                        }
                    }
                ]
            }
        }
    }

    data = json.dumps(newPageData)

    res = requests.post(createdUrl, headers=headers, data=data)
    if int(res.status_code) != 200:
        data = res.json()
        pretty_data = json.dumps(data, indent=4, ensure_ascii=False)

        with open("./db.json", "w", encoding="utf8") as f:
            f.write(pretty_data)
    return int(res.status_code)


async def update_page(api_key, page_id, status):
    headers = {
        "Authorization": "Bearer " + api_key,
        "Content-Type": "application/json",
        "Notion-Version": "2022-02-22"
    }
    update_url = f"https://api.notion.com/v1/pages/{page_id}"
    data = {
        "properties": {
            "정산": {
                "status": {
                    "name": status
                }
            }
        }
    }
    response = requests.patch(update_url, headers=headers, json=data)
    print(response.status_code)
    return response.status_code


if __name__ == '__main__':
    page_values = {
        '이름': 'test',
        '출발역': '동탄',
        '도착역': '수서',
        '날짜': '2025-02-02',
        '시간': '12',
        '타입': 'srt',
        '좌석수': 1,
        '정산': '발권 전',
        '비고': "파이썬"
    }
    read_database(api_key, db_id)
    # update_page(api_key, '1771f029-1d29-802c-ac7a-dcf19a8fed89', '')
    # create_page(api_key, db_id, page_values)
