"""Fake statement data generation utilities."""

from __future__ import annotations

import random
from datetime import UTC, datetime, timedelta

from faker import Faker

from .statement_pdf import StatementDocumentData, StatementTransaction

fake = Faker()


def _format_currency(amount: float) -> str:
    return f"{amount:,.2f}".replace(",", " ")


def generate_fake_statement_data(transaction_count: int = 100) -> StatementDocumentData:
    now = datetime.now(UTC).date()
    start_date = now.replace(day=1)

    full_name = fake.name().upper()
    account_number = "".join(str(random.randint(0, 9)) for _ in range(10))

    balance = round(random.uniform(2_000, 20_000), 2)
    transactions: list[StatementTransaction] = []

    for _ in range(transaction_count):
        txn_date = fake.date_between(start_date=start_date, end_date=now)
        is_credit = random.random() > 0.65
        amount = round(random.uniform(20, 6_500), 2)

        money_in = ""
        money_out = ""
        if is_credit:
            balance += amount
            money_in = _format_currency(amount)
        else:
            balance -= amount
            money_out = f"-{_format_currency(amount)}"

        transactions.append(
            StatementTransaction(
                posting_date=txn_date.strftime("%d/%m/%Y"),
                transaction_date=txn_date.strftime("%d/%m/%Y"),
                description=fake.sentence(nb_words=4).rstrip("."),
                money_in=money_in,
                money_out=money_out,
                balance=_format_currency(max(balance, 0.0)),
            )
        )

    transactions.sort(
        key=lambda txn: datetime.strptime(txn.posting_date, "%d/%m/%Y"),
        reverse=False,
    )

    return StatementDocumentData(
        title="Savings Account Statement",
        bank_name="Capitec Bank",
        statement_date=now.strftime("%d/%m/%Y"),
        branch=f"{random.randint(100000, 999999)}",
        device=f"{random.randint(1000, 9999)}",
        from_date=start_date.strftime("%d/%m/%Y"),
        to_date=now.strftime("%d/%m/%Y"),
        print_date=(now + timedelta(days=0)).strftime("%d/%m/%Y"),
        customer_name=full_name,
        address_line_1=fake.street_address().upper(),
        address_line_2=fake.city().upper(),
        address_line_3=fake.state().upper(),
        postal_code=fake.postcode(),
        account_number=account_number,
        available_balance=_format_currency(max(balance, 0.0)),
        transactions=transactions,
    )
