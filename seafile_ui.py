from PyQt5.QtWidgets import QWidget, QApplication, QMessageBox, QMainWindow, \
    QListWidgetItem, QFileDialog, QDialog
from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtCore import QSize, Qt, QDateTime
from Ui_Login import Ui_Form
from conf import config
from Ui_MainWindows import Ui_MainWindow
from Ui_Links import Ui_Dialog
from Ui_ShareConf import Ui_Dialog as ShareConf
import sys
import requests
from urllib.parse import urlencode
import urllib
import json
import traceback
import os
from seafile import Libraries
import random, string
import _thread

"""
这个文件为UI功能窗口，主要为调用seafile.py文件
"""


class Login(QWidget, Ui_Form):
    def __init__(self, parent=None):
        super(Login, self).__init__(parent)
        self.setupUi(self)
        self.login_button.clicked.connect(self.login_func)
        self.password_input.returnPressed.connect(self.login_func)
        self.url = "box.nju.edu.cn"
        self.username_input.setText(config.username)
        self.password_input.setText(config.password)

    def login_func(self):
        if self.username_input.text() and self.password_input.text():
            base_url = "https://{}/api2/auth-token/".format(self.url)
            params = {
                'username': self.username_input.text(),
                'password': self.password_input.text()
            }
            html = requests.post(base_url, data=params)
            if html.status_code == 200:
                res = html.json()
                self.token = res['token']
                temp = self.winshow(self.token)
                print(self.token)
                self.hide()
            else:
                QMessageBox.critical(self, "警告", "用户名或密码错误", QMessageBox.Ok)
        else:
            QMessageBox.critical(self, "警告", "用户名和密码不能为空", QMessageBox.Ok)

    def winshow(self, token):
        main_windows = MainWindow(self)
        main_windows.token = token
        main_windows.init()
        main_windows.show()
        return main_windows


class MainWindow(QMainWindow, Ui_MainWindow):
    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent)
        self.setupUi(self)
        self.token = ""
        self.library = None

    def init(self):
        self.library = Libraries(self.token)
        self.libraries_list = self.library.get_libraries()
        for lib in self.libraries_list:
            self.library.tree.create_node(tag=lib['name'], parent=self.library.root, data=lib)
            item = QListWidgetItem()
            icon = QIcon()
            if not lib['encrypted']:
                icon.addPixmap(QPixmap("./resource/lib.png"), QIcon.Selected, QIcon.On)
            else:
                icon.addPixmap(QPixmap("./resource/lib-encrypted.png"), QIcon.Selected, QIcon.On)
            item.setIcon(icon)
            item.setText(lib['name'])
            self.listWidget.addItem(item)

        self.url_path.returnPressed.connect(self.skip)
        self.url_path.setText(self.library.path)
        self.listWidget.itemDoubleClicked.connect(self.forward)
        self.back.clicked.connect(self.backward)
        self.select_all.clicked.connect(self.check)
        self.search_button.clicked.connect(self.search)
        self.pushButton.clicked.connect(self.creatUploadLinks)
        self.uploadFolderButton.clicked.connect(self.creatFolder)
        self.search_input.returnPressed.connect(self.search)
        self.search_input.textChanged.connect(self.search)
        self.checkSharedLink.clicked.connect(self.ShowLinkWindow)

    def check(self):
        if self.select_all.isChecked():
            self.listWidget.selectAll()
            for i in range(self.listWidget.count()):
                if not self.listWidget.item(i).isHidden():
                    self.listWidget.item(i).setCheckState(Qt.Checked)
        else:
            self.listWidget.clearSelection()
            for i in range(self.listWidget.count()):
                self.listWidget.item(i).setCheckState(Qt.Unchecked)

    def update_list(self, item_list):
        for node in self.library.tree.children(self.library.current.identifier):
            self.library.tree.remove_node(node.identifier)
        self.listWidget.clear()
        self.item_list = item_list
        self.url_path.setText(self.library.path)
        for item_data in item_list:
            if item_data is None:
                continue
            self.library.tree.create_node(tag=item_data['name'], parent=self.library.current, data=item_data)
            item = QListWidgetItem()
            icon = QIcon()
            if item_data['type'] in ['dir', 'folder']:
                icon.addPixmap(QPixmap("./resource/folder-192.png"), QIcon.Selected, QIcon.On)
            elif item_data['type'] in ['repo', 'srepo', 'grepo'] and item_data['encrypted'] == False:
                icon.addPixmap(QPixmap("./resource/lib.png"), QIcon.Selected, QIcon.On)
            elif item_data['type'] in ['repo', 'srepo', 'grepo'] and item_data['encrypted'] == True:
                icon.addPixmap(QPixmap("./resource/lib-encrypted.png"), QIcon.Selected, QIcon.On)
            else:
                icon.addPixmap(QPixmap("./resource/file.png"), QIcon.Selected, QIcon.On)
            item.setIcon(icon)
            item.setText(item_data['name'])
            item.setCheckState(Qt.Unchecked)
            self.listWidget.addItem(item)
        self.library.tree.show()

    def forward(self):
        """
        前进
        """
        id_index = self.listWidget.currentRow()
        item_list = self.library.get_dir(id_index)
        if item_list is not None:
            self.update_list(item_list)

    def backward(self):
        """
        后退
        """
        if self.library.current.tag == 'root':
            return None

        self.library.current = self.library.history[-1]
        self.library.history.pop()
        self.library.path = self.library.path_history[-1]
        self.library.path_history.pop()

        print(self.library.current)
        if self.library.current.tag == 'root':
            item_list = self.libraries_list
            self.library.repo_id = None
        else:
            # item_list = self.library.get_data(self.library.path)
            items = self.library.tree.children(self.library.current.identifier)
            item_list = []
            for item in items:
                item_list.append(item.data)
        print(item_list)
        self.update_list(item_list)

    def skip(self):
        """
        跳转
        """
        if self.library.repo_id is None:
            QMessageBox.critical(self, "警告", "请先进入资料库", QMessageBox.Ok)
            return
        path = self.url_path.text()
        try:
            item_list = self.library.get_data(path)
            self.library.history.append(self.library.current)
            self.library.path_history.append(self.library.path)
            self.library.current = self.library.tree.create_node(tag=path, parent=self.library.current)
            self.update_list(item_list)
            self.library.path = path
            self.url_path.setText(path)

        except ValueError:
            QMessageBox.critical(self, "警告", "无此路径或路径错误", QMessageBox.Ok)

    def search(self, text=None):
        if self.library.repo_id is None:
            QMessageBox.critical(self, "警告", "请先指定资料库", QMessageBox.Ok)
            return

        q = self.search_input.text()
        if text is None or len(q) == 0:
            for i in range(self.listWidget.count()):
                item = self.listWidget.item(i)
                item.setHidden(False)
        else:
            for i in range(self.listWidget.count()):
                item = self.listWidget.item(i)
                if q in item.text():
                    item.setHidden(False)
                else:
                    item.setHidden(True)

    def creatFolder(self):
        if self.library.repo_id is None:
            QMessageBox.critical(self, "警告", "请先指定资料库", QMessageBox.Ok)
            return
        QMessageBox.information(self, "注意", "csv/txt 每行存一个文件夹名称", QMessageBox.Ok)

        fileName, fileType = QFileDialog.getOpenFileName(self, "打开图片", "", "*.csv;;*.txt")

        if len(fileName) == 0:
            return

        basePath = self.url_path.text()

        QMessageBox.information(self, "通知", "正在上传请稍后", QMessageBox.Ok)
        with open(fileName, 'r', encoding="utf-8") as f:
            for line in f:
                folderName = line.replace("\n", "")
                self.library.creatDirectory(basePath + folderName)
        QMessageBox.information(self, "通知", "上传完成，请刷新", QMessageBox.Ok)

    def creatUploadLinks(self):
        if self.library.repo_id is None:
            QMessageBox.critical(self, "警告", "请先指定资料库", QMessageBox.Ok)
            return

        self.select_all.setChecked(False)
        paths = []
        basePath = self.url_path.text()
        for i in range(self.listWidget.count()):
            item = self.listWidget.item(i)
            if item.checkState():
                item.setCheckState(Qt.Unchecked)
                if self.item_list[i]['type'] in ['dir', 'folder']:
                    paths.append(basePath + item.text())

        if len(paths) == 0:
            QMessageBox.critical(self, "警告", "请选择文件夹", QMessageBox.Ok)
            return

        share_windows = ShareConfig(self)
        share_windows.token = self.token
        share_windows.library = self.library
        share_windows.paths = paths
        share_windows.init()
        share_windows.show()

    def ShowLinkWindow(self):
        main_windows = CheckLinks(self)
        main_windows.token = self.token
        main_windows.init()
        main_windows.show()


class CheckLinks(QDialog, Ui_Dialog):
    def __init__(self, parent=None):
        super(QDialog, self).__init__(parent)
        self.setupUi(self)

    def init(self):
        self.library = Libraries(self.token)
        self.link_list = self.library.getSharedLinks()
        for link in self.link_list:
            item = QListWidgetItem()
            icon = QIcon()
            icon.addPixmap(QPixmap("./resource/link.png"), QIcon.Selected, QIcon.On)
            item.setIcon(icon)
            item.setText(link['repo_name'] + "/" + link['path'])
            item.setCheckState(Qt.Unchecked)
            self.listWidget.addItem(item)
        self.select_all.clicked.connect(self.check)
        self.deleteLinks.clicked.connect(self.deleteUploadLinks)

    def check(self):
        if self.select_all.isChecked():
            self.listWidget.selectAll()
            for i in range(self.listWidget.count()):
                self.listWidget.item(i).setCheckState(Qt.Checked)
        else:
            self.listWidget.clearSelection()
            for i in range(self.listWidget.count()):
                self.listWidget.item(i).setCheckState(Qt.Unchecked)

    def deleteUploadLinks(self):
        selectedCount = 0
        for i in range(self.listWidget.count()):
            item = self.listWidget.item(i)
            if item.checkState():
                selectedCount += 1
        if selectedCount == 0:
            QMessageBox.critical(self, "警告", "请选择要删除的链接", QMessageBox.Ok)
            return
        for i in range(self.listWidget.count()):
            item = self.listWidget.item(i)
            if item.checkState():
                self.library.deleteSharedLinks(self.link_list[i]['token'])
        QMessageBox.information(self, "完成", "删除成功", QMessageBox.Ok)
        self.destroy()


def create8BitPassword():
    src = string.ascii_letters + string.digits
    result = random.sample(src, 5)  # 从字母和数字中随机取5位
    result.extend(random.sample(string.digits, 1))  # 让密码中一定包含数字
    result.extend(random.sample(string.ascii_lowercase, 1))  # 让密码中一定包含小写字母
    result.extend(random.sample(string.ascii_uppercase, 1))  # 让密码中一定包含大写字母
    random.shuffle(result)  # 打乱列表顺序
    result = ''.join(result)  # 将列表转化为字符串
    return result


class ShareConfig(QDialog, ShareConf):
    def __init__(self, parent=None):
        super(QDialog, self).__init__(parent)
        self.setupUi(self)

    def init(self):
        self.generateLinksButton.clicked.connect(self.generateLinks)
        self.checkAndDownload.setChecked(True)
        self.checkAndDownload.clicked.connect(self.selectCheckBox)
        self.checkOnly.clicked.connect(self.selectCheckBox)
        self.downloadAndUpload.clicked.connect(self.selectCheckBox)
        self.Expiration.setMinimumDateTime(QDateTime.currentDateTime())
        self.Expiration.setCalendarPopup(True)
        self.Expiration.setDisplayFormat("yyyy-MM-dd HH:mm")

        self.can_edit = False
        self.can_download = False
        self.can_upload = False

    def selectCheckBox(self):
        # 预览与下载
        if self.checkAndDownload.isChecked():
            self.can_upload = False
            self.can_download = True
            return
        # 下载和上传
        if self.downloadAndUpload.isChecked():
            self.can_download = True
            self.can_upload = True
            return
        # 仅查看
        if self.checkOnly.isChecked():
            self.can_download = False
            self.can_upload = False

    def generateLinks(self):
        passwords = []
        for i in range(len(self.paths)):
            passwords.append(None)
        expiration_time = None
        if self.SetPassword.isChecked():
            passwords = self.getPasswords()

        if self.SetExpiration.isChecked():
            expiration_time = self.Expiration.text().replace(" ", "T") + ":00+08:00"

        permissions = {
            "can_edit": self.can_edit,
            "can_download": self.can_download,
            "can_upload": self.can_upload
        }

        with open("linksOfFolder.csv", "a+", encoding="utf-8") as f:
            f.write("文件名,共享连接，密码\n")
            for i in range(len(self.paths)):
                result = self.library.creatUploadLink(self.paths[i], permissions, password=passwords[i],
                                                      expiration_time=expiration_time)
                if result[0]:
                    content = result[1]["obj_name"] + "," + result[1]['link'] + ","
                    if passwords[i] is None:
                        content += "无 \n"
                    else:
                        content += passwords[i] + "\n"
                    f.write(content)
                else:
                    f.write(self.paths[i] + "," + result[1]['error_msg'] + "\n")
        QMessageBox.information(self, "注意", "请在linksOfFolder.csv中查看结果", QMessageBox.Ok)
        self.destroy()

    def getPasswords(self):
        result = []
        if self.samePassword.isChecked():
            password = self.password.text()
            if len(password) == 0:
                print("请输入密码")
                return
            for i in range(len(self.paths)):
                result.append(password)
        elif self.generatePassword.isChecked():
            while len(result) != len(self.paths):
                p = create8BitPassword()
                if p not in result:
                    result.append(p)
        return result


if __name__ == '__main__':
    app = QApplication(sys.argv)
    login = Login()
    # test = QWidget()
    # login.get_libraries()
    login.show()
    sys.exit(app.exec_())
