import dotenv
dotenv.load_dotenv()

from pathlib import Path
import yaml
from crewai import Crew, Agent, Task
from crewai.tools import tool


@tool("번역 도구")
def translate_text(text: str) -> str:
    """
    영어 텍스트를 한국어로 번역합니다.
    Args:
        text: 번역할 영어 텍스트
    Returns:
        한국어로 번역된 텍스트
    """
    # 실제 번역 로직은 여기에 구현하거나, 외부 API를 사용할 수 있습니다
    # 여기서는 간단한 예시로 반환합니다
    return f"[번역됨] {text}"

# @CrewBase 데코레이터 제거 : 자동매핑 기능 비활성화
class TranslatorCrew:
    
    # 초기화 메서드
    def __init__(self):
        config_path = Path(__file__).parent / "config"
        # 번역 전용 config 파일 사용
        with open(config_path / "translate_agents.yaml") as f:
            self.agents_config = yaml.safe_load(f)
        with open(config_path / "translate_tasks.yaml") as f:
            self.tasks_config = yaml.safe_load(f)
    
    # 번역 에이전트 생성 메서드 
    # @agent 데코레이터 제거 : 자동매핑 기능 비활성화
    def translator_agent(self):
        return Agent(
            **self.agents_config["translator_agent"],
            verbose=True
        )

    # 번역 태스크 생성 메서드 
    # @task 데코레이터 제거 : 자동매핑 기능 비활성화
    def translate_task(self):
        task_config = self.tasks_config["translate_task"].copy()
        task_config.pop("agent", None)
        return Task(
            **task_config,
            agent=self.translator_agent(),
            verbose=True
        )

    # 워크플로우 조합 메서드 
    # @crew 데코레이터 제거 : 자동매핑 기능 비활성화
    def assemble_crew(self):
        return Crew(
            agents=[self.translator_agent()],
            tasks=[self.translate_task()],
            verbose=True
        )




# 메인 함수
# 워크플로우 실행 및 결과 출력
if __name__ == "__main__":
    crew_instance = TranslatorCrew()
    result = crew_instance.assemble_crew().kickoff(inputs={"sentence": "I'm S, I like to ride my bycicle in Napoli"})
    print(result)

