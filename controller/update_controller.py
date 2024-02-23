import re
import sys
import json
import typing
import datetime
from database import LogMaker
from repository import GptCheatDao
from repository import BadSmellDao
from database import create_session
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
            item.bad_smell_in_base = False
            item.valid_bad_smell = False
            item.dt_insertion = datetime.datetime.now()
            session.add(item)
            session.commit()
            print("OK")

    @staticmethod
    def __simple_parser(text: str) -> str:
        return (str(text).replace('}', '').
                replace('{', '').
                replace('"', '').
                replace('\n', '').
                replace('[', '').
                replace(']', '').replace("'", '')).lower()

    def __bad_answer(self, item: typing.Type[BadSmell]) -> None:
        bad_smells = self.__check_json_and_get_keys(item.chat_gpt_response)
        if "smell" in str(bad_smells):
            key = [smell for smell in bad_smells if "smell" in smell.lower()]
            if len(key) > 1:
                if "features" in str(item.chat_gpt_response):
                    gpt_response = json.loads(item.chat_gpt_response)['features']
                else:
                    gpt_response = json.loads(item.chat_gpt_response)[key[1]]
                item.bad_smell_gpt = self.__simple_parser(gpt_response)
            else:
                gpt_response = json.loads(item.chat_gpt_response)[key[0]]
                if "smells" not in str(gpt_response):
                    item.bad_smell_gpt = self.__simple_parser(gpt_response)
                else:
                    item.bad_smell_gpt = ("Incoherent response format,"
                                          " very different from what was expected.")
            item.valid_bad_smell = True
            item.dt_insertion = datetime.datetime.now()
            item.found_any = True
            item.bad_smell_not_found = item.badsmell_base if not (
                any(item.badsmell_base in x for x in self.__simple_parser(str(gpt_response)).split(','))) else ''
            if item.bad_smell_not_found:
                item.bad_smell_in_base = False
            else:
                item.bad_smell_in_base = True
            item.bad_smell_not_in_the_base = self.__simple_parser(str([x for x in
                                                                       self.__simple_parser(str(gpt_response)).split(',')
                                                                       if item.badsmell_base.lower() not in x.lower()]))


        else:
            item.bad_smell_gpt = ("Incoherent response format,"
                                  " very different from what was expected.")
            item.valid_bad_smell = False
            item.dt_insertion = datetime.datetime.now()
            item.found_any = False
            item.bad_smell_in_base = False
            item.bad_smell_not_found = item.bad_smell_in_base
        with create_session() as session:
            session.add(item)
            session.commit()
            print("OK1")

    def __parser(self, item: typing.Type[BadSmell], values) -> None:
        result = self.__simple_parser(values)
        item.bad_smell_gpt = result
        item.valid_bad_smell = True
        item.dt_insertion = datetime.datetime.now()
        item.found_any = True
        item.bad_smell_not_found = item.badsmell_base if not (
            any(item.badsmell_base in x for x in self.__simple_parser(str(result)).split(','))) else ''

        if item.bad_smell_not_found:
            item.bad_smell_in_base = False
        else:
            item.bad_smell_in_base = True
        item.bad_smell_not_in_the_base = self.__simple_parser(str([x for x in
                                                                   self.__simple_parser(result).split(',')
                                                                   if item.badsmell_base.lower() not in x.lower()]))
        with create_session() as session:
            session.add(item)
            session.commit()
            session.close()
            print("OK2")

    @staticmethod
    def __negative_parser(item: typing.Type[BadSmell]) -> None:
        item.bad_smell_gpt = ""
        item.valid_bad_smell = False
        item.dt_insertion = datetime.datetime.now()
        item.found_any = False
        item.bad_smell_in_base = False
        item.bad_smell_not_found = item.bad_smell_in_base
        with create_session() as session:
            session.add(item)
            session.commit()
            session.close()
            print("OK3")

    def __verify(self, item: typing.Type[BadSmell]) -> None:
        json_keys_values = self.__check_json_and_get_values(item.chat_gpt_response)
        if json_keys_values is not None:
            resolved = False
            for index, (key, value) in enumerate(json_keys_values.items()):
                if not index:
                    resolved = self.__check_if_there_is_yes_or_not(str(item.chat_gpt_response))
                    item.found_any = resolved
                elif resolved:
                    try:
                        self.__parser(item, value)
                    except Exception as err:
                        LogMaker.write_log(f"error to update id_base {item.id_base} {err}", "error")
                else:
                    try:
                        self.__negative_parser(item)
                    except Exception as err:
                        LogMaker.write_log(f"error to update id_base {item.id_base} {err}", "error")
        else:
            print("Rodar o parser para string padrão")
            print(item.chat_gpt_response)
            sys.exit(0)

    @staticmethod
    def __gpt_cheat(item: typing.Type[BadSmell]) -> None:
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

    def __save_with_low_keys(self, item: typing.Type[BadSmell], smell: str) -> None:
        smell: str = self.__simple_parser(smell)
        item.bad_smell_gpt = smell
        item.valid_bad_smell = True
        item.dt_insertion = datetime.datetime.now()
        item.found_any = True
        item.bad_smell_not_found = item.badsmell_base if not (
            any(item.badsmell_base in x for x in self.__simple_parser(str(smell)).split(','))) else ''
        if item.bad_smell_not_found:
            item.bad_smell_in_base = False
        else:
            item.bad_smell_in_base = True
        item.bad_smell_not_in_the_base = self.__simple_parser(str([x for x in
                                                                   self.__simple_parser(smell).split(',')
                                                                   if item.badsmell_base.lower() not in x.lower()]))
        with create_session() as session:
            session.add(item)
            session.commit()
            session.close()
            print("OK4")

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
                            try:
                                self.__update_low_row(item)
                                self.__gpt_cheat(item)
                            except Exception as err:
                                LogMaker.write_log(f"error to update id_base {item.id_base} {err}", "error")
                        elif exists and smell:
                            try:
                                self.__save_with_low_keys(item, smell)
                            except Exception as err:
                                LogMaker.write_log(f"error to update id_base {item.id_base} {err}", "error")
                        continue
                    elif len(keys) > 2:
                        self.__bad_answer(item)
                        continue
                    self.__verify(item)
                else:
                    self.__not_question += 1
                    LogMaker.write_log(f"Without question {self.__not_question} -> id base: {item.id_base}"
                                       f" -> Link: {item.url_github}", "warning")
            offset += self.__offset
