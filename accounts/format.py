import csv
from datetime import datetime
from io import StringIO

import tablib
from import_export.formats.base_formats import Format

from accounts.models import Account


class BPostCSV(Format):
    CONTENT_TYPE = 'text/csv'

    def get_title(self):
        return "csv extract from bpost"

    def create_dataset(self, in_stream):
        csv_reader = csv.reader(StringIO(in_stream), delimiter=';')

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
            (number, date, description,
             amount, currency, effective_date,
             counterparty_IBAN, counterparty_name, *communication,
             reference, _) = row
            transaction_date = datetime.strptime(date, "%Y-%m-%d")
            data.append((
                account_id,
                number,
                transaction_date.year,
                transaction_date,
                description,
                float(amount.replace(',', '.')),
                currency,
                datetime.strptime(effective_date, "%d/%m/%Y"),
                counterparty_IBAN,
                counterparty_name,
                '\n'.join(communication),
                reference
            ))

        return data

    def export_data(self, dataset, **kwargs):
        """
        Returns format representation for given dataset.
        """
        raise NotImplementedError()

    def is_binary(self):
        return False

    def get_read_mode(self):
        return 'r'

    def get_extension(self):
        return ("csv",)

    def get_content_type(self):
        return 'text/csv'

    @classmethod
    def is_available(cls):
        return True

    def can_import(self):
        return True

    def can_export(self):
        return False
