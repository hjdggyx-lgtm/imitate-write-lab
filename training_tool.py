from writing_train_ui import WritingTrainWindow
from PyQt6.QtWidgets import QApplication
import sys

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = WritingTrainWindow()
    win.show()
    sys.exit(app.exec())