# 내장함수
import re
import requests
import dotenv
import yaml
# crewai agent 
from crewai import Crew, Agent, Task
from crewai.project import CrewBase, agent, crew, task
from crewai.tools import tool
from typing import Dict, Optional
# 외부라이브러리
# 크롤링
from bs4 import BeautifulSoup
# API
from pathlib import Path
from datetime import datetime, timedelta

dotenv.load_dotenv()

""" 
김도원 아오 까다로워 정말 
기능1 : 영상뉴스인경우 제외
기능2 : 일주일 이내 뉴스만 크롤링 
기능3 : 정치, 경제만 필터링 수집 
기능 4 : 뉴스 요약 생성 

tool
네이버 뉴스 수집 도구 
"""

# 영상뉴스 제외 로직 구현 참/거짓
def is_video_article(title:str, link:str) -> bool:
    """ 동영상인지 확인하는 함수 """
    if not title:
        return False

    title_lower = title.lower()
    link_lower = link.lower()

    video_keywords = ['동영상','영상','방송','video','tv','broadcast']

    if any(keyword in title_lower or keyword in link_lower for keyword in video_keywords):
        return True
    else: 
        return False

    

  


# 날짜 파싱 함수   // 쓸데없는것같은 것 까지 적어놓을 것 
def parse_news_date(date_str: str) -> Optional[datetime]:
    """ 날짜 문자열을 datetime 으로 변환하는 함수 """
    if not date_str or date_str =="날짜 없음 ":
        return None

    # 공백 제거 후 날짜 문자열 저장 
    date_str = date_str.strip()
    # 상대적 시간표현 
    relative_patterns = [
        (r'(\d+)\s*분\s*전', 'minutes'),
        (r'(\d+)\s*시간\s*전', 'hours'),
        (r'(\d+)\s*일\s*전', 'days'),
        (r'방금', 'now')
    ]

    for pattern, unit in relative_patterns:
        match = re.search(pattern, date_str)
        if match:
            now = datetime.now()
            if unit =='now':
                return now 
            elif unit =='minutes':
                minutes_ago = int(match.group(1))
                return now - timedelta(minutes=minutes_ago)
            elif unit =='hours':
                hours_ago = int(match.group(1))
                return now - timedelta(hours=hours_ago)
            elif unit =='days':
                days_ago = int(match.group(1))
                return now - timedelta(days=days_ago)

    # 절대 날짜 형식 처리 
    date_formats = [
        '%Y.%m.%d',
        '%Y-%m.%d',
        '%Y.%m.%d %H:%M',
        '%Y-%m.%d %H:%M',
        '%Y.%m.%d %H:%M:%S',
        '%Y-%m.%d %H:%M:%S',
    ]
    # 날짜 형식 시도 
    for fmt in date_formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue

    # 정규식으로 날짜 추출 시도 
    date_pattern = fr'(\d{4})[.\-/](\d{1,2})][\.\-/](\d{1,2})'
    match = re.search(date_pattern, date_str)
    if match:
        year, month, day = match.groups()
        try:
            return datetime(int(year), int(month), int(day))
        except ValueError:
            pass
    return None


# 일주일 이내 뉴스 기사 확인하는 삼수 
def is_within_week(date_str: str) -> bool:
    """ 일주일 이내 뉴스인지 확인하는 함수 """
    parsed_date = parse_news_date(date_str)
    # 날짜를 파싱할 수 없을 때 불포함 
    if parsed_date is None:
        return False
    now = datetime.now()
    week_ago = now - timedelta(days=7)
    return parsed_date >= week_ago
        


## 정치, 경제만 필터링 수집 
def collect_news(category: str, num_article: int =5) -> list[Dict]:
    """ 네이버 뉴스 카테고리 정치 , 경제 뉴스를 수집하는 함수 
    
    Args:
        category: 뉴스 카테고리 ('정치', '경제')
        num_article: 수집할 뉴스 개수 (기본값 : 5개)

    Returns:
        뉴스 리스트 (각 뉴스의 title, link,content,date를 포함)
    """ 
    #네이버 뉴스 카테고리 매핑 secion 정치 : 100 , 경제 :101
    category_map = {
        '정치':'100',
        '경제':'101',
    }
    
    if category not in category_map:
        return []
    #   카테고리에 맞는 sid 값 추출 
    sid = category_map[category]
    print(f"sid:{sid}")
    news_list = []
    #네이버 뉴스 리스트 페이지 URL
    try:
        url = f"https://news.naver.com/section/{sid}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7'
        }
        response = requests.get(url, headers=headers, timeout = 10)
        response.raise_for_status()
        response.encoding = 'utf-8'
        # HTML 파싱 후 뉴스링크 추출  
        soup = BeautifulSoup(response.content, 'html.parser')
        #여러 선택자로 뉴스링크 찾기 
        news_links = []
        # 중복 제거를 위한 세트 
        seen_links = set()
        # 방법 1: ul.type06_headline 또는 ul.type06 안의 dt > a 찾기
        found_enough = False
        for ul in soup.find_all('ul', class_=lambda x: x and ('type06' in str(x) or 'headline' in str(x))):
            if found_enough:
                break
            for li in ul.find_all('li'):
                if found_enough:
                    break
                dt = li.find('dt')
                if dt:
                    a_tag = dt.find('a')
                    if a_tag and a_tag.get('href'):
                        href = a_tag.get('href')
                        title = a_tag.get('title', '') or a_tag.text.strip()
                        # 상대 경로를 절대경로로 반환 
                        if href.startswith('/'):
                            href = 'https://news.naver.com' + href
                        elif not href.startswith('http'):
                            continue
                        # 날짜 정보 추출 시도 
                        date = ""
                        # 날짜 태그 찾기 
                        date_tag = li.find('span', class_=lambda x: x and ('date' in str(x).lower() or 'time' in str(x).lower()))
                        if not date_tag:
                            date_tag = li.find('dd', class_=lambda x: x and 'date' in str(x).lower())
                        if date_tag:
                            date = date_tag.get_text(strip=True)
                        # 추가 날짜 찾기 시도
                        if not date:
                            date_elem = li.find('span', string=re.compile(r'\d{4}[.\-/]\d{1,2}[.\-/]\d{1,2}'))
                            if date_elem:
                                date = date_elem.get_text(strip=True)
                        #동영상 기사 제외
                        if href and title and len(title.strip()) > 5 and not is_video_article(title, href):
                            #중복 제거 
                            if href not in seen_links:
                                seen_links.add(href)
                                news_links.append({
                                    'title': title.strip(),
                                    'link': href,
                                    'date': date
                                }) 
                                if len(news_links) >= num_article * 3:  # 충분히 많이 수집 (날짜 필터링 전)
                                    found_enough = True
                                    break
        
        print(f"  [디버그] 방법1로 수집된 링크: {len(news_links)}개")
        
        # 방법 2: dt 태그의 a 링크 찾기 (전체 페이지)
        if len(news_links) < num_article * 3:
            for li in soup.find_all('li', class_='_item'):
                if len(news_links) >= num_article * 3:
                    break
                a_tag = li.find('a')
                if a_tag and a_tag.get('href'):
                    href = a_tag.get('href')
                    title = a_tag.get('title', '') or a_tag.text.strip()
                    if href.startswith('/'):
                        href = 'https://news.naver.com' + href
                    elif not href.startswith('http'):
                        continue
                    # 날짜 정보 추출 시도 
                    date = ""
                    parent = li.find_parent('dt')
                    if parent:
                        parent_span = parent.find(
                            'span',
                            class_=lambda x: x and ('date' in str(x).lower() or 'time' in str(x).lower()))  # lambda 함수 사용 : 문자열 검사
                        #날짜 태그 찾기 
                        if parent_span:
                            date = parent_span.get_text(strip=True)
                    # 추가 날짜 찾기 시도
                    if not date:
                        date_elem = li.find('span', string=re.compile(r'\d{4}[.\-/]\d{1,2}[.\-/]\d{1,2}'))
                        if date_elem:
                            date = date_elem.get_text(strip=True)
                    #동영상 기사 제외 
                    if href and title and len(title.strip()) > 5 and not is_video_article(title, href):
                        if href not in seen_links:
                            seen_links.add(href)
                            news_links.append({
                                'title': title.strip(),
                                'link': href,
                                'date': date
                            })
        
        print(f"  [디버그] 방법2로 수집된 링크: {len(news_links)}개 (전체)")
        
        #일주일 이내 기사만 필터링 (날짜가 없는 경우도 일단 포함, 나중에 본문에서 날짜 확인)
        filtered_news = []
        for news_item in news_links:
            date = news_item.get('date', '')
            #날짜가 있으면 일주일 이내인지 확인, 없으면 일단 포함
            if date:
                if is_within_week(date):
                    filtered_news.append(news_item)
            else:
                # 날짜가 없으면 일단 포함 (본문에서 날짜를 찾을 수 있음)
                filtered_news.append(news_item)
            
        print(f"  [디버그] 필터링 후 뉴스: {len(filtered_news)}개")
        
        # 필요한 개수만큼만 가져오기 (필터링 후에도 충분한 기사를 확보하기 위해 더 많이 수집)
        unique_news = filtered_news[:num_article *2]
        #각 뉴스의 본문 가져오기 
        for news_item in unique_news:
            title = news_item['title']
            link = news_item['link']
            date = news_item.get('date', '')
            content = ""
            #본문 가져오기 
            try: 
                article_response = requests.get(link, headers = headers, timeout = 10)
                article_response.raise_for_status()
                article_response.encoding = 'utf-8'
                article_soup = BeautifulSoup(article_response.content, 'html.parser')
                #날짜 정보를 못 가져 온 경우 여러 경우의 수로 날짜정보  추출 
                if not date:
                    #여러 날짜 선택자 시도 
                    date_selectors = [
                        ('span', {'class': 't11'}),
                        ('span', {'class':'_article_date'}),
                        ('div',  {'class': 'article_info'}),
                        ('span', {'class': 'date'}),
                        ('div', {'class': 'press_date'}),
                    ]
                    #날짜 태그 찾기 
                    for tag, attrs in date_selectors:
                        date_tag = article_soup.find(tag, attrs)
                        if date_tag:
                            date=date_tag.get_text(strip= True) #strip: True 양쪽의 공백 제거 
                            if date:
                                break
                    #data-module ="ArticleBody" 
                    if not date:
                        article_info = article_soup.find('div', class_=lambda x: x and isinstance(x, str) and ('info' in x.lower() or 'date' in x.lower()))
                        if article_info:
                            date_text = article_info.get_text(strip= True)
                            #날짜 형식 추출 (YYYY.MM.DD 또는 YYYY-MM-DD 등)
                            date_pattern = r'\d{4}[.\-/]\d{1,2}[.\-/]\d{1,2}'
                            match = re.search(date_pattern, date_text)
                            if match:
                                date = match.group()
                #본문 찾기 - 여러 선택자 시도 
                article_body = None
                selectors = [
                    ('div', {'id': 'articleBodyContents'}),
                    ('div', {'id': 'newsEndContents'}),
                    ('div', {'id': 'articeBody'}),
                    ('article', {'id': 'dic_area'}),
                    ('div', {'class': '_article_body_contents'}),
                    ('div', {'class': 'go_trans _article_content'}),
                    ('div', {'id': 'articleBody'}),
                ]
                for tag, attrs in selectors:
                    article_body = article_soup.find(tag, attrs)
                    if article_body:
                        break
                # 일반적인 본문 영역 찾기
                if not article_body:
                    #data-module="ArticleBody" 속성을 가진 div 찾기 
                    article_body = article_soup.find('div', {'data-module' : 'ArticleBody'})
                    if not article_body:
                        #class에 article, body, content가 포함되어있는지 확인 
                        article_body= article_soup.find('div',class_ = lambda x: x and isinstance(x, str) and ('article' in x.lower() or 'body' in x.lower() or 'content' in x.lower()))
                        if not article_body:
                            #div article body content 
                            article_body = article_soup.find('div', class_= lambda x: x and isinstance(x, str) and ('article' in x.lower()or 'body'in x.lower() or 'content' in x.lower()))
                
                # 본문을 찾았으면 처리
                if article_body:
                    #스크립트 , 스타일, 광고 제거 
                    for element in article_body.find_all(['script', 'style', 'iframe', 'noscript', 'button']):
                        element.decompose()
                    
                    #불필요한 클래스 제거 
                    for br in article_body.find_all('br'):
                        br.replace_with(' ')
                    
                    # 본문 추출 
                    content = article_body.get_text(strip=True, separator=' ')
                    #연속된 공백 제거
                    content = ' '.join(content.split())

                    #본문이 너무 짧으면 (20자 이하) 없는것으로 처리 
                    if len(content) < 20:
                        content = ""
                    
        
            except Exception as e:
                content = f"본문을 가져오는 동안 오류발생: {str(e)}"
            
            if not title or len(title.strip())<5:
                #공백이 없으면 링크에서 추출 시도 
                title = link.split('/')[-1].split('?')[0] if'/' in link else '제목없음'
            #본문이 없거나 너무 짧으면 본문 없음으로 표시 (20자 이내 )
            if not content or len(content.strip()) < 20:
                content = "본문 없음"
            else:
                #본문이 있으면 처음 1000자만 사용 
                content = content[:1000]
                #날짜 정리 
                date = date.strip() 
                if not date:
                    date = "날짜 없음"
                
                # 일주일 이내 확인 (날짜가 없으면 일단 포함)
                should_include = False
                if date == "날짜 없음":
                    # 날짜가 없으면 일단 포함 (최신 뉴스일 가능성이 높음)
                    should_include = True
                elif is_within_week(date):
                    # 날짜가 있고 일주일 이내면 포함
                    should_include = True
                
                if should_include:
                    news_list.append({
                        'title': title.strip(),
                        'link': link,
                        'content': content,
                        'date': date,
                        'category': category,
                    })
                    
    except Exception as e:
        # 뉴스 수집 중 오류 발생 시 빈 리스트 반환 
        return [f"뉴스 수집 중 오류 발생: {str(e)}"]
    
    return news_list
    
    

    
    






# 뉴스 요약 
def summerize_news():
    pass 



@tool("네이버 뉴스 수집 도구")
def collect_naver_news(category:str, num_articles:int =5) -> list[dict]:
    """ 네이버 뉴스에서 정치, 경제 뉴스를 수집합니다. 
    
    Args:
        category: 뉴스 카테고리 ('정치', '경제')
        num_articles: 수집할 뉴스 개수 (기본값 : 5개)

    Returns:
        뉴스 리스트 (각 뉴스의 title, link,content,date를 포함)
    """ 
    
    return collect_news(category, num_articles) # 뉴스 수집 함수 호출 


@CrewBase
class NewsSummaryCrew:
    
    def __init__(self):
        config_path = Path(__file__).parent / "config"
        with open(config_path / "agents.yaml") as f:
            agents_config = yaml.safe_load(f)
        with open(config_path / "tasks.yaml") as f:
            tasks_config = yaml.safe_load(f)
    
        # agents_config, tasks_config 인스턴스 내부 변수로 저장  후 사용 
        self.agents_config = agents_config
        self.tasks_config = tasks_config

    @agent
    def news_collector_agent(self):
        return Agent(
            #'**언패킹' 개별 키워드요소를 풀어 인자로 전달 하는 연산자 
            **self.agents_config["news_collector_agent"],
            tools = [collect_naver_news],
            verbose = True #디버깅 모드 
        )

    @agent
    def news_summarizer_agent(self):
        return Agent(
            **self.agents_config["news_summarizer_agent"],
            verbose = True
        )
    
    # 정치 뉴스 수집 테스크 
    @task
    def collect_politics_news_task(self):
        task_config = self.tasks_config["collect_politics_news_task"].copy()
        task_config.pop("agent", None)
        return Task(
            **task_config,
            agent = self.news_collector_agent(),
            tools = [collect_naver_news],
            verbose = True # 디버깅 모드 
        )
    # 경제 뉴스 수집 테스크 
    @task
    def collect_economy_news_task(self):
        task_config = self.tasks_config["collect_economy_news_task"].copy()
        task_config.pop("agent", None)
        return Task(
            **task_config,
            agent = self.news_collector_agent(),
            tools = [
                collect_naver_news
            ],
            verbose = True

        )
    # 정치 뉴스 요약 테스크 
    @task 
    def summarize_politics_news_task(self):
        task_config = self.tasks_config["summarize_politics_news_task"].copy()
        task_config.pop("agent", None)
        return Task(
            **task_config,
            agent = self.news_summarizer_agent(),
            context = [self.collect_politics_news_task()],
            verbose = True
        )

    # 경제 뉴스 요약 테스크 
    @task
    def summarize_economy_news_task(self):
        task_config = self.tasks_config["summarize_economy_news_task"].copy()
        task_config.pop("agent", None)
        return Task(
            **task_config,
            agent = self.news_summarizer_agent(),
            context = [self.collect_economy_news_task()],
            verbose = True
        )

    #워크플로우 조합 
    @crew
    def assemble_crew(self):
        return Crew(
            agents = [
                self.news_collector_agent(),
                self.news_summarizer_agent()
            ],
            tasks = [
                self.collect_politics_news_task(),
                self.collect_economy_news_task(),
                self.summarize_politics_news_task(),
                self.summarize_economy_news_task()
            ],
            verbose = True
        )

# 크롤링 테스트 코드
if __name__ == "__main__":
    print(f"name: {__name__}")
    print(f"__main__: {__file__}")
    print("=" * 50)
    print("크롤링 테스트 시작...")
    print("=" * 50)
    
    # 정치 뉴스 크롤링 테스트
    print("\n[테스트] 정치 뉴스 크롤링 중...")
    try:
        politics_news = collect_news("정치", 3)
        print(f"수집된 뉴스 개수: {len(politics_news)}개")
        if politics_news:
            print("\n첫 번째 뉴스:")
            print(f"  제목: {politics_news[0].get('title', 'N/A')}")
            print(f"  링크: {politics_news[0].get('link', 'N/A')}")
            print(f"  날짜: {politics_news[0].get('date', 'N/A')}")
            print(f"  본문 길이: {len(politics_news[0].get('content', ''))}자")
        else:
            print("수집된 뉴스가 없습니다.")
    except Exception as e:
        print(f"오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()
    
    # 경제 뉴스 크롤링 테스트
    print("\n[테스트] 경제 뉴스 크롤링 중...")
    try:
        economy_news = collect_news("경제", 3)
        print(f"수집된 뉴스 개수: {len(economy_news)}개")
        if economy_news:
            print("\n첫 번째 뉴스:")
            print(f"  제목: {economy_news[0].get('title', 'N/A')}")
            print(f"  링크: {economy_news[0].get('link', 'N/A')}")
            print(f"  날짜: {economy_news[0].get('date', 'N/A')}")
            print(f"  본문 길이: {len(economy_news[0].get('content', ''))}자")
        else:
            print("수집된 뉴스가 없습니다.")
    except Exception as e:
        print(f"오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 50)
    print("크롤링 테스트 완료")
    print("=" * 50)

# NewsSummaryCrew().assemble_crew().kickoff(inputs={f"num_articles":5})