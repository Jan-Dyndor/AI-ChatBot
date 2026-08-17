from threading import Lock


class ConversationLockManager:
    """Manage in-memory locks assigned to individual conversations.

    Each conversation ID is associated with its own Lock object. Requests for
    the same conversation receive the same lock and must be processed one at
    a time. Requests for different conversations receive different locks and
    can be processed concurrently.

    A separate registry lock protects the dictionary while conversation locks
    are being retrieved or created. This prevents two threads from creating
    different locks for the same conversation at the same time.

    This manager works only within a single Python process (only one worker), and all requests
    must use the same ConversationLockManager instance.
    """

    def __init__(self) -> None:
        self._lock_dict: dict[int, Lock] = {}
        self._registry_lock = Lock()

    def get_or_create_lock(self, conversation_id: int) -> Lock:
        """Return the existing lock for a conversation or create a new one.

        Access to the lock dictionary is protected by the registry lock. This
        makes the check-and-create operation atomic and guarantees that all
        threads receive the same Lock object for a given conversation ID.

        The returned conversation lock is not acquired by this method. The
        caller is responsible for acquiring and releasing it.

        Args:
            conversation_id: ID of the conversation that requires a lock.

        Returns:
            The Lock object assigned to the given conversation.
        """
        with self._registry_lock:
            if conversation_id not in self._lock_dict:
                self._lock_dict[conversation_id] = Lock()
            return self._lock_dict[conversation_id]
