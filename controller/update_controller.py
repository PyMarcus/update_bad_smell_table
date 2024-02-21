import datetime
import re
import json
import sys
import typing
from typing import Type
from database import create_session
from database import LogMaker
from repository import BadSmellDao
from repository import GptCheatDao
from models import GptCheat, BadSmell


class UpdateController:
    def __init__(self, offset: int) -> None:
        self.__offset = offset
        self.__not_question: int = 0

    @staticmethod
    def __check_json_and_get_keys(chatgpt_response: str) -> typing.Optional[typing.List[str]]:
        try:
            json_data = json.loads(chatgpt_response)
            if isinstance(json_data, dict):
                return [k for k in list(json_data.keys())]
            else:
                return None
        except ValueError:
            return None

    @staticmethod
    def __check_json_and_get_values(chatgpt_response: str) -> typing.Optional[typing.Dict[str, str]]:
        try:
            json_data = json.loads(chatgpt_response)
            if isinstance(json_data, dict):
                return json_data
            else:
                return None
        except ValueError:
            return None

    @staticmethod
    def __check_if_there_is_yes_or_not(answer: str) -> bool:
        if "yes" in answer.lower():
            return True
        return False

    @staticmethod
    def __regex(text: str) -> typing.Optional[str]:
        regex_list = [
            r'the bad smells are:\s*(.*?)$',
            r'"\w*bad_smells":\s*(\[[^\]]*\])',
            r'"\w*the bad smells are":\s*(\[[^\]]*\])',
            r'"\w*the_bad_smells_are":\s*(\[[^\]]*\])',
            r'"\w*bad smells are":\s*(\[[^\]]*\])',
            r'"\w*bad_smells_are":\s*(\[[^\]]*\])',
            r'"\w*detected_bad_smells":\s*(\[[^\]]*\])',
            r'"\w*detected bad smells":\s*(\[[^\]]*\])',
            r'the bad smells are:\s*(\[[^\]]*\])',
            r'"\w*bad smells":\s*(\[[^\]]*\])(?:[^"]+|$)',
            r'"\w*badsmells":\s*(\[[^\]]*\])(?:[^"]+|$)',
        ]
        for regex in regex_list:
            match = re.search(regex, text.lower())
            if match:
                bad_smells_list = match.group(1)
                return ((bad_smells_list.replace('}', '').
                         replace('{', '').replace('"', '')).replace('\n', '')
                        .replace('[', '').replace(']', ''))
        return None

    @staticmethod
    def __parser_low_keys(gpt_response: str) -> typing.Optional[str] and bool:
        if "no" in str(gpt_response).lower():
            return None, False
        else:
            try_regex = UpdateController.__regex(str(gpt_response))
            if try_regex:
                return try_regex, True
            return None, True

    @staticmethod
    def __update_low_row(item: typing.Type[BadSmell]) -> None:
        with create_session() as session:
            item.bad_smell_gpt = "Not specified"
            item.found_any = False
            item.bad_smell_not_found = item.bad_smell_in_base
            item.valid_bad_smell = False
            item.dt_insertion = datetime.datetime.now()
            session.add(item)
            session.commit()
            session.close()

    @staticmethod
    def __simple_parser(text: str) -> str:
        return (str(text).replace('}', '').
                replace('{', '').replace('"', '').
                replace('\n', '').replace('[', '').
                replace(']', ''))

    @staticmethod
    def __bad_answer(item: typing.Type[BadSmell]) -> None:
        bad_smells = UpdateController.__check_json_and_get_keys(item.chat_gpt_response)
        if "smell" in str(bad_smells):
            key = [smell for smell in bad_smells if "smell" in smell.lower()]
            if len(key) > 1:
                if "features" in str(item.chat_gpt_response):
                    gpt_response = json.loads(item.chat_gpt_response)['features']
                else:
                    gpt_response = json.loads(item.chat_gpt_response)[key[1]]
                item.chat_gpt_response = UpdateController.__simple_parser(gpt_response)
            else:
                gpt_response = json.loads(item.chat_gpt_response)[key[0]]
                if "smells" not in str(gpt_response):
                    item.chat_gpt_response = UpdateController.__simple_parser(gpt_response)
                else:
                    item.chat_gpt_response = ("Incoherent response format,"
                                              " very different from what was expected.")
            item.valid_bad_smell = True
            item.dt_insertion = datetime.datetime.now()
            item.found_any = True
            item.bad_smell_not_found = [x for x in gpt_response if str(x).lower() not in str(item.bad_smell_in_base).lower()]
        else:
            item.chat_gpt_response = ("Incoherent response format,"
                                      " very different from what was expected.")
            item.valid_bad_smell = False
            item.dt_insertion = datetime.datetime.now()
            item.found_any = False
            item.bad_smell_not_found = item.bad_smell_in_base
        print(item.chat_gpt_response)
        with create_session() as session:
            session.add(item)
            session.commit()
            session.close()

    def run(self) -> None:
        offset = 0
        while True:
            items = BadSmellDao.select_all_from_bad_smell(offset)
            if not items:
                break
            for item in items:
                keys: typing.List[str] = self.__check_json_and_get_keys(item.chat_gpt_response)
                if keys:
                    if len(keys) < 2 or "NO" in str(item.chat_gpt_response):
                        smell, exists = self.__parser_low_keys(item.chat_gpt_response)

                        if exists and not smell:
                            # self.__update_low_row(item)
                            gpt_cheat: GptCheat = GptCheat(
                                id=item.id_source_code,
                                id_bad_smell=item.id_bad_smell,
                                nr_question=item.nr_question,
                                id_base=item.id_base
                            )
                            if GptCheatDao.create(gpt_cheat):
                                LogMaker.write_log(f"Inserted into gptcheat id_base: {item.id_base}"
                                                   f" id_smell: {item.id_bad_smell}", "info")
                            else:
                                LogMaker.write_log(f"Fail to Insert into gptcheat id_base: {item.id_base}"
                                                   f" id_smell: {item.id_bad_smell}", "info")
                        else:
                            ...  # implementar recuperacao de smells
                        continue
                    elif len(keys) > 2:
                        self.__bad_answer(item)
                        continue
                    json_keys_values = self.__check_json_and_get_values(item.chat_gpt_response)
                    if json_keys_values is not None:
                        for index, (key, value) in enumerate(json_keys_values.items()):
                            ...
                            # resolved = self.__parser(item.chat_gpt_response, value)
                            # print(resolved)
                    else:
                        print("Rodar o parser para string padrão")
                        print(item.chat_gpt_response)
                        sys.exit(0)
                else:
                    self.__not_question += 1
                    LogMaker.write_log(f"Without question {self.__not_question} -> id base: {item.id_base}"
                                       f" -> Link: {item.url_github}", "warning")
                # sys.exit(0)
            offset += self.__offset
