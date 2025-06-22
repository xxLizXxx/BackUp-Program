import sys
import os
import shutil
import datetime
import subprocess
from PyQt5 import QtWidgets, QtCore, QtGui

GLOBAL_STYLE = """
QWidget {
    background-color: #f0f0f0;
    font-family: "Microsoft YaHei", sans-serif;
    font-size: 12pt;
}

QPushButton {
    background-color: #4CAF50;
    color: white;
    border: none;
    border-radius: 5px;
    padding: 5px 10px;
}

QPushButton:hover {
    background-color: #45a049;
}

QLineEdit, QSpinBox {
    border: 1px solid #ccc;
    border-radius: 3px;
    padding: 3px;
    background-color: white;
}

QLabel {
    color: #333;
}
"""
class ConfirmCheckBox(QtWidgets.QCheckBox):
   
    def mousePressEvent(self, event):
        if not self.isChecked():
            msg = QtWidgets.QMessageBox(self)
            msg.setWindowTitle("确认覆盖备份")
            msg.setText("您已选择覆盖备份，备份将会覆盖目标位置已有文件，<span style='color:red; font-weight:bold;'>您的原文件可能会丢失</span>，是否确认？")
            msg.setIcon(QtWidgets.QMessageBox.Warning)
            msg.setStandardButtons(QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
            ret = msg.exec_()
            if ret == QtWidgets.QMessageBox.Yes:
                self.setChecked(True)
            event.accept()
        else:
            super().mousePressEvent(event)

class AutoBackupDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super(AutoBackupDialog, self).__init__(parent)
        self.setWindowTitle("设定自动保存间隔")
        layout = QtWidgets.QVBoxLayout(self)

        label = QtWidgets.QLabel("请选择自动保存间隔时间（10～300分钟）：")
        layout.addWidget(label)

        self.spinBox = QtWidgets.QSpinBox(self)
        self.spinBox.setMinimum(10)
        self.spinBox.setMaximum(300) 
        self.spinBox.setValue(10)
        layout.addWidget(self.spinBox)

        buttonBox = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        buttonBox.accepted.connect(self.accept)
        buttonBox.rejected.connect(self.reject)
        layout.addWidget(buttonBox)

    def getInterval(self):
        return self.spinBox.value()

class BackupApp(QtWidgets.QWidget):
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("LZ-backup")
        self.resize(600, 320)

        self.setStyleSheet(GLOBAL_STYLE)

        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.auto_backup)

        sourceLabel = QtWidgets.QLabel("需要备份的文件或文件夹:")
        self.sourceLineEdit = QtWidgets.QLineEdit()

        fileButton = QtWidgets.QPushButton("选择文件")
        fileButton.clicked.connect(self.choose_file)

        folderButton = QtWidgets.QPushButton("选择文件夹")
        folderButton.clicked.connect(self.choose_folder)

        sourceLayout = QtWidgets.QHBoxLayout()
        sourceLayout.addWidget(self.sourceLineEdit)
        sourceLayout.addWidget(fileButton)
        sourceLayout.addWidget(folderButton)

        backupPathLabel = QtWidgets.QLabel("备份路径:")
        self.backupPathLineEdit = QtWidgets.QLineEdit("C:\\LZbackup\\")
        backupPathButton = QtWidgets.QPushButton("浏览")
        backupPathButton.clicked.connect(self.choose_backup_path)
        backupPathLayout = QtWidgets.QHBoxLayout()
        backupPathLayout.addWidget(self.backupPathLineEdit)
        backupPathLayout.addWidget(backupPathButton)

        self.autoButton = QtWidgets.QPushButton("设定自动保存")
        self.autoButton.clicked.connect(self.set_auto_backup)
        self.manualButton = QtWidgets.QPushButton("手动保存")
        self.manualButton.clicked.connect(self.manual_backup)
        buttonLayout = QtWidgets.QHBoxLayout()
        buttonLayout.addWidget(self.autoButton)
        buttonLayout.addWidget(self.manualButton)

        self.logButton = QtWidgets.QPushButton("打开日志文件")
        self.logButton.clicked.connect(self.open_log_file)


        self.overwriteCheckbox = ConfirmCheckBox("保存时覆盖原文件")
        self.overwriteCheckbox.setChecked(False)

        mainLayout = QtWidgets.QVBoxLayout(self)
        mainLayout.addWidget(sourceLabel)
        mainLayout.addLayout(sourceLayout)
        mainLayout.addWidget(backupPathLabel)
        mainLayout.addLayout(backupPathLayout)
        mainLayout.addLayout(buttonLayout)
        mainLayout.addWidget(self.overwriteCheckbox)
        mainLayout.addWidget(self.logButton)

        self.check_and_create_backup_path()
        self.init_log_file()

    def init_log_file(self):
        log_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lzbackup.log")
        if not os.path.exists(log_file):
            try:
                with open(log_file, "w", encoding="utf-8") as f:
                    f.write("")
            except Exception as e:
                QtWidgets.QMessageBox.warning(self, "日志文件错误", f"无法创建日志文件：{e}")

    def choose_file(self):
        filePath, _ = QtWidgets.QFileDialog.getOpenFileName(self, "选择文件", "", "所有文件 (*)")
        if filePath:
            self.sourceLineEdit.setText(filePath)

    def choose_folder(self):
        dirPath = QtWidgets.QFileDialog.getExistingDirectory(self, "选择文件夹", "")
        if dirPath:
            self.sourceLineEdit.setText(dirPath)

    def choose_backup_path(self):
        options = QtWidgets.QFileDialog.Options()
        options |= QtWidgets.QFileDialog.ShowDirsOnly
        path = QtWidgets.QFileDialog.getExistingDirectory(self, "选择备份路径", self.backupPathLineEdit.text(), options=options)
        if path:
            self.backupPathLineEdit.setText(path)
            self.check_and_create_backup_path()

    def check_and_create_backup_path(self):
        path = self.backupPathLineEdit.text()
        if not os.path.exists(path):
            try:
                os.makedirs(path)
            except Exception as e:
                QtWidgets.QMessageBox.warning(self, "错误", f"无法创建备份路径: {path}\n错误: {e}")

    def set_auto_backup(self):
        dialog = AutoBackupDialog(self)
        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            interval_minutes = dialog.getInterval()
            interval_ms = interval_minutes * 60 * 1000
            self.timer.start(interval_ms)
            QtWidgets.QMessageBox.information(self, "自动保存", f"已设置自动保存，间隔 {interval_minutes} 分钟")
        else:
            return

    def manual_backup(self):
        if not self.overwriteCheckbox.isChecked():
            ret = QtWidgets.QMessageBox.question(self, "确认备份",
                                                 "确定要进行备份吗？",
                                                 QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
            if ret != QtWidgets.QMessageBox.Yes:
                return
        self.perform_backup()

    def auto_backup(self):
        self.perform_backup(auto=True)

    def perform_backup(self, auto=False):

        source = self.sourceLineEdit.text().strip()
        backup_dir = self.backupPathLineEdit.text().strip()
        if not source or not os.path.exists(source):
            if not auto:
                QtWidgets.QMessageBox.warning(self, "错误", "请选择正确的备份文件或文件夹")
            return

        self.check_and_create_backup_path()

        overwrite = self.overwriteCheckbox.isChecked()
        basename = os.path.basename(source)
        if not overwrite:
            # 生成时间戳
            timestamp = datetime.datetime.now().strftime("%Y%m%d-%H-%M-%S")
            if os.path.isfile(source):
                name, ext = os.path.splitext(basename)
                new_name = f"{name}-{timestamp}{ext}"
                target = os.path.join(backup_dir, new_name)
            else:
                new_name = f"{basename}-{timestamp}"
                target = os.path.join(backup_dir, new_name)
        else:
            target = os.path.join(backup_dir, basename)

        try:
            if os.path.isfile(source):
                shutil.copy2(source, target)
            else:
                if os.path.exists(target) and overwrite:
                    shutil.rmtree(target)
                    shutil.copytree(source, target)
                else:
                    shutil.copytree(source, target)
            
            size = self.get_size(target)
            size_str = self.format_size(size)
            time_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            backup_mode = "自动保存" if auto else "手动保存"
            log_line = f"[{time_str}] {source} -> {target} | {backup_mode} | {size_str}\n"
            self.write_log(log_line)
            
            if not auto:
                QtWidgets.QMessageBox.information(self, "成功", f"备份成功，已保存到：\n{target}")
        except Exception as e:
            if not auto:
                QtWidgets.QMessageBox.warning(self, "错误", f"备份失败：\n{e}")

    def write_log(self, log_line):
        log_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lzbackup.log")
        try:
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(log_line)
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, "日志写入错误", f"写入日志文件失败：{e}")

    def get_size(self, path):
        total_size = 0
        if os.path.isfile(path):
            total_size = os.path.getsize(path)
        else:
            for dirpath, _, filenames in os.walk(path):
                for f in filenames:
                    fp = os.path.join(dirpath, f)
                    if os.path.exists(fp):
                        total_size += os.path.getsize(fp)
        return total_size

    def format_size(self, size):
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024:
                return f"{size:.2f} {unit}"
            size /= 1024
        return f"{size:.2f} TB"

    def open_log_file(self):
        log_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lzbackup.log")
        if not os.path.exists(log_file):
            QtWidgets.QMessageBox.information(self, "日志文件", "日志文件不存在！")
            return

        try:
            if sys.platform.startswith("win"):
                os.startfile(log_file)
            elif sys.platform.startswith("darwin"):
                subprocess.call(["open", log_file])
            else:
                subprocess.call(["xdg-open", log_file])
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, "错误", f"无法打开日志文件：{e}")

if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    window = BackupApp()
    window.show()
    sys.exit(app.exec_())
