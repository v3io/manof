# Copyright 2018 Iguazio
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import datetime
import logging
import textwrap
import simplejson

import colorama
import pygments.formatters
import pygments.lexers

import clients.logging.formatter.helpers as helpers


class HumanReadableFormatter(logging.Formatter):
    def __init__(self, enable_colors, *args, **kwargs):
        super(HumanReadableFormatter, self).__init__(*args, **kwargs)
        self._enable_colors = enable_colors

    # Maps severity to its letter representation
    _level_to_short_name = {
        helpers.Severity.Verbose: 'V',
        helpers.Severity.Debug: 'D',
        helpers.Severity.Info: 'I',
        helpers.Severity.Warning: 'W',
        helpers.Severity.Error: 'E',
    }

    # Maps severity to its color representation
    _level_to_color = {
        helpers.Severity.Warning: colorama.Fore.LIGHTYELLOW_EX,
        helpers.Severity.Error: colorama.Fore.LIGHTRED_EX,
    }

    def format(self, record):
        def _get_what_color():
            return {
                helpers.Severity.Verbose: colorama.Fore.LIGHTCYAN_EX,
                helpers.Severity.Debug: colorama.Fore.LIGHTCYAN_EX,
                helpers.Severity.Info: colorama.Fore.CYAN,
                helpers.Severity.Warning: colorama.Fore.LIGHTCYAN_EX,
                helpers.Severity.Error: colorama.Fore.LIGHTCYAN_EX,
            }.get(record.levelno, colorama.Fore.LIGHTCYAN_EX)

        # coloured using pygments
        if self._enable_colors:
            more = self._prettify_output(record.vars) if len(record.vars) else ''
        else:
            more = simplejson.dumps(record.vars) if len(record.vars) else ''

        output = {
            'reset_color': colorama.Fore.RESET,
            'when': datetime.datetime.fromtimestamp(record.created).strftime(
                '%d.%m.%y %H:%M:%S.%f'
            ),
            'when_color': colorama.Fore.WHITE,
            'who': record.name[-30:],
            'who_color': colorama.Fore.WHITE,
            'severity': HumanReadableFormatter._level_to_short_name[record.levelno],
            'severity_color': HumanReadableFormatter._level_to_color.get(
                record.levelno, colorama.Fore.RESET
            ),
            'what': record.getMessage(),
            'what_color': _get_what_color(),
            'more': more,
        }

        # Slice ms to be at maximum of 3 digits
        try:
            time_parts = output['when'].split('.')
            time_parts[-1] = time_parts[-1][:-3]
            output['when'] = '.'.join(time_parts)
        except Exception:
            pass

        # Disable coloring if requested
        if not self._enable_colors:
            for ansi_color in [f for f in output.keys() if 'color' in f]:
                output[ansi_color] = ''

        return (
            '{when_color}{when}{reset_color} {who_color}{who:>10}:{reset_color} '
            '{severity_color}({severity}){reset_color} {what_color}{what}{reset_color} '
            '{more}'.format(**output)
        )

    def _prettify_output(self, vars_dict):
        """
        Creates a string formatted version according to the length of the values in the
        dictionary, if the string value is larger than 40 chars, wrap the string using textwrap and
        output it last.

        :param vars_dict: dictionary containing the message vars
        :type vars_dict: dict(str: str)
        :rtype: str
        """
        short_values = []

        # some params for the long texts
        long_values = []
        content_indent = '   '
        wrap_width = 80

        for var_name, var_value in vars_dict.items():

            if isinstance(var_value, dict):
                long_values.append(
                    (
                        var_name,
                        simplejson.dumps(
                            var_value, indent=4, cls=helpers.ObjectEncoder
                        ),
                    )
                )

            # if the value is a string over 40 chars long
            elif isinstance(var_value, str) and len(var_value) > 40:
                wrapped_text = textwrap.fill(
                    '"{0}"'.format(var_value),
                    width=wrap_width,
                    break_long_words=False,
                    initial_indent=content_indent,
                    subsequent_indent=content_indent,
                    replace_whitespace=False,
                )

                long_values.append((var_name, wrapped_text))
            else:
                short_values.append((var_name, str(var_value)))

        # this will return the following
        # {a: b, c: d} (short stuff in the form of json dictionary)
        # {"some value":
        #                 "very long text for debugging purposes"}

        # The long text is not a full json string, but a raw string (not escaped), as to keep it human readable,
        # but it is surrounded by double-quotes so the coloring lexer will eat it up
        values_str = ''
        if short_values:
            values_str = helpers.JsonFormatter.format_to_json_str(
                {k: v for k, v in short_values}
            )
        if long_values:
            values_str += '\n'

            for lv_name, lv_value in long_values:
                values_str += '{{{0}:\n{1}}}\n'.format(
                    helpers.JsonFormatter.format_to_json_str(lv_name),
                    lv_value.rstrip('\n'),
                )
        json_lexer = pygments.lexers.get_lexer_by_name('Json')
        formatter = pygments.formatters.get_formatter_by_name(
            'terminal16m', style='paraiso-dark'
        )
        return pygments.highlight(values_str, json_lexer, formatter)
