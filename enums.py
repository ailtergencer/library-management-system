
from enum import Enum

class BookReturnStatus(Enum):
    PENDING = 0         # admin henüz kontrol etmedi
    NOT_RETURNED = 1    # kitap iade edilmedi
    RETURNED_OK = 2     # kitap sağlam iade edildi
    DAMAGED = 3         # kitap hasarlı iade edildi
    LATE = 4            # kitap geç iade edildi
    LOST = 5            # kitap kayboldu
