"""Utilities for generating account statement PDFs with fpdf2."""

from __future__ import annotations

from dataclasses import dataclass

from fpdf import FPDF


@dataclass(slots=True)
class StatementTransaction:
    posting_date: str
    transaction_date: str
    description: str
    money_in: str = ""
    money_out: str = ""
    balance: str = ""


@dataclass(slots=True)
class StatementDocumentData:
    title: str
    bank_name: str
    statement_date: str
    branch: str
    device: str
    from_date: str
    to_date: str
    print_date: str
    customer_name: str
    address_line_1: str
    address_line_2: str
    address_line_3: str
    postal_code: str
    account_number: str
    available_balance: str
    transactions: list[StatementTransaction]


class AccountStatementPdf(FPDF):
    def __init__(self) -> None:
        super().__init__(orientation="P", unit="mm", format="A4")
        self.set_auto_page_break(auto=True, margin=12)

    def render(self, payload: StatementDocumentData) -> bytes:
        self.add_page()

        self.set_font("Helvetica", "B", 8)
        self.cell(
            0,
            4,
            "24hr Client Care Centre 0860 10 20 43",
            align="C",
            new_x="LMARGIN",
            new_y="NEXT",
        )
        self.cell(0, 4, "capitecbank.co.za", align="C", new_x="LMARGIN", new_y="NEXT")
        self.ln(4)

        self.set_font("Helvetica", "B", 18)
        self.cell(0, 10, payload.title, new_x="LMARGIN", new_y="NEXT")
        self.ln(2)

        self.set_draw_color(150, 150, 150)
        self.rect(70, 35, 55, 35)
        self.set_xy(70, 40)
        self.set_font("Helvetica", "", 11)
        self.cell(55, 6, payload.bank_name, align="C", new_x="LMARGIN", new_y="NEXT")
        self.set_x(70)
        self.cell(
            55, 6, payload.statement_date, align="C", new_x="LMARGIN", new_y="NEXT"
        )
        self.set_x(70)
        self.cell(
            55, 6, f"Branch: {payload.branch}", align="C", new_x="LMARGIN", new_y="NEXT"
        )
        self.set_x(70)
        self.cell(
            55, 6, f"Device: {payload.device}", align="C", new_x="LMARGIN", new_y="NEXT"
        )

        self.set_xy(10, 75)
        self.set_font("Helvetica", "B", 10)
        self.cell(80, 5, "Personal Details", new_x="LMARGIN", new_y="NEXT")
        self.set_font("Helvetica", "", 9)
        self.cell(80, 5, payload.customer_name, new_x="LMARGIN", new_y="NEXT")
        self.cell(80, 5, payload.address_line_1, new_x="LMARGIN", new_y="NEXT")
        self.cell(80, 5, payload.address_line_2, new_x="LMARGIN", new_y="NEXT")
        self.cell(80, 5, payload.address_line_3, new_x="LMARGIN", new_y="NEXT")
        self.cell(80, 5, payload.postal_code, new_x="LMARGIN", new_y="NEXT")

        self.set_xy(125, 40)
        self.set_font("Helvetica", "B", 10)
        self.cell(60, 5, "Tax Invoice", new_x="LMARGIN", new_y="NEXT")
        self.set_x(125)
        self.set_font("Helvetica", "", 9)
        self.cell(60, 5, f"From: {payload.from_date}", new_x="LMARGIN", new_y="NEXT")
        self.set_x(125)
        self.cell(60, 5, f"To: {payload.to_date}", new_x="LMARGIN", new_y="NEXT")
        self.set_x(125)
        self.cell(60, 5, f"Print: {payload.print_date}", new_x="LMARGIN", new_y="NEXT")
        self.set_x(125)
        self.cell(
            60, 5, f"Account: {payload.account_number}", new_x="LMARGIN", new_y="NEXT"
        )

        current_y = self._render_transactions(payload.transactions)

        self.set_xy(10, current_y + 8)
        self.set_font("Helvetica", "B", 10)
        self.cell(45, 6, "Available Balance:")
        self.set_font("Helvetica", "", 10)
        self.cell(45, 6, payload.available_balance)

        output = self.output()
        if isinstance(output, (bytes, bytearray)):
            return bytes(output)
        return output.encode("latin-1")

    def _render_table_header(self, y_position: float) -> float:
        self.set_font("Helvetica", "B", 8)
        self.set_xy(10, y_position)
        self.cell(26, 5, "Posting Date")
        self.set_xy(36, y_position)
        self.cell(26, 5, "Trans Date")
        self.set_xy(62, y_position)
        self.cell(70, 5, "Description")
        self.set_xy(132, y_position)
        self.cell(22, 5, "Money In", align="R")
        self.set_xy(154, y_position)
        self.cell(22, 5, "Money Out", align="R")
        self.set_xy(176, y_position)
        self.cell(24, 5, "Balance", align="R")
        return y_position + 6

    def _render_transactions(self, transactions: list[StatementTransaction]) -> float:
        current_y = self._render_table_header(120)
        self.set_font("Helvetica", "", 8)

        for txn in transactions:
            if current_y > 272:
                self.add_page()
                current_y = self._render_table_header(20)
                self.set_font("Helvetica", "", 8)

            self.set_xy(10, current_y)
            self.cell(26, 5, txn.posting_date)
            self.set_xy(36, current_y)
            self.cell(26, 5, txn.transaction_date)
            self.set_xy(62, current_y)
            self.cell(70, 5, txn.description[:52])
            self.set_xy(132, current_y)
            self.cell(22, 5, txn.money_in, align="R")
            self.set_xy(154, current_y)
            self.cell(22, 5, txn.money_out, align="R")
            self.set_xy(176, current_y)
            self.cell(24, 5, txn.balance, align="R")
            current_y += 5

        return current_y
