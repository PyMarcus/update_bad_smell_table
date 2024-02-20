from repository import BadSmellDao


class UpdateController:
    def __init__(self, offset: int) -> None:
        self.__offset = offset

    def run(self) -> None:
        offset = 0
        while True:
            items = BadSmellDao.select_all_from_bad_smell(offset)
            if not items:
                break
            for item in items:
                print(item)
            offset += offset
