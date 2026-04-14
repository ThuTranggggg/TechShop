import logging


class StructuredFormatter(logging.Formatter):
    def format(self, record):
        base_message = super().format(record)
        return f"service={getattr(record, 'service', 'django')} {base_message}"
