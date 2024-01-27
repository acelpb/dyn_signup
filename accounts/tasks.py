from accounts.models import Account
from openpyxl import Workbook

# %%


def export_year(year=2023):
    # %%
    workbook = Workbook()
    for account in Account.objects.all():
        sheet = workbook.create_sheet(account.name)
        account.operation_set.filter(year=year).ordered("number")
        sheet

        print(account)

    # %%
    return
