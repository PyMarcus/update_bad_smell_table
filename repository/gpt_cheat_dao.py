from models import GptCheat
from database import create_session
from database import LogMaker


class GptCheatDao:
    @staticmethod
    def create(gpt_cheat: GptCheat) -> bool:
        try:
            with create_session() as session:
                session.add(gpt_cheat)
                session.commit()
                return True
        except Exception as err:
            LogMaker.write_log(f"Fail to insert into gpt_cheat {err}", "error")
            return False
