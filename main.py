import sys
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QLineEdit, QHeaderView, QMessageBox, QGroupBox,
    QFormLayout, QFileDialog, QTextEdit
)
from PyQt6.QtCore import Qt
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.utils import simpleSplit
import datetime

TAX_RATE = 0.13

MATERIAL_TYPES = ["PT 5/4", "CEDAR 5/4", "PT 2x6", "CEDAR 2x6", "PVC/Comp"]

class JustDeckITQuotes(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Just Deck IT - Quotes")
        self.resize(1200, 700)

        layout = QVBoxLayout(self)

        # Customer info
        customer_group = QGroupBox("Customer Information")
        customer_form = QFormLayout()
        self.customer_name = QLineEdit()
        self.customer_address = QLineEdit()
        self.customer_phone = QLineEdit()
        self.customer_email = QLineEdit()
        customer_form.addRow("Name:", self.customer_name)
        customer_form.addRow("Address:", self.customer_address)
        customer_form.addRow("Phone:", self.customer_phone)
        customer_form.addRow("Email:", self.customer_email)
        customer_group.setLayout(customer_form)
        layout.addWidget(customer_group)

        # Add item inputs (Description, Area, rates for each material type)
        input_layout = QHBoxLayout()
        self.desc_input = QLineEdit()
        self.desc_input.setPlaceholderText("Description")
        self.area_input = QLineEdit()
        self.area_input.setPlaceholderText("Area")

        input_layout.addWidget(self.desc_input)
        input_layout.addWidget(self.area_input)

        self.rate_inputs = []
        for mt in MATERIAL_TYPES:
            inp = QLineEdit()
            inp.setPlaceholderText(f"Rate {mt}")
            inp.setFixedWidth(70)
            input_layout.addWidget(inp)
            self.rate_inputs.append(inp)

            cost_label = QLabel(f"Cost {mt}")
            cost_label.setFixedWidth(80)
            input_layout.addWidget(cost_label)

        self.add_btn = QPushButton("Add Item")
        self.add_btn.clicked.connect(self.add_item)
        input_layout.addWidget(self.add_btn)

        layout.addLayout(input_layout)

        # Table
        self.table = QTableWidget(0, 2 + len(MATERIAL_TYPES)*2)
        headers = ["Description", "Area"]
        for mt in MATERIAL_TYPES:
            headers.append(mt)
            headers.append("Cost to Client")
        self.table.setHorizontalHeaderLabels(headers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.itemChanged.connect(self.item_changed)
        layout.addWidget(self.table)

        # Summary labels
        self.summary_layout = QHBoxLayout()
        layout.addLayout(self.summary_layout)
        self.subtotal_labels = []
        self.hst_labels = []
        self.total_labels = []

        self.summary_layout.addSpacing(300)

        for _ in MATERIAL_TYPES:
            vbox = QVBoxLayout()
            st = QLabel("Subtotal: $0.00")
            hs = QLabel(f"HST ({int(TAX_RATE*100)}%): $0.00")
            tt = QLabel("Total: $0.00")
            vbox.addWidget(st)
            vbox.addWidget(hs)
            vbox.addWidget(tt)
            self.summary_layout.addLayout(vbox)
            self.subtotal_labels.append(st)
            self.hst_labels.append(hs)
            self.total_labels.append(tt)

        # Notes section
        notes_group = QGroupBox("Notes & Scope (Optional)")
        notes_layout = QVBoxLayout()
        self.notes_text = QTextEdit()
        notes_layout.addWidget(self.notes_text)
        notes_group.setLayout(notes_layout)
        layout.addWidget(notes_group)

        # Save button
        self.save_btn = QPushButton("Save Quote & Generate PDF")
        self.save_btn.clicked.connect(self.save_quote)
        layout.addWidget(self.save_btn)

    def add_item(self):
        desc = self.desc_input.text().strip()
        if not desc:
            QMessageBox.warning(self, "Invalid Input", "Description is required.")
            return

        try:
            area = float(self.area_input.text())
        except ValueError:
            QMessageBox.warning(self, "Invalid Input", "Area must be a number.")
            return

        rates = []
        for inp in self.rate_inputs:
            try:
                r = float(inp.text())
            except ValueError:
                r = 0.0
            rates.append(r)

        self.table.blockSignals(True)

        row = self.table.rowCount()
        self.table.insertRow(row)

        self.table.setItem(row, 0, QTableWidgetItem(desc))
        self.table.setItem(row, 1, QTableWidgetItem(f"{area:.2f}"))

        for i, rate in enumerate(rates):
            rate_col = 2 + i*2
            cost_col = rate_col + 1

            rate_item = QTableWidgetItem(f"{rate:.2f}")
            rate_item.setFlags(Qt.ItemFlag.ItemIsEditable | Qt.ItemFlag.ItemIsEnabled)
            self.table.setItem(row, rate_col, rate_item)

            cost = area * rate
            cost_item = QTableWidgetItem(f"{cost:.2f}")
            cost_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
            self.table.setItem(row, cost_col, cost_item)

        self.table.blockSignals(False)

        self.desc_input.clear()
        self.area_input.clear()
        for inp in self.rate_inputs:
            inp.clear()

        self.update_summary()

    def item_changed(self, item):
        row = item.row()
        col = item.column()

        # Check if the change was in a rate column (2, 4, 6, ...)
        if col > 1 and col % 2 == 0:
            try:
                new_rate = float(item.text())
                area = float(self.table.item(row, 1).text())
                new_cost = area * new_rate

                # Update the cost item in the next column
                self.table.item(row, col + 1).setText(f"{new_cost:.2f}")

                # Update summary totals
                self.update_summary()
            except (ValueError, AttributeError):
                # Occurs if item text is not a valid float, or if an item is None.
                pass

    def update_summary(self):
        subtotals = [0.0]*len(MATERIAL_TYPES)
        for row in range(self.table.rowCount()):
            for i in range(len(MATERIAL_TYPES)):
                cost_col = 3 + i*2
                item = self.table.item(row, cost_col)
                if item:
                    try:
                        subtotals[i] += float(item.text())
                except ValueError:
                    # Item text is not a valid float, so we skip it.
                    pass

        for i, subtotal in enumerate(subtotals):
            hst = subtotal * TAX_RATE
            total = subtotal + hst
            self.subtotal_labels[i].setText(f"Subtotal: ${subtotal:.2f}")
            self.hst_labels[i].setText(f"HST ({int(TAX_RATE*100)}%): ${hst:.2f}")
            self.total_labels[i].setText(f"Total: ${total:.2f}")

    def save_quote(self):
        if self.table.rowCount() == 0:
            QMessageBox.warning(self, "No Items", "Add at least one material quote item.")
            return

        options = QFileDialog.Option.DontUseNativeDialog
        filename, _ = QFileDialog.getSaveFileName(self, "Save PDF Quote", "", "PDF Files (*.pdf)", options=options)
        if not filename:
            return

        self.generate_pdf(filename)
        QMessageBox.information(self, "Saved", f"Quote saved and PDF generated:\n{filename}")

    def generate_pdf(self, filename):
        c = canvas.Canvas(filename, pagesize=letter)
        page_w, page_h = letter
        margin = 50
        y = page_h - margin

        y = self._draw_pdf_header(c, y, page_w, margin)
        y = self._draw_pdf_customer_info(c, y, margin)

        total_width = page_w - 2 * margin

        # Define weights for each column
        weights = [3.5, 1]  # Description, Area
        for _ in MATERIAL_TYPES:
            weights.extend([2, 2.5])  # Material Rate, Material Cost

        total_weight = sum(weights)

        # Calculate column widths based on weights
        col_widths = [(w / total_weight) * total_width for w in weights]

        # Calculate x positions for each column start
        x_positions = [margin]
        for w in col_widths:
            x_positions.append(x_positions[-1] + w)

        y = self._draw_pdf_table(c, y, page_w, page_h, margin, x_positions)
        y = self._draw_pdf_summary(c, y, x_positions)
        self._draw_pdf_notes_and_footer(c, y, page_w, page_h, margin)

        c.save()

    def _draw_pdf_header(self, c, y, page_w, margin):
        c.setFont("Helvetica-Bold", 16)
        c.drawString(margin, y, "JUST DECK IT - QUOTE")
        y -= 25

        current_month_year = datetime.date.today().strftime("%B %Y")
        desc_text = (
            "Each estimate is carefully prepared to reflect accurate costs based on material quantities, "
            "types, and labor hours required for your project. Our quotes break down the pricing for each "
            "material type and area, allowing you to see a clear, itemized cost structure that ensures full transparency.\n\n"
            "Our pricing reflects current market rates and includes applicable taxes for your region. "
            "We aim to offer competitive, fair pricing while maintaining high standards of quality and craftsmanship. "
            "Each quote also offers flexibility with optional upgrades and materials to tailor your project to your preferences and budget.\n\n"
            f"Estimate based on lumber and decking prices {current_month_year}."
        )
        c.setFont("Helvetica", 9)

        desc_lines = simpleSplit(desc_text, "Helvetica", 9, page_w - 2 * margin)
        for line in desc_lines:
            c.drawString(margin, y, line)
            y -= 12

        y -= 20
        return y

    def _draw_pdf_customer_info(self, c, y, margin):
        c.setFont("Helvetica", 10)
        c.drawString(margin, y, f"Date: {datetime.date.today().strftime('%b %d, %Y')}")
        y -= 15
        c.drawString(margin, y, f"Customer: {self.customer_name.text()}")
        y -= 15
        c.drawString(margin, y, f"Address: {self.customer_address.text()}")
        y -= 15
        c.drawString(margin, y, f"Phone: {self.customer_phone.text()}")
        y -= 15
        c.drawString(margin, y, f"Email: {self.customer_email.text()}")
        y -= 30
        return y

    def _draw_pdf_table(self, c, y, page_w, page_h, margin, x_positions):
        c.setFont("Helvetica-Bold", 10)
        headers = ["Description", "Area"]
        for mt in MATERIAL_TYPES:
            headers.append(mt)
            headers.append("Cost to Client")

        for i, header in enumerate(headers):
            col_start = x_positions[i]
            col_end = x_positions[i + 1]
            text_width = c.stringWidth(header, "Helvetica-Bold", 10)
            c.drawString(col_start + (col_end - col_start - text_width) / 2, y, header)
        y -= 15

        c.setFont("Helvetica", 9)
        row_height = 15

        for row in range(self.table.rowCount()):
            desc_col_w = x_positions[1] - x_positions[0]
            desc_text = self.table.item(row, 0).text()
            desc_wrapped = simpleSplit(desc_text, "Helvetica", 9, desc_col_w - 6)
            desc_wrapped = desc_wrapped[:3]
            max_lines = len(desc_wrapped)
            y_start = y

            for i, line in enumerate(desc_wrapped):
                c.drawString(x_positions[0] + 3, y_start - i * row_height, line)

            area_text = self.table.item(row, 1).text()
            area_start = x_positions[1]
            area_end = x_positions[2]
            area_width = c.stringWidth(area_text, "Helvetica", 9)
            c.drawString(area_start + (area_end - area_start - area_width) / 2, y_start, area_text)

            for i in range(len(MATERIAL_TYPES)):
                rate_text = self.table.item(row, 2 + i * 2).text()
                cost_text = self.table.item(row, 3 + i * 2).text()

                rate_start = x_positions[2 + i * 2]
                rate_end = x_positions[3 + i * 2]
                rate_width = c.stringWidth(rate_text, "Helvetica", 9)
                c.drawString(rate_end - rate_width - 3, y_start, rate_text)

                cost_start = x_positions[3 + i * 2]
                cost_end = x_positions[4 + i * 2]
                cost_width = c.stringWidth(cost_text, "Helvetica", 9)
                c.drawString(cost_end - cost_width - 3, y_start, cost_text)

            y -= max_lines * row_height + 5

            if y < margin + 100:
                c.showPage()
                y = page_h - margin
                c.setFont("Helvetica-Bold", 10)
                for i, header_text in enumerate(headers):
                    col_start = x_positions[i]
                    col_end = x_positions[i + 1]
                    text_width = c.stringWidth(header_text, "Helvetica-Bold", 10)
                    c.drawString(col_start + (col_end - col_start - text_width) / 2, y, header_text)
                y -= 15
                c.setFont("Helvetica", 9)

        return y

    def _draw_pdf_summary(self, c, y, x_positions):
        y -= 15
        c.setFont("Helvetica-Bold", 10)

        start_col = 2
        for i in range(len(MATERIAL_TYPES)):
            cost_col_index = start_col + i * 2 + 1

            subtotal = 0.0
            for row in range(self.table.rowCount()):
                item = self.table.item(row, cost_col_index)
                if item:
                    try:
                        subtotal += float(item.text())
                    except ValueError:
                        pass
            hst = subtotal * TAX_RATE
            total = subtotal + hst

            col_start = x_positions[cost_col_index]
            col_end = x_positions[cost_col_index + 1]

            for text, offset in zip(
                    [f"Subtotal: ${subtotal:.2f}", f"HST ({int(TAX_RATE * 100)}%): ${hst:.2f}",
                     f"Total: ${total:.2f}"],
                    [0, -15, -30]
            ):
                text_width = c.stringWidth(text, "Helvetica-Bold", 10)
                c.drawString(col_end - text_width - 3, y + offset, text)

        y -= 45
        return y

    def _draw_pdf_notes_and_footer(self, c, y, page_w, page_h, margin):
        notes = self.notes_text.toPlainText().strip()
        if notes:
            c.setFont("Helvetica-Bold", 11)
            c.drawString(margin, y, "Notes & Scope:")
            y -= 15
            c.setFont("Helvetica", 9)

            note_lines = simpleSplit(notes, "Helvetica", 9, page_w - 2 * margin)
            for line in note_lines:
                if y < margin + 20:
                    c.showPage()
                    y = page_h - margin
                c.drawString(margin, y, line)
                y -= 12

        y -= 30
        footer_lines = [
            "PT = Pressure Treated Lumber",
            "LF = Linear Foot",
            "Prices reflect square footage unless otherwise marked"
        ]
        c.setFont("Helvetica-Oblique", 8)
        for line in footer_lines:
            if y < margin + 20:
                c.showPage()
                y = page_h - margin
            c.drawString(margin, y, line)
            y -= 12

        return y



if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = JustDeckITQuotes()
    window.show()
    sys.exit(app.exec())
