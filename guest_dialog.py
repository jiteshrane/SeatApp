from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QFormLayout,
    QLineEdit,
    QDialogButtonBox
)


class GuestDialog(QDialog):

    def __init__(self, guest=None, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Guest")

        layout = QVBoxLayout(self)

        form = QFormLayout()

        self.first_name = QLineEdit()
        self.last_name = QLineEdit()

        form.addRow("First Name:", self.first_name)
        form.addRow("Last Name:", self.last_name)

        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )

        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout.addWidget(buttons)

        # Editing an existing guest
        if guest is not None:
            self.first_name.setText(guest.first_name)
            self.last_name.setText(guest.last_name)