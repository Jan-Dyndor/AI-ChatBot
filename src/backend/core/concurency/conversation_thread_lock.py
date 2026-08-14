from threading import Lock


class ConversationLockManager:
    """Klasa typy singleton ktora bedzie trzymac inofrmacje o conversation ID i obiektice Lock do niej przypisanym pop top by zapwenic ze tylko jeden thread (watek) moze pracowac nad dana konwersacja i uniemozliwic race condition"""

    def __init__(self) -> None:
        self._lock_dict: dict[int, Lock] = {}
        self._registry_lock = Lock()

    def get_or_create_lock(self, conversation_id: int) -> Lock:
        """Funckcja ma dict w ktorym bedzie trzymac conversation_ID i przypisany jej obiekt Lock ktory bedzie mozna zajmowac i zwalniac
        A takze ma swoj wlasny obirkt Lock ktory zapewni ze tylko jeden thread na raz bedzie przegladac dict z conversation_id by uniemozliwic sytuacje ze dwa thready w tym samym czasie sprawdza slownik i ustala ze nie ma zablokwanego locka dla danej kowersacji i zaczna race condition

        Args:
            conversation_id (int): _description_

        Returns:
            Lock: Zwraca obiekt Lock
        """
        with self._registry_lock:
            if conversation_id not in self._lock_dict:
                self._lock_dict[conversation_id] = Lock()
            return self._lock_dict[conversation_id]
