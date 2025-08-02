import sys
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QLineEdit, QHeaderView, QMessageBox, QGroupBox,
    QFormLayout, QFileDialog, QTextEdit, QComboBox
)
from PyQt6.QtCore import Qt
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.utils import simpleSplit
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
import datetime
import sqlite3

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
        self.desc_input = QComboBox()
        self.desc_input.setEditable(True)
        self.desc_input.setPlaceholderText("Description")
        self.desc_input.lineEdit().textEdited.connect(self.update_suggestions)
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
            headers.append("Cost")
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

    def update_suggestions(self, text):
        if len(text) < 2:
            return

        suggestions = get_matching_descriptions(text)

        self.desc_input.blockSignals(True)

        current_text = self.desc_input.currentText()

        self.desc_input.clear()
        if suggestions:
            self.desc_input.addItems(suggestions)

        self.desc_input.setEditText(current_text)
        self.desc_input.blockSignals(False)

        if suggestions:
            self.desc_input.showPopup()

    def add_item(self):
        desc = self.desc_input.currentText().strip()
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

        try:
            # Save to database
            customer_id = add_customer(
                self.customer_name.text(),
                self.customer_address.text(),
                self.customer_phone.text(),
                self.customer_email.text()
            )
            if customer_id is None:
                raise Exception("Could not save or retrieve customer. Email is required.")

            quote_id = add_quote(
                customer_id,
                datetime.date.today().isoformat(),
                self.notes_text.toPlainText()
            )

            for row in range(self.table.rowCount()):
                description = self.table.item(row, 0).text()
                area = float(self.table.item(row, 1).text())
                rates = [float(self.table.item(row, 2 + i*2).text()) for i in range(len(MATERIAL_TYPES))]
                costs = [float(self.table.item(row, 3 + i*2).text()) for i in range(len(MATERIAL_TYPES))]
                add_quote_item(quote_id, description, area, rates, costs)

            QMessageBox.information(self, "Saved", f"Quote saved to PDF and database:\n{filename}")

        except Exception as e:
            QMessageBox.critical(self, "Database Error", f"Could not save quote to database: {e}")

    def generate_pdf(self, filename):
        doc = SimpleDocTemplate(filename, pagesize=letter)
        styles = getSampleStyleSheet()
        story = []

        from reportlab.lib.enums import TA_CENTER

        # Centered, bold title
        title_style = styles['h1']
        title_style.alignment = TA_CENTER
        story.append(Paragraph("<b>JUST DECK IT</b>", title_style))
        story.append(Spacer(1, 24))

        # Left-aligned customer info with bold labels and larger font
        customer_info_style = styles['Normal']
        customer_info_style.fontSize = 11
        customer_info_text = f"""
        <b>Name:</b> {self.customer_name.text()}<br/>
        <b>Address:</b> {self.customer_address.text()}<br/>
        <b>Phone:</b> {self.customer_phone.text()}<br/>
        <b>Email:</b> {self.customer_email.text()}
        """
        story.append(Paragraph(customer_info_text, customer_info_style))
        story.append(Spacer(1, 12))

        # "Quote:" sub-heading
        story.append(Paragraph("<b>Quote:</b>", styles['h2']))
        story.append(Spacer(1, 12))

        # Description
        current_month_year = datetime.date.today().strftime("%B %Y")
        desc_text = (
            "Each estimate is carefully prepared to reflect accurate costs based on material quantities, "
            "types, and labor hours required for your project. Our quotes break down the pricing for each "
            "material type and area, allowing you to see a clear, itemized cost structure that ensures full transparency.<br/><br/>"
            "Our pricing reflects current market rates and includes applicable taxes for your region. "
            "We aim to offer competitive, fair pricing while maintaining high standards of quality and craftsmanship. "
            "Each quote also offers flexibility with optional upgrades and materials to tailor your project to your preferences and budget.<br/><br/>"
            f"Estimate based on lumber and decking prices {current_month_year}."
        )
        story.append(Paragraph(desc_text, styles['BodyText']))
        story.append(Spacer(1, 24))

        # --- Table Data ---
        body_style = styles['BodyText']
        header = ["Description", "Area"]
        for mt in MATERIAL_TYPES:
            header.append(mt)
            header.append("Cost")

        data = [header]

        for row in range(self.table.rowCount()):
            row_data = []
            desc_text = self.table.item(row, 0).text().replace('\n', '<br/>')
            row_data.append(Paragraph(desc_text, body_style))
            row_data.append(self.table.item(row, 1).text())
            for i in range(len(MATERIAL_TYPES)):
                row_data.append(self.table.item(row, 2 + i * 2).text())
                row_data.append(self.table.item(row, 3 + i * 2).text())
            data.append(row_data)

        # --- True Content-Based Column Width Calculation ---
        total_width = doc.width
        num_cols = len(header)
        font_name = 'Helvetica'
        data_font_size = 8
        header_font_size = 10

        max_widths = [0] * num_cols
        for i in range(num_cols):
            header_width = stringWidth(str(data[0][i]), 'Helvetica-Bold', header_font_size)
            max_widths[i] = max(max_widths[i], header_width)

            for row_idx in range(1, len(data)):
                cell = data[row_idx][i]
                text = cell.getPlainText() if hasattr(cell, 'getPlainText') else str(cell)
                # Estimate width of wrapped paragraphs by taking the longest word
                if isinstance(cell, Paragraph):
                    words = text.split()
                    if words:
                        text = max(words, key=len)

                cell_width = stringWidth(text, font_name, data_font_size)
                max_widths[i] = max(max_widths[i], cell_width)

        padding = 15
        ideal_widths = [w + padding for w in max_widths]

        total_ideal_width = sum(ideal_widths)
        if total_ideal_width > total_width:
            scale_factor = total_width / total_ideal_width
            col_widths = [w * scale_factor for w in ideal_widths]
        else:
            extra_space = total_width - total_ideal_width
            col_widths = ideal_widths
            col_widths[0] += extra_space

        # --- Summary Data Calculation ---
        subtotals = [0.0] * len(MATERIAL_TYPES)
        for row in range(self.table.rowCount()):
            for i in range(len(MATERIAL_TYPES)):
                cost_col = 3 + i * 2
                item = self.table.item(row, cost_col)
                if item:
                    try:
                        subtotals[i] += float(item.text())
                    except ValueError:
                        pass

        # --- Add Summary Rows to Table Data ---
        data.append([''] * len(header)) # Spacer row

        # Subtotal Row
        subtotal_row = [''] * len(header)
        subtotal_row[0] = 'Subtotal:'
        for i in range(len(MATERIAL_TYPES)):
            cost_col_idx = 3 + i * 2
            subtotal_row[cost_col_idx] = f"${subtotals[i]:.2f}"
        data.append(subtotal_row)

        # HST Row
        hst_row = [''] * len(header)
        hst_row[0] = f"HST ({int(TAX_RATE*100)}%):"
        for i in range(len(MATERIAL_TYPES)):
            cost_col_idx = 3 + i * 2
            hst = subtotals[i] * TAX_RATE
            hst_row[cost_col_idx] = f"${hst:.2f}"
        data.append(hst_row)

        # Total Row
        total_row = [''] * len(header)
        total_row[0] = 'Total:'
        for i in range(len(MATERIAL_TYPES)):
            cost_col_idx = 3 + i * 2
            total = subtotals[i] * (1 + TAX_RATE)
            total_row[cost_col_idx] = f"${total:.2f}"
        data.append(total_row)

        # --- Create Table ---
        table = Table(data, colWidths=col_widths)

        # --- Apply Style ---
        style = TableStyle([
            ('GRID', (0,0), (-1,-1), 1, colors.black),
            ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
            ('TEXTCOLOR', (0,0), (-1,0), colors.black),
            ('ALIGN', (0,0), (-1,0), 'CENTER'),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('ALIGN', (1,1), (1,-1), 'RIGHT'), # Area column
            ('FONTSIZE', (0,1), (-1,-1), 8), # Set font size for data rows
        ])
        # Align rate and cost columns
        for i in range(len(MATERIAL_TYPES)):
            rate_col = 2 + i * 2
            cost_col = rate_col + 1
            style.add('ALIGN', (rate_col, 1), (rate_col, -1), 'RIGHT')
            style.add('ALIGN', (cost_col, 1), (cost_col, -1), 'RIGHT')
            style.add('FONTNAME', (cost_col, 1), (cost_col, -1), 'Helvetica-Bold')

        # --- Summary Rows Styling ---
        summary_start_row = -3
        # SPAN command to merge cells for the labels, and ALIGN to right-align the label
        style.add('SPAN', (0, summary_start_row), (1, summary_start_row))
        style.add('ALIGN', (0, summary_start_row), (0, summary_start_row), 'RIGHT')
        style.add('SPAN', (0, -2), (1, -2))
        style.add('ALIGN', (0, -2), (0, -2), 'RIGHT')
        style.add('SPAN', (0, -1), (1, -1))
        style.add('ALIGN', (0, -1), (0, -1), 'RIGHT')

        # Bold font for summary rows
        style.add('FONTNAME', (0, summary_start_row), (-1, -1), 'Helvetica-Bold')

        # Remove grid lines for the spacer row
        style.add('LINEABOVE', (0, summary_start_row -1), (-1, summary_start_row -1), 1, colors.black)
        style.add('LINEBELOW', (0, -1), (-1, -1), 1, colors.black)

        table.setStyle(style)
        story.append(table)
        story.append(Spacer(1, 24))

        # Notes & Footer
        notes = self.notes_text.toPlainText().strip()
        if notes:
            story.append(Paragraph("<b>Notes & Scope:</b>", styles['h3']))
            story.append(Paragraph(notes.replace('\n', '<br/>'), styles['BodyText']))
            story.append(Spacer(1, 12))

        footer_text = """
        PT = Pressure Treated Lumber<br/>
        LF = Linear Foot<br/>
        Prices reflect square footage unless otherwise marked
        """
        story.append(Paragraph(footer_text, styles['Italic']))

        story.append(Spacer(1, 48))

        signature_text = """
        <font size=12><b>Ryan Graziano,</b></font><br/>
        <font size=10>
        Proprietor,<br/>
        Just Deck IT,<br/>
        131 Main St, Brighton, ON, K0k 1h0<br/>
        (647) 208-7486
        </font>
        """
        story.append(Paragraph(signature_text, styles['Normal']))

        doc.build(story)

# --- Database Functions ---
def init_db():
    """
    Initializes the database and creates tables if they don't exist.
    """
    try:
        conn = sqlite3.connect('quotes.db')
        cursor = conn.cursor()

        # Create customers table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            address TEXT,
            phone TEXT,
            email TEXT UNIQUE
        )
        """)

        # Create quotes table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS quotes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER NOT NULL,
            quote_date TEXT NOT NULL,
            notes TEXT,
            FOREIGN KEY (customer_id) REFERENCES customers (id)
        )
        """)

        # Create quote_items table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS quote_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            quote_id INTEGER NOT NULL,
            description TEXT NOT NULL,
            area REAL NOT NULL,
            pt_5_4_rate REAL,
            pt_5_4_cost REAL,
            cedar_5_4_rate REAL,
            cedar_5_4_cost REAL,
            pt_2x6_rate REAL,
            pt_2x6_cost REAL,
            cedar_2x6_rate REAL,
            cedar_2x6_cost REAL,
            pvc_comp_rate REAL,
            pvc_comp_cost REAL,
            FOREIGN KEY (quote_id) REFERENCES quotes (id)
        )
        """)

        conn.commit()
    except sqlite3.Error as e:
        print(f"Database error: {e}")
    finally:
        if conn:
            conn.close()

def add_customer(name, address, phone, email):
    """Adds a customer to the database or retrieves the ID if they exist."""
    conn = sqlite3.connect('quotes.db')
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT OR IGNORE INTO customers (name, address, phone, email) VALUES (?, ?, ?, ?)",
                       (name, address, phone, email))
        conn.commit()

        cursor.execute("SELECT id FROM customers WHERE email = ?", (email,))
        result = cursor.fetchone()
        if result:
            return result[0]
        return None
    finally:
        conn.close()

def add_quote(customer_id, quote_date, notes):
    """Adds a quote to the database and returns the new quote's ID."""
    conn = sqlite3.connect('quotes.db')
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO quotes (customer_id, quote_date, notes) VALUES (?, ?, ?)",
                       (customer_id, quote_date, notes))
        quote_id = cursor.lastrowid
        conn.commit()
        return quote_id
    finally:
        conn.close()

def add_quote_item(quote_id, description, area, rates, costs):
    """Adds a single line item to a quote."""
    conn = sqlite3.connect('quotes.db')
    cursor = conn.cursor()
    try:
        item_data = (
            quote_id, description, area,
            rates[0], costs[0],
            rates[1], costs[1],
            rates[2], costs[2],
            rates[3], costs[3],
            rates[4], costs[4]
        )
        cursor.execute("""
            INSERT INTO quote_items (
                quote_id, description, area,
                pt_5_4_rate, pt_5_4_cost,
                cedar_5_4_rate, cedar_5_4_cost,
                pt_2x6_rate, pt_2x6_cost,
                cedar_2x6_rate, cedar_2x6_cost,
                pvc_comp_rate, pvc_comp_cost
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, item_data)
        conn.commit()
    finally:
        conn.close()

def get_matching_descriptions(search_term):
    """Retrieves unique descriptions from the database that match the search term."""
    conn = sqlite3.connect('quotes.db')
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT DISTINCT description FROM quote_items WHERE description LIKE ? LIMIT 10", ('%' + search_term + '%',))
        descriptions = [row[0] for row in cursor.fetchall()]
        return descriptions
    finally:
        conn.close()

if __name__ == "__main__":
    init_db()
    app = QApplication(sys.argv)
    window = JustDeckITQuotes()
    window.show()
    sys.exit(app.exec())
