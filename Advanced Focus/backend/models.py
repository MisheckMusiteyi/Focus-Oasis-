from sqlalchemy import Column, Integer, String, Float, ForeignKey, Date, DateTime, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime, date
from .database import Base

class Admin(Base):
    __tablename__ = "admins"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    email = Column(String, unique=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class Student(Base):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    student_name = Column(String, index=True, nullable=False)
    student_number = Column(String, unique=True, index=True)
    student_class = Column(String, index=True)
    status = Column(String, default="Active") # Active, Suspended, Inactive

    # Personal info
    date_of_birth = Column(String)
    gender = Column(String)
    address = Column(String)
    guardian_name = Column(String)
    guardian_phone = Column(String)
    profile_photo_b64 = Column(String)  # Base64 string for student photo

    # Relationships
    payments = relationship("FeePayment", back_populates="student", cascade="all, delete-orphan")
    performances = relationship("Performance", back_populates="student", cascade="all, delete-orphan")
    attendances = relationship("Attendance", back_populates="student", cascade="all, delete-orphan")
    created_at = Column(DateTime, default=datetime.utcnow)

class FeePayment(Base):
    __tablename__ = "fee_payments"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    date = Column(Date, nullable=False, default=date.today)
    month_covered = Column(String, nullable=False) # e.g. "January 2026"
    amount_paid = Column(Float, nullable=False)
    payment_method = Column(String, nullable=False) # e.g. "Cash", "Card", "Bank Transfer"

    student = relationship("Student", back_populates="payments")

class Performance(Base):
    __tablename__ = "performances"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    date = Column(Date, nullable=False, default=date.today)
    activity = Column(String, nullable=False) # e.g. "Mathematics Test 1"
    mark = Column(String, nullable=False) # e.g. "85%"
    comment = Column(String)

    student = relationship("Student", back_populates="performances")

class Attendance(Base):
    __tablename__ = "attendances"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    date = Column(Date, nullable=False, default=date.today)
    status = Column(String, nullable=False) # e.g. "✅ Present", "❌ Absent"

    student = relationship("Student", back_populates="attendances")

class SchoolExpense(Base):
    __tablename__ = "school_expenses"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, nullable=False, default=date.today)
    category = Column(String, nullable=False)
    description = Column(String)
    amount = Column(Float, nullable=False)

class OtherIncome(Base):
    __tablename__ = "other_incomes"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, nullable=False, default=date.today)
    source = Column(String, nullable=False)
    amount = Column(Float, nullable=False)
