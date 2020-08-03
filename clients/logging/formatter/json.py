import datetime
import logging

import clients.logging.formatter.helpers


class FilebeatJsonFormatter(logging.Formatter):

    def format(self, record):

        # handle non-json-parsable vars:
        try:

            # we can't delete from record.vars because of other handlers
            more = dict(record.vars) if len(record.vars) else {}
            try:
                del more['ctx']
            except Exception:
                pass
        except Exception as exc:
            more = f'Record vars are not parsable: {str(exc)}'

        try:
            what = record.getMessage()
        except Exception as exc:
            what = f'Log message is not parsable: {str(exc)}'

        output = {
            'when': datetime.datetime.fromtimestamp(record.created).isoformat(),
            'who': record.name,
            'severity': logging.getLevelName(record.levelno),
            'what': what,
            'more': more,
            'ctx': record.vars.get('ctx', ''),
            'lang': 'py'
        }

        return clients.logging.formatter.helpers.JsonFormatter.format_to_json_str(output)
