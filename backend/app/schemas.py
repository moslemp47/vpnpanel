from pydantic import BaseModel, EmailStr, field_validator

class SignupRequest(BaseModel):
    email: EmailStr
    password: str

    @field_validator("password")
    @classmethod
    def strong(cls, v):
        if len(v) < 6:
            raise ValueError("Password must be at least 6 characters")
        return v

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class PlanOut(BaseModel):
    id: int
    name: str
    price: float
    duration_days: int
    quota_gb: float
    class Config:
        from_attributes = True

class CreateOrderRequest(BaseModel):
    plan_id: int

class OrderOut(BaseModel):
    id: int
    status: str
    amount: float
    subscription_id: int | None = None
    class Config:
        from_attributes = True

class ProvisionRequest(BaseModel):
    subscription_id: int
    provider: str = "marzban"
