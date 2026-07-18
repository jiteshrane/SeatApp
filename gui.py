from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QListWidget,
    QGraphicsView,
    QHBoxLayout,
    QStatusBar,
    QFileDialog,
    QLabel,
    QSpinBox,
    QPushButton,
    QVBoxLayout,
    QListWidgetItem,
    QAbstractItemView
)
from PySide6.QtWidgets import QMessageBox
from PySide6.QtGui import QPainter, QDrag
from PySide6.QtCore import Qt, QMimeData

from graphics import RoomScene
from file_io import load_guest_list
from models import Guest
from guest_dialog import GuestDialog
import os
from PySide6.QtGui import QShortcut, QKeySequence
from PySide6.QtGui import QBrush, QColor

# =========================
# GUEST LIST WIDGET
# =========================
class GuestListWidget(QListWidget):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.guests = []

        self.setDragEnabled(True)
        self.setSelectionMode(QAbstractItemView.SingleSelection)

    def setGuests(self, guests):
        self.guests = guests

    def refreshGuests(self):

        self.clear()

        for guest in self.guests:
            if guest.seat is None:
                item = QListWidgetItem(guest.full_name)
                item.setData(Qt.UserRole, guest)
                self.addItem(item)

    def startDrag(self, supportedActions):

        item = self.currentItem()
        if item is None:
            return

        guest = item.data(Qt.UserRole)

        drag = QDrag(self)
        mime = QMimeData()

        mime.setText(guest.full_name)
        mime.setProperty("guest_obj", guest)

        drag.setMimeData(mime)
        drag.exec(Qt.MoveAction)


# =========================
# MAIN WINDOW
# =========================
class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("Wedding Seating Planner")

        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QHBoxLayout()
        central_widget.setLayout(layout)

        # -------------------------
        # WIDGETS
        # -------------------------
        self.guest_list = GuestListWidget()

        self.scene = RoomScene()
        self.scene.main_window = self
        self.scene.guest_list = self.guest_list

        self.view = QGraphicsView(self.scene)
        self.view.setRenderHint(QPainter.Antialiasing)

        # -------------------------
        # DATA
        # -------------------------
        # Default guests (fallback)
        self.guests = [
            Guest(0, "John", "Smith"),
            Guest(1, "Jane", "Smith"),
            Guest(2, "Emily", "Jones"),
            Guest(3, "Mike", "Brown")
        ]

        # Auto-load provided guest list if available
        if os.path.exists("guest_list.xlsx"):
            print("FOUND guest_list.xlsx - loading guest list")

            self.guests = load_guest_list("guest_list.xlsx")

        else:
            print("No guest_list.xlsx found - using default guests")

        self.selected_guest = None
        self.undo_stack = []

        self.scene.guests = self.guests

        # -------------------------
        # BIND
        # -------------------------
        self.guest_list.setGuests(self.guests)
        self.guest_list.refreshGuests()

        # -------------------------
        # LEFT PANEL
        # -------------------------
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)

        left_layout.addWidget(self.guest_list)

        # Guest buttons
        self.add_guest_btn = QPushButton("Add Guest")
        self.edit_guest_btn = QPushButton("Edit Guest")
        self.delete_guest_btn = QPushButton("Delete Guest")

        self.undo_btn = QPushButton("Undo")

        left_layout.addWidget(self.undo_btn)

        self.undo_btn.clicked.connect(self.undo)

        left_layout.addWidget(self.add_guest_btn)
        left_layout.addWidget(self.edit_guest_btn)
        left_layout.addWidget(self.delete_guest_btn)

        # Room setup controls
        left_layout.addWidget(QLabel("Room Setup"))

        # Tables
        left_layout.addWidget(QLabel("Round Tables"))
        self.num_tables_spin = QSpinBox()
        self.num_tables_spin.setRange(1, 100)
        self.num_tables_spin.setValue(2)
        left_layout.addWidget(self.num_tables_spin)

        # Seats per table
        left_layout.addWidget(QLabel("Seats per Table"))
        self.seats_per_table_spin = QSpinBox()
        self.seats_per_table_spin.setRange(2, 20)
        self.seats_per_table_spin.setValue(8)
        left_layout.addWidget(self.seats_per_table_spin)

        # Head table seats
        left_layout.addWidget(QLabel("Head Table Seats"))
        self.head_table_spin = QSpinBox()
        self.head_table_spin.setRange(2, 30)
        self.head_table_spin.setValue(8)
        left_layout.addWidget(self.head_table_spin)

        # Regenerate button (STEP 11)
        self.regen_btn = QPushButton("Regenerate Layout")
        self.regen_btn.clicked.connect(self.regenerate_layout)
        left_layout.addWidget(self.regen_btn)

        # -------------------------
        # RIGHT PANEL (scene)
        # -------------------------
        layout.addWidget(left_panel, 1)
        layout.addWidget(self.view, 3)

        # -------------------------
        # STATUS BAR
        # -------------------------
        self.setStatusBar(QStatusBar())
        self.statusBar().showMessage("Ready")

        # -------------------------
        # MENU
        # -------------------------
        file_menu = self.menuBar().addMenu("File")

        import_action = file_menu.addAction("Import Guest List")
        import_action.triggered.connect(self.import_guest_list)

        save_action = file_menu.addAction("Save Seating")
        save_action.triggered.connect(
            lambda: self.save_seating()
        )

        load_action = file_menu.addAction("Load Seating")
        load_action.triggered.connect(
            lambda: self.load_seating("seating.json")
        )

                # Auto-load previous session
        print("Looking for save file at:")
        print(os.path.abspath("last_seating.json"))

        if os.path.exists("seating.json"):

            print("AUTO LOADING SAVED FILE")
            self.load_seating("seating.json")

        elif os.path.exists("guest_list.xlsx"):

            print("FIRST RUN - LOADING GUEST LIST")

            self.auto_import_guest_list("guest_list.xlsx")

            self.scene.generate_layout(
                num_tables=12,
                seats_per_table=8,
                head_table_seats=16
            )

            self.save_seating()

        else:

            print("NO SAVED FILE FOUND")

        self.add_guest_btn.clicked.connect(self.add_guest)
        self.edit_guest_btn.clicked.connect(self.edit_guest)
        self.delete_guest_btn.clicked.connect(self.delete_guest)

        self.guest_list.itemSelectionChanged.connect(self.on_guest_selected)

        self.undo_shortcut = QShortcut(
            QKeySequence("Ctrl+Z"),
            self
        )

        self.undo_shortcut.activated.connect(self.undo)

        self.showMaximized()

    def autosave(self):

        self.save_seating()

        print("AUTOSAVED")

    def undo(self):

        if not self.undo_stack:
            self.statusBar().showMessage("Nothing to undo")
            return

        action = self.undo_stack.pop()

        if action["type"] == "move_guest":

            guest = action["guest"]
            old_seat = action["old_seat"]
            new_seat = action["new_seat"]

            # Clear current seat
            new_seat.guest = None
            new_seat.graphics.refresh()

            # Restore old seat
            if old_seat is not None:
                old_seat.guest = guest
                old_seat.graphics.refresh()
                guest.seat = old_seat

            else:
                guest.seat = None

            self.guest_list.refreshGuests()

        self.statusBar().showMessage("Undo complete")

    def on_guest_selected(self):

        item = self.guest_list.currentItem()

        if item is None:
            self.selected_guest = None
            return

        self.selected_guest = item.data(Qt.UserRole)

        print("SELECTED:", self.selected_guest.full_name)

    # =========================
    # STEP 11 FUNCTION
    # =========================
    def regenerate_layout(self):

        from PySide6.QtWidgets import QMessageBox

        reply = QMessageBox.question(
            self,
            "Regenerate Layout",
            "Regenerating the layout will remove current seating assignments.\n\nContinue?",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply != QMessageBox.Yes:
            return

        num_tables = self.num_tables_spin.value()
        seats = self.seats_per_table_spin.value()
        head_seats = self.head_table_spin.value()

        self.scene.generate_layout(
            num_tables=num_tables,
            seats_per_table=seats,
            head_table_seats=head_seats
        )

    # =========================
    # IMPORT GUESTS
    # =========================
    def import_guest_list(self):

        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Open Guest List",
            "",
            "Excel (*.xlsx *.xls);;CSV (*.csv)"
        )

        if not filename:
            return

        self.guests = load_guest_list(filename)

        self.scene.guests = self.guests

        self.guest_list.setGuests(self.guests)
        self.guest_list.refreshGuests()

        self.statusBar().showMessage(f"Loaded {len(self.guests)} guests")

    def auto_import_guest_list(self, filename="guest_list.xlsx"):

        if not os.path.exists(filename):
            return False

        print("AUTO LOADING GUEST LIST:", filename)

        self.guests = load_guest_list(filename)

        self.scene.guests = self.guests

        self.guest_list.setGuests(self.guests)
        self.guest_list.refreshGuests()

        print(f"Loaded {len(self.guests)} guests")

        return True

    # =========================
    # SAVE (unchanged)
    # =========================
    def save_seating(self, checked=False, filename="last_seating.json"):

        filename = "seating.json"

        import json

        data = {
            "guests": [],
            "layout": {
                "round_tables": self.num_tables_spin.value(),
                "seats_per_table": self.seats_per_table_spin.value(),
                "head_table_seats": self.head_table_spin.value()
            },
            "tables": []
        }

        for table in self.scene.tables:

            table_data = {
            "name": table.name,
            "x": table.graphics.pos().x(),
            "y": table.graphics.pos().y(),
            "seats": []
            }

            for seat in table.seats:

                table_data["seats"].append({
                    "number": seat.number,
                    "guest_id": seat.guest.id if seat.guest else None
                })

            data["tables"].append(table_data)

        for guest in self.guests:
            data["guests"].append({
                "id": guest.id,
                "first_name": guest.first_name,
                "last_name": guest.last_name
            })

        with open(filename, "w") as f:
            json.dump(data, f, indent=4)

        # =========================
        # LOAD (unchanged)
        # =========================

    def load_seating(self, filename="seating.json"):

        import json

        with open(filename, "r") as f:
            data = json.load(f)

        print("LOADING SEATING")

        # -------------------------
        # Restore GUI layout values
        # -------------------------

        self.num_tables_spin.setValue(
            data["layout"]["round_tables"]
        )

        self.seats_per_table_spin.setValue(
            data["layout"]["seats_per_table"]
        )

        self.head_table_spin.setValue(
            data["layout"]["head_table_seats"]
        )

        print(
            "SAVED HEAD SEATS:",
            data["layout"]["head_table_seats"]
        )


        # -------------------------
        # Restore guests
        # -------------------------

        self.guests = []

        for g in data["guests"]:

            guest = Guest(
                g["id"],
                g["first_name"],
                g["last_name"]
            )

            self.guests.append(guest)

        self.guest_list.setGuests(self.guests)


        # -------------------------
        # Rebuild layout
        # -------------------------

        self.scene.generate_layout(
            num_tables=data["layout"]["round_tables"],
            seats_per_table=data["layout"]["seats_per_table"],
            head_table_seats=data["layout"]["head_table_seats"]
        )


        # -------------------------
        # Restore tables
        # -------------------------

        for saved_table in data["tables"]:

            matching_table = None

            for table in self.scene.tables:

                if table.name == saved_table["name"]:
                    matching_table = table
                    break


            if matching_table is None:
                print(
                    "TABLE NOT FOUND:",
                    saved_table["name"]
                )
                continue


            # Restore table position

            if hasattr(matching_table, "graphics"):

                matching_table.graphics.setPos(
                    saved_table.get("x", 0),
                    saved_table.get("y", 0)
                )


            # -------------------------
            # Restore seats
            # -------------------------

            for saved_seat in saved_table["seats"]:

                guest_id = saved_seat["guest_id"]

                if guest_id is None:
                    continue


                seat_index = saved_seat["number"] - 1


                if seat_index >= len(matching_table.seats):

                    print(
                        "Skipping invalid seat:",
                        matching_table.name,
                        saved_seat["number"]
                    )

                    continue


                # Find guest

                guest = None

                for g in self.guests:

                    if g.id == guest_id:
                        guest = g
                        break


                if guest is None:
                    print(
                        "Guest not found:",
                        guest_id
                    )
                    continue


                # Assign seat

                seat = matching_table.seats[seat_index]

                seat.guest = guest
                guest.seat = seat


                print(
                    "RESTORED:",
                    guest.full_name,
                    "to",
                    matching_table.name,
                    "seat",
                    seat.number
                )


                # Refresh graphics

                if seat.graphics is not None:

                    print("REFRESHING:", guest.full_name)

                    seat.graphics.refresh()

                else:

                    print(
                        "WARNING: Missing graphics for",
                        matching_table.name,
                        seat.number
                    )


        # -------------------------
        # Refresh UI
        # -------------------------

        self.guest_list.refreshGuests()

        self.scene.update()
        self.view.viewport().update()


        # Final verification

        for table in self.scene.tables:

            for seat in table.seats:

                if seat.guest is not None:

                    print(
                        "FINAL CHECK:",
                        table.name,
                        seat.number,
                        seat.guest.full_name
                    )


        from PySide6.QtCore import QTimer

        QTimer.singleShot(
            100,
            lambda: self.scene.update()
        )

        print("LOAD COMPLETE")


    def add_guest(self):

        dialog = GuestDialog(parent=self)

        if dialog.exec():

            # Generate next available ID
            next_id = 0

            if self.guests:
                next_id = max(g.id for g in self.guests) + 1

            guest = Guest(
                next_id,
                dialog.first_name.text().strip(),
                dialog.last_name.text().strip()
            )

            self.guests.append(guest)

            self.guest_list.refreshGuests()
            self.autosave()

            self.statusBar().showMessage(
                f"Added {guest.full_name}"
            )


    def edit_guest(self):

        guest = self.selected_guest

        if guest is None:
            self.statusBar().showMessage("Select a guest first.")
            return

        dialog = GuestDialog(guest, self)

        if dialog.exec():

            guest.first_name = dialog.first_name.text().strip()
            guest.last_name = dialog.last_name.text().strip()

            self.guest_list.refreshGuests()

            # Refresh seats
            for table in self.scene.tables:
                for seat in table.seats:
                    if seat.guest == guest:
                        seat.graphics.refresh()

            self.statusBar().showMessage(f"Updated {guest.full_name}")
            self.autosave()


    def delete_guest(self):

        guest = self.selected_guest

        if guest is None:
            self.statusBar().showMessage("Select a guest first.")
            return

        reply = QMessageBox.question(
            self,
            "Delete Guest",
            f"Are you sure you want to delete {guest.full_name}?",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply != QMessageBox.Yes:
            return

        # Unseat if necessary
        if guest.seat is not None:
            guest.seat.graphics.unseat()

        self.guests.remove(guest)

        self.selected_guest = None

        self.guest_list.refreshGuests()

        self.statusBar().showMessage(
            f"Deleted {guest.full_name}"
        )
        self.autosave()