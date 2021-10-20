from .models import Status
from .utils import get_sauna_id, get_sauna_name, get_default_status


def test_get_sauna_id():
    id_a = get_sauna_id()
    id_b = get_sauna_id()
    assert id_a == id_b


def test_get_sauna_name():
    name_a = get_sauna_name()
    name_b = get_sauna_name()
    assert name_a == name_b


def test_get_default_status():
    status = get_default_status()
    assert isinstance(status, Status)
