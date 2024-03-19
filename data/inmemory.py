class InMemoryRepo:
    def __init__(self):
        self._collection = dict()

    def add(self, report):
        self._collection[report.id] = report
