import sys
import os
import sqlite3
import re
from datetime import datetime
import pandas as pd

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QComboBox, QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox, QTabWidget, QFormLayout, QGroupBox, QFileDialog,
    QDoubleSpinBox, QGridLayout, QDialog, QDialogButtonBox, QDateEdit, QListWidget, QListWidgetItem, QCheckBox
)
from PyQt5.QtCore import Qt, QDate, QUrl
from PyQt5.QtGui import QFont, QDesktopServices

from reportlab.lib.pagesizes import A5
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

# ---------------- NUMBERS TO WORDS HELPER ----------------
def number_to_words(num):
    try:
        num = int(round(num))
    except Exception:
        return ""
    if num == 0:
        return "Zero Rupees Only"
    
    units = ["", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine", "Ten",
             "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen", "Sixteen", "Seventeen", "Eighteen", "Nineteen"]
    tens = ["", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"]

    def convert_less_than_thousand(n):
        res = ""
        if n >= 100:
            res += units[n // 100] + " Hundred "
            n %= 100
        if n >= 20:
            res += tens[n // 10] + " "
            n %= 10
        if n > 0:
            res += units[n] + " "
        return res

    words = ""
    if num >= 10000000:
        words += convert_less_than_thousand(num // 10000000) + "Crore "
        num %= 10000000
    if num >= 100000:
        words += convert_less_than_thousand(num // 100000) + "Lakh "
        num %= 100000
    if num >= 1000:
        words += convert_less_than_thousand(num // 1000) + "Thousand "
        num %= 1000
    if num > 0:
        words += convert_less_than_thousand(num)

    return words.strip() + " Rupees Only"


# ---------------- DATABASE PATH SETUP ----------------
def get_db_path():
    if getattr(sys, 'frozen', False):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_dir, "gajanan_clinic.db")

DB_PATH = get_db_path()

def get_connection():
    conn = sqlite3.connect(DB_PATH, timeout=10)
    return conn

# ---------------- DATE FORMAT HELPER ----------------
def format_display_date(date_str):
    if not date_str:
        return ""
    try:
        dt = datetime.strptime(date_str.strip(), "%d/%m/%Y")
        return dt.strftime("%d-%b-%Y").upper()
    except ValueError:
        return date_str

# ---------------- DATABASE SETUP ----------------
def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("PRAGMA journal_mode = WAL;")
    cursor.execute("PRAGMA synchronous = NORMAL;")
    cursor.execute("PRAGMA busy_timeout = 5000;")
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS patients (
            sr_no INTEGER PRIMARY KEY AUTOINCREMENT,
            reg_date TEXT,
            patient_name TEXT,
            age INTEGER,
            sex TEXT,
            mobile TEXT,
            doctor_name TEXT,
            usg_scan TEXT,
            scan_type TEXT,
            usg_rate REAL,
            discount REAL DEFAULT 0.0,
            payment_mode TEXT,
            cash_amount REAL,
            online_amount REAL,
            payment_status TEXT DEFAULT 'Paid'
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS child_patients (
            sr_no INTEGER PRIMARY KEY AUTOINCREMENT,
            reg_date TEXT,
            title TEXT,
            patient_name TEXT,
            age TEXT,
            mobile TEXT,
            given_vaccines TEXT,
            total_amount REAL DEFAULT 0.0,
            discount REAL DEFAULT 0.0,
            payment_mode TEXT,
            cash_amount REAL DEFAULT 0.0,
            online_amount REAL DEFAULT 0.0,
            payment_status TEXT DEFAULT 'Pending'
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS vaccines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vaccine_name TEXT UNIQUE,
            price REAL,
            type TEXT DEFAULT 'Vaccine'
        )
    ''')

    cursor.execute("PRAGMA table_info(vaccines)")
    columns = [column[1] for column in cursor.fetchall()]
    if 'type' not in columns:
        cursor.execute("ALTER TABLE vaccines ADD COLUMN type TEXT DEFAULT 'Vaccine'")

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS doctors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            hospital_name TEXT,
            address TEXT,
            commission_percent REAL DEFAULT 0.0,
            adjustment_amount REAL DEFAULT 0.0,
            last_reset_month TEXT
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usg_scans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scan_name TEXT UNIQUE,
            scan_type TEXT,
            price REAL
        )
    ''')
    
    conn.commit()
    conn.close()

# ---------------- ACTION POPUP DIALOG ----------------
class PatientActionDialog(QDialog):
    def __init__(self, patient_name, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Action")
        self.setFixedSize(320, 160)
        self.selected_action = None

        self.setStyleSheet("""
            QDialog { background-color: #1e1e2e; color: #cdd6f4; }
            QLabel { color: #cdd6f4; font-size: 13px; font-weight: bold; }
            QPushButton {
                background-color: #89b4fa;
                color: #11111b;
                border-radius: 5px;
                padding: 10px;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover { background-color: #b4befe; }
            QPushButton#btn_print { background-color: #a6e3a1; color: #11111b; }
        """)

        layout = QVBoxLayout()
        lbl = QLabel(f"Patient: {patient_name}\nWhat would you like to do?")
        lbl.setAlignment(Qt.AlignCenter)
        layout.addWidget(lbl)

        btn_update = QPushButton("Patient Details Update")
        btn_update.clicked.connect(self.on_update)

        btn_print = QPushButton("Print Bill")
        btn_print.setObjectName("btn_print")
        btn_print.clicked.connect(self.on_print)

        layout.addWidget(btn_update)
        layout.addWidget(btn_print)
        self.setLayout(layout)

    def on_update(self):
        self.selected_action = "UPDATE"
        self.accept()

    def on_print(self):
        self.selected_action = "PRINT"
        self.accept()

# ---------------- MULTI VACCINE SELECTION DIALOG ----------------
class SelectVaccinesDialog(QDialog):
    def __init__(self, current_selected="", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Vaccines / Particulars")
        self.setFixedSize(450, 420)
        
        self.setStyleSheet("""
            QDialog { background-color: #1e1e2e; color: #cdd6f4; font-weight: bold; }
            QLabel { font-weight: bold; color: #cdd6f4; }
            QListWidget { background-color: #313244; color: #cdd6f4; font-weight: bold; border: 1px solid #45475a; }
            QListWidget::item { padding: 8px; border-bottom: 1px solid #45475a; }
            QListWidget::item:hover { background-color: #45475a; cursor: pointer; }
            QPushButton { background-color: #a6e3a1; color: #11111b; font-weight: bold; border-radius: 4px; padding: 6px; }
        """)

        layout = QVBoxLayout()
        layout.addWidget(QLabel("Select Vaccine / Particulars:"))

        self.list_widget = QListWidget()
        
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT vaccine_name, price, type FROM vaccines ORDER BY vaccine_name ASC")
        v_list = cursor.fetchall()
        conn.close()

        curr_items = [v.strip() for v in current_selected.split(",") if v.strip()]

        for name, price, item_type in v_list:
            type_tag = f"[{item_type or 'Vaccine'}]"
            item_text = f"{name} {type_tag} (₹ {price:.2f})"
            item = QListWidgetItem(item_text)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            
            if any(name in c for c in curr_items):
                item.setCheckState(Qt.Checked)
            else:
                item.setCheckState(Qt.Unchecked)
                
            self.list_widget.addItem(item)

        self.list_widget.itemClicked.connect(self.on_item_clicked)
        layout.addWidget(self.list_widget)

        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

        self.setLayout(layout)

    def on_item_clicked(self, item):
        if item.checkState() == Qt.Checked:
            item.setCheckState(Qt.Unchecked)
        else:
            item.setCheckState(Qt.Checked)

    def get_selected(self):
        selected = []
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if item.checkState() == Qt.Checked:
                selected.append(item.text())
        return selected

# ---------------- CAPTURE PAYMENT DIALOG WITH DISCOUNT ----------------
class CapturePaymentDialog(QDialog):
    def __init__(self, sr_no, total_rate, existing_discount=0.0, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Capture Payment - Sr No: {sr_no}")
        self.setFixedSize(380, 280)
        self.sr_no = sr_no
        self.total_rate = total_rate
        
        self.setStyleSheet("""
            QDialog { background-color: #1e1e2e; color: #cdd6f4; font-weight: bold; }
            QLabel { font-weight: bold; color: #cdd6f4; }
            QComboBox, QDoubleSpinBox { background-color: #313244; color: #cdd6f4; font-weight: bold; padding: 5px; border: 1px solid #45475a; }
            QPushButton { background-color: #a6e3a1; color: #11111b; font-weight: bold; border-radius: 4px; padding: 6px; }
        """)

        layout = QVBoxLayout()
        form = QFormLayout()

        self.lbl_total = QLabel(f"₹ {total_rate:.2f}")
        self.lbl_total.setStyleSheet("color: #f9e2af; font-size: 14px;")

        self.spn_discount = QDoubleSpinBox()
        self.spn_discount.setMaximum(100000)
        self.spn_discount.setValue(existing_discount)
        self.spn_discount.valueChanged.connect(self.update_payable)

        self.lbl_payable = QLabel(f"₹ {max(0.0, total_rate - existing_discount):.2f}")
        self.lbl_payable.setStyleSheet("color: #a6e3a1; font-size: 14px;")
        
        self.cmb_mode = QComboBox()
        self.cmb_mode.addItems(["Cash", "Online/UPI", "Card", "Partial"])
        self.cmb_mode.currentIndexChanged.connect(self.toggle_mode)

        self.spn_cash = QDoubleSpinBox()
        self.spn_cash.setMaximum(100000)
        
        self.spn_online = QDoubleSpinBox()
        self.spn_online.setMaximum(100000)
        self.spn_online.setEnabled(False)

        form.addRow("Total Rate:", self.lbl_total)
        form.addRow("Discount (₹):", self.spn_discount)
        form.addRow("Payable Amount:", self.lbl_payable)
        form.addRow("Payment Mode:", self.cmb_mode)
        form.addRow("Cash Amount (₹):", self.spn_cash)
        form.addRow("Online Amount (₹):", self.spn_online)

        layout.addLayout(form)

        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

        self.setLayout(layout)
        self.update_payable()

    def update_payable(self):
        disc = self.spn_discount.value()
        payable = max(0.0, self.total_rate - disc)
        self.lbl_payable.setText(f"₹ {payable:.2f}")
        self.toggle_mode()

    def toggle_mode(self):
        disc = self.spn_discount.value()
        payable = max(0.0, self.total_rate - disc)
        mode = self.cmb_mode.currentText()

        if mode == "Cash":
            self.spn_cash.setEnabled(True)
            self.spn_cash.setValue(payable)
            self.spn_online.setEnabled(False)
            self.spn_online.setValue(0)
        elif mode in ["Online/UPI", "Card"]:
            self.spn_cash.setEnabled(False)
            self.spn_cash.setValue(0)
            self.spn_online.setEnabled(True)
            self.spn_online.setValue(payable)
        elif mode == "Partial":
            self.spn_cash.setEnabled(True)
            self.spn_online.setEnabled(True)
            self.spn_cash.setValue(payable / 2)
            self.spn_online.setValue(payable / 2)

    def get_data(self):
        return self.cmb_mode.currentText(), self.spn_discount.value(), self.spn_cash.value(), self.spn_online.value()

# ---------------- MAIN APPLICATION CLASS ----------------
class GajananApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Gajanan Diagnostic and Child Care Clinic - Management System")
        self.resize(1366, 768)
        self.selected_patient_id = None
        self.selected_child_id = None
        self.selected_scan_id = None
        self.selected_doctor_id = None
        self.selected_vaccine_id = None
        
        self.setStyleSheet("""
            QMainWindow, QWidget {
                background-color: #1e1e2e;
                color: #cdd6f4;
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 13px;
                font-weight: bold;
            }
            QGroupBox {
                border: 2px solid #45475a;
                border-radius: 8px;
                margin-top: 10px;
                font-size: 14px;
                font-weight: bold;
                color: #89b4fa;
                padding-top: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 5px;
            }
            QLabel { font-weight: bold; font-size: 13px; }
            QLineEdit, QComboBox, QDoubleSpinBox, QDateEdit {
                background-color: #313244;
                border: 1px solid #45475a;
                border-radius: 4px;
                padding: 6px;
                color: #cdd6f4;
                font-weight: bold;
                font-size: 13px;
                min-height: 22px;
            }
            QLineEdit:focus, QComboBox:focus, QDoubleSpinBox:focus, QDateEdit:focus {
                border: 1px solid #89b4fa;
            }
            QPushButton {
                background-color: #89b4fa;
                color: #11111b;
                border-radius: 5px;
                padding: 8px 12px;
                font-weight: bold;
                font-size: 12px;
                min-height: 25px;
            }
            QPushButton:hover { background-color: #b4befe; }
            QPushButton#btn_print { background-color: #a6e3a1; color: #11111b; }
            QPushButton#btn_clear { background-color: #f38ba8; color: #11111b; }
            QPushButton#btn_delete {
                background-color: #f38ba8;
                color: #11111b;
                font-size: 12px;
                font-weight: bold;
                border-radius: 4px;
                padding: 3px 6px;
                min-height: 20px;
            }
            QPushButton#btn_add_bill {
                background-color: #f9e2af;
                color: #11111b;
                font-size: 11px;
                font-weight: bold;
                padding: 3px 6px;
                border-radius: 4px;
                min-height: 20px;
            }
            QPushButton#btn_capture {
                background-color: #fab387;
                color: #11111b;
                font-size: 12px;
                font-weight: bold;
                padding: 3px 6px;
                border-radius: 4px;
                min-height: 20px;
            }
            QTableWidget {
                background-color: #181825;
                gridline-color: #45475a;
                font-weight: bold;
                font-size: 12px;
                border: 1px solid #45475a;
                border-radius: 6px;
            }
            QHeaderView::section {
                background-color: #313244;
                color: #89b4fa;
                padding: 6px;
                font-weight: bold;
                font-size: 12px;
                border: 1px solid #45475a;
            }
            QTabWidget::pane { border: 1px solid #45475a; }
            QTabBar::tab {
                background: #313244;
                color: #cdd6f4;
                padding: 10px 18px;
                font-weight: bold;
                font-size: 13px;
            }
            QTabBar::tab:selected { background: #89b4fa; color: #11111b; }
            QCheckBox { color: #cdd6f4; font-weight: bold; font-size: 12px; }
        """)

        self.init_ui()

    def init_ui(self):
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        self.tab_dashboard = QWidget()
        self.tab_entry = QWidget()
        self.tab_usg_register = QWidget()
        self.tab_child_register = QWidget()
        self.tab_vac_register = QWidget()
        self.tab_vaccines = QWidget()
        self.tab_doctors = QWidget()
        self.tab_scans = QWidget()

        self.tabs.addTab(self.tab_dashboard, "Dashboard")
        self.tabs.addTab(self.tab_entry, "Patient Registration Form")
        self.tabs.addTab(self.tab_usg_register, "Sonography Patient Register")
        self.tabs.addTab(self.tab_child_register, "Child Care Register")
        self.tabs.addTab(self.tab_vac_register, "Vaccine Register")
        self.tabs.addTab(self.tab_vaccines, "Vaccine Master")
        self.tabs.addTab(self.tab_doctors, "Doctor Management")
        self.tabs.addTab(self.tab_scans, "USG Scan Management")

        self.setup_dashboard()
        self.setup_entry_form()
        self.setup_usg_register_table()
        self.setup_child_register_table()
        self.setup_vaccine_register_tab()
        self.setup_vaccines_tab()
        self.setup_doctors()
        self.setup_scans()

        self.load_doctor_dropdowns()
        self.load_scan_dropdowns()
        self.load_vaccines_table()
        self.load_doctors_table()
        self.load_scans_table()
        self.refresh_patient_table()
        self.refresh_child_table()
        self.refresh_vaccine_register()
        self.update_dashboard()

        self.tabs.currentChanged.connect(self.on_tab_changed)

    def on_tab_changed(self, index):
        if index == 0:
            self.update_dashboard()
        elif index == 2:
            self.refresh_patient_table()
        elif index == 3:
            self.refresh_child_table()
        elif index == 4:
            self.refresh_vaccine_register()
        elif index == 5:
            self.load_vaccines_table()
        elif index == 6:
            self.load_doctors_table()

    # ---------------- PDF GENERATION METHOD ----------------
    def generate_pdf_bill_general(self, receipt_no, date_str, patient_name, age_sex, mobile, items_list, discount_val, payment_mode, filename_prefix="Bill"):
        if getattr(sys, 'frozen', False):
            base_dir = os.path.dirname(sys.executable)
        else:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            
        bills_dir = os.path.join(base_dir, "Bills")
        if not os.path.exists(bills_dir):
            os.makedirs(bills_dir)

        filename = os.path.join(bills_dir, f"{filename_prefix}_{receipt_no}.pdf")

        doc = SimpleDocTemplate(
            filename,
            pagesize=A5,
            rightMargin=10,
            leftMargin=10,
            topMargin=10,
            bottomMargin=10
        )

        printable_width = 400
        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            'TitleStyle', parent=styles['Heading1'], fontName='Helvetica-Bold', fontSize=11, leading=13, alignment=1, textColor=colors.HexColor('#1A237E')
        )
        subtitle_style = ParagraphStyle(
            'SubtitleStyle', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=7.5, leading=9, alignment=1, textColor=colors.HexColor('#333333')
        )
        info_label_style = ParagraphStyle(
            'InfoLabel', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=7.5, leading=9, textColor=colors.HexColor('#222222')
        )
        info_val_style = ParagraphStyle(
            'InfoVal', parent=styles['Normal'], fontName='Helvetica', fontSize=7.5, leading=9, textColor=colors.HexColor('#111111')
        )
        tbl_header_style = ParagraphStyle(
            'TblHeader', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=8, leading=10, alignment=0, textColor=colors.whitesmoke
        )
        tbl_header_right = ParagraphStyle('TblHeaderRight', parent=tbl_header_style, alignment=2)
        item_style = ParagraphStyle(
            'ItemStyle', parent=styles['Normal'], fontName='Helvetica', fontSize=7.5, leading=9, textColor=colors.HexColor('#222222')
        )
        item_right = ParagraphStyle('ItemRight', parent=item_style, alignment=2)
        tot_style = ParagraphStyle(
            'TotStyle', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=8.5, leading=10, alignment=2, textColor=colors.whitesmoke
        )

        gross_total = sum(item[1] for item in items_list)
        discount_val = float(discount_val or 0.0)
        net_payable = max(0.0, gross_total - discount_val)
        words_amt = number_to_words(net_payable)

        header_p = Paragraph("GAJANAN DIAGNOSTIC & CHILD CARE CLINIC", title_style)
        sub_p = Paragraph("Shop No - 117, 41 City Hub, Hadapsar, Pune | Contact: +91 9860150120", subtitle_style)

        patient_info_data = [
            [
                Paragraph("<b>Receipt No:</b>", info_label_style), Paragraph(str(receipt_no), info_val_style),
                Paragraph("<b>Date:</b>", info_label_style), Paragraph(format_display_date(date_str), info_val_style)
            ],
            [
                Paragraph("<b>Patient Name:</b>", info_label_style), Paragraph(patient_name, info_val_style),
                Paragraph("<b>Age / Sex:</b>", info_label_style), Paragraph(str(age_sex), info_val_style)
            ],
            [
                Paragraph("<b>Mobile No:</b>", info_label_style), Paragraph(str(mobile or "-"), info_val_style),
                Paragraph("", info_label_style), Paragraph("", info_val_style)
            ]
        ]
        patient_info_table = Table(patient_info_data, colWidths=[65, 130, 55, 120])
        patient_info_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
            ('TOPPADDING', (0, 0), (-1, -1), 1),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ]))

        particulars_data = [[Paragraph("Particulars", tbl_header_style), Paragraph("Amount (₹)", tbl_header_right)]]
        
        for item_name, item_price in items_list:
            particulars_data.append([
                Paragraph(item_name, item_style),
                Paragraph(f"{item_price:.2f}", item_right)
            ])

        if discount_val > 0:
            particulars_data.append([Paragraph("Gross Amount", item_style), Paragraph(f"{gross_total:.2f}", item_right)])
            particulars_data.append([Paragraph("Discount", item_style), Paragraph(f"- {discount_val:.2f}", item_right)])

        particulars_data.append([Paragraph("TOTAL PAYABLE", tot_style), Paragraph(f"₹ {net_payable:.2f}", tot_style)])

        particulars_table = Table(particulars_data, colWidths=[275, 95])
        particulars_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (1, 0), colors.HexColor('#1A237E')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
            ('TOPPADDING', (0, 0), (-1, -1), 2),
            ('GRID', (0, 0), (-1, -2), 0.5, colors.HexColor('#CCCCCC')),
            ('BACKGROUND', (0, -1), (1, -1), colors.HexColor('#008000')),
            ('BOTTOMPADDING', (0, -1), (1, -1), 3),
            ('TOPPADDING', (0, -1), (1, -1), 3),
        ]))

        footer_data = [
            [Paragraph(f"<b>Amount in Words:</b> {words_amt}", info_label_style)],
            [Paragraph(f"<b>Payment Mode:</b> {payment_mode}", info_label_style)],
            [Spacer(1, 8)],
            [Paragraph("<b>Authorised Signature</b>", ParagraphStyle('AuthSig', parent=info_label_style, alignment=2))]
        ]
        footer_table = Table(footer_data, colWidths=[370])
        footer_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
            ('TOPPADDING', (0, 0), (-1, -1), 0),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ]))

        inner_content = [
            [header_p], [sub_p], [Spacer(1, 2)],
            [patient_info_table], [Spacer(1, 4)],
            [particulars_table], [Spacer(1, 4)],
            [footer_table]
        ]

        main_box_table = Table(inner_content, colWidths=[printable_width])
        main_box_table.setStyle(TableStyle([
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#1A237E')),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('LEFTPADDING', (0, 0), (-1, -1), 5),
            ('RIGHTPADDING', (0, 0), (-1, -1), 5),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))

        doc.build([main_box_table])
        QDesktopServices.openUrl(QUrl.fromLocalFile(filename))

    def generate_pdf_bill(self, receipt_no, date_str, patient_name, age, sex, mobile, doctor, scan, rate, discount, paymode, cash, online):
        age_sex = f"{age} Y / {sex}" if age else f"{sex}"
        items_list = [(scan, float(rate))]
        self.generate_pdf_bill_general(receipt_no, date_str, patient_name, age_sex, mobile, items_list, discount, paymode, filename_prefix="USG_Bill")

    def generate_child_pdf_bill(self, receipt_no, date_str, patient_name, age, mobile, given_vaccines, total_amount, discount, paymode, cash, online):
        items_list = []
        raw_items = [v.strip() for v in str(given_vaccines or "").split(",") if v.strip()]
        
        for item_str in raw_items:
            m = re.match(r"^(.*?)(?:\s*\[.*?\])?\s*\(\s*₹\s*([\d.]+)\s*\)$", item_str)
            if m:
                items_list.append((m.group(1).strip(), float(m.group(2))))
            else:
                items_list.append((item_str, 0.0))

        if not items_list:
            items_list = [("Vaccination / Particular Service", float(total_amount or 0.0))]

        self.generate_pdf_bill_general(receipt_no, date_str, patient_name, age or "-", mobile, items_list, discount, paymode, filename_prefix="Child_Bill")

    # ---------------- 1. DASHBOARD ----------------
    def setup_dashboard(self):
        layout = QVBoxLayout()
        layout.setSpacing(10)
        
        header = QLabel("GAJANAN DIAGNOSTIC AND CHILD CARE CLINIC\n"
                        "Shop No - 117, 41 City Hub, Hadapsar | Contact: +91 9860150120")
        header.setAlignment(Qt.AlignCenter)
        header.setStyleSheet("font-size: 16px; font-weight: bold; color: #f9e2af; margin-bottom: 2px;")
        layout.addWidget(header)

        # Today Filter Row
        date_filter_row = QHBoxLayout()
        date_filter_row.addStretch()
        lbl_date_filter = QLabel("Select Daily Dashboard Date:")
        lbl_date_filter.setStyleSheet("font-size: 13px; font-weight: bold; color: #89b4fa;")
        
        self.dash_date_filter = QDateEdit()
        self.dash_date_filter.setCalendarPopup(True)
        self.dash_date_filter.setDisplayFormat("dd/MM/yyyy")
        self.dash_date_filter.setDate(QDate.currentDate())
        self.dash_date_filter.dateChanged.connect(self.update_dashboard)

        date_filter_row.addWidget(lbl_date_filter)
        date_filter_row.addWidget(self.dash_date_filter)
        date_filter_row.addStretch()
        layout.addLayout(date_filter_row)

        # Today Daily Summary Box
        lay_daily_boxes = QHBoxLayout()

        self.box_usg_today = QGroupBox("Sonography Daily Summary")
        lay_usg_grid = QGridLayout()
        self.lbl_today_count = QLabel("0")
        self.lbl_today_obs = QLabel("0")
        self.lbl_today_reg = QLabel("0")
        self.lbl_today_cash = QLabel("₹ 0.00")
        self.lbl_today_online = QLabel("₹ 0.00")
        self.lbl_today_total = QLabel("₹ 0.00")
        self.lbl_today_total.setStyleSheet("color: #a6e3a1; font-size: 13px; font-weight: bold;")

        lay_usg_grid.addWidget(QLabel("Total Patients:"), 0, 0)
        lay_usg_grid.addWidget(self.lbl_today_count, 0, 1)
        lay_usg_grid.addWidget(QLabel("Obs Scans:"), 1, 0)
        lay_usg_grid.addWidget(self.lbl_today_obs, 1, 1)
        lay_usg_grid.addWidget(QLabel("Regular Scans:"), 2, 0)
        lay_usg_grid.addWidget(self.lbl_today_reg, 2, 1)

        lay_usg_grid.addWidget(QLabel("Cash Total:"), 0, 2)
        lay_usg_grid.addWidget(self.lbl_today_cash, 0, 3)
        lay_usg_grid.addWidget(QLabel("Online Total:"), 1, 2)
        lay_usg_grid.addWidget(self.lbl_today_online, 1, 3)
        lay_usg_grid.addWidget(QLabel("Total Business:"), 2, 2)
        lay_usg_grid.addWidget(self.lbl_today_total, 2, 3)
        self.box_usg_today.setLayout(lay_usg_grid)

        self.box_child_today = QGroupBox("Child Care Daily Summary")
        lay_child_grid = QGridLayout()
        self.lbl_child_today_count = QLabel("0")
        self.lbl_child_today_cash = QLabel("₹ 0.00")
        self.lbl_child_today_online = QLabel("₹ 0.00")
        self.lbl_child_today_total = QLabel("₹ 0.00")
        self.lbl_child_today_total.setStyleSheet("color: #a6e3a1; font-size: 13px; font-weight: bold;")

        lay_child_grid.addWidget(QLabel("Child Patients:"), 0, 0)
        lay_child_grid.addWidget(self.lbl_child_today_count, 0, 1)
        lay_child_grid.addWidget(QLabel("Cash Total:"), 0, 2)
        lay_child_grid.addWidget(self.lbl_child_today_cash, 0, 3)
        lay_child_grid.addWidget(QLabel("Online Total:"), 1, 2)
        lay_child_grid.addWidget(self.lbl_child_today_online, 1, 3)
        lay_child_grid.addWidget(QLabel("Total Business:"), 2, 2)
        lay_child_grid.addWidget(self.lbl_child_today_total, 2, 3)
        self.box_child_today.setLayout(lay_child_grid)

        lay_daily_boxes.addWidget(self.box_usg_today)
        lay_daily_boxes.addWidget(self.box_child_today)
        layout.addLayout(lay_daily_boxes)

        # Monthly Summary Box
        box_monthly = QGroupBox("Monthly Summary & Reports")
        lay_monthly = QVBoxLayout()
        filter_row = QHBoxLayout()
        
        self.cmb_month = QComboBox()
        self.cmb_month.addItems([str(i).zfill(2) for i in range(1, 13)])
        self.cmb_month.setCurrentText(datetime.now().strftime("%m"))
        self.cmb_month.currentIndexChanged.connect(self.update_monthly_dashboard)
        
        self.cmb_year = QComboBox()
        self.cmb_year.addItems([str(y) for y in range(2023, 2035)])
        self.cmb_year.setCurrentText(datetime.now().strftime("%Y"))
        self.cmb_year.currentIndexChanged.connect(self.update_monthly_dashboard)

        btn_export = QPushButton("Download Monthly Excel Report")
        btn_export.clicked.connect(self.export_to_excel)

        filter_row.addWidget(QLabel("Select Month:"))
        filter_row.addWidget(self.cmb_month, 1)
        filter_row.addWidget(QLabel("Year:"))
        filter_row.addWidget(self.cmb_year, 1)
        filter_row.addWidget(btn_export, 2)
        filter_row.addStretch()
        lay_monthly.addLayout(filter_row)

        m_tables_layout = QHBoxLayout()
        box_m_usg = QGroupBox("Sonography Monthly Data")
        lay_m_usg = QGridLayout()
        self.lbl_month_tot_patients = QLabel("0")
        self.lbl_month_obs_patients = QLabel("0")
        self.lbl_month_reg_patients = QLabel("0")
        self.lbl_month_cash = QLabel("₹ 0.00")
        self.lbl_month_online = QLabel("₹ 0.00")
        self.lbl_month_total_business = QLabel("₹ 0.00")
        self.lbl_month_total_business.setStyleSheet("color: #a6e3a1; font-size: 13px; font-weight: bold;")

        lay_m_usg.addWidget(QLabel("Total Patients:"), 0, 0)
        lay_m_usg.addWidget(self.lbl_month_tot_patients, 0, 1)
        lay_m_usg.addWidget(QLabel("Obs Patients:"), 1, 0)
        lay_m_usg.addWidget(self.lbl_month_obs_patients, 1, 1)
        lay_m_usg.addWidget(QLabel("Regular Patients:"), 2, 0)
        lay_m_usg.addWidget(self.lbl_month_reg_patients, 2, 1)
        lay_m_usg.addWidget(QLabel("Total Cash:"), 0, 2)
        lay_m_usg.addWidget(self.lbl_month_cash, 0, 3)
        lay_m_usg.addWidget(QLabel("Total Online:"), 1, 2)
        lay_m_usg.addWidget(self.lbl_month_online, 1, 3)
        lay_m_usg.addWidget(QLabel("Total Business:"), 2, 2)
        lay_m_usg.addWidget(self.lbl_month_total_business, 2, 3)
        box_m_usg.setLayout(lay_m_usg)

        box_m_child = QGroupBox("Child Care Monthly Data")
        lay_m_child = QGridLayout()
        self.lbl_child_m_tot_patients = QLabel("0")
        self.lbl_child_m_cash = QLabel("₹ 0.00")
        self.lbl_child_m_online = QLabel("₹ 0.00")
        self.lbl_child_m_total_business = QLabel("₹ 0.00")
        self.lbl_child_m_total_business.setStyleSheet("color: #a6e3a1; font-size: 13px; font-weight: bold;")

        lay_m_child.addWidget(QLabel("Child Patients:"), 0, 0)
        lay_m_child.addWidget(self.lbl_child_m_tot_patients, 0, 1)
        lay_m_child.addWidget(QLabel("Total Cash:"), 0, 2)
        lay_m_child.addWidget(self.lbl_child_m_cash, 0, 3)
        lay_m_child.addWidget(QLabel("Total Online:"), 1, 2)
        lay_m_child.addWidget(self.lbl_child_m_online, 1, 3)
        lay_m_child.addWidget(QLabel("Total Business:"), 2, 2)
        lay_m_child.addWidget(self.lbl_child_m_total_business, 2, 3)
        box_m_child.setLayout(lay_m_child)

        m_tables_layout.addWidget(box_m_usg)
        m_tables_layout.addWidget(box_m_child)
        lay_monthly.addLayout(m_tables_layout)
        box_monthly.setLayout(lay_monthly)
        layout.addWidget(box_monthly)

        # ---------------- FINANCIAL YEAR SUMMARY SECTION (PATIENT COUNT ONLY) ----------------
        box_fy = QGroupBox("Financial Year Summary (01 April - 31 March)")
        lay_fy = QVBoxLayout()

        fy_filter_row = QHBoxLayout()
        self.cmb_fy = QComboBox()
        curr_year = datetime.now().year
        curr_month = datetime.now().month
        default_start_year = curr_year if curr_month >= 4 else curr_year - 1
        
        for y in range(2023, 2035):
            self.cmb_fy.addItem(f"FY {y}-{str(y+1)[2:]}", y)
        
        default_idx = self.cmb_fy.findData(default_start_year)
        if default_idx != -1:
            self.cmb_fy.setCurrentIndex(default_idx)
            
        self.cmb_fy.currentIndexChanged.connect(self.update_fy_dashboard)

        btn_export_fy = QPushButton("Download Financial Year Excel Report")
        btn_export_fy.clicked.connect(self.export_fy_to_excel)

        fy_filter_row.addWidget(QLabel("Select Financial Year:"))
        fy_filter_row.addWidget(self.cmb_fy, 1)
        fy_filter_row.addWidget(btn_export_fy, 2)
        fy_filter_row.addStretch()
        lay_fy.addLayout(fy_filter_row)

        fy_tables_layout = QHBoxLayout()

        # FY Sonography Box (Only Patient Counts)
        box_fy_usg = QGroupBox("Sonography Yearly Data")
        lay_fy_usg = QGridLayout()
        self.lbl_fy_usg_patients = QLabel("0")
        self.lbl_fy_usg_obs = QLabel("0")
        self.lbl_fy_usg_reg = QLabel("0")

        lay_fy_usg.addWidget(QLabel("Total Patients:"), 0, 0)
        lay_fy_usg.addWidget(self.lbl_fy_usg_patients, 0, 1)
        lay_fy_usg.addWidget(QLabel("Obs Scans:"), 1, 0)
        lay_fy_usg.addWidget(self.lbl_fy_usg_obs, 1, 1)
        lay_fy_usg.addWidget(QLabel("Regular Scans:"), 2, 0)
        lay_fy_usg.addWidget(self.lbl_fy_usg_reg, 2, 1)
        box_fy_usg.setLayout(lay_fy_usg)

        # FY Child Care Box (Only Patient Count)
        box_fy_child = QGroupBox("Child Care Yearly Data")
        lay_fy_child = QGridLayout()
        self.lbl_fy_child_patients = QLabel("0")

        lay_fy_child.addWidget(QLabel("Total Child Patients:"), 0, 0)
        lay_fy_child.addWidget(self.lbl_fy_child_patients, 0, 1)
        box_fy_child.setLayout(lay_fy_child)

        # FY Combined Grand Box (Only Total Combined Patients Count)
        box_fy_combined = QGroupBox("Combined Yearly Total")
        lay_fy_combined = QGridLayout()
        self.lbl_fy_total_patients = QLabel("0")
        self.lbl_fy_total_patients.setStyleSheet("color: #f9e2af; font-size: 15px; font-weight: bold;")

        lay_fy_combined.addWidget(QLabel("Combined Total Patients:"), 0, 0)
        lay_fy_combined.addWidget(self.lbl_fy_total_patients, 0, 1)
        box_fy_combined.setLayout(lay_fy_combined)

        fy_tables_layout.addWidget(box_fy_usg)
        fy_tables_layout.addWidget(box_fy_child)
        fy_tables_layout.addWidget(box_fy_combined)
        lay_fy.addLayout(fy_tables_layout)

        box_fy.setLayout(lay_fy)
        layout.addWidget(box_fy)

        layout.addStretch()

        watermark_label = QLabel(
            "© 2026 Shivtirth Marketings Pune. All rights reserved\n"
            "Developed by - Shivtirth Marketings Pune"
        )
        watermark_label.setAlignment(Qt.AlignCenter)
        watermark_label.setStyleSheet("color: #f9e2af; font-size: 12px; font-weight: bold; margin-top: 4px;")
        layout.addWidget(watermark_label)

        self.tab_dashboard.setLayout(layout)

    def update_dashboard(self):
        selected_date = self.dash_date_filter.date().toString("dd/MM/yyyy")
        
        self.box_usg_today.setTitle(f"Sonography Daily Summary ({selected_date})")
        self.box_child_today.setTitle(f"Child Care Daily Summary ({selected_date})")

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*), SUM(cash_amount), SUM(online_amount) FROM patients WHERE reg_date=?", (selected_date,))
        res = cursor.fetchone()
        tot_patients = res[0] or 0
        cash_tot = res[1] or 0.0
        online_tot = res[2] or 0.0
        usg_tot = cash_tot + online_tot

        cursor.execute("SELECT COUNT(*) FROM patients WHERE reg_date=? AND scan_type='Obstetrics Scan'", (selected_date,))
        obs_count = cursor.fetchone()[0] or 0

        cursor.execute("SELECT COUNT(*) FROM patients WHERE reg_date=? AND scan_type='Regular Scan'", (selected_date,))
        reg_count = cursor.fetchone()[0] or 0

        self.lbl_today_count.setText(str(tot_patients))
        self.lbl_today_obs.setText(str(obs_count))
        self.lbl_today_reg.setText(str(reg_count))
        self.lbl_today_cash.setText(f"₹ {cash_tot:.2f}")
        self.lbl_today_online.setText(f"₹ {online_tot:.2f}")
        self.lbl_today_total.setText(f"₹ {usg_tot:.2f}")

        cursor.execute("SELECT COUNT(*), SUM(cash_amount), SUM(online_amount) FROM child_patients WHERE reg_date=?", (selected_date,))
        c_res = cursor.fetchone()
        c_patients = c_res[0] or 0
        c_cash = c_res[1] or 0.0
        c_online = c_res[2] or 0.0
        c_tot = c_cash + c_online

        self.lbl_child_today_count.setText(str(c_patients))
        self.lbl_child_today_cash.setText(f"₹ {c_cash:.2f}")
        self.lbl_child_today_online.setText(f"₹ {c_online:.2f}")
        self.lbl_child_today_total.setText(f"₹ {c_tot:.2f}")

        conn.close()
        self.update_monthly_dashboard()
        self.update_fy_dashboard()

    def update_monthly_dashboard(self):
        m = self.cmb_month.currentText()
        y = self.cmb_year.currentText()

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*), SUM(cash_amount), SUM(online_amount), SUM(cash_amount + online_amount) FROM patients WHERE reg_date LIKE ?", (f'%/{m}/{y}',))
        res = cursor.fetchone()
        m_patients = res[0] or 0
        m_cash = res[1] or 0.0
        m_online = res[2] or 0.0
        m_total_biz = res[3] or 0.0

        cursor.execute("SELECT COUNT(*) FROM patients WHERE reg_date LIKE ? AND scan_type='Obstetrics Scan'", (f'%/{m}/{y}',))
        m_obs = cursor.fetchone()[0] or 0

        cursor.execute("SELECT COUNT(*) FROM patients WHERE reg_date LIKE ? AND scan_type='Regular Scan'", (f'%/{m}/{y}',))
        m_reg = cursor.fetchone()[0] or 0

        self.lbl_month_tot_patients.setText(str(m_patients))
        self.lbl_month_obs_patients.setText(str(m_obs))
        self.lbl_month_reg_patients.setText(str(m_reg))
        self.lbl_month_cash.setText(f"₹ {m_cash:.2f}")
        self.lbl_month_online.setText(f"₹ {m_online:.2f}")
        self.lbl_month_total_business.setText(f"₹ {m_total_biz:.2f}")

        cursor.execute("SELECT COUNT(*), SUM(cash_amount), SUM(online_amount), SUM(cash_amount + online_amount) FROM child_patients WHERE reg_date LIKE ?", (f'%/{m}/{y}',))
        c_res = cursor.fetchone()
        cm_patients = c_res[0] or 0
        cm_cash = c_res[1] or 0.0
        cm_online = c_res[2] or 0.0
        cm_total_biz = c_res[3] or 0.0

        self.lbl_child_m_tot_patients.setText(str(cm_patients))
        self.lbl_child_m_cash.setText(f"₹ {cm_cash:.2f}")
        self.lbl_child_m_online.setText(f"₹ {cm_online:.2f}")
        self.lbl_child_m_total_business.setText(f"₹ {cm_total_biz:.2f}")

        conn.close()

    def update_fy_dashboard(self):
        start_year = self.cmb_fy.currentData()
        if not start_year:
            return

        start_date = datetime(start_year, 4, 1)
        end_date = datetime(start_year + 1, 3, 31)

        conn = get_connection()
        cursor = conn.cursor()

        # Query all USG patients
        cursor.execute("SELECT reg_date, scan_type FROM patients")
        usg_rows = cursor.fetchall()

        fy_usg_count = 0
        fy_usg_obs = 0
        fy_usg_reg = 0

        for r_date, s_type in usg_rows:
            if not r_date:
                continue
            try:
                dt = datetime.strptime(r_date.strip(), "%d/%m/%Y")
            except ValueError:
                continue

            if start_date <= dt <= end_date:
                fy_usg_count += 1
                if s_type == 'Obstetrics Scan':
                    fy_usg_obs += 1
                elif s_type == 'Regular Scan':
                    fy_usg_reg += 1

        self.lbl_fy_usg_patients.setText(str(fy_usg_count))
        self.lbl_fy_usg_obs.setText(str(fy_usg_obs))
        self.lbl_fy_usg_reg.setText(str(fy_usg_reg))

        # Query all Child Care patients
        cursor.execute("SELECT reg_date FROM child_patients")
        child_rows = cursor.fetchall()

        fy_child_count = 0

        for (r_date,) in child_rows:
            if not r_date:
                continue
            try:
                dt = datetime.strptime(r_date.strip(), "%d/%m/%Y")
            except ValueError:
                continue

            if start_date <= dt <= end_date:
                fy_child_count += 1

        self.lbl_fy_child_patients.setText(str(fy_child_count))

        # Combined Total Patient Count
        combined_patients = fy_usg_count + fy_child_count
        self.lbl_fy_total_patients.setText(str(combined_patients))

        conn.close()

    def export_to_excel(self):
        m = self.cmb_month.currentText()
        y = self.cmb_year.currentText()
        
        conn = get_connection()
        query = f"SELECT * FROM patients WHERE reg_date LIKE '%/{m}/{y}' ORDER BY sr_no DESC"
        df_usg = pd.read_sql_query(query, conn)
        
        query_child = f"SELECT * FROM child_patients WHERE reg_date LIKE '%/{m}/{y}' ORDER BY sr_no DESC"
        df_child = pd.read_sql_query(query_child, conn)
        conn.close()

        if df_usg.empty and df_child.empty:
            QMessageBox.warning(self, "Warning", "No data found for the selected month!")
            return

        filename, _ = QFileDialog.getSaveFileName(self, "Save Monthly Excel Report", f"Clinic_Report_{m}_{y}.xlsx", "Excel Files (*.xlsx)")
        if filename:
            with pd.ExcelWriter(filename) as writer:
                if not df_usg.empty:
                    df_usg.to_excel(writer, sheet_name='Sonography Patients', index=False)
                if not df_child.empty:
                    df_child.to_excel(writer, sheet_name='Child Care Patients', index=False)
            QMessageBox.information(self, "Success", "Excel report downloaded successfully!")

    def export_fy_to_excel(self):
        start_year = self.cmb_fy.currentData()
        if not start_year:
            return

        start_date = datetime(start_year, 4, 1)
        end_date = datetime(start_year + 1, 3, 31)

        conn = get_connection()
        df_usg_all = pd.read_sql_query("SELECT * FROM patients ORDER BY sr_no DESC", conn)
        df_child_all = pd.read_sql_query("SELECT * FROM child_patients ORDER BY sr_no DESC", conn)
        conn.close()

        def filter_by_date(df):
            if df.empty:
                return df
            valid_indices = []
            for idx, row in df.iterrows():
                r_date = row.get('reg_date')
                if not r_date:
                    continue
                try:
                    dt = datetime.strptime(str(r_date).strip(), "%d/%m/%Y")
                    if start_date <= dt <= end_date:
                        valid_indices.append(idx)
                except ValueError:
                    continue
            return df.loc[valid_indices]

        df_usg_fy = filter_by_date(df_usg_all)
        df_child_fy = filter_by_date(df_child_all)

        if df_usg_fy.empty and df_child_fy.empty:
            QMessageBox.warning(self, "Warning", "No data found for the selected Financial Year!")
            return

        fy_str = f"FY_{start_year}_{str(start_year+1)[2:]}"
        filename, _ = QFileDialog.getSaveFileName(self, "Save Financial Year Excel Report", f"Clinic_Report_{fy_str}.xlsx", "Excel Files (*.xlsx)")
        if filename:
            with pd.ExcelWriter(filename) as writer:
                if not df_usg_fy.empty:
                    df_usg_fy.to_excel(writer, sheet_name='Sonography Patients', index=False)
                if not df_child_fy.empty:
                    df_child_fy.to_excel(writer, sheet_name='Child Care Patients', index=False)
            QMessageBox.information(self, "Success", "Financial Year Excel report downloaded successfully!")

    # ---------------- 2. DUAL REGISTRATION FORM ----------------
    def setup_entry_form(self):
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(20)

        box_usg = QGroupBox("Sonography Patient Registration / Edit")
        usg_layout = QFormLayout()
        usg_layout.setSpacing(10)

        self.inp_date = QDateEdit()
        self.inp_date.setCalendarPopup(True)
        self.inp_date.setDisplayFormat("dd/MM/yyyy")
        self.inp_date.setDate(QDate.currentDate())

        self.inp_pname = QLineEdit()
        self.inp_age = QLineEdit()
        self.cmb_sex = QComboBox()
        self.cmb_sex.addItems(["Male", "Female", "Other"])
        self.inp_mobile = QLineEdit()
        
        self.cmb_pdoctor = QComboBox()
        self.cmb_pscan = QComboBox()
        self.cmb_pscan.currentIndexChanged.connect(self.on_scan_selected)
        
        self.inp_rate = QLineEdit()
        self.inp_discount = QDoubleSpinBox()
        self.inp_discount.setMaximum(100000)

        self.cmb_paymode = QComboBox()
        self.cmb_paymode.addItems(["Cash", "Online/UPI", "Card", "Partial", "Pending / Unpaid"])
        self.cmb_paymode.currentIndexChanged.connect(self.toggle_partial_inputs)

        self.inp_cash = QDoubleSpinBox()
        self.inp_cash.setMaximum(100000)
        self.inp_online = QDoubleSpinBox()
        self.inp_online.setMaximum(100000)
        self.inp_cash.setEnabled(False)
        self.inp_online.setEnabled(False)

        usg_layout.addRow("Date:", self.inp_date)
        usg_layout.addRow("Patient Name:", self.inp_pname)
        usg_layout.addRow("Age:", self.inp_age)
        usg_layout.addRow("Sex:", self.cmb_sex)
        usg_layout.addRow("Mobile No:", self.inp_mobile)
        usg_layout.addRow("Referred Doctor:", self.cmb_pdoctor)
        usg_layout.addRow("USG Scan:", self.cmb_pscan)
        usg_layout.addRow("Scan Rate (₹):", self.inp_rate)
        usg_layout.addRow("Discount (₹):", self.inp_discount)
        usg_layout.addRow("Payment Mode:", self.cmb_paymode)
        usg_layout.addRow("Cash Paid (₹):", self.inp_cash)
        usg_layout.addRow("Online Paid (₹):", self.inp_online)

        btn_usg_layout = QHBoxLayout()
        self.btn_save = QPushButton("Save USG Details")
        self.btn_save.clicked.connect(lambda: self.save_patient(print_bill=False))
        
        self.btn_save_print = QPushButton("Save & Print Bill")
        self.btn_save_print.setObjectName("btn_print")
        self.btn_save_print.clicked.connect(lambda: self.save_patient(print_bill=True))

        btn_clear_form = QPushButton("Clear")
        btn_clear_form.setObjectName("btn_clear")
        btn_clear_form.clicked.connect(self.clear_form)

        btn_usg_layout.addWidget(self.btn_save)
        btn_usg_layout.addWidget(self.btn_save_print)
        btn_usg_layout.addWidget(btn_clear_form)
        usg_layout.addRow(btn_usg_layout)

        box_usg.setLayout(usg_layout)

        box_child = QGroupBox("Child Care Patient Registration / Edit")
        child_layout = QFormLayout()
        child_layout.setSpacing(12)

        self.inp_child_date = QDateEdit()
        self.inp_child_date.setCalendarPopup(True)
        self.inp_child_date.setDisplayFormat("dd/MM/yyyy")
        self.inp_child_date.setDate(QDate.currentDate())

        self.cmb_child_title = QComboBox()
        self.cmb_child_title.addItems(["Master", "Baby", "Miss", "Mr"])

        self.inp_child_name = QLineEdit()
        
        self.inp_child_age_year = QLineEdit()
        self.inp_child_age_year.setPlaceholderText("Years")
        self.inp_child_age_month = QLineEdit()
        self.inp_child_age_month.setPlaceholderText("Months")
        self.inp_child_age_day = QLineEdit()
        self.inp_child_age_day.setPlaceholderText("Days")
        
        lay_age = QHBoxLayout()
        lay_age.setContentsMargins(0, 0, 0, 0)
        lay_age.addWidget(self.inp_child_age_year)
        lay_age.addWidget(QLabel("Years"))
        lay_age.addWidget(self.inp_child_age_month)
        lay_age.addWidget(QLabel("Months"))
        lay_age.addWidget(self.inp_child_age_day)
        lay_age.addWidget(QLabel("Days"))

        self.inp_child_mobile = QLineEdit()

        child_layout.addRow("Date:", self.inp_child_date)
        child_layout.addRow("Title:", self.cmb_child_title)
        child_layout.addRow("Patient Name:", self.inp_child_name)
        child_layout.addRow("Age:", lay_age)
        child_layout.addRow("Mobile No:", self.inp_child_mobile)

        btn_child_layout = QHBoxLayout()
        self.btn_save_child = QPushButton("Save Child Details")
        self.btn_save_child.clicked.connect(lambda: self.save_child_patient(print_bill=False))

        self.btn_save_child_print = QPushButton("Save & Print Bill")
        self.btn_save_child_print.setObjectName("btn_print")
        self.btn_save_child_print.clicked.connect(lambda: self.save_child_patient(print_bill=True))

        btn_clear_child = QPushButton("Clear")
        btn_clear_child.setObjectName("btn_clear")
        btn_clear_child.clicked.connect(self.clear_child_form)

        btn_child_layout.addWidget(self.btn_save_child)
        btn_child_layout.addWidget(self.btn_save_child_print)
        btn_child_layout.addWidget(btn_clear_child)

        child_layout.addRow(btn_child_layout)
        box_child.setLayout(child_layout)

        main_layout.addWidget(box_usg, 1)
        main_layout.addWidget(box_child, 1)
        self.tab_entry.setLayout(main_layout)

    def on_scan_selected(self):
        sname = self.cmb_pscan.currentText()
        if not sname:
            return
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT price FROM usg_scans WHERE scan_name=?", (sname,))
        res = cursor.fetchone()
        conn.close()
        if res:
            self.inp_rate.setText(str(res[0]))

    def toggle_partial_inputs(self):
        mode = self.cmb_paymode.currentText()
        try:
            rate = float(self.inp_rate.text() or 0.0)
        except ValueError:
            rate = 0.0
        disc = self.inp_discount.value()
        payable = max(0.0, rate - disc)

        if mode == "Cash":
            self.inp_cash.setEnabled(True)
            self.inp_cash.setValue(payable)
            self.inp_online.setEnabled(False)
            self.inp_online.setValue(0.0)
        elif mode in ["Online/UPI", "Card"]:
            self.inp_cash.setEnabled(False)
            self.inp_cash.setValue(0.0)
            self.inp_online.setEnabled(True)
            self.inp_online.setValue(payable)
        elif mode == "Partial":
            self.inp_cash.setEnabled(True)
            self.inp_online.setEnabled(True)
            self.inp_cash.setValue(payable / 2)
            self.inp_online.setValue(payable / 2)
        else:
            self.inp_cash.setEnabled(False)
            self.inp_cash.setValue(0.0)
            self.inp_online.setEnabled(False)
            self.inp_online.setValue(0.0)

    def save_patient(self, print_bill=False):
        date_str = self.inp_date.date().toString("dd/MM/yyyy")
        pname = self.inp_pname.text().strip()
        age = self.inp_age.text().strip()
        sex = self.cmb_sex.currentText()
        mobile = self.inp_mobile.text().strip()
        doctor = self.cmb_pdoctor.currentText()
        scan = self.cmb_pscan.currentText()
        
        try:
            rate = float(self.inp_rate.text().strip() or 0.0)
        except ValueError:
            rate = 0.0
            
        discount = self.inp_discount.value()
        paymode = self.cmb_paymode.currentText()
        cash = self.inp_cash.value()
        online = self.inp_online.value()

        if not pname or not scan:
            QMessageBox.warning(self, "Error", "Patient Name and USG Scan are required!")
            return

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT scan_type FROM usg_scans WHERE scan_name=?", (scan,))
        scan_type_res = cursor.fetchone()
        scan_type = scan_type_res[0] if scan_type_res else "Regular Scan"

        p_status = "Pending" if paymode == "Pending / Unpaid" else "Paid"

        if self.selected_patient_id:
            cursor.execute('''
                UPDATE patients 
                SET reg_date=?, patient_name=?, age=?, sex=?, mobile=?, doctor_name=?, usg_scan=?, scan_type=?, usg_rate=?, discount=?, payment_mode=?, cash_amount=?, online_amount=?, payment_status=?
                WHERE sr_no=?
            ''', (date_str, pname, age, sex, mobile, doctor, scan, scan_type, rate, discount, paymode, cash, online, p_status, self.selected_patient_id))
            patient_id = self.selected_patient_id
            QMessageBox.information(self, "Success", "USG Patient details updated successfully!")
        else:
            cursor.execute('''
                INSERT INTO patients (reg_date, patient_name, age, sex, mobile, doctor_name, usg_scan, scan_type, usg_rate, discount, payment_mode, cash_amount, online_amount, payment_status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (date_str, pname, age, sex, mobile, doctor, scan, scan_type, rate, discount, paymode, cash, online, p_status))
            patient_id = cursor.lastrowid
            QMessageBox.information(self, "Success", "New USG Patient saved successfully!")

        conn.commit()
        conn.close()

        if print_bill:
            self.generate_pdf_bill(patient_id, date_str, pname, age, sex, mobile, doctor, scan, rate, discount, paymode, cash, online)

        self.clear_form()
        self.refresh_patient_table()
        self.update_dashboard()
        self.tabs.setCurrentIndex(2)

    def save_child_patient(self, print_bill=False):
        date_str = self.inp_child_date.date().toString("dd/MM/yyyy")
        title = self.cmb_child_title.currentText()
        pname = self.inp_child_name.text().strip()
        
        y_str = self.inp_child_age_year.text().strip()
        m_str = self.inp_child_age_month.text().strip()
        d_str = self.inp_child_age_day.text().strip()
        
        age_parts = []
        if y_str: age_parts.append(f"{y_str} Y")
        if m_str: age_parts.append(f"{m_str} M")
        if d_str: age_parts.append(f"{d_str} D")
        age = " ".join(age_parts)
        
        mobile = self.inp_child_mobile.text().strip()

        if not pname:
            QMessageBox.warning(self, "Error", "Child Patient Name is required!")
            return

        conn = get_connection()
        cursor = conn.cursor()

        if self.selected_child_id:
            cursor.execute('''
                UPDATE child_patients 
                SET reg_date=?, title=?, patient_name=?, age=?, mobile=?
                WHERE sr_no=?
            ''', (date_str, title, pname, age, mobile, self.selected_child_id))
            child_id = self.selected_child_id
            QMessageBox.information(self, "Success", "Child Patient details updated successfully!")
        else:
            cursor.execute('''
                INSERT INTO child_patients (reg_date, title, patient_name, age, mobile)
                VALUES (?, ?, ?, ?, ?)
            ''', (date_str, title, pname, age, mobile))
            child_id = cursor.lastrowid
            QMessageBox.information(self, "Success", "New Child Patient saved successfully!")

        conn.commit()
        
        cursor.execute("SELECT given_vaccines, total_amount, discount, payment_mode, cash_amount, online_amount FROM child_patients WHERE sr_no=?", (child_id,))
        c_data = cursor.fetchone()
        conn.close()

        if print_bill and c_data:
            full_pname = f"{title} {pname}".strip()
            self.generate_child_pdf_bill(
                child_id, date_str, full_pname, age, mobile,
                c_data[0] or "", c_data[1] or 0.0, c_data[2] or 0.0,
                c_data[3] or "Pending", c_data[4] or 0.0, c_data[5] or 0.0
            )

        self.clear_child_form()
        self.refresh_child_table()
        self.update_dashboard()
        self.tabs.setCurrentIndex(3)

    def clear_form(self):
        self.selected_patient_id = None
        self.inp_date.setDate(QDate.currentDate())
        self.inp_pname.clear()
        self.inp_age.clear()
        self.cmb_sex.setCurrentIndex(0)
        self.inp_mobile.clear()
        if self.cmb_pdoctor.count() > 0: self.cmb_pdoctor.setCurrentIndex(0)
        if self.cmb_pscan.count() > 0: self.cmb_pscan.setCurrentIndex(0)
        self.inp_rate.clear()
        self.inp_discount.setValue(0.0)
        self.cmb_paymode.setCurrentIndex(0)
        self.inp_cash.setValue(0.0)
        self.inp_online.setValue(0.0)
        self.btn_save.setText("Save USG Details")

    def clear_child_form(self):
        self.selected_child_id = None
        self.inp_child_date.setDate(QDate.currentDate())
        self.cmb_child_title.setCurrentIndex(0)
        self.inp_child_name.clear()
        self.inp_child_age_year.clear()
        self.inp_child_age_month.clear()
        self.inp_child_age_day.clear()
        self.inp_child_mobile.clear()
        self.btn_save_child.setText("Save Child Details")

    # ---------------- 3. SONOGRAPHY REGISTER TABLE ----------------
    def setup_usg_register_table(self):
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(15, 15, 15, 15)

        filter_box = QGroupBox("Search & Filter Options")
        filter_layout = QHBoxLayout()

        self.cmb_usg_date = QDateEdit()
        self.cmb_usg_date.setCalendarPopup(True)
        self.cmb_usg_date.setDisplayFormat("dd/MM/yyyy")
        self.cmb_usg_date.setDate(QDate.currentDate())
        self.cmb_usg_date.dateChanged.connect(self.refresh_patient_table)

        self.inp_search = QLineEdit()
        self.inp_search.setPlaceholderText("Search Name...")
        self.inp_search.textChanged.connect(self.filter_patient_table)

        self.cmb_filter_doc = QComboBox()
        self.cmb_filter_doc.currentIndexChanged.connect(self.filter_by_doctor)

        btn_clear_filter = QPushButton("Clear Filters")
        btn_clear_filter.setObjectName("btn_clear")
        btn_clear_filter.clicked.connect(self.reset_patient_filter)

        self.lbl_usg_reg_count = QLabel("Daily Patients: 0")
        self.lbl_usg_reg_count.setStyleSheet("color: #f9e2af; font-size: 13px; font-weight: bold; margin-left: 10px;")

        filter_layout.addWidget(QLabel("Date:"))
        filter_layout.addWidget(self.cmb_usg_date)
        filter_layout.addWidget(QLabel("Search:"))
        filter_layout.addWidget(self.inp_search, 2)
        filter_layout.addWidget(QLabel("Filter Doctor:"))
        filter_layout.addWidget(self.cmb_filter_doc, 2)
        filter_layout.addWidget(btn_clear_filter)
        filter_layout.addWidget(self.lbl_usg_reg_count)
        filter_box.setLayout(filter_layout)

        self.table_patients = QTableWidget()
        self.table_patients.setColumnCount(15)
        self.table_patients.setHorizontalHeaderLabels([
            "Sr.No", "Date", "Name", "Age", "Sex", "Mobile", 
            "Doctor", "USG Scan", "Payable Rate", "Discount (₹)", "Payment Mode", "Cash", "Online", "Status", "Action"
        ])
        
        self.table_patients.setWordWrap(True)
        self.table_patients.verticalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        
        header = self.table_patients.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Interactive)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(6, QHeaderView.Stretch)
        header.setSectionResizeMode(7, QHeaderView.Stretch)

        self.table_patients.doubleClicked.connect(self.on_table_double_click)

        main_layout.addWidget(filter_box)
        main_layout.addWidget(self.table_patients)
        self.tab_usg_register.setLayout(main_layout)

    def refresh_patient_table(self):
        selected_d = self.cmb_usg_date.date().toString("dd/MM/yyyy")

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM patients WHERE reg_date = ?", (selected_d,))
        d_count = cursor.fetchone()[0] or 0
        self.lbl_usg_reg_count.setText(f"Daily Patients: {d_count}")

        cursor.execute("SELECT sr_no, reg_date, patient_name, age, sex, mobile, doctor_name, usg_scan, usg_rate, discount, payment_mode, cash_amount, online_amount, payment_status FROM patients WHERE reg_date = ? ORDER BY sr_no ASC", (selected_d,))
        rows = cursor.fetchall()
        conn.close()

        self.table_patients.setUpdatesEnabled(False)
        self.table_patients.setRowCount(0)

        for row_idx, row_data in enumerate(rows):
            self.table_patients.insertRow(row_idx)
            formatted_date = format_display_date(row_data[1])
            db_sr_no = row_data[0]
            daily_count = row_idx + 1

            rate_val = row_data[8] or 0.0
            disc_val = row_data[9] or 0.0
            payable_rate = max(0.0, rate_val - disc_val)

            display_row = [
                daily_count, formatted_date, row_data[2], row_data[3],
                row_data[4], row_data[5], row_data[6], row_data[7],
                f"₹ {payable_rate:.2f}", f"₹ {disc_val:.2f}", row_data[10],
                f"₹ {(row_data[11] or 0.0):.2f}", f"₹ {(row_data[12] or 0.0):.2f}"
            ]

            for col_idx in range(13):
                val = display_row[col_idx]
                item = QTableWidgetItem(str(val) if val is not None else "")
                item.setFont(QFont("Segoe UI", 9, QFont.Bold))
                item.setTextAlignment(Qt.AlignCenter)
                self.table_patients.setItem(row_idx, col_idx, item)

            status = row_data[13] or "Paid"
            status_item = QTableWidgetItem()
            status_item.setFont(QFont("Segoe UI", 10, QFont.Bold))
            status_item.setTextAlignment(Qt.AlignCenter)

            if status == "Pending":
                status_item.setText("⏳ Pending")
                status_item.setForeground(Qt.red)
            else:
                status_item.setText("✅ Paid")
                status_item.setForeground(Qt.green)
            self.table_patients.setItem(row_idx, 13, status_item)

            action_widget = QWidget()
            action_layout = QHBoxLayout(action_widget)
            action_layout.setContentsMargins(2, 2, 2, 2)
            action_layout.setSpacing(4)
            action_layout.setAlignment(Qt.AlignCenter)

            if status == "Pending":
                btn_cap = QPushButton("💳")
                btn_cap.setToolTip("Capture Payment")
                btn_cap.setObjectName("btn_capture")
                btn_cap.clicked.connect(lambda checked, s=db_sr_no, r=rate_val, d=disc_val: self.open_capture_payment_dialog(s, r, d))
                action_layout.addWidget(btn_cap)

            btn_del = QPushButton("🗑️")
            btn_del.setObjectName("btn_delete")
            btn_del.clicked.connect(lambda checked, s=db_sr_no, name=row_data[2]: self.delete_patient(s, name))
            action_layout.addWidget(btn_del)

            self.table_patients.setCellWidget(row_idx, 14, action_widget)

        self.table_patients.setUpdatesEnabled(True)

    def open_capture_payment_dialog(self, sr_no, total_rate, existing_discount=0.0):
        dialog = CapturePaymentDialog(sr_no, total_rate, existing_discount, self)
        if dialog.exec_() == QDialog.Accepted:
            paymode, disc, cash, online = dialog.get_data()
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE patients 
                SET discount=?, payment_mode=?, cash_amount=?, online_amount=?, payment_status='Paid'
                WHERE sr_no=?
            ''', (disc, paymode, cash, online, sr_no))
            conn.commit()
            conn.close()
            QMessageBox.information(self, "Success", "Payment details captured successfully!")
            self.refresh_patient_table()
            self.update_dashboard()

    def filter_patient_table(self):
        search_text = self.inp_search.text().lower().strip()
        for row in range(self.table_patients.rowCount()):
            name_item = self.table_patients.item(row, 2)
            show = False
            if name_item and search_text in name_item.text().lower(): show = True
            self.table_patients.setRowHidden(row, not show)

    def filter_by_doctor(self):
        doc_filter = self.cmb_filter_doc.currentText()
        if doc_filter == "All Doctors":
            for row in range(self.table_patients.rowCount()):
                self.table_patients.setRowHidden(row, False)
            return

        for row in range(self.table_patients.rowCount()):
            doc_item = self.table_patients.item(row, 6)
            show = doc_item and doc_item.text() == doc_filter
            self.table_patients.setRowHidden(row, not show)

    def reset_patient_filter(self):
        self.inp_search.clear()
        self.cmb_filter_doc.setCurrentIndex(0)
        for row in range(self.table_patients.rowCount()):
            self.table_patients.setRowHidden(row, False)

    def delete_patient(self, sr_no, p_name):
        reply = QMessageBox.question(self, 'Confirm Delete', f"Are you sure you want to delete patient '{p_name}'?", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM patients WHERE sr_no=?", (sr_no,))
            conn.commit()
            conn.close()

            self.refresh_patient_table()
            self.update_dashboard()

    def on_table_double_click(self, index):
        row = index.row()
        selected_d = self.cmb_usg_date.date().toString("dd/MM/yyyy")

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT sr_no, reg_date, patient_name, age, sex, mobile, doctor_name, usg_scan, usg_rate, discount, payment_mode, cash_amount, online_amount FROM patients WHERE reg_date = ? ORDER BY sr_no ASC", (selected_d,))
        rows = cursor.fetchall()
        conn.close()

        if row < len(rows):
            data = rows[row]
            p_name = data[2]
            dialog = PatientActionDialog(p_name, self)
            if dialog.exec_() == QDialog.Accepted:
                if dialog.selected_action == "UPDATE":
                    self.selected_patient_id = data[0]
                    if data[1]:
                        qdt = QDate.fromString(data[1], "dd/MM/yyyy")
                        if qdt.isValid(): self.inp_date.setDate(qdt)
                    self.inp_pname.setText(str(data[2] or ""))
                    self.inp_age.setText(str(data[3] or ""))
                    self.cmb_sex.setCurrentText(str(data[4] or "Male"))
                    self.inp_mobile.setText(str(data[5] or ""))
                    self.cmb_pdoctor.setCurrentText(str(data[6] or ""))
                    self.cmb_pscan.setCurrentText(str(data[7] or ""))
                    self.inp_rate.setText(str(data[8] or 0.0))
                    self.inp_discount.setValue(data[9] or 0.0)
                    self.cmb_paymode.setCurrentText(str(data[10] or "Cash"))
                    self.inp_cash.setValue(data[11] or 0.0)
                    self.inp_online.setValue(data[12] or 0.0)
                    self.btn_save.setText("Update USG Details")
                    self.tabs.setCurrentIndex(1)

                elif dialog.selected_action == "PRINT":
                    self.generate_pdf_bill(
                        data[0], data[1], data[2], data[3], data[4], data[5],
                        data[6], data[7], data[8] or 0.0, data[9] or 0.0,
                        data[10] or "Cash", data[11] or 0.0, data[12] or 0.0
                    )

    # ---------------- 4. CHILD CARE REGISTER TABLE ----------------
    def setup_child_register_table(self):
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(15, 15, 15, 15)

        filter_box = QGroupBox("Search Child Patients")
        filter_layout = QHBoxLayout()

        self.cmb_child_date = QDateEdit()
        self.cmb_child_date.setCalendarPopup(True)
        self.cmb_child_date.setDisplayFormat("dd/MM/yyyy")
        self.cmb_child_date.setDate(QDate.currentDate())
        self.cmb_child_date.dateChanged.connect(self.refresh_child_table)

        self.inp_search_child = QLineEdit()
        self.inp_search_child.setPlaceholderText("Search Child Name...")
        self.inp_search_child.textChanged.connect(self.filter_child_table)

        btn_clear = QPushButton("Clear Search")
        btn_clear.setObjectName("btn_clear")
        btn_clear.clicked.connect(lambda: self.inp_search_child.clear())

        self.lbl_child_reg_count = QLabel("Daily Patients: 0")
        self.lbl_child_reg_count.setStyleSheet("color: #f9e2af; font-size: 13px; font-weight: bold; margin-left: 10px;")

        filter_layout.addWidget(QLabel("Date:"))
        filter_layout.addWidget(self.cmb_child_date)
        filter_layout.addWidget(QLabel("Search:"))
        filter_layout.addWidget(self.inp_search_child, 3)
        filter_layout.addWidget(btn_clear)
        filter_layout.addWidget(self.lbl_child_reg_count)
        filter_box.setLayout(filter_layout)

        self.table_child = QTableWidget()
        self.table_child.setColumnCount(13)
        
        self.table_child.setHorizontalHeaderLabels([
            "Sr.No", "Date", "Title", "Patient Name", "Age", "Mobile",
            "Particulars", "Payable Total (₹)", "Discount (₹)", "Payment Mode", "Status", "Add Particulars", "Action"
        ])

        self.table_child.setWordWrap(True)
        self.table_child.verticalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        
        header = self.table_child.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Interactive)
        header.setSectionResizeMode(3, QHeaderView.Stretch)
        header.setSectionResizeMode(6, QHeaderView.Stretch)

        self.table_child.doubleClicked.connect(self.on_child_double_click)

        main_layout.addWidget(filter_box)
        main_layout.addWidget(self.table_child)
        self.tab_child_register.setLayout(main_layout)

    def refresh_child_table(self):
        selected_d = self.cmb_child_date.date().toString("dd/MM/yyyy")

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM child_patients WHERE reg_date = ?", (selected_d,))
        d_count = cursor.fetchone()[0] or 0
        self.lbl_child_reg_count.setText(f"Daily Patients: {d_count}")

        cursor.execute("SELECT sr_no, reg_date, title, patient_name, age, mobile, given_vaccines, total_amount, discount, payment_mode, cash_amount, online_amount, payment_status FROM child_patients WHERE reg_date = ? ORDER BY sr_no ASC", (selected_d,))
        rows = cursor.fetchall()
        conn.close()

        self.table_child.setUpdatesEnabled(False)
        self.table_child.setRowCount(0)

        for row_idx, row_data in enumerate(rows):
            self.table_child.insertRow(row_idx)
            formatted_date = format_display_date(row_data[1])
            db_sr_no = row_data[0]
            daily_count = row_idx + 1

            total_amt = row_data[7] or 0.0
            disc_val = row_data[8] or 0.0
            payable_amt = max(0.0, total_amt - disc_val)

            display_row = [
                daily_count, formatted_date, row_data[2], row_data[3],
                row_data[4], row_data[5], row_data[6] or "",
                f"₹ {payable_amt:.2f}", f"₹ {disc_val:.2f}", row_data[9] or "Pending"
            ]

            for col_idx in range(10):
                val = display_row[col_idx]
                item = QTableWidgetItem(str(val) if val is not None else "")
                item.setFont(QFont("Segoe UI", 9, QFont.Bold))
                item.setTextAlignment(Qt.AlignCenter)
                self.table_child.setItem(row_idx, col_idx, item)

            status = row_data[12] or "Pending"
            status_item = QTableWidgetItem()
            status_item.setFont(QFont("Segoe UI", 10, QFont.Bold))
            status_item.setTextAlignment(Qt.AlignCenter)

            if status == "Pending":
                status_item.setText("⏳ Pending")
                status_item.setForeground(Qt.red)
            else:
                status_item.setText("✅ Paid")
                status_item.setForeground(Qt.green)
            self.table_child.setItem(row_idx, 10, status_item)

            btn_add = QPushButton("➕ Billing")
            btn_add.setObjectName("btn_add_bill")
            btn_add.clicked.connect(lambda checked, s=db_sr_no, curr_v=row_data[6]: self.open_vaccine_selection(s, curr_v))
            self.table_child.setCellWidget(row_idx, 11, btn_add)

            action_widget = QWidget()
            action_layout = QHBoxLayout(action_widget)
            action_layout.setContentsMargins(2, 2, 2, 2)
            action_layout.setSpacing(4)
            action_layout.setAlignment(Qt.AlignCenter)

            if status == "Pending":
                btn_cap = QPushButton("💳")
                btn_cap.setToolTip("Capture Payment")
                btn_cap.setObjectName("btn_capture")
                btn_cap.clicked.connect(lambda checked, s=db_sr_no, r=total_amt, d=disc_val: self.open_child_capture_payment_dialog(s, r, d))
                action_layout.addWidget(btn_cap)

            btn_del = QPushButton("🗑️")
            btn_del.setObjectName("btn_delete")
            btn_del.clicked.connect(lambda checked, s=db_sr_no, name=row_data[3]: self.delete_child_patient(s, name))
            action_layout.addWidget(btn_del)

            self.table_child.setCellWidget(row_idx, 12, action_widget)

        self.table_child.setUpdatesEnabled(True)

    def open_vaccine_selection(self, sr_no, current_selected):
        dialog = SelectVaccinesDialog(current_selected or "", self)
        if dialog.exec_() == QDialog.Accepted:
            selected_items = dialog.get_selected()
            given_str = ", ".join(selected_items)
            
            tot_amt = 0.0
            for item in selected_items:
                m = re.search(r'\(₹\s*([\d.]+)\)', item)
                if m:
                    tot_amt += float(m.group(1))

            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE child_patients 
                SET given_vaccines=?, total_amount=?
                WHERE sr_no=?
            ''', (given_str, tot_amt, sr_no))
            conn.commit()
            conn.close()

            self.refresh_child_table()

    def open_child_capture_payment_dialog(self, sr_no, total_rate, existing_discount=0.0):
        dialog = CapturePaymentDialog(sr_no, total_rate, existing_discount, self)
        if dialog.exec_() == QDialog.Accepted:
            paymode, disc, cash, online = dialog.get_data()
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE child_patients 
                SET discount=?, payment_mode=?, cash_amount=?, online_amount=?, payment_status='Paid'
                WHERE sr_no=?
            ''', (disc, paymode, cash, online, sr_no))
            conn.commit()
            conn.close()
            QMessageBox.information(self, "Success", "Child Payment captured successfully!")
            self.refresh_child_table()
            self.update_dashboard()

    def filter_child_table(self):
        search_txt = self.inp_search_child.text().lower().strip()
        for row in range(self.table_child.rowCount()):
            name_item = self.table_child.item(row, 3)
            show = False
            if name_item and search_txt in name_item.text().lower(): show = True
            self.table_child.setRowHidden(row, not show)

    def delete_child_patient(self, sr_no, p_name):
        reply = QMessageBox.question(self, 'Confirm Delete', f"Are you sure you want to delete child patient '{p_name}'?", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM child_patients WHERE sr_no=?", (sr_no,))
            conn.commit()
            conn.close()

            self.refresh_child_table()
            self.update_dashboard()

    def on_child_double_click(self, index):
        row = index.row()
        selected_d = self.cmb_child_date.date().toString("dd/MM/yyyy")

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT sr_no, reg_date, title, patient_name, age, mobile FROM child_patients WHERE reg_date = ? ORDER BY sr_no ASC", (selected_d,))
        rows = cursor.fetchall()
        conn.close()

        if row < len(rows):
            data = rows[row]
            p_name = f"{data[2] or ''} {data[3] or ''}".strip()
            dialog = PatientActionDialog(p_name, self)
            if dialog.exec_() == QDialog.Accepted:
                if dialog.selected_action == "UPDATE":
                    self.selected_child_id = data[0]
                    if data[1]:
                        qdt = QDate.fromString(data[1], "dd/MM/yyyy")
                        if qdt.isValid(): self.inp_child_date.setDate(qdt)
                    self.cmb_child_title.setCurrentText(str(data[2] or "Master"))
                    self.inp_child_name.setText(str(data[3] or ""))
                    
                    age_str = str(data[4] or "")
                    y_m = re.search(r'(\d+)\s*Y', age_str)
                    m_m = re.search(r'(\d+)\s*M', age_str)
                    d_m = re.search(r'(\d+)\s*D', age_str)
                    
                    self.inp_child_age_year.setText(y_m.group(1) if y_m else "")
                    self.inp_child_age_month.setText(m_m.group(1) if m_m else "")
                    self.inp_child_age_day.setText(d_m.group(1) if d_m else "")
                    
                    self.inp_child_mobile.setText(str(data[5] or ""))
                    self.btn_save_child.setText("Update Child Details")
                    self.tabs.setCurrentIndex(1)

                elif dialog.selected_action == "PRINT":
                    conn = get_connection()
                    cursor = conn.cursor()
                    cursor.execute("SELECT given_vaccines, total_amount, discount, payment_mode, cash_amount, online_amount FROM child_patients WHERE sr_no=?", (data[0],))
                    c_data = cursor.fetchone()
                    conn.close()
                    if c_data:
                        self.generate_child_pdf_bill(
                            data[0], data[1], p_name, data[4], data[5],
                            c_data[0] or "", c_data[1] or 0.0, c_data[2] or 0.0,
                            c_data[3] or "Pending", c_data[4] or 0.0, c_data[5] or 0.0
                        )

    # ---------------- 5. VACCINE REGISTER TAB ----------------
    def setup_vaccine_register_tab(self):
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(15, 15, 15, 15)

        filter_box = QGroupBox("Vaccine Register Filter & Search (Date / Patient / Month)")
        filter_layout = QHBoxLayout()

        self.vac_filter_from_date = QDateEdit()
        self.vac_filter_from_date.setCalendarPopup(True)
        self.vac_filter_from_date.setDisplayFormat("dd/MM/yyyy")
        self.vac_filter_from_date.setDate(QDate.currentDate().addDays(-30))

        self.vac_filter_to_date = QDateEdit()
        self.vac_filter_to_date.setCalendarPopup(True)
        self.vac_filter_to_date.setDisplayFormat("dd/MM/yyyy")
        self.vac_filter_to_date.setDate(QDate.currentDate())

        self.inp_search_vac_reg = QLineEdit()
        self.inp_search_vac_reg.setPlaceholderText("Search Patient Name / Vaccine...")
        self.inp_search_vac_reg.textChanged.connect(self.refresh_vaccine_register)

        btn_apply_vac_filter = QPushButton("Apply Date Filter")
        btn_apply_vac_filter.clicked.connect(self.refresh_vaccine_register)

        btn_export_vac_excel = QPushButton("Export Vaccine Register to Excel")
        btn_export_vac_excel.setObjectName("btn_print")
        btn_export_vac_excel.clicked.connect(self.export_vaccine_register_excel)

        filter_layout.addWidget(QLabel("From:"))
        filter_layout.addWidget(self.vac_filter_from_date)
        filter_layout.addWidget(QLabel("To:"))
        filter_layout.addWidget(self.vac_filter_to_date)
        filter_layout.addWidget(btn_apply_vac_filter)
        filter_layout.addWidget(QLabel("Search:"))
        filter_layout.addWidget(self.inp_search_vac_reg, 2)
        filter_layout.addWidget(btn_export_vac_excel)

        filter_box.setLayout(filter_layout)

        self.table_vac_register = QTableWidget()
        self.table_vac_register.setColumnCount(5)
        self.table_vac_register.setHorizontalHeaderLabels([
            "Sr.No", "Date", "Patient Name", "Age", "Given Vaccines"
        ])
        
        self.table_vac_register.setWordWrap(True)
        self.table_vac_register.verticalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)

        header = self.table_vac_register.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Interactive)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(4, QHeaderView.Stretch)

        main_layout.addWidget(filter_box)
        main_layout.addWidget(self.table_vac_register)
        self.tab_vac_register.setLayout(main_layout)

    def refresh_vaccine_register(self):
        from_dt = self.vac_filter_from_date.date().toString("dd/MM/yyyy")
        to_dt = self.vac_filter_to_date.date().toString("dd/MM/yyyy")
        search_txt = self.inp_search_vac_reg.text().strip().lower()

        f_date = datetime.strptime(from_dt, "%d/%m/%Y")
        t_date = datetime.strptime(to_dt, "%d/%m/%Y")

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT vaccine_name, type FROM vaccines")
        master_type_map = {row[0].strip().lower(): (row[1] or 'Vaccine') for row in cursor.fetchall()}

        cursor.execute("SELECT sr_no, reg_date, title, patient_name, age, given_vaccines FROM child_patients WHERE given_vaccines IS NOT NULL AND given_vaccines != '' ORDER BY sr_no DESC")
        rows = cursor.fetchall()
        conn.close()

        self.table_vac_register.setUpdatesEnabled(False)
        self.table_vac_register.setRowCount(0)
        row_count = 0

        for r in rows:
            r_date_str = r[1]
            try:
                r_dt = datetime.strptime(r_date_str.strip(), "%d/%m/%Y")
            except Exception:
                continue

            if f_date <= r_dt <= t_date:
                full_patient_name = f"{r[2] or ''} {r[3] or ''}".strip()
                p_name_lower = full_patient_name.lower()
                raw_vac_str = str(r[5] or "")

                raw_items = [v.strip() for v in raw_vac_str.split(",") if v.strip()]
                filtered_vac_items = []

                for v_item in raw_items:
                    clean_v_name = re.sub(r'\[.*?\]|\(.*?\)', '', v_item).strip()
                    item_type = master_type_map.get(clean_v_name.lower(), 'Vaccine')
                    
                    if item_type == 'Vaccine':
                        filtered_vac_items.append(clean_v_name)

                if not filtered_vac_items:
                    continue

                formatted_vac_text_search = " ".join(filtered_vac_items).lower()

                if search_txt and (search_txt not in p_name_lower and search_txt not in formatted_vac_text_search):
                    continue

                formatted_vac_list = [f"{idx:02d}) {v_name}" for idx, v_name in enumerate(filtered_vac_items, start=1)]
                formatted_vac_text = "\n".join(formatted_vac_list)

                self.table_vac_register.insertRow(row_count)
                formatted_d = format_display_date(r_date_str)

                display_vals = [
                    row_count + 1,
                    formatted_d,
                    full_patient_name,
                    r[4] or "",
                    formatted_vac_text
                ]

                for col_idx in range(5):
                    item = QTableWidgetItem(str(display_vals[col_idx]))
                    item.setTextAlignment(Qt.AlignCenter)
                    self.table_vac_register.setItem(row_count, col_idx, item)

                row_count += 1

        self.table_vac_register.setUpdatesEnabled(True)

    def export_vaccine_register_excel(self):
        from_dt = self.vac_filter_from_date.date().toString("dd/MM/yyyy")
        to_dt = self.vac_filter_to_date.date().toString("dd/MM/yyyy")
        
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT vaccine_name, type FROM vaccines")
        master_type_map = {row[0].strip().lower(): (row[1] or 'Vaccine') for row in cursor.fetchall()}

        query = "SELECT sr_no, reg_date, title, patient_name, age, given_vaccines FROM child_patients WHERE given_vaccines IS NOT NULL AND given_vaccines != '' ORDER BY sr_no DESC"
        df = pd.read_sql_query(query, conn)
        conn.close()

        if df.empty:
            QMessageBox.warning(self, "Warning", "No Vaccine Register data found for export!")
            return

        export_data = []
        export_row_idx = 1
        for idx, row in df.iterrows():
            f_date = format_display_date(row['reg_date'])
            full_name = f"{row['title'] or ''} {row['patient_name'] or ''}".strip()
            
            raw_items = [v.strip() for v in str(row['given_vaccines'] or '').split(",") if v.strip()]
            filtered_vac_items = []
            
            for v_item in raw_items:
                clean_v_name = re.sub(r'\[.*?\]|\(.*?\)', '', v_item).strip()
                item_type = master_type_map.get(clean_v_name.lower(), 'Vaccine')
                if item_type == 'Vaccine':
                    filtered_vac_items.append(clean_v_name)

            if not filtered_vac_items:
                continue

            formatted_vac_list = [f"{v_i:02d}) {v_name}" for v_i, v_name in enumerate(filtered_vac_items, start=1)]
            formatted_vac_text = "\n".join(formatted_vac_list)

            export_data.append({
                "Sr No": export_row_idx,
                "Date": f_date,
                "Patient Name": full_name,
                "Age": row['age'] or "",
                "Given Vaccines": formatted_vac_text
            })
            export_row_idx += 1

        if not export_data:
            QMessageBox.warning(self, "Warning", "No Vaccination records match the filter!")
            return

        df_export = pd.DataFrame(export_data)
        filename, _ = QFileDialog.getSaveFileName(self, "Save Vaccine Register Excel", f"Vaccine_Register_{from_dt.replace('/', '_')}_to_{to_dt.replace('/', '_')}.xlsx", "Excel Files (*.xlsx)")
        if filename:
            df_export.to_excel(filename, index=False)
            QMessageBox.information(self, "Success", "Vaccine Register Excel exported successfully!")

    # ---------------- 6. VACCINE MASTER ----------------
    def setup_vaccines_tab(self):
        layout = QHBoxLayout()
        layout.setContentsMargins(15, 15, 15, 15)

        box_form = QGroupBox("Add / Edit Vaccine or Particular")
        form_layout = QFormLayout()

        self.inp_vname = QLineEdit()
        self.inp_vprice = QDoubleSpinBox()
        self.inp_vprice.setMaximum(100000)

        self.cmb_vtype = QComboBox()
        self.cmb_vtype.addItems(["Vaccine", "Particulars / Service"])

        form_layout.addRow("Name:", self.inp_vname)
        form_layout.addRow("Price (₹):", self.inp_vprice)
        form_layout.addRow("Type Category:", self.cmb_vtype)

        btn_row = QHBoxLayout()
        self.btn_save_v = QPushButton("Save Item")
        self.btn_save_v.clicked.connect(self.save_vaccine)

        btn_clear_v = QPushButton("Clear")
        btn_clear_v.setObjectName("btn_clear")
        btn_clear_v.clicked.connect(self.clear_vaccine_form)

        btn_row.addWidget(self.btn_save_v)
        btn_row.addWidget(btn_clear_v)
        form_layout.addRow(btn_row)

        box_form.setLayout(form_layout)

        self.table_vaccines = QTableWidget()
        self.table_vaccines.setColumnCount(4)
        self.table_vaccines.setHorizontalHeaderLabels(["ID", "Name", "Price (₹)", "Category Type"])
        self.table_vaccines.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table_vaccines.doubleClicked.connect(self.on_vaccine_double_click)

        layout.addWidget(box_form, 1)
        layout.addWidget(self.table_vaccines, 2)
        self.tab_vaccines.setLayout(layout)

    def load_vaccines_table(self):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, vaccine_name, price, type FROM vaccines ORDER BY vaccine_name ASC")
        rows = cursor.fetchall()
        conn.close()

        self.table_vaccines.setRowCount(0)
        for r_idx, row in enumerate(rows):
            self.table_vaccines.insertRow(r_idx)
            for c_idx in range(4):
                val = row[c_idx]
                if c_idx == 2: val = f"₹ {val:.2f}"
                item = QTableWidgetItem(str(val) if val is not None else "")
                item.setTextAlignment(Qt.AlignCenter)
                self.table_vaccines.setItem(r_idx, c_idx, item)

    def save_vaccine(self):
        name = self.inp_vname.text().strip()
        price = self.inp_vprice.value()
        vtype = self.cmb_vtype.currentText()

        if not name:
            QMessageBox.warning(self, "Error", "Vaccine / Particular Name is required!")
            return

        conn = get_connection()
        cursor = conn.cursor()

        if self.selected_vaccine_id:
            cursor.execute("UPDATE vaccines SET vaccine_name=?, price=?, type=? WHERE id=?", (name, price, vtype, self.selected_vaccine_id))
            QMessageBox.information(self, "Success", "Item updated successfully!")
        else:
            try:
                cursor.execute("INSERT INTO vaccines (vaccine_name, price, type) VALUES (?, ?, ?)", (name, price, vtype))
                QMessageBox.information(self, "Success", "Item added successfully!")
            except sqlite3.IntegrityError:
                QMessageBox.warning(self, "Error", "An item with this name already exists!")

        conn.commit()
        conn.close()

        self.clear_vaccine_form()
        self.load_vaccines_table()

    def clear_vaccine_form(self):
        self.selected_vaccine_id = None
        self.inp_vname.clear()
        self.inp_vprice.setValue(0.0)
        self.cmb_vtype.setCurrentIndex(0)
        self.btn_save_v.setText("Save Item")

    def on_vaccine_double_click(self, index):
        row = index.row()
        self.selected_vaccine_id = int(self.table_vaccines.item(row, 0).text())
        self.inp_vname.setText(self.table_vaccines.item(row, 1).text())
        
        price_txt = self.table_vaccines.item(row, 2).text().replace("₹", "").strip()
        self.inp_vprice.setValue(float(price_txt or 0.0))
        self.cmb_vtype.setCurrentText(self.table_vaccines.item(row, 3).text())
        
        self.btn_save_v.setText("Update Item")

    # ---------------- 7. DOCTOR MANAGEMENT ----------------
    def setup_doctors(self):
        layout = QHBoxLayout()
        layout.setContentsMargins(15, 15, 15, 15)

        box_form = QGroupBox("Add / Edit Doctor")
        form_layout = QFormLayout()

        self.inp_doc_name = QLineEdit()
        self.inp_doc_hosp = QLineEdit()
        self.inp_doc_addr = QLineEdit()

        form_layout.addRow("Doctor Name:", self.inp_doc_name)
        form_layout.addRow("Hospital Name:", self.inp_doc_hosp)
        form_layout.addRow("Address / Location:", self.inp_doc_addr)

        btn_row = QHBoxLayout()
        self.btn_save_doc = QPushButton("Save Doctor")
        self.btn_save_doc.clicked.connect(self.save_doctor)

        btn_clear_doc = QPushButton("Clear")
        btn_clear_doc.setObjectName("btn_clear")
        btn_clear_doc.clicked.connect(self.clear_doctor_form)

        btn_row.addWidget(self.btn_save_doc)
        btn_row.addWidget(btn_clear_doc)
        form_layout.addRow(btn_row)

        box_form.setLayout(form_layout)

        self.table_doctors = QTableWidget()
        self.table_doctors.setColumnCount(4)
        self.table_doctors.setHorizontalHeaderLabels(["ID", "Doctor Name", "Hospital Name", "Address"])
        self.table_doctors.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table_doctors.doubleClicked.connect(self.on_doctor_double_click)

        layout.addWidget(box_form, 1)
        layout.addWidget(self.table_doctors, 2)
        self.tab_doctors.setLayout(layout)

    def load_doctors_table(self):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, hospital_name, address FROM doctors ORDER BY name ASC")
        rows = cursor.fetchall()
        conn.close()

        self.table_doctors.setRowCount(0)
        for r_idx, row in enumerate(rows):
            self.table_doctors.insertRow(r_idx)
            for c_idx in range(4):
                item = QTableWidgetItem(str(row[c_idx]) if row[c_idx] is not None else "")
                item.setTextAlignment(Qt.AlignCenter)
                self.table_doctors.setItem(r_idx, c_idx, item)

    def save_doctor(self):
        name = self.inp_doc_name.text().strip()
        hosp = self.inp_doc_hosp.text().strip()
        addr = self.inp_doc_addr.text().strip()

        if not name:
            QMessageBox.warning(self, "Error", "Doctor Name is required!")
            return

        conn = get_connection()
        cursor = conn.cursor()

        if self.selected_doctor_id:
            cursor.execute("UPDATE doctors SET name=?, hospital_name=?, address=? WHERE id=?", (name, hosp, addr, self.selected_doctor_id))
            QMessageBox.information(self, "Success", "Doctor details updated successfully!")
        else:
            try:
                cursor.execute("INSERT INTO doctors (name, hospital_name, address) VALUES (?, ?, ?)", (name, hosp, addr))
                QMessageBox.information(self, "Success", "Doctor added successfully!")
            except sqlite3.IntegrityError:
                QMessageBox.warning(self, "Error", "Doctor with this name already exists!")

        conn.commit()
        conn.close()

        self.clear_doctor_form()
        self.load_doctors_table()
        self.load_doctor_dropdowns()

    def clear_doctor_form(self):
        self.selected_doctor_id = None
        self.inp_doc_name.clear()
        self.inp_doc_hosp.clear()
        self.inp_doc_addr.clear()
        self.btn_save_doc.setText("Save Doctor")

    def on_doctor_double_click(self, index):
        row = index.row()
        self.selected_doctor_id = int(self.table_doctors.item(row, 0).text())
        self.inp_doc_name.setText(self.table_doctors.item(row, 1).text())
        self.inp_doc_hosp.setText(self.table_doctors.item(row, 2).text())
        self.inp_doc_addr.setText(self.table_doctors.item(row, 3).text())
        self.btn_save_doc.setText("Update Doctor")

    def load_doctor_dropdowns(self):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM doctors ORDER BY name ASC")
        docs = [row[0] for row in cursor.fetchall()]
        conn.close()

        self.cmb_pdoctor.clear()
        self.cmb_pdoctor.addItems(docs)

        self.cmb_filter_doc.clear()
        self.cmb_filter_doc.addItem("All Doctors")
        self.cmb_filter_doc.addItems(docs)

    # ---------------- 8. SCAN MANAGEMENT ----------------
    def setup_scans(self):
        layout = QHBoxLayout()
        layout.setContentsMargins(15, 15, 15, 15)

        box_form = QGroupBox("Add / Edit USG Scan")
        form_layout = QFormLayout()

        self.inp_scan_name = QLineEdit()
        self.cmb_scan_type = QComboBox()
        self.cmb_scan_type.addItems(["Regular Scan", "Obstetrics Scan"])
        self.inp_scan_price = QDoubleSpinBox()
        self.inp_scan_price.setMaximum(100000)

        form_layout.addRow("Scan Name:", self.inp_scan_name)
        form_layout.addRow("Scan Category Type:", self.cmb_scan_type)
        form_layout.addRow("Price (₹):", self.inp_scan_price)

        btn_row = QHBoxLayout()
        self.btn_save_scan = QPushButton("Save USG Scan")
        self.btn_save_scan.clicked.connect(self.save_scan)

        btn_clear_scan = QPushButton("Clear")
        btn_clear_scan.setObjectName("btn_clear")
        btn_clear_scan.clicked.connect(self.clear_scan_form)

        btn_row.addWidget(self.btn_save_scan)
        btn_row.addWidget(btn_clear_scan)
        form_layout.addRow(btn_row)

        box_form.setLayout(form_layout)

        self.table_scans = QTableWidget()
        self.table_scans.setColumnCount(4)
        self.table_scans.setHorizontalHeaderLabels(["ID", "Scan Name", "Category Type", "Price (₹)"])
        self.table_scans.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table_scans.doubleClicked.connect(self.on_scan_double_click)

        layout.addWidget(box_form, 1)
        layout.addWidget(self.table_scans, 2)
        self.tab_scans.setLayout(layout)

    def load_scans_table(self):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, scan_name, scan_type, price FROM usg_scans ORDER BY scan_name ASC")
        rows = cursor.fetchall()
        conn.close()

        self.table_scans.setRowCount(0)
        for r_idx, row in enumerate(rows):
            self.table_scans.insertRow(r_idx)
            for c_idx in range(4):
                val = row[c_idx]
                if c_idx == 3: val = f"₹ {val:.2f}"
                item = QTableWidgetItem(str(val) if val is not None else "")
                item.setTextAlignment(Qt.AlignCenter)
                self.table_scans.setItem(r_idx, c_idx, item)

    def save_scan(self):
        name = self.inp_scan_name.text().strip()
        stype = self.cmb_scan_type.currentText()
        price = self.inp_scan_price.value()

        if not name:
            QMessageBox.warning(self, "Error", "Scan Name is required!")
            return

        conn = get_connection()
        cursor = conn.cursor()

        if self.selected_scan_id:
            cursor.execute("UPDATE usg_scans SET scan_name=?, scan_type=?, price=? WHERE id=?", (name, stype, price, self.selected_scan_id))
            QMessageBox.information(self, "Success", "USG Scan updated successfully!")
        else:
            try:
                cursor.execute("INSERT INTO usg_scans (scan_name, scan_type, price) VALUES (?, ?, ?)", (name, stype, price))
                QMessageBox.information(self, "Success", "USG Scan added successfully!")
            except sqlite3.IntegrityError:
                QMessageBox.warning(self, "Error", "Scan with this name already exists!")

        conn.commit()
        conn.close()

        self.clear_scan_form()
        self.load_scans_table()
        self.load_scan_dropdowns()

    def clear_scan_form(self):
        self.selected_scan_id = None
        self.inp_scan_name.clear()
        self.cmb_scan_type.setCurrentIndex(0)
        self.inp_scan_price.setValue(0.0)
        self.btn_save_scan.setText("Save USG Scan")

    def on_scan_double_click(self, index):
        row = index.row()
        self.selected_scan_id = int(self.table_scans.item(row, 0).text())
        self.inp_scan_name.setText(self.table_scans.item(row, 1).text())
        self.cmb_scan_type.setCurrentText(self.table_scans.item(row, 2).text())
        
        price_txt = self.table_scans.item(row, 3).text().replace("₹", "").strip()
        self.inp_scan_price.setValue(float(price_txt or 0.0))
        self.btn_save_scan.setText("Update USG Scan")

    def load_scan_dropdowns(self):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT scan_name FROM usg_scans ORDER BY scan_name ASC")
        scans = [row[0] for row in cursor.fetchall()]
        conn.close()

        self.cmb_pscan.clear()
        self.cmb_pscan.addItems(scans)


# ---------------- MAIN APPLICATION EXECUTION ----------------
if __name__ == "__main__":
    init_db()
    app = QApplication(sys.argv)
    window = GajananApp()
    window.showMaximized()
    sys.exit(app.exec_())