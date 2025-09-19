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

class Recommendation(BaseModel):
    name: str
    description: str
    quote: str
    stages: list[SystemStageLiteralManual]

class EthicalTradeOff(BaseModel):
    name: str
    description: str
    quote: str
    concerned_harms: list[HarmTypeLiteral]
    humanity_relevance: HumanityRelevance
    impartiality_relevance: ImpartialityRelevance
    independence_relevance: IndependenceRelevance
    neutrality_relevance: NeutralityRelevance
    recommendations: list[Recommendation]

class ExtractedTradeOffs(BaseModel):
    tradeoffs: list[EthicalTradeOff]