from typing import Optional, Literal
from pydantic import BaseModel

class HumanityRelevance(BaseModel):
    relevance_score: int
    relevance_justification: str
    relevance_quote: Optional[str]

class ImpartialityRelevance(BaseModel):
    relevance_score: int
    relevance_justification: str
    relevance_quote: Optional[str]

class IndependenceRelevance(BaseModel):
    relevance_score: int
    relevance_justification: str
    relevance_quote: int

class NeutralityRelevance(BaseModel):
    relevance_score: int
    relevance_justification: str
    relevance_quote: Optional[str]

HarmTypeLiteral = Literal[
    "Representational Harms",
    "Allocative Harms",
    "Quality-of-Service Harms",
    "Interpersonal Harms",
    "Social System Harms"
]

class ExtractedHarms(BaseModel):
    quote: str
    harm_type: HarmTypeLiteral

EthicalObligationLiteral = Literal[
    "Provide highest attainable quality of care and services",
    "Protect and care for response workers",
    "Minimize harms of response",
    "Support a locally led response",
    "Appropriate acquisition and management of assets",
    "Distribute benefits and burdens equitably",
    "Practice honesty and transparency",
    "Incorporate local knowledge and norms"
]

class EthicalObligation(BaseModel):
    name: EthicalObligationLiteral

SystemStageLiteralManual = Literal[
    "Data Sourcing & Selection",
    "Data Preprocessing & Annotation",
    "Model Selection & Pretraining",
    "Fine-tuning & Instruction Tuning",
    "Safety Tuning & Red-Teaming",
    "Deployment & Local Adaptation",
    "Continuous Monitoring & Alignment",
    "Governance & Maintenance"
]

class Rating(BaseModel):
    scope: float
    scale: float
    applicability: float
    final_score: float

class Recommendation(BaseModel):
    name: str
    description: str
    quote: str
    stages: list[SystemStageLiteralManual]
    rating: Rating

class SystemContext(BaseModel):
    objective: str
    context_of_use: str
    beneficiary: str

class EthicalTradeOff(BaseModel):
    system_context: SystemContext
    name: str
    description: str
    conflicted_ethical_obligation: list[EthicalObligationLiteral]
    quote: str
    concerned_harms: list[HarmTypeLiteral]
    humanity_relevance: HumanityRelevance
    impartiality_relevance: ImpartialityRelevance
    independence_relevance: IndependenceRelevance
    neutrality_relevance: NeutralityRelevance
    recommendations: list[Recommendation]

class ExtractedTradeOffs(BaseModel):
    tradeoffs: list[EthicalTradeOff]