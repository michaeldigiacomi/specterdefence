from sqlalchemy import Column, String, cast
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class LoginAnalyticsModel(Base):
    __tablename__ = 'login_analytics'
    id = Column(String, primary_key=True)
    anomaly_flags = Column(JSONB)

expr = cast(LoginAnalyticsModel.anomaly_flags, String) != "[]"
expr2 = cast(LoginAnalyticsModel.anomaly_flags, String) != cast("[]", String)

print("Expr 1 compiled (Postgres):", expr.compile(dialect=__import__('sqlalchemy.dialects.postgresql').dialects.postgresql.dialect()))
print("Expr 2 compiled (Postgres):", expr2.compile(dialect=__import__('sqlalchemy.dialects.postgresql').dialects.postgresql.dialect()))
