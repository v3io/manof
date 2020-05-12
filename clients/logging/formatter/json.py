import datetime
import logging

import helpers


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
            more = 'Record vars are not parsable: {0}'.format(str(exc))

        try:
            what = record.getMessage()
        except Exception as exc:
            what = 'Log message is not parsable: {0}'.format(str(exc))

        output = {
            'when': datetime.datetime.fromtimestamp(record.created).isoformat(),
            'who': record.name,
            'severity': logging.getLevelName(record.levelno),
            'what': what,
            'more': more,
            'ctx': record.vars.get('ctx', ''),
            'lang': 'py'
        }

        return helpers.JsonFormatter.format_to_json_str(output)
