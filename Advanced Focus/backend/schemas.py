from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import date, datetime

# Token Schemas
class Token(BaseModel):
    access_token: str
    token_type: str
    user_type: str # "student" or "admin"
    username: str
    display_name: str

class TokenData(BaseModel):
    username: Optional[str] = None
    user_type: Optional[str] = None

# Admin Schemas
class AdminCreate(BaseModel):
    username: str
    password: str
    email: Optional[EmailStr] = None

class AdminOut(BaseModel):
    id: int
    username: str
    email: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

# Student Personal Details Update
class StudentUpdate(BaseModel):
    student_name: Optional[str] = None
    date_of_birth: Optional[str] = None
    gender: Optional[str] = None
    address: Optional[str] = None
    guardian_name: Optional[str] = None
    guardian_phone: Optional[str] = None
    profile_photo_b64: Optional[str] = None

# Student Registration Schema (by Admin)
class StudentCreate(BaseModel):
    username: str
    password: str
    student_name: str
    student_number: str
    student_class: str
    date_of_birth: Optional[str] = None
    gender: Optional[str] = None
    address: Optional[str] = None
    guardian_name: Optional[str] = None
    guardian_phone: Optional[str] = None

class StudentOut(BaseModel):
    id: int
    username: str
    student_name: str
    student_number: Optional[str] = None
    student_class: Optional[str] = None
    status: str
    date_of_birth: Optional[str] = None
    gender: Optional[str] = None
    address: Optional[str] = None
    guardian_name: Optional[str] = None
    guardian_phone: Optional[str] = None
    profile_photo_b64: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

# Fee Payment Schemas
class FeePaymentCreate(BaseModel):
    student_id: int
    month_covered: str
    amount_paid: float
    payment_method: str
    date: Optional[date] = None

class FeePaymentOut(BaseModel):
    id: int
    student_id: int
    date: date
    month_covered: str
    amount_paid: float
    payment_method: str

    class Config:
        from_attributes = True

# Performance Schemas
class PerformanceCreate(BaseModel):
    student_id: int
    activity: str
    mark: str
    comment: Optional[str] = None
    date: Optional[date] = None

class PerformanceOut(BaseModel):
    id: int
    student_id: int
    date: date
    activity: str
    mark: str
    comment: Optional[str] = None

    class Config:
        from_attributes = True

# Attendance Schemas
class AttendanceCreate(BaseModel):
    student_id: int
    status: str
    date: Optional[date] = None

class AttendanceOut(BaseModel):
    id: int
    student_id: int
    date: date
    status: str

    class Config:
        from_attributes = True

# School Expense Schemas
class SchoolExpenseCreate(BaseModel):
    category: str
    description: Optional[str] = None
    amount: float
    date: Optional[date] = None

class SchoolExpenseOut(BaseModel):
    id: int
    date: date
    category: str
    description: Optional[str] = None
    amount: float

    class Config:
        from_attributes = True

# Other Income Schemas
class OtherIncomeCreate(BaseModel):
    source: str
    amount: float
    date: Optional[date] = None

class OtherIncomeOut(BaseModel):
    id: int
    date: date
    source: str
    amount: float

    class Config:
        from_attributes = True

# Student Full Profile Output for Student Logins
class StudentDashboardData(BaseModel):
    student: StudentOut
    payments: List[FeePaymentOut]
    performances: List[PerformanceOut]
    attendances: List[AttendanceOut]
    overall_balance: float
