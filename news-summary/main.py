import dotenv
dotenv.load_dotenv()

import yaml
import re
from datetime import datetime, timedelta
from pathlib import Path
import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
from crewai.tools import tool
from crewai import Crew, Agent, Task
from crewai.project import CrewBase, agent, task, crew


def is_video_article(title: str, link: str) -> bool:
    """동영상 기사인지 확인하는 함수"""
    if not title:
        return False
    
    title_lower = title.lower()
    link_lower = link.lower()
    
    # 제목에 동영상 관련 키워드가 있는지 확인
    video_keywords = ['동영상', '영상', 'video', 'tv', '방송']
    if any(keyword in title_lower for keyword in video_keywords):
        return True
    
    # 링크에 동영상 관련 키워드가 있는지 확인
    if any(keyword in link_lower for keyword in ['video', 'tv', 'broadcast']):
        return True
    
    return False


def parse_date(date_str: str) -> Optional[datetime]:
    """날짜 문자열을 datetime 객체로 변환"""
    if not date_str or date_str == "날짜 없음":
        return None
    
    date_str = date_str.strip()
    
    # 상대적 시간 표현 처리 (예: "1시간 전", "2일 전", "방금")
    relative_patterns = [
        (r'(\d+)\s*분\s*전', 'minutes'),
        (r'(\d+)\s*시간\s*전', 'hours'),
        (r'(\d+)\s*일\s*전', 'days'),
        (r'방금', 'now'),
    ]
    
    for pattern, unit in relative_patterns:
        match = re.search(pattern, date_str)
        if match:
            now = datetime.now()
            if unit == 'now':
                return now
            elif unit == 'minutes':
                minutes_ago = int(match.group(1))
                return now - timedelta(minutes=minutes_ago)
            elif unit == 'hours':
                hours_ago = int(match.group(1))
                return now - timedelta(hours=hours_ago)
            elif unit == 'days':
                days_ago = int(match.group(1))
                return now - timedelta(days=days_ago)
    
    # 절대 날짜 형식 처리
    date_formats = [
        '%Y.%m.%d',           # 2024.01.15
        '%Y-%m-%d',           # 2024-01-15
        '%Y/%m/%d',           # 2024/01/15
        '%Y.%m.%d %H:%M',     # 2024.01.15 14:30
        '%Y-%m-%d %H:%M',     # 2024-01-15 14:30
        '%Y.%m.%d %H:%M:%S',  # 2024.01.15 14:30:00
        '%Y년 %m월 %d일',     # 2024년 1월 15일
        '%Y.%m.%d %H:%M:%S',  # 2024.01.15 14:30:00
    ]
    
    for fmt in date_formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    
    # 정규식으로 날짜 추출 시도
    date_pattern = r'(\d{4})[.\-/](\d{1,2})[.\-/](\d{1,2})'
    match = re.search(date_pattern, date_str)
    if match:
        year, month, day = match.groups()
        try:
            return datetime(int(year), int(month), int(day))
        except ValueError:
            pass
    
    return None


def is_within_week(date_str: str) -> bool:
    """날짜가 최근 일주일 이내인지 확인"""
    parsed_date = parse_date(date_str)
    if parsed_date is None:
        # 날짜를 파싱할 수 없으면 포함 (안전한 선택)
        return True
    
    now = datetime.now()
    week_ago = now - timedelta(days=7)
    
    return parsed_date >= week_ago


def _collect_naver_news_impl(category: str, num_articles: int = 5) -> List[Dict]:
    """
    네이버 뉴스에서 지정된 카테고리의 최신 뉴스를 수집합니다.
    
    Args:
        category: 뉴스 카테고리 ('정치' 또는 '경제')
        num_articles: 수집할 뉴스 개수 (기본값: 5)
    
    Returns:
        뉴스 리스트 (각 뉴스는 title, link, content, date를 포함)
    """
    # 네이버 뉴스 카테고리 매핑
    category_map = {
        '정치': '100',
        '경제': '101'
    }
    
    if category not in category_map:
        return []
    
    sid = category_map[category]
    news_list = []
    
    try:
        # 네이버 뉴스 리스트 페이지 URL
        url = f"https://news.naver.com/main/list.naver?mode=LSD&mid=sec&sid1={sid}"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        response.encoding = 'utf-8'
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # 여러 선택자로 뉴스 링크 찾기
        news_links = []
        seen_links = set()
        
        # 방법 1: ul.type06_headline 또는 ul.type06 안의 dt > a 찾기
        for ul in soup.find_all('ul', class_=lambda x: x and ('type06' in x or 'headline' in x)):
            for li in ul.find_all('li'):
                dt = li.find('dt')
                if dt:
                    a_tag = dt.find('a')
                    if a_tag and a_tag.get('href'):
                        href = a_tag.get('href')
                        title = a_tag.get('title', '') or a_tag.text.strip()
                        # 상대 경로를 절대 경로로 변환
                        if href.startswith('/'):
                            href = 'https://news.naver.com' + href
                        elif not href.startswith('http'):
                            continue
                        
                        # 날짜 정보 추출 (리스트 페이지에서)
                        date = ""
                        date_tag = li.find('span', class_=lambda x: x and ('date' in str(x).lower() or 'time' in str(x).lower()))
                        if not date_tag:
                            date_tag = li.find('dd', class_=lambda x: x and 'date' in str(x).lower())
                        if date_tag:
                            date = date_tag.get_text(strip=True)
                        
                        # 동영상 기사 제외 및 유효성 검사
                        if href and title and len(title.strip()) > 5 and not is_video_article(title, href):
                            # 중복 제거
                            if href not in seen_links:
                                seen_links.add(href)
                                news_links.append({'title': title.strip(), 'link': href, 'date': date})
                                if len(news_links) >= num_articles:
                                    break
            if len(news_links) >= num_articles:
                break
        
        # 방법 2: dt 태그의 a 링크 찾기 (전체 페이지)
        if len(news_links) < num_articles:
            for dt in soup.find_all('dt'):
                a_tag = dt.find('a')
                if a_tag and a_tag.get('href'):
                    href = a_tag.get('href')
                    title = a_tag.get('title', '') or a_tag.text.strip()
                    if href.startswith('/'):
                        href = 'https://news.naver.com' + href
                    elif not href.startswith('http'):
                        continue
                    
                    # 날짜 정보 추출 시도
                    date = ""
                    parent = dt.find_parent('li')
                    if parent:
                        date_tag = parent.find('span', class_=lambda x: x and ('date' in str(x).lower() or 'time' in str(x).lower()))
                        if date_tag:
                            date = date_tag.get_text(strip=True)
                    
                    # 동영상 기사 제외 및 유효성 검사
                    if href and title and len(title.strip()) > 5 and not is_video_article(title, href):
                        if href not in seen_links:
                            seen_links.add(href)
                            news_links.append({'title': title.strip(), 'link': href, 'date': date})
                            if len(news_links) >= num_articles:
                                break
        
        # 방법 3: li._item의 a 태그 찾기
        if len(news_links) < num_articles:
            for li in soup.find_all('li', class_='_item'):
                a_tag = li.find('a')
                if a_tag and a_tag.get('href'):
                    href = a_tag.get('href')
                    title = a_tag.get('title', '') or a_tag.text.strip()
                    if href.startswith('/'):
                        href = 'https://news.naver.com' + href
                    elif not href.startswith('http'):
                        continue
                    
                    # 날짜 정보 추출
                    date = ""
                    date_tag = li.find('span', class_=lambda x: x and ('date' in str(x).lower() or 'time' in str(x).lower()))
                    if date_tag:
                        date = date_tag.get_text(strip=True)
                    
                    # 동영상 기사 제외 및 유효성 검사
                    if href and title and len(title.strip()) > 5 and not is_video_article(title, href):
                        if href not in seen_links:
                            seen_links.add(href)
                            news_links.append({'title': title.strip(), 'link': href, 'date': date})
                            if len(news_links) >= num_articles:
                                break
        
        # 일주일 이내 기사만 필터링 (리스트 페이지에서 날짜가 있는 경우)
        # 날짜가 없거나 일주일 이내인 기사만 포함
        filtered_news = []
        for news_item in news_links:
            date = news_item.get('date', '')
            # 날짜가 없거나 일주일 이내인 경우 포함 (날짜가 없으면 나중에 기사 페이지에서 확인)
            if not date or is_within_week(date):
                filtered_news.append(news_item)
        
        # 필요한 개수만큼만 가져오기 (필터링 후에도 충분한 기사를 확보하기 위해 더 많이 수집)
        unique_news = filtered_news[:num_articles * 2]  # 여유있게 수집
        
        # 각 뉴스의 본문 가져오기
        for news_item in unique_news:
            title = news_item['title']
            link = news_item['link']
            date = news_item.get('date', '')  # 리스트 페이지에서 가져온 날짜
            content = ""
            
            try:
                article_response = requests.get(link, headers=headers, timeout=10)
                article_response.raise_for_status()
                article_response.encoding = 'utf-8'
                article_soup = BeautifulSoup(article_response.content, 'html.parser')
                
                # 날짜 정보 추출 (기사 페이지에서, 리스트 페이지에서 못 가져온 경우)
                if not date:
                    # 여러 날짜 선택자 시도
                    date_selectors = [
                        ('span', {'class': 't11'}),
                        ('span', {'class': '_article_date'}),
                        ('div', {'class': 'article_info'}),
                        ('span', {'class': 'date'}),
                        ('div', {'class': 'press_date'}),
                    ]
                    
                    for tag, attrs in date_selectors:
                        date_tag = article_soup.find(tag, attrs)
                        if date_tag:
                            date = date_tag.get_text(strip=True)
                            if date:
                                break
                    
                    # data-module="ArticleBody" 내부의 날짜 찾기
                    if not date:
                        article_info = article_soup.find('div', class_=lambda x: x and isinstance(x, str) and ('info' in x.lower() or 'date' in x.lower()))
                        if article_info:
                            date_text = article_info.get_text(strip=True)
                            # 날짜 형식 추출 (YYYY.MM.DD 또는 YYYY-MM-DD 등)
                            date_pattern = r'\d{4}[.\-/]\d{1,2}[.\-/]\d{1,2}'
                            match = re.search(date_pattern, date_text)
                            if match:
                                date = match.group()
                
                # 본문 찾기 - 여러 선택자 시도
                article_body = None
                
                # 최신 네이버 뉴스 본문 선택자들 (우선순위 순)
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
                    # data-module="ArticleBody" 속성을 가진 div 찾기
                    article_body = article_soup.find('div', {'data-module': 'ArticleBody'})
                
                if not article_body:
                    # class에 article, body, content가 포함된 div 찾기
                    article_body = article_soup.find('div', class_=lambda x: x and isinstance(x, str) and ('article' in x.lower() or 'body' in x.lower() or 'content' in x.lower()))
                
                if article_body:
                    # 스크립트, 스타일, 광고 제거
                    for element in article_body.find_all(['script', 'style', 'iframe', 'noscript', 'button']):
                        element.decompose()
                    
                    # 불필요한 클래스 제거 (광고, 추천 기사 등)
                    for ad in article_body.find_all(class_=lambda x: x and isinstance(x, str) and ('ad' in x.lower() or 'advertisement' in x.lower() or 'promotion' in x.lower() or 'recommend' in x.lower() or 'related' in x.lower())):
                        ad.decompose()
                    
                    # 불필요한 속성 제거
                    for br in article_body.find_all('br'):
                        br.replace_with(' ')
                    
                    content = article_body.get_text(strip=True, separator=' ')
                    # 연속된 공백 정리
                    content = ' '.join(content.split())
                    
                    # 본문이 너무 짧으면 (20자 미만) 본문 없음으로 처리
                    if len(content) < 20:
                        content = ""
                    
            except Exception as e:
                content = f"본문을 가져오는 중 오류 발생: {str(e)}"
            
            if not title or len(title.strip()) < 5:
                # 제목이 없으면 링크에서 추출 시도
                title = link.split('/')[-1].split('?')[0] if '/' in link else "제목 없음"
            
            # 본문이 없거나 너무 짧으면 본문 없음으로 표시
            if not content or len(content.strip()) < 20:
                content = "본문 없음"
            else:
                # 본문이 있으면 처음 1000자만 사용
                content = content[:1000]
            
            # 날짜 정리
            date = date.strip() if date else "날짜 없음"
            
            # 일주일 이내 기사만 포함
            if is_within_week(date):
                news_list.append({
                    'title': title.strip(),
                    'link': link,
                    'content': content,
                    'date': date
                })
        
    except Exception as e:
        return [{'error': f'뉴스 수집 중 오류 발생: {str(e)}'}]
    
    return news_list


@tool("네이버 뉴스 수집 도구")
def collect_naver_news(category: str, num_articles: int = 5) -> List[Dict]:
    """
    네이버 뉴스에서 지정된 카테고리의 최신 뉴스를 수집합니다.
    
    Args:
        category: 뉴스 카테고리 ('정치' 또는 '경제')
        num_articles: 수집할 뉴스 개수 (기본값: 5)
    
    Returns:
        뉴스 리스트 (각 뉴스는 title, link, content, date를 포함)
    """
    return _collect_naver_news_impl(category, num_articles)


@CrewBase
class NewsSummaryCrew:
    
    def __init__(self):
        config_path = Path(__file__).parent / "config"
        with open(config_path / "agents.yaml") as f:
            agents_config = yaml.safe_load(f)
        with open(config_path / "tasks.yaml") as f:
            tasks_config = yaml.safe_load(f)
        self.agents_config = agents_config
        self.tasks_config = tasks_config
    
    @agent
    def news_collector_agent(self):
        return Agent(
            **self.agents_config["news_collector_agent"],
            tools=[collect_naver_news],
            verbose=True
        )
    
    @agent
    def news_summarizer_agent(self):
        return Agent(
            **self.agents_config["news_summarizer_agent"],
            verbose=True
        )
    
    @task
    def collect_politics_news_task(self):
        task_config = self.tasks_config["collect_politics_news_task"].copy()
        task_config.pop("agent")
        return Task(
            **task_config,
            agent=self.news_collector_agent()
        )
    
    @task
    def collect_economy_news_task(self):
        task_config = self.tasks_config["collect_economy_news_task"].copy()
        task_config.pop("agent")
        return Task(
            **task_config,
            agent=self.news_collector_agent()
        )
    
    @task
    def summarize_politics_news_task(self):
        task_config = self.tasks_config["summarize_politics_news_task"].copy()
        task_config.pop("agent")
        return Task(
            **task_config,
            agent=self.news_summarizer_agent(),
            context=[self.collect_politics_news_task()]
        )
    
    @task
    def summarize_economy_news_task(self):
        task_config = self.tasks_config["summarize_economy_news_task"].copy()
        task_config.pop("agent")
        return Task(
            **task_config,
            agent=self.news_summarizer_agent(),
            context=[self.collect_economy_news_task()]
        )
    
    @crew
    def assemble_crew(self):
        return Crew(
            agents=[
                self.news_collector_agent(),
                self.news_summarizer_agent()
            ],
            tasks=[
                self.collect_politics_news_task(),
                self.collect_economy_news_task(),
                self.summarize_politics_news_task(),
                self.summarize_economy_news_task()
            ],
            verbose=True
        )


def escape_html(text: str) -> str:
    """HTML 특수문자 이스케이프"""
    if not text:
        return ""
    return (text
            .replace('&', '&amp;')
            .replace('<', '&lt;')
            .replace('>', '&gt;')
            .replace('"', '&quot;')
            .replace("'", '&#39;'))


def generate_html_report(politics_summary: str, economy_summary: str, 
                         politics_news: List[Dict], economy_news: List[Dict]) -> str:
    """HTML 보고서 생성 (profileReport 스타일)"""
    
    # 정치 뉴스 카드 HTML 생성
    politics_cards = ""
    for i, news in enumerate(politics_news[:5], 1):
        title = escape_html(news.get('title', '제목 없음'))
        content = escape_html(news.get('content', '본문 없음')[:200])
        date = escape_html(news.get('date', '날짜 없음'))
        link = escape_html(news.get('link', '#'))
        
        politics_cards += f"""
        <div class="news-card">
            <div class="news-header">
                <span class="news-number">#{i}</span>
                <span class="news-date">{date}</span>
            </div>
            <h3 class="news-title">{title}</h3>
            <p class="news-content">{content}...</p>
            <a href="{link}" target="_blank" class="news-link">원문 보기 →</a>
        </div>
        """
    
    # 경제 뉴스 카드 HTML 생성
    economy_cards = ""
    for i, news in enumerate(economy_news[:5], 1):
        title = escape_html(news.get('title', '제목 없음'))
        content = escape_html(news.get('content', '본문 없음')[:200])
        date = escape_html(news.get('date', '날짜 없음'))
        link = escape_html(news.get('link', '#'))
        
        economy_cards += f"""
        <div class="news-card">
            <div class="news-header">
                <span class="news-number">#{i}</span>
                <span class="news-date">{date}</span>
            </div>
            <h3 class="news-title">{title}</h3>
            <p class="news-content">{content}...</p>
            <a href="{link}" target="_blank" class="news-link">원문 보기 →</a>
        </div>
        """
    
    html_template = f"""
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>뉴스 요약 보고서</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            min-height: 100vh;
        }}
        
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
            overflow: hidden;
        }}
        
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px;
            text-align: center;
        }}
        
        .header h1 {{
            font-size: 2.5em;
            margin-bottom: 10px;
            font-weight: 700;
        }}
        
        .header p {{
            font-size: 1.1em;
            opacity: 0.9;
        }}
        
        .report-date {{
            margin-top: 15px;
            font-size: 0.9em;
            opacity: 0.8;
        }}
        
        .section {{
            padding: 40px;
            border-bottom: 1px solid #e0e0e0;
        }}
        
        .section:last-child {{
            border-bottom: none;
        }}
        
        .section-title {{
            font-size: 1.8em;
            color: #333;
            margin-bottom: 30px;
            padding-bottom: 15px;
            border-bottom: 3px solid #667eea;
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        
        .section-title::before {{
            content: '';
            width: 5px;
            height: 30px;
            background: #667eea;
            border-radius: 3px;
        }}
        
        .summary-box {{
            background: #f8f9fa;
            border-left: 4px solid #667eea;
            padding: 20px;
            margin-bottom: 30px;
            border-radius: 5px;
            line-height: 1.8;
            color: #444;
            white-space: pre-wrap;
        }}
        
        .news-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }}
        
        .news-card {{
            background: white;
            border: 1px solid #e0e0e0;
            border-radius: 10px;
            padding: 20px;
            transition: transform 0.3s, box-shadow 0.3s;
            box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);
        }}
        
        .news-card:hover {{
            transform: translateY(-5px);
            box-shadow: 0 10px 25px rgba(0, 0, 0, 0.15);
        }}
        
        .news-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
        }}
        
        .news-number {{
            background: #667eea;
            color: white;
            padding: 5px 12px;
            border-radius: 20px;
            font-size: 0.85em;
            font-weight: 600;
        }}
        
        .news-date {{
            color: #666;
            font-size: 0.85em;
        }}
        
        .news-title {{
            font-size: 1.1em;
            color: #333;
            margin-bottom: 12px;
            line-height: 1.4;
            font-weight: 600;
        }}
        
        .news-content {{
            color: #666;
            font-size: 0.95em;
            line-height: 1.6;
            margin-bottom: 15px;
        }}
        
        .news-link {{
            color: #667eea;
            text-decoration: none;
            font-weight: 600;
            font-size: 0.9em;
            transition: color 0.3s;
        }}
        
        .news-link:hover {{
            color: #764ba2;
        }}
        
        .stats {{
            display: flex;
            justify-content: space-around;
            padding: 30px;
            background: #f8f9fa;
            border-top: 1px solid #e0e0e0;
        }}
        
        .stat-item {{
            text-align: center;
        }}
        
        .stat-number {{
            font-size: 2em;
            font-weight: 700;
            color: #667eea;
        }}
        
        .stat-label {{
            color: #666;
            margin-top: 5px;
            font-size: 0.9em;
        }}
        
        @media (max-width: 768px) {{
            .news-grid {{
                grid-template-columns: 1fr;
            }}
            
            .header h1 {{
                font-size: 1.8em;
            }}
            
            .section {{
                padding: 20px;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📰 뉴스 요약 보고서</h1>
            <p>네이버 뉴스 정치/경제 분야 최신 기사 분석</p>
            <div class="report-date">생성일: {datetime.now().strftime('%Y년 %m월 %d일 %H:%M')}</div>
        </div>
        
        <div class="stats">
            <div class="stat-item">
                <div class="stat-number">{len(politics_news[:5])}</div>
                <div class="stat-label">정치 기사</div>
            </div>
            <div class="stat-item">
                <div class="stat-number">{len(economy_news[:5])}</div>
                <div class="stat-label">경제 기사</div>
            </div>
            <div class="stat-item">
                <div class="stat-number">{len(politics_news[:5]) + len(economy_news[:5])}</div>
                <div class="stat-label">전체 기사</div>
            </div>
        </div>
        
        <div class="section">
            <h2 class="section-title">🏛️ 정치 뉴스 요약</h2>
            <div class="summary-box">{escape_html(politics_summary)}</div>
            <div class="news-grid">
                {politics_cards}
            </div>
        </div>
        
        <div class="section">
            <h2 class="section-title">💰 경제 뉴스 요약</h2>
            <div class="summary-box">{escape_html(economy_summary)}</div>
            <div class="news-grid">
                {economy_cards}
            </div>
        </div>
    </div>
</body>
</html>
    """
    return html_template


def parse_task_result(result_str: str) -> tuple:
    """태스크 결과에서 뉴스 데이터와 요약 추출"""
    import json
    import ast
    
    # JSON 형식으로 파싱 시도
    try:
        if isinstance(result_str, str):
            # JSON 문자열인 경우
            if result_str.strip().startswith('[') or result_str.strip().startswith('{'):
                try:
                    data = json.loads(result_str)
                    if isinstance(data, list):
                        return data, ""
                    elif isinstance(data, dict):
                        return data.get('news', []), data.get('summary', "")
                except:
                    pass
            
            # Python 리스트/딕셔너리 문자열인 경우
            try:
                data = ast.literal_eval(result_str)
                if isinstance(data, list):
                    return data, ""
                elif isinstance(data, dict):
                    return data.get('news', []), data.get('summary', "")
            except:
                pass
    except:
        pass
    
    return [], result_str


if __name__ == "__main__":
    # 뉴스 수집 개수 설정
    num_articles = 5
    
    print("="*50)
    print("뉴스 수집 및 요약 시작...")
    print("="*50)
    
    # 직접 뉴스 수집 (태스크 실행 전에 데이터 확보)
    print("\n[1/2] 정치 뉴스 수집 중...")
    politics_news = _collect_naver_news_impl("정치", num_articles)
    print(f"   수집된 정치 뉴스: {len(politics_news)}개")
    
    print("\n[2/2] 경제 뉴스 수집 중...")
    economy_news = _collect_naver_news_impl("경제", num_articles)
    print(f"   수집된 경제 뉴스: {len(economy_news)}개")
    
    # 각 태스크를 개별적으로 실행하여 요약 생성
    print("\n" + "="*50)
    print("뉴스 요약 생성 중...")
    print("="*50)
    
    crew = NewsSummaryCrew()
    
    # 정치 뉴스 요약 생성
    print("\n[1/2] 정치 뉴스 요약 생성 중...")
    politics_collect_task = crew.collect_politics_news_task()
    politics_summarize_task = crew.summarize_politics_news_task()
    
    # 정치 뉴스 수집 및 요약을 위한 간단한 Crew 생성
    politics_crew = Crew(
        agents=[crew.news_collector_agent(), crew.news_summarizer_agent()],
        tasks=[politics_collect_task, politics_summarize_task],
        verbose=False
    )
    politics_result = politics_crew.kickoff(inputs={"num_articles": num_articles})
    politics_summary = str(politics_result)
    
    # 경제 뉴스 요약 생성
    print("\n[2/2] 경제 뉴스 요약 생성 중...")
    economy_collect_task = crew.collect_economy_news_task()
    economy_summarize_task = crew.summarize_economy_news_task()
    
    economy_crew = Crew(
        agents=[crew.news_collector_agent(), crew.news_summarizer_agent()],
        tasks=[economy_collect_task, economy_summarize_task],
        verbose=False
    )
    economy_result = economy_crew.kickoff(inputs={"num_articles": num_articles})
    economy_summary = str(economy_result)
    
    # 요약에서 불필요한 부분 제거 및 정리
    import re
    
    # 정치 요약 정리
    if "Final Answer" in politics_summary:
        # "Final Answer:" 이후 부분만 추출
        final_answer_idx = politics_summary.find("Final Answer")
        if final_answer_idx >= 0:
            politics_summary = politics_summary[final_answer_idx:].split("Final Answer")[-1].strip()
            # 앞뒤 불필요한 문자 제거
            politics_summary = re.sub(r'^[:\-\s]*', '', politics_summary)
            politics_summary = re.sub(r'[:\-\s]*$', '', politics_summary)
    
    # 경제 요약 정리
    if "Final Answer" in economy_summary:
        # "Final Answer:" 이후 부분만 추출
        final_answer_idx = economy_summary.find("Final Answer")
        if final_answer_idx >= 0:
            economy_summary = economy_summary[final_answer_idx:].split("Final Answer")[-1].strip()
            # 앞뒤 불필요한 문자 제거
            economy_summary = re.sub(r'^[:\-\s]*', '', economy_summary)
            economy_summary = re.sub(r'[:\-\s]*$', '', economy_summary)
    
    # 빈 요약 처리
    if not politics_summary or len(politics_summary.strip()) < 10:
        politics_summary = "정치 뉴스 요약 정보를 가져오지 못했습니다."
    if not economy_summary or len(economy_summary.strip()) < 10:
        economy_summary = "경제 뉴스 요약 정보를 가져오지 못했습니다."
    
    # HTML 보고서 생성
    print("\nHTML 보고서 생성 중...")
    html_report = generate_html_report(
        politics_summary=politics_summary[:1000] if len(politics_summary) > 1000 else politics_summary,
        economy_summary=economy_summary[:1000] if len(economy_summary) > 1000 else economy_summary,
        politics_news=politics_news[:5],
        economy_news=economy_news[:5]
    )
    
    # HTML 파일 저장
    output_file = f"news_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_report)
    
    print("\n" + "="*50)
    print("✅ 완료!")
    print("="*50)
    print(f"HTML 보고서가 생성되었습니다: {output_file}")
    print(f"브라우저에서 열어보세요!")
    print(f"\n수집된 뉴스:")
    print(f"  - 정치: {len(politics_news)}개")
    print(f"  - 경제: {len(economy_news)}개")