import streamlit as st
from agents import Agent, RunContextWrapper, input_guardrail, Runner, GuardrailFunctionOutput, handoff

# RECOMMENDED_PROMPT_PREFIX를 여러 경로에서 시도
try:
    from agents.extensions.handoff_prompt import RECOMMENDED_PROMPT_PREFIX
except ImportError:
    try:
        from agents.extentions.handoff_prompt import RECOMMENDED_PROMPT_PREFIX
    except ImportError:
        # 기본 handoff 프롬프트 접두어 정의
        RECOMMENDED_PROMPT_PREFIX = """When transferring to another agent, provide clear context about the customer's issue and why the transfer is necessary. Ensure a smooth handoff experience."""

from models import UserAccountContext, InputGuardRailOutput, handoffData
from my_agents.account_agent import account_agent
from my_agents.technical_agent  import technical_agent
from my_agents.billing_agent import billing_agent
from my_agents.order_agent import order_agent





Input_guardrail_agent = Agent(
    name = "Input Guardrail Agent",
    instructions = """ 
    Ensure the user's request specifically pertains to User Account details, Billing inquiries, Order information, or Technical upport isssues, and is not off-topic.
    If the request is off-topic,
    return a reason for the wripwrie. you can make small conversation with the user, specially at the beginning of the conversation, but don't help with requests that
    are not related to User Account details, billling inquiries, Order information, or Technical Support issue.
    """,
    output_type = InputGuardRailOutput,
    
)




@input_guardrail
async def off_topic_guardrail(
    wrapper : RunContextWrapper[UserAccountContext],
    agent: Agent[UserAccountContext],
    input: str,
    ):
    result = await Runner.run(Input_guardrail_agent, input, context=wrapper.context,)
    pass 
    
    
    return GuardrailFunctionOutput(
        output_info = result.final_output,
        tripwire_triggered = result.final_output.is_off_topic
    )






def dynamic_triage_agent_instructions(
    wrapper: RunContextWrapper[UserAccountContext],
    agent: Agent[UserAccountContext],
):
    return f"""
    {RECOMMENDED_PROMPT_PREFIX}
    
    You are a customer support agent. You ONLY help customers with their questions about their User Account, Billing, Orders, or Technical Support.
    You call customers by their name.
    
    The customer's name is {wrapper.context.name}.
    The customer's email is {wrapper.context.email}.
    The customer's tier is {wrapper.context.tier}.
    
    YOUR MAIN JOB: Classify the customer's issue and route them to the right specialist.
    
    ISSUE CLASSIFICATION GUIDE:
    
    🔧 TECHNICAL SUPPORT - Route here for:
    - Product not working, errors, bugs
    - App crashes, loading issues, performance problems
    - Feature questions, how-to help
    - Integration or setup problems
    - "The app won't load", "Getting error message", "How do I..."
    
    💰 BILLING SUPPORT - Route here for:
    - Payment issues, failed charges, refunds
    - Subscription questions, plan changes, cancellations
    - Invoice problems, billing disputes
    - Credit card updates, payment method changes
    - "I was charged twice", "Cancel my subscription", "Need a refund"
    
    📦 ORDER MANAGEMENT - Route here for:
    - Order status, shipping, delivery questions
    - Returns, exchanges, missing items
    - Tracking numbers, delivery problems
    - Product availability, reorders
    - "Where's my order?", "Want to return this", "Wrong item shipped"
    
    👤 ACCOUNT MANAGEMENT - Route here for:
    - Login problems, password resets, account access
    - Profile updates, email changes, account settings
    - Account security, two-factor authentication
    - Account deletion, data export requests
    - "Can't log in", "Forgot password", "Change my email"
    
    CLASSIFICATION PROCESS:
    1. Listen to the customer's issue
    2. Ask clarifying questions if the category isn't clear
    3. Classify into ONE of the four categories above
    4. Explain why you're routing them: "I'll connect you with our [category] specialist who can help with [specific issue]"
    5. Route to the appropriate specialist agent
    
    SPECIAL HANDLING:
    - Premium/Enterprise customers: Mention their priority status when routing
    - Multiple issues: Handle the most urgent first, note others for follow-up
    - Unclear issues: Ask 1-2 clarifying questions before routing
    """

#handoff 핸들러 함수
def handle_handoff(
    wrapper: RunContextWrapper[UserAccountContext],
    input_data: handoffData,
   
):
    with st.sidebar:
        st.write(f"""
        Handing off to {input_data.to_agent_name}
        Reason:{input_data.reason}
        Issue Type : {input_data.issue_type}
        Description : {input_data.issue_description}
        """)
    pass

def make_handoff(agent):
    return handoff(
        agent=agent,
        on_handoff=handle_handoff,
        input_type=handoffData,
    )



triage_agent = Agent(
    name="Triage Agent",
    instructions=dynamic_triage_agent_instructions,
    input_guardrails=[
        off_topic_guardrail
    ],
    # tools=[
    #     technical_agent.as_tool(
    #         tool=name="Technical Help Tool",
    #         tool_descriptions="Use this when the user needs tech support."
    #     )
    # ],
    handoffs=[
        make_handoff(technical_agent),
        make_handoff(billing_agent),
        make_handoff(order_agent),
        make_handoff(account_agent),
    ]
)

# triage_agent.handoffs[0].agent.name
# triage_agent.handoffs[0].agent.instructions
# triage_agent.handoffs[0].agent.input_guardrails
# triage_agent.handoffs[0].agent.tools
# triage_agent.handoffs[0].agent.handoffs
# triage_agent.handoffs[0].agent.handoffs[0].agent.name
# triage_agent.handoffs[0].agent.handoffs[0].agent.instructions
# triage_agent.handoffs[0].agent.handoffs[0].agent.input_guardrails
# triage_agent.handoffs[0].agent.handoffs[0].agent.tools
# triage_agent.handoffs[0].agent.handoffs[0].agent.handoffs