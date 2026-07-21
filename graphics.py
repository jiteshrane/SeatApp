import math

from PySide6.QtCore import Qt, QMimeData
from PySide6.QtGui import QDrag
from PySide6.QtGui import QBrush, QColor, QPen
from PySide6.QtWidgets import (
    QGraphicsScene,
    QGraphicsItem,
    QGraphicsEllipseItem,
    QGraphicsRectItem,
    QGraphicsTextItem
)
from models import Table
from PySide6.QtCore import QTimer
# =========================
# SEAT ITEM
# =========================
class SeatItem(QGraphicsEllipseItem):

    def __init__(self, seat_model, x, y, radius=10):
        super().__init__(-radius, -radius, radius * 2, radius * 2)

        self.model = seat_model
        self.model.graphics = self
        self.setPos(x, y)

        self.setBrush(QBrush(QColor(220, 220, 220)))
        self.setPen(QPen(Qt.black, 1))

        self.setAcceptDrops(True)
        self.setAcceptedMouseButtons(Qt.LeftButton)
        self.setAcceptHoverEvents(True)
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)

        self.text = QGraphicsTextItem("", self)
        rect = self.text.boundingRect()
        self.text.setPos(
            -rect.width() / 2,
            -25
        )
        self.text.setZValue(20)
        self.setFlag(QGraphicsItem.ItemIsMovable, False)
        self.drag_start_position = None

    def mousePressEvent(self, event):

        scene = self.scene()

        if self.model.guest is not None and hasattr(scene, "main_window"):

            mw = scene.main_window

            mw.selected_guest = self.model.guest

            # Highlight guest in the list if present
            for i in range(mw.guest_list.count()):

                item = mw.guest_list.item(i)

                if item.data(Qt.UserRole) == self.model.guest:
                    mw.guest_list.setCurrentItem(item)
                    break

            print("SELECTED FROM SEAT:", self.model.guest.full_name)

    def refresh(self):

        if self.model.guest is None:

            self.setBrush(QBrush(QColor(220, 220, 220)))
            self.text.setPlainText("")
            self.setToolTip("")

        else:

            self.setBrush(QBrush(QColor(144, 238, 144)))
            self.text.setPlainText(self.model.guest.short_name)
            self.setToolTip(self.model.guest.full_name)
        

        self.text.update()
        self.update()

        if self.scene():
            self.scene().update()

    def dragEnterEvent(self, event):
        if event.mimeData().hasText():
            event.acceptProposedAction()
        else:
            event.ignore()
        print("DRAG ENTER SEAT")
        event.acceptProposedAction()


    def dragMoveEvent(self, event):
        if event.mimeData().hasText():
            event.acceptProposedAction()
        else:
            event.ignore()
        print("DRAG MOVE SEAT")

    def dropEvent(self, event):

        guest = event.mimeData().property("guest_obj")
        print("DROP :", guest.full_name if guest else None, id(guest) if guest else None)

        if guest is None:
            name = event.mimeData().text()
            scene = self.scene()

            for g in scene.guests:
                if g.full_name == name:
                    guest = g
                    break

        if guest is None:
            return

        seat = self.model

        # -----------------------------
        # 1. If guest already seated → clear old seat
        # -----------------------------
        if guest.seat is not None:
            old_seat = guest.seat
            old_seat.guest = None
            old_seat.graphics.refresh()

        # -----------------------------
        # 2. If this seat already occupied → unseat previous guest
        # -----------------------------
        if seat.guest is not None:
            old_guest = seat.guest
            old_guest.seat = None
            seat.guest = None

            self.refresh()
            scene = self.scene()

            if hasattr(scene, "main_window"):
                scene.main_window.autosave()



        # -----------------------------
        # 3. Save undo state
        # -----------------------------

        scene = self.scene()

        if hasattr(scene, "main_window"):

            scene.main_window.undo_stack.append({
                "type": "move_guest",
                "guest": guest,
                "old_seat": guest.seat,
                "new_seat": seat
            })


        # -----------------------------
        # 4. Assign new relationship
        # -----------------------------

        seat.guest = guest
        guest.seat = seat

        self.refresh()

        print("SEAT STATE:", seat.guest.full_name if seat.guest else None)
        print("MODEL STATE:", self.model.guest.full_name if self.model.guest else None)
        # -----------------------------
        # 4. Update visuals
        # -----------------------------

        scene = self.scene()

        scene = self.scene()

        if hasattr(scene, "guest_list"):
            scene.guest_list.refreshGuests()

        # Autosave after EVERY successful move
        if hasattr(scene, "main_window"):
            print("CALLING AUTOSAVE")
            scene.main_window.autosave()

        event.accept()

    def unseat(self):

        if self.model.guest is None:
            return

        guest = self.model.guest

        self.model.guest = None
        guest.seat = None

        self.refresh()

        scene = self.scene()
        if hasattr(scene, "guest_list"):
            scene.guest_list.refreshGuests()

    def mouseDoubleClickEvent(self, event):

        self.unseat()

        event.accept()

    def dragEnterEvent(self, event):
        print("DRAG ENTER SEAT (confirmed SeatItem)")
        event.acceptProposedAction()

    def mouseMoveEvent(self, event):

        if self.model.guest is None:
            return

        scene = self.scene()

        if scene is None or not scene.views():
            return

        drag = QDrag(scene.views()[0])

        mime = QMimeData()

        mime.setText(self.model.guest.full_name)
        mime.setProperty("guest_obj", self.model.guest)

        drag.setMimeData(mime)

        drag.exec(Qt.MoveAction)



# =========================
# ROUND TABLE
# =========================
class RoundTableItem(QGraphicsItem):

    def __init__(self, table_model, x, y):
        super().__init__()

        self.model = table_model
        self.model.graphics = self

        self.name = table_model.name
        self.seats = len(table_model.seats)

        self.setPos(x, y)

        self.setFlag(QGraphicsItem.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)

        self.setZValue(10)

        # Table body
        self.table = QGraphicsEllipseItem(-50, -50, 100, 100, self)
        self.table.setBrush(QBrush(QColor("white")))
        self.table.setPen(QPen(Qt.black, 2))

        # Label
        self.label = QGraphicsTextItem(self.name, self)
        self.label.setPos(-25, -10)

        self.seat_items = []
        self.draw_seats()

    def draw_seats(self):

        radius = 80
        seat_radius = 10

        for i in range(self.seats):

            angle = 2 * math.pi * i / self.seats

            x = radius * math.cos(angle)
            y = radius * math.sin(angle)

            seat_model = self.model.seats[i]

            seat = SeatItem(seat_model, x, y, seat_radius)
            seat.setParentItem(self)
            seat.setParentItem(self)

            self.seat_items.append(seat)

    def boundingRect(self):
        return self.childrenBoundingRect()

    def paint(self, painter, option, widget):
        pass


# =========================
# HEAD TABLE
# =========================
# =========================
# HEAD TABLE
# =========================
class HeadTableItem(QGraphicsItem):

    def __init__(self, table_model, x, y):
        super().__init__()

        self.model = table_model
        self.model.graphics = self

        self.setPos(x, y)

        self.setFlag(QGraphicsItem.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)

        # Table body
        self.table = QGraphicsRectItem(-150, -30, 300, 60, self)
        self.table.setBrush(QBrush(QColor(245, 245, 245)))
        self.table.setPen(QPen(Qt.black, 2))

        # Label
        self.label = QGraphicsTextItem("Head Table", self)
        self.label.setPos(-45, -10)

        # Create seats
        self.seat_items = []
        self.draw_seats()

    def draw_seats(self):

        spacing = 35
        total_seats = len(self.model.seats)

        # Split seats between front and back
        front_count = total_seats // 2
        back_count = total_seats - front_count

        seat_index = 0

        # Front side
        for i in range(front_count):

            x = (i - (front_count - 1) / 2) * spacing
            y = 55

            seat = SeatItem(
                self.model.seats[seat_index],
                x,
                y,
                10
            )

            seat.setParentItem(self)
            self.seat_items.append(seat)

            seat_index += 1


        # Back side
        for i in range(back_count):

            x = (i - (back_count - 1) / 2) * spacing
            y = -55

            seat = SeatItem(
                self.model.seats[seat_index],
                x,
                y,
                10
            )

            seat.setParentItem(self)
            self.seat_items.append(seat)

            seat_index += 1

    def boundingRect(self):
        return self.childrenBoundingRect()

    def paint(self, painter, option, widget):
        pass


# =========================
# SCENE
# =========================
class RoomScene(QGraphicsScene):

    def __init__(self):
        super().__init__()

        self.tables = []

        self.setSceneRect(0, 0, 1000, 700)

        self.draw_grid()

        self.guests = []

        self.generate_layout(
        num_tables=2,
        seats_per_table=8,
        head_table_seats=8
)

    def draw_grid(self):

        pen = QPen(QColor(225, 225, 225))
        spacing = 50

        for x in range(0, 2001, spacing):
            self.addLine(x, 0, x, 1500, pen)

        for y in range(0, 1501, spacing):
            self.addLine(0, y, 2000, y, pen)

    def generate_layout(self, num_tables, seats_per_table, head_table_seats):

        print(f"Generating: {num_tables} tables, {seats_per_table} seats/table, {head_table_seats} head seats")

        # Clear scene + reset model
        self.clear()
        self.tables = []

        # -------------------------
        # HEAD TABLE
        # -------------------------
        head = Table(
            "Head Table 1",
            head_table_seats,
            "head"
        )
        self.tables.append(head)

        # Match the round-table layout
        cols = min(4, num_tables)
        spacing_x = 260

        # Center of the round-table grid
        left_edge = 150
        right_edge = left_edge + (cols - 1) * spacing_x

        head_x = (left_edge + right_edge) / 2
        head_y = 100

        self.addItem(HeadTableItem(head, head_x, head_y))

        # -------------------------
        # ROUND TABLES
        # -------------------------
        cols = min(4, num_tables)
        spacing_x = 260
        spacing_y = 220

        for i in range(num_tables):

            table = Table(f"Table {i+1}", seats_per_table)
            self.tables.append(table)

            col = i % cols
            row = i // cols

            x = 150 + col * spacing_x
            y = 290 + row * spacing_y

            table_item = RoundTableItem(table, x, y)
            self.addItem(table_item)

        rect = self.itemsBoundingRect()

        rect = self.itemsBoundingRect().adjusted(-100, -100, 100, 100)

        self.setSceneRect(rect)

        for view in self.views():
            view.setSceneRect(rect)
