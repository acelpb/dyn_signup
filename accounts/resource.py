from import_export import resources

from .models import Operation


class OperationResource(resources.ModelResource):
    class Meta:
        model = Operation
        skip_unchanged = True
        report_skipped = False
        import_id_fields = ("year", "number")
