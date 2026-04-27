import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.postgres import PostgresSaver
from psycopg_pool import ConnectionPool
from dotenv import load_dotenv

# Import LangChain components for the Research and Pricing Agents
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_groq import ChatGroq

# Import your custom state and node logic
from state import AgentState, ProposalSection, PricingModel
from agents import extractor_node

load_dotenv()

os.environ["LANGGRAPH_STRICT_MSGPACK"] = "false"

# --- 1. Request Schemas ---
class ProposalRequest(BaseModel):
    rfp_text: str
    thread_id: str

class PricingApproval(BaseModel):
    thread_id: str
    is_approved: bool

# --- 2. Database Configuration ---
db_uri = os.environ.get("DATABASE_URI")

pool = ConnectionPool(
    conninfo=db_uri, 
    max_size=20,
    kwargs={"prepare_threshold": None} 
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    with pool.connection() as conn:
        conn.autocommit = True
        PostgresSaver(conn).setup()
    print("Production state tables initialized.")
    yield
    pool.close()

app = FastAPI(title="B2B Proposal Multi-Agent API", lifespan=lifespan)

# --- 3. CORS Configuration ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 4. Agent Nodes & Routing ---

def research_node(state: AgentState) -> AgentState:
    """Fetches real-time market data based on extracted requirements."""
    reqs = state.get("extracted_requirements")
    
    if reqs and reqs.infrastructure:
        search = TavilySearchResults(max_results=2)
        query = f"Average enterprise migration and implementation cost for {reqs.infrastructure} architecture 2026"
        results = search.invoke({"query": query})
        state["research_data"] = str(results)
    else:
        state["research_data"] = "No specific infrastructure requirements extracted."
        
    state["current_agent"] = "research"
    return state

def pricing_node(state: AgentState) -> AgentState:
    """Calculates dynamic pricing using LLM and research data."""
    reqs = state.get("extracted_requirements")
    research = state.get("research_data", "")
    
    # Initialize LLM with structured output to match your Pydantic schema
    llm = ChatGroq(
        model="llama-3.3-70b-versatile", 
        temperature=0.1
    ).with_structured_output(PricingModel)
    
    prompt = f"""
    Calculate a realistic enterprise pricing model based on the following context.
    
    Technical Requirements: {reqs}
    Market Research Data: {research}
    
    Output the software license cost, implementation fee, and maintenance percentage. Ensure the implementation fee aligns with the scale of the infrastructure required.
    """
    
    pricing_result = llm.invoke(prompt)
    state["financial_pricing"] = pricing_result
    state["current_agent"] = "pricing"
    return state

def critic_node(state: AgentState) -> AgentState:
    """QA Agent: Evaluates pricing logic against requirements."""
    reqs = state.get("extracted_requirements")
    pricing = state.get("financial_pricing")
    
    if reqs and pricing:
        if "AWS" in reqs.infrastructure and pricing.implementation_fee < 10000:
            state["errors"].append("Critic: Pricing too low for complex AWS migration. Recalculate.")
            state["current_agent"] = "critic_revision_requested"
            return state
            
    state["current_agent"] = "critic_approved"
    return state

def should_continue(state: AgentState):
    """Router logic for self-correction loop."""
    if state["current_agent"] == "critic_revision_requested":
        return "pricing"
    return "document_writer"

def document_writer_node(state: AgentState) -> AgentState:
    """Synthesizes all state data into a professional B2B proposal."""
    reqs = state.get("extracted_requirements")
    pricing = state.get("financial_pricing")
    rfp_input = state.get("rfp_input", "Standard Infrastructure Migration")
    
    # Safely extract values regardless of whether the state rehydrated as a dict or Pydantic model
    if isinstance(reqs, dict):
        infra = reqs.get("infrastructure", "Cloud")
    else:
        infra = getattr(reqs, "infrastructure", "Cloud")

    if isinstance(pricing, dict):
        sw_cost = pricing.get("software_license_cost", 0)
        imp_fee = pricing.get("implementation_fee", 0)
        maint = pricing.get("maintenance_percentage", 0)
    else:
        sw_cost = getattr(pricing, "software_license_cost", 0)
        imp_fee = getattr(pricing, "implementation_fee", 0)
        maint = getattr(pricing, "maintenance_percentage", 0)
    
    # Initialize the LLM (standard text output, not structured)
    llm = ChatGroq(
        model="llama-3.3-70b-versatile", 
        temperature=0.4 
    )
    
    prompt = f"""
    You are an expert B2B Technical Proposal Writer. Your task is to draft a comprehensive proposal based on the following validated data.
    
    --- DATA CONTEXT ---
    Client Needs: {rfp_input}
    Technical Architecture: {reqs}
    Financial Model:
    - Software License: ${sw_cost:,.2f}
    - Implementation Fee: ${imp_fee:,.2f}
    - Maintenance: {maint}%
    
    --- REQUIRED FORMAT (MARKDOWN) ---
    Draft the proposal with the following sections:
    1. Executive Summary
    2. Proposed Technical Architecture
    3. Financial Investment
    4. Next Steps
    
    Keep the tone professional, persuasive, and concise. Do not use generic corporate jargon.
    """
    
    # Generate the proposal document
    proposal_content = llm.invoke(prompt).content
    
    # Save to state
    state["drafted_sections"]["executive_summary"] = ProposalSection(
        section_title="Final Proposal",
        content=proposal_content,
        approved=True
    )
    state["current_agent"] = "document_writer"
    state["workflow_complete"] = True
    return state
# --- 5. Graph Construction ---

def build_graph(checkpointer):
    workflow = StateGraph(AgentState)
    
    workflow.add_node("extractor", extractor_node)
    workflow.add_node("research", research_node)
    workflow.add_node("pricing", pricing_node)
    workflow.add_node("critic", critic_node)
    workflow.add_node("document_writer", document_writer_node)
    
    workflow.set_entry_point("extractor")
    workflow.add_edge("extractor", "research")
    workflow.add_edge("research", "pricing")
    workflow.add_edge("pricing", "critic")
    
    workflow.add_conditional_edges(
        "critic",
        should_continue,
        {
            "pricing": "pricing",
            "document_writer": "document_writer"
        }
    )
    
    workflow.add_edge("document_writer", END)
    
    return workflow.compile(checkpointer=checkpointer, interrupt_before=["document_writer"])

# --- 6. Endpoints ---

@app.post("/generate-proposal")
async def generate_proposal(request: ProposalRequest):
    config = {"configurable": {"thread_id": request.thread_id}}
    
    initial_state = AgentState(
        rfp_input=request.rfp_text,
        extracted_requirements=None,
        research_data=None,
        financial_pricing=None,
        drafted_sections={},
        current_agent="user",
        human_review_required=False,
        workflow_complete=False,
        errors=[]
    )
    
    try:
        with pool.connection() as conn:
            checkpointer = PostgresSaver(conn)
            agent_workflow = build_graph(checkpointer)
            final_state = agent_workflow.invoke(initial_state, config=config)
            return {"status": "paused_for_review", "data": final_state}
    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/approve-pricing")
async def approve_pricing(request: PricingApproval):
    config = {"configurable": {"thread_id": request.thread_id}}
    try:
        with pool.connection() as conn:
            checkpointer = PostgresSaver(conn)
            agent_workflow = build_graph(checkpointer)
            
            if not request.is_approved:
                return {"status": "rejected", "message": "Workflow stopped."}
            
            resumed_state = agent_workflow.invoke(None, config=config)
            return {"status": "completed", "data": resumed_state}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)