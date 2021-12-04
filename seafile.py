import requests
from treelib import Tree, Node

"""
这个文件是用来进行接口调用的
整个文件系统用一个树来模拟
每获取一个文件夹的内容就创建一个子节点来存储
这里需要注意的是，如果用户直接输入路径，那么就在当前的节点下，直接创建一个新的节点来存储
这样后退键就可以完全记录下整个的路径
"""


class Libraries:
    def __init__(self, token):
        self.token = token
        self.headers = {
            'Authorization': "Token {}".format(self.token),
            'Accept': 'application/json; indent=4',

        }
        self.tree = Tree()
        self.root = Node("root")
        self.current = self.root
        self.repo_id = None
        self.tree.add_node(self.root)
        self.path = '/'
        self.history = []
        self.path_history = []

    def get_libraries(self):
        url = "https://box.nju.edu.cn/api2/repos/"
        html = requests.get(url, headers=self.headers)
        return html.json()

    def get_data(self, path):
        url = "https://box.nju.edu.cn/api2/repos/{}/dir/?p={}".format(self.repo_id, path)
        html = requests.get(url, headers=self.headers)
        try:
            return html.json()
        except:
            raise ValueError()

    def get_dir(self, id_index):
        id_data = self.tree.children(self.current.identifier)[id_index].data
        if id_data['type'] in ['repo', 'srepo', 'grepo']:
            self.repo_id = id_data['id']
            self.path_history.append(self.path)
        elif id_data['type'] not in ['dir', 'folder']:
            return None
        else:
            name = id_data['name']
            self.path_history.append(self.path)
            if 'path' in id_data.keys():
                self.path = id_data['path']
            else:
                self.path += '{}/'.format(name)
        self.history.append(self.current)

        self.current = self.tree.children(self.current.identifier)[id_index]
        return self.get_data(self.path)

    def search(self, q):
        base_url = "http://box.nju.edu.cn/api/v2.1/search-file/"
        params = {
            "repo_id": self.repo_id,
            "q": q
        }
        html = requests.get(base_url, params=params, headers=self.headers)
        return html.json()

    def creatUploadLink(self, path):
        base_url = "https://box.nju.edu.cn/api/v2.1/share-links/"
        body = {
            "repo_id": self.repo_id,
            "path": path,
            "permissions": {
                "can_edit": False,
                "can_download": True,
                "can_upload": True
            }
        }
        header = self.headers
        header["Content-type"] = "application/json"

        response = requests.post(base_url, json=body, headers=header)
        result = response.json()
        if result.get("error_msg"):
            print(result['error_msg'])
        else:
            print(result.get("link"))
            return result['link']

    def creatDirectory(self, path):
        base_url = "https://box.nju.edu.cn/api2/repos/{}/dir/".format(self.repo_id)
        body = {
            "operation": "mkdir"
        }
        params = {
            "p": path
        }
        header = self.headers
        header["Accept"] = "application/json; charset=utf-8; indent=4"

        response = requests.post(base_url, data=body, params=params, headers=header)
        print(response.json())
