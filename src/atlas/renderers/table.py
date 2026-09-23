from rich.table import Table


class TableRenderer:

    def create(self, title: str, columns: list[str]) -> Table:

        table = Table(title=title)

        for column in columns:
            table.add_column(column)

        return table
