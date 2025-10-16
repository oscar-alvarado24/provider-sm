from pydantic import BaseModel


class BranchData(BaseModel):
    company_id: str
    branch_id: str
