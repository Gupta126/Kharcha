from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    # Server settings
    HOST: str = "0.0.0.0"
    PORT: int = 8090
    
    # ERP service specific settings
    EMPLOYEES_FILE: str = "../data/seed/employees.json"
    
    # Status transition delays (in seconds)
    IN_REVIEW_DELAY: int = 10
    APPROVED_DELAY: int = 20
    PAID_DELAY: int = 30
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
