from everyclass.rpc import init as _init_rpc
from everyclass.rpc.entity import Entity as _entity
from everyclass.server.utils.config import get_config
from everyclass.server.utils.encryption import encrypt

_init_rpc(resource_id_encrypt_function=encrypt)  # 为 everyclass.rpc 模块注入 encrypt 函数

_entity.set_base_url(get_config().ENTITY_BASE_URL)
_entity.set_request_token(get_config().ENTITY_TOKEN)
