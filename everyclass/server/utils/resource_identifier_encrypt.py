import re
from binascii import a2b_base64

from Crypto.Cipher import AES

from everyclass.server.config import get_config


def _fill_16(text):
    """
    自动填充至十六位或十六的倍数
    :param text: 需要被填充的字符串
    :return: 已经被空白符填充的字符串
    """
    text += '\0' * (16 - (len(text) % 16))
    return str.encode(text)


def _aes_decrypt(aes_key, aes_text):
    """
    使用密钥解密文本信息，将会自动填充空白字符
    :param aes_key: 解密密钥
    :param aes_text: 需要解密的文本
    :return: 经过解密的数据
    """
    # 初始化解码器
    cipher = AES.new(_fill_16(aes_key), AES.MODE_ECB)
    # 优先逆向解密十六进制为bytes
    decrypt = a2b_base64(aes_text.replace('-', '/').replace("%3D", "=").encode())
    # 使用aes解密密文
    decrypt_text = str(cipher.decrypt(decrypt), encoding='utf-8').replace('\0', '')
    # 返回执行结果
    return decrypt_text.strip()


def identifier_decrypt(data: str, encryption_key: str = None, resource_type: str = None):
    """
    解密资源标识符

    :param data: 加密后的字符串
    :param encryption_key: 可选的 key
    :param resource_type: 验证资源类型（student、teacher、klass、room）
    :return:
    """
    if not encryption_key:
        encryption_key = get_config().RESOURCE_IDENTIFIER_ENCRYPTION_KEY

    data = _aes_decrypt(encryption_key, data)

    group = re.match(r'^(student|teacher|klass|room);([\s\S]+)$', data)  # 通过正则校验确定数据的正确性
    if group is None:
        raise ValueError('Decrypted data is invalid: %s' % data)
    else:
        if resource_type and group.group(1) != resource_type:
            raise ValueError('Resource type not correspond')
        return group.group(1), group.group(2)
