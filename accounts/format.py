import csv
from datetime import datetime
from io import StringIO

import tablib
from import_export.formats.base_formats import Format

from accounts.models import Account


class BPostCSV(Format):
    CONTENT_TYPE = "text/csv"

    def __init__(self, encoding=None):
        super().__init__()

    def get_title(self):
        return "csv extract from bpost"

    def create_dataset(self, in_stream):
        csv_reader = csv.reader(StringIO(in_stream), delimiter=";")

        _, iban, account_type = next(csv_reader)
        account, _ = Account.objects.get_or_create(IBAN=iban, name=account_type)
        account_id = account.id
        data = tablib.Dataset()
        next(csv_reader)
        data.headers = (
            "account",
            "number",
            "year",
            "date",
            "description",
            "amount",
            "currency",
            "effective_date",
            "counterparty_IBAN",
            "counterparty_name",
            "communication",
            "reference",
        )

        for row in csv_reader:
            (
                number,
                date,
                description,
                amount,
                currency,
                effective_date,
                counterparty_IBAN,
                counterparty_name,
                *communication,
                reference,
                _,
            ) = row
            transaction_date = datetime.strptime(date, "%Y-%m-%d")
            effective_date = datetime.strptime(effective_date, "%Y-%m-%d")
            data.append(
                (
                    account_id,
                    number,
                    transaction_date.year,
                    transaction_date,
                    description,
                    float(amount.replace(",", ".")),
                    currency,
                    effective_date,
                    counterparty_IBAN,
                    counterparty_name,
                    "\n".join(communication),
                    reference,
                )
            )

        return data

    def export_data(self, dataset, **kwargs):
        """
        Returns format representation for given dataset.
        """
        raise NotImplementedError()

    def is_binary(self):
        return False

    def get_read_mode(self):
        return "r"

    def get_extension(self):
        return ("csv",)

    def get_content_type(self):
        return "text/csv"

    @classmethod
    def is_available(cls):
        return True

    def can_import(self):
        return True

    def can_export(self):
        return False


class FortisCSV(Format):
    CONTENT_TYPE = "text/csv"

    def __init__(self, encoding=None):
        super().__init__()

    def get_title(self):
        return "csv extract from fortis"

    _account_ids = {}

    def get_account_id(self, iban):
        account_id = self._account_ids.get(iban)
        if account_id is None:
            account, _ = Account.objects.get_or_create(
                IBAN=iban, defaults={"name": "Fortis"}
            )
            account_id = account.id
            self._account_ids[iban] = account_id
        return account_id

    def create_dataset(self, in_stream):
        csv_reader = csv.reader(StringIO(in_stream), delimiter=";")
        data = tablib.Dataset()
        next(csv_reader)
        data.headers = (
            "account",
            "number",
            "year",
            "date",
            "description",
            "amount",
            "currency",
            "effective_date",
            "counterparty_IBAN",
            "counterparty_name",
            "communication",
            "reference",
        )

        for row in csv_reader:
            (
                date_operation_number,
                date,
                effective_date,
                amount,
                currency,
                account,
                _type_of_transaction,
                counterparty_IBAN,
                counterparty_name,
                communication,
                description,
                _status,
                _cancellation,
            ) = row
            number = date_operation_number.split("-")[1]
            if not number:
                continue
            transaction_date = datetime.strptime(date, "%d/%m/%Y")
            data.append(
                (
                    self.get_account_id(account),
                    number,
                    transaction_date.year,
                    transaction_date,
                    description,
                    float(amount),
                    currency,
                    datetime.strptime(effective_date, "%d/%m/%Y"),
                    counterparty_IBAN,
                    counterparty_name,
                    communication,
                    description,
                )
            )

        return data

    def export_data(self, dataset, **kwargs):
        """
        Returns format representation for given dataset.
        """
        raise NotImplementedError()

    def is_binary(self):
        return False

    def get_read_mode(self):
        return "r"

    def get_extension(self):
        return ("csv",)

    def get_content_type(self):
        return "text/csv"

    @classmethod
    def is_available(cls):
        return True

    def can_import(self):
        return True

    def can_export(self):
        return False
