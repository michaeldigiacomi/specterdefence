from sqlalchemy import Column, String, cast, literal
from sqlalchemy.dialects.postgresql import JSONB as PG_JSONB
from sqlalchemy.types import JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects import postgresql, sqlite

Base = declarative_base()

class LoginAnalyticsModel(Base):
    __tablename__ = 'login_analytics'
    id = Column(String, primary_key=True)
    # Testing with generic JSON type which is likely what the model uses
    anomaly_flags = Column(JSON)

expr1 = LoginAnalyticsModel.anomaly_flags != []
expr2 = cast(LoginAnalyticsModel.anomaly_flags, String) != "[]"
expr3 = func.json_array_length(LoginAnalyticsModel.anomaly_flags) > 0 if hasattr(func, 'json_array_length') else None
expr4 = LoginAnalyticsModel.anomaly_flags.isnot(None) # maybe null?
from sqlalchemy import func

print("Expr 1 (PG):", expr1.compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}))
print("Expr 1 (SQ):", expr1.compile(dialect=sqlite.dialect(), compile_kwargs={"literal_binds": True}))

