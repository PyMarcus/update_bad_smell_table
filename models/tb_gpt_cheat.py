import datetime
import sqlalchemy as sa
from sqlalchemy.orm import declarative_base


class GptCheat(declarative_base()):
    """table that will be filled with the execution of the process."""

    __tablename__: str = 'tb_gpt_cheats'
    id: int = sa.Column(sa.BigInteger, primary_key=True, autoincrement=True)
    id_bad_smell: int = sa.Column(sa.BigInteger)
    id_base: int = sa.Column(sa.Integer)
    nr_question: int = sa.Column(sa.Integer)
    created_at: datetime.datetime = sa.Column(sa.DateTime, default=datetime.datetime.now, index=True)
