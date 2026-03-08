import sys
from PyQt5.QtWidgets import QApplication
from pet_entity import FoxPet

if __name__ == '__main__':
    app = QApplication(sys.argv)
    pet = FoxPet()
    sys.exit(app.exec_())