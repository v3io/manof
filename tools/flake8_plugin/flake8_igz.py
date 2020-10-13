import inflection
import token
import re


class Constants(object):

    string_prefixes = 'ubrUBR'
    log_levels = ['verbose', 'debug', 'info', 'warn', 'error']


class Utils(object):
    @staticmethod
    def get_string_tokens(tokens):
        for tid, lexeme, start, end, _ in tokens:
            if tid == token.STRING:
                lexeme = lexeme.lstrip(Constants.string_prefixes)
                yield lexeme, start, end


def single_quote_strings(logical_line, tokens):
    for (
        lexeme,
        start,
        _,
    ) in Utils.get_string_tokens(tokens):
        if lexeme.startswith('"') and not lexeme.startswith('"""'):
            yield start, 'I100 double-quote string used (expected single-quote)'


def multiline_string_on_newline(logical_line, tokens):
    for (
        lexeme,
        start,
        end,
    ) in Utils.get_string_tokens(tokens):
        if lexeme.startswith('"""'):
            if not re.match(r'^\"\"\"\n', lexeme):
                yield start, 'I101 multiline string must start on next line after triple double-quotes'
            if not re.search(r'\n\s*\"\"\"$', lexeme):
                yield end, 'I102 multiline string must end with triple double-quotes in new line'


def multiline_string_double_quotes(logical_line, tokens):
    for (
        lexeme,
        start,
        _,
    ) in Utils.get_string_tokens(tokens):
        if lexeme.startswith('\'\'\''):
            yield start, 'I103 triple single-quotes used in multiline string (expected triple double-quotes)'


def ctx_log_non_string_first_param(logical_line, tokens):
    if logical_line.startswith('ctx.log.'):
        for idx, (tid, lexeme, start, _, _) in enumerate(tokens):
            if tid == token.NAME and lexeme in Constants.log_levels:

                # plus one for the ( parentheses, plus one for the first param
                first_param_token = tokens[idx + 2]

                if first_param_token[0] == token.STRING:
                    yield first_param_token[
                        2
                    ], 'I104 ctx.log.{0} call with string as first param'.format(lexeme)


def class_name_camel_case(logical_line, tokens):
    if logical_line.startswith('class'):
        for idx, (tid, lexeme, start, _, _) in enumerate(tokens):
            if tid == token.NAME and lexeme == 'class':
                class_name_token = tokens[idx + 1]
                camelized = inflection.camelize(class_name_token[1], True)

                if class_name_token[1] != camelized:
                    yield class_name_token[
                        2
                    ], 'I105 class name not camel case. (suggestion: {0})'.format(
                        camelized
                    )


def logger_forbid_passing_self(logical_line, tokens):
    if logical_line.startswith('self._logger.'):
        for idx, (tid, lexeme, start, _, _) in enumerate(tokens):
            if tid == token.NAME and lexeme in Constants.log_levels:

                # plus one for the ( parentheses, plus one for the first param
                first_param_token = tokens[idx + 2]

                if (
                    first_param_token[1] == 'self'
                    and first_param_token[0] != token.STRING
                ):
                    yield first_param_token[
                        2
                    ], 'I106 self._logger.{0} call with self as first param'.format(
                        lexeme
                    )
