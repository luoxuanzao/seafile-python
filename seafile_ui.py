from PyQt5.QtWidgets import QWidget, QApplication, QMessageBox, QMainWindow, \
    QListWidgetItem, QFileDialog
from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtCore import QSize, Qt
from Ui_Login import Ui_Form
from conf import config
from Ui_MainWindows import Ui_MainWindow
import sys
import requests
from urllib.parse import urlencode
import urllib
import json
import traceback
import os
from seafile import Libraries

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
        self.pushButton.clicked.connect(self.getUploadLinks)
        self.uploadFolderButton.clicked.connect(self.creatFolder)
        self.search_input.returnPressed.connect(self.search)

    def check(self):
        if self.select_all.isChecked():
            self.listWidget.selectAll()
            for i in range(self.listWidget.count()):
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
        # print(self.library.history)
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
        if self.library.repo_id == None:
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

    def search(self):
        q = self.search_input.text()
        if self.library.repo_id is None:
            QMessageBox.critical(self, "警告", "请先指定资料库", QMessageBox.Ok)
            return
        items = self.library.search(q)
        item_list = []
        self.library.history.append(self.library.current)
        self.library.path_history.append(self.library.path)
        self.library.current = self.library.tree.create_node(tag=q, parent=self.library.current)
        for item in items['data']:
            item['name'] = item['path'].split('/')[-1]
            item_list.append(item)
        self.update_list(item_list)

    def creatFolder(self):
        if self.library.repo_id is None:
            QMessageBox.critical(self, "警告", "请先指定资料库", QMessageBox.Ok)
            return
        csvName, fileType = QFileDialog.getOpenFileName(self, "打开图片", "", "*.csv;;*.txt")

        basePath = self.url_path.text()

        with open(csvName, 'r', encoding="utf-8") as f:
            for line in f:
                folderName = line.replace("\n", "")
                self.library.creatDirectory(basePath + folderName)

    def getUploadLinks(self):
        if self.library.repo_id is None:
            QMessageBox.critical(self, "警告", "请先指定资料库", QMessageBox.Ok)
            return
        result = []
        basePath = self.url_path.text()
        for i in range(self.listWidget.count()):
            item = self.listWidget.item(i)
            if item.checkState():
                item.setCheckState(Qt.Unchecked)
                if self.item_list[i]['type'] in ['dir', 'folder']:
                    link = self.library.creatUploadLink(basePath + item.text())
                    storeNode = {"link": link, "folderName": item.text()}
                    result.append(storeNode)
        if len(result) > 0:
            with open("linksOfFolder.csv", "a+") as f:
                for i in range(len(result)):
                    f.write(result[i]['link'] + "," + result[i]["folderName"] + "\n")

        self.select_all.setChecked(False)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    login = Login()
    # test = QWidget()
    # login.get_libraries()
    login.show()
    sys.exit(app.exec_())
