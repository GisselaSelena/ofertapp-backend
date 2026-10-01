class FakeRedis:
    def __init__(self):
        self.values = {}

    def set(self, key, value, ex=None):
        self.values[key] = value

    def get(self, key):
        return self.values.get(key)

    def delete(self, key):
        return self.values.pop(key, None) is not None


class FakeQuery:
    def __init__(self, result=None):
        self.result = result

    def filter(self, *conditions):
        return self

    def order_by(self, *expressions):
        return self

    def options(self, *expressions):
        return self

    def distinct(self):
        return self

    def first(self):
        return self.result[0] if isinstance(self.result, list) and self.result else (
            None if isinstance(self.result, list) else self.result
        )

    def all(self):
        if self.result is None:
            return []
        return self.result if isinstance(self.result, list) else [self.result]


class FakeSession:
    def __init__(self, query_results=None, refresh_id=None):
        self.query_results = query_results or {}
        self.refresh_id = refresh_id
        self.added = []
        self.deleted = []
        self.commits = 0
        self.rollbacks = 0

    def query(self, model_or_column):
        return FakeQuery(self.query_results.get(model_or_column))

    def add(self, instance):
        self.added.append(instance)

    def commit(self):
        self.commits += 1

    def refresh(self, instance):
        if self.refresh_id is not None:
            instance.id = self.refresh_id

    def delete(self, instance):
        self.deleted.append(instance)

    def rollback(self):
        self.rollbacks += 1
