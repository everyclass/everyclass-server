import logging


class CustomFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        if hasattr(record, "structured_data"):
            # Override message with extra info
            record.msg = "%s %s" % (
                self._join_extra(record.structured_data),
                record.msg
            )
        return super().format(record)

    @staticmethod
    def _join_extra(extra: dict) -> str:
        return "[%s]" % ", ".join([
            '%s:%s' % (key, value)
            for (key, value) in extra.items()
        ])
