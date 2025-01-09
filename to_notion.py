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
    pretty_data = json.dumps(data, indent=4, ensure_ascii=False)

    with open("./db.json", "w", encoding="utf8") as f:
        f.write(pretty_data)


def create_page(api_key, db_id, page_values):
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
    print(res.status_code)
    if int(res.status_code) != 200:
        data = res.json()
        pretty_data = json.dumps(data, indent=4, ensure_ascii=False)

        with open("./db.json", "w", encoding="utf8") as f:
            f.write(pretty_data)


if __name__ == '__main__':
    page_values = {
        '이름': 'Doom',
        '출발역': 26,
        '도착역': 26,
        '날짜': 26,
        '시간': 26,
        '타입': 26,
        '좌석수': 26,
        '정산': 'Data Analyst',
        '비고': "파이썬"
    }
    read_database(api_key, db_id)
    # create_page(api_key, db_id, page_values)
