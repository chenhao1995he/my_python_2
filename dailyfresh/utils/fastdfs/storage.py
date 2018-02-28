from django.core.files.storage import Storage
from fdfs_client.client import Fdfs_client
from django.conf import settings


class FastDFSStorage(Storage):
    """自定义Django储存系统的类"""
    def __init__(self, client_conf=None, server_ip=None):
        """初始化, 设置参数"""
        if client_conf is None:
            client_conf = settings.CLIENT_CONF
        self.client_conf = client_conf

        if server_ip is None:
            server_ip = settings.SERVER_IP
        self.server_ip = server_ip

    def _open(self, name, mode='rb'):
        pass

    def _save(self, name, content):
        """储存文件是时使用:参数2是上传来的文件名, 参数3是上传来的File对象"""
        # 创建客户端client
        client = Fdfs_client(self.client_conf)
        # 获取client获取文件的内容
        file_data = content.read()
        try:
            # Django借助client向FastDFS服务器上传文件
            result = client.upload_by_buffer(file_data)
        except Exception as e:
            print(e)
            print(1000)
            raise

        # 根据返回数据, 并判断数据是否上传成功
        if result.get('Status') == 'Upload successed.':
            # 读取file_id
            file_id = result.get("Remote file_id")
            # 返回Django储存起来即可
            return file_id
        else:
            # 开发工具类时,出现异常不要擅自处理, 交给使用者处理
            raise Exception('上传文件到FastDFS失败66666666')

    def exists(self, name):
        """Django用来判断文件是否存在的"""

        # 由于Djnago不存储图片，所以永远返回Fasle，直接保存到FastFDS
        return False

    def url(self, name):
        """用于返回图片在服务器上完整的地址：server_ip+path"""
        return self.server_ip + name


