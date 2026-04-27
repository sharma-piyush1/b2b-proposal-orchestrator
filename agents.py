import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from state import AgentState, TechnicalArchitecture

load_dotenv()

llm = ChatGroq(
    temperature=0,
    model_name="llama-3.3-70b-versatile",
    api_key=os.environ.get("GROQ_API_KEY")
)

def extractor_node(state: AgentState) -> AgentState:
    rfp_text = state.get("rfp_input", "")
    
    extraction_prompt = f"""
    Extract the technical requirements from the following RFP.
    
    Rules:
    1. If the infrastructure is not explicitly stated, output "Unspecified".
    2. If the latency SLA is not explicitly stated, output "Standard".
    
    RFP Text: {rfp_text}
    """
    
    structured_llm = llm.with_structured_output(TechnicalArchitecture)
    
    try:
        result = structured_llm.invoke(extraction_prompt)
        state["extracted_requirements"] = result
        
        # Flag if core requirements are missing
        if result.infrastructure == "Unspecified":
            state["errors"].append("Warning: Infrastructure requirements missing from RFP.")
            
        state["current_agent"] = "extractor"
    except Exception as e:
        state["errors"].append(f"Extraction error: {str(e)}")
        
    return state

def critic_node(state: AgentState) -> AgentState:
    """Evaluates the alignment between requirements and pricing."""
    reqs = state.get("extracted_requirements")
    pricing = state.get("financial_pricing")
    
    # Logic check: If AWS is selected but implementation fee is suspiciously low
    if reqs and pricing:
        if "AWS" in reqs.infrastructure and pricing.implementation_fee < 5000:
            state["errors"].append("Critic: Implementation fee too low for AWS deployment.")
            state["current_agent"] = "critic_revision_requested"
            return state
            
    state["current_agent"] = "critic_approved"
    return state


if __name__ == "__main__":
    test_state = AgentState(
        rfp_input="We need a cloud-based multi-agent system using AWS. It must process data with sub-second latency.",
        extracted_requirements=None,
        financial_pricing=None,
        drafted_sections={},
        current_agent="",
        human_review_required=False,
        workflow_complete=False,
        errors=[]
    )
    
    new_state = extractor_node(test_state)
    
    if new_state["errors"]:
        print("Execution Errors:")
        for error in new_state["errors"]:
            print(error)
    else:
        print("Extraction Successful:")
        print(new_state["extracted_requirements"])