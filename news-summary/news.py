# 내장함수 

import re
import os
from urllib import response
import dotenv
dotenv.load_dotenv()
import yaml
import requests
# 외장함수 
# crewai  
from crewai import  Agent, Task,Crew
from crewai.tools import tool
from crewai.project import CrewBase, agent,task,crew
from typing import Dict, Optional

# 크롤링 
from bs4 import BeautifulSoup
# API
from pathlib import Path
#date
from datetime import datetime,timedelta

#함수 정의 
#네이버 뉴스 수집 
#일주일 이내 뉴스만 수집 
#정치,경제뉴스 필터 
#정치 뉴스 요약5개 
#경제뉴스 요약 5개 

#뉴스 수집 함수
def collect_news(category:str, num_articles:int) -> list[dict]:
    """
    네이버 뉴스 카테고리 정치 , 경제 뉴스를 수집하는 함수 
    
    Args: 
        category : 뉴스 카테고리 ('정치', '경제')
        num_articles: 수집할 뉴스 개수 (기본값 : 5개)
    Returns:
        뉴스 리스트 (각 뉴스의 title, link,content,date를 포함)
    """

    # print(f"category:{category}")
    # print(f"num_articles:{num_articles}")

    # print(f"news_list:{news_list}")
    #뉴스 카테고리 매핑 
    category_map = {
        "정치":"100",
        "경제":"101",
    }
    if category not in category_map:
        return []
    #카테고리에 있는 값 sid 값 추출 
    sid = category_map[category]
    print(f"sid: {sid}")

    news_list = []
    news_links = []
    
    try:
        #url뉴스 리스트 페이지 (새로운 형식: /section/{sid})
        url = f"https://news.naver.com/section/{sid}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7'
        }

        #requests 요청 
        response = requests.get(url, headers = headers, timeout = 10 )
        response.raise_for_status()
        response.encoding = 'utf-8'
        
        #HTML 파싱 
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # 중복제거를 위한 세트
        seen_links = set()
        
        # 방법 1: 해드라인 뉴스 - ul.type06_headline 또는 ul.type06 안의 dt > a 찾기
        for ul in soup.find_all('ul', class_=lambda x: x and ('type06' in str(x) or 'headline' in str(x))):
            if len(news_links) >= num_articles:
                break
            for li in ul.find_all('li'):
                if len(news_links) >= num_articles:
                    break
                dt = li.find('dt')
                if dt:
                    a_tag = dt.find('a')
                    if a_tag and a_tag.get('href'):
                        href = a_tag.get('href')
                        title = a_tag.get('title', '') or a_tag.text.strip()
                        # 상대 경로를 절대경로로 변환
                        if href.startswith('/'):
                            href = 'https://news.naver.com' + href
                        elif not href.startswith('http'):
                            continue
                        # 중복 제거 및 추가
                        if href and title and len(title.strip()) > 5:
                            if href not in seen_links:
                                seen_links.add(href)
                                news_links.append({
                                    'title': title.strip(),
                                    'link': href
                                })
        
        print(f"해드라인 뉴스 수집: {len(news_links)}개")
        
        # 방법 2: section_latest에서 뉴스 수집
        if len(news_links) < num_articles:
            latest_section = soup.find('div', class_='section_latest')
            if latest_section:
                # ul.sa_list를 찾아서 각 ul을 순회
                for ul in latest_section.find_all('ul', class_='sa_list'):
                    if len(news_links) >= num_articles:
                        break
                    # 각 ul 안의 li를 순회
                    for li in ul.find_all('li'):
                        if len(news_links) >= num_articles:
                            break
                        # a 태그 찾기
                        a_tag = li.find('a', href=True)
                        if a_tag:
                            href = a_tag.get('href')
                            # 제목 찾기 - 여러 선택자 시도
                            title = None
                            title_elem = li.find('div', class_='sa_text_title')
                            if title_elem:
                                strong = title_elem.find('strong', class_='sa_text_strong')
                                if strong:
                                    title = strong.get_text(strip=True)
                                else:
                                    title = title_elem.get_text(strip=True)
                            # title 속성 또는 텍스트로 대체
                            if not title:
                                title = a_tag.get('title', '') or a_tag.get_text(strip=True)
                            # 상대 경로를 절대경로로 변환
                            if href.startswith('/'):
                                href = 'https://news.naver.com' + href
                            elif not href.startswith('http'):
                                continue
                            # 중복 제거 및 추가
                            if href and title and len(title.strip()) > 5:
                                if href not in seen_links:
                                    seen_links.add(href)
                                    news_links.append({
                                        'title': title.strip(),
                                        'link': href
                                    })
        
        print(f"전체 수집된 뉴스: {len(news_links)}개")
        
        # 방법 3: li._item에서 뉴스 수집 (백업)
        if len(news_links) < num_articles:
            for li in soup.find_all('li', class_='_item'):
                if len(news_links) >= num_articles:
                    break
                a_tag = li.find('a', href=True)
                if a_tag:
                    href = a_tag.get('href')
                    title = a_tag.get('title', '') or a_tag.get_text(strip=True)
                    if href.startswith('/'):
                        href = 'https://news.naver.com' + href
                    elif not href.startswith('http'):
                        continue
                    if href and title and len(title.strip()) > 5:
                        if href not in seen_links:
                            seen_links.add(href)
                            news_links.append({
                                'title': title.strip(),
                                'link': href
                            })
        
        # 요청한 개수만큼만 반환
        news_list = news_links[:num_articles]


    except Exception as e:
        return f"뉴스 수집 중 오류발생 : {str(e)}"

    return news_list
# 뉴스 정치/경제 필터 함수 
def filter_politics_news():
    pass 

#뉴스 경제 요약 함수 
def summarize_economy_news():
    pass
# 정치 뉴스 요약 함수 
def summarize_politics_news():
    pass 

#경제 뉴스 요약 함수 
def summarize_economy_news():
    pass

# tool 정의 
@tool("네이버 뉴스 수집 도구")
def collect_naver_news(category: str , num_articles:int =5) -> list[dict]:
    """ 
    네이버 뉴스에서 정치, 경제 뉴스를 수집합니다. 
    Args: 
        category: 뉴스 카테고리 ('정치', '경제')
        num_articles : 수집할 뉴스 개수 (기본값 : 5개)
    Returns:
        뉴스 리스트 (각 뉴스의 title, link,content,date를 포함)
    """
    
    return collect_news(category, num_articles)


#테스트 코드 
if __name__ == "__main__":
    # @tool 데코레이터가 적용된 함수는 직접 호출할 수 없으므로
    # 내부 함수인 collect_news를 직접 호출
    result = collect_news("정치", 3)
    print(f"수집된 뉴스: {len(result)}개")
    
    # filter_politics_news()
    # summarize_politics_news()
    # summarize_economy_news()
    print("뉴스 수집 요약 완료 ")

