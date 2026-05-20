from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field


class SQLAgentRequest(BaseModel):
    question: str = Field(..., min_length=1)


class SQLAgentResponse(BaseModel):
    sql: Optional[str]
    result: Optional[Union[int, float, str, List[Dict[str, Any]]]]
    summary: str
    status: str
    attempts: int
    error: Optional[str] = None


class AgentAttemptLog(BaseModel):
    attempt: int
    sql: str
    status: str
    error: Optional[str] = None
    duration_seconds: float = 0.0


class AgentRunLog(BaseModel):
    question: str
    decomposition: Dict[str, Any]
    attempts: List[AgentAttemptLog]
    final_status: str
    summary: str
