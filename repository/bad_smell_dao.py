import typing
from models import BadSmell
from database import create_session


class BadSmellDao:
    @staticmethod
    def select_all_from_bad_smell(offset: int) -> typing.List[typing.Type[BadSmell]]:
        with create_session() as session:
            data = session.query(BadSmell).offset(offset).limit(300).all()
            return data
