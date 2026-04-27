from typing import Dict, List, Optional
from typing_extensions import TypedDict
from pydantic import BaseModel, Field

class TechnicalArchitecture(BaseModel):
    components: List[str] = Field(description="Key technical components required.")
    infrastructure: str = Field(description="Cloud or local infrastructure requirements.")
    latency_sla: str = Field(description="Service Level Agreement for latency.")

class PricingModel(BaseModel):
    software_license_cost: float = Field(description="Annual software licensing cost.")
    implementation_fee: float = Field(description="One-time implementation fee.")
    maintenance_percentage: float = Field(description="Annual maintenance fee percentage.")

class ProposalSection(BaseModel):
    section_title: str
    content: str
    approved: bool = False

class AgentState(TypedDict):
    rfp_input: str
    extracted_requirements: Optional[TechnicalArchitecture]
    financial_pricing: Optional[PricingModel]
    drafted_sections: Dict[str, ProposalSection]
    current_agent: str
    human_review_required: bool
    workflow_complete: bool
    errors: List[str]
    research_data: str | None