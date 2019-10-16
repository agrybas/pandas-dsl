import logging
import pandas as pd
import numpy as np
import arpeggio
from arpeggio import Optional, ZeroOrMore, OneOrMore, EOF
from arpeggio import RegExMatch as _
from arpeggio import ParserPython, PTNodeVisitor
from arpeggio import visit_parse_tree
from arpeggio.export import PTDOTExporter


def number(): return _(r'\d*\.\d*|\d+')


# def source(): return _(r'[a-z_]+')
def ticker(): return _(r'[-_+0-9A-Z]+')


def operator(): return '+', '-', '*', '/'


# def source_ticker(): return (source, ':', ticker)
# def ticker_expr(): return [('{', ticker, '}'), ('{', source_ticker, '}')]
def ticker_expr(): return '{', ticker, '}'


# def signed_number(): return ['+', '-'], number


# def signed_ticker(): return ['+', '-'], ticker_expr


# def number_ticker(): return [number, signed_number], operator, ticker_expr




# def item(): return [number, signed_number, ticker_expr, signed_ticker]


def factor(): return Optional(['+', '-']), [number, ticker_expr, ("(", expression, ")")]

def term(): return factor, ZeroOrMore(["*", "/"], factor)

def expression(): return term, ZeroOrMore(["+", "-"], term)


def calc(): return OneOrMore(expression), EOF


logger = logging.getLogger()
logger.setLevel(logging.INFO)
logger.addHandler(logging.StreamHandler())


class CIXVisitor(PTNodeVisitor):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.data = pd.DataFrame()
        self.__tickers = set()
        self.__sources = set()
        self.__source_tickers = set()

    def visit_number(self, node, children):
        return float(node.value)

    # def visit_signed_number(self, node, children):
    #     sign = -1.0 if children[0] == '-' else 1.0
    #     return sign * float(children[-1])

    # def visit_signed_ticker(self, node, children):
    #     sign = -1.0 if children[0] == '-' else 1.0
    #     # logger.info(f'Data columns: {self.data.columns}')
    #     # logger.info(f'Node value: {node.value}')
    #     return sign * children[-1]

    def visit_ticker(self, node, _):
        self.__tickers.add(node.value)
        if not self.data.empty:
            return self.data[node.value].copy(deep=True)
        else:
            return np.NaN

    def visit_source(self, node, _):
        self.__sources.add(node.value)

    def visit_source_ticker(self, node, _):
        self.__source_tickers.add(node.value)

    def visit_factor(self, node, children):
        if self.debug:
            logger.info(f'Factor: {children}')
        if len(children) == 1:
            return children[0]
        sign = -1 if children[0] == '-' else 1
        return sign * children[1]

    def visit_term(self, node, children):
        if self.debug:
            logger.info(f'Term: {children}')
        if isinstance(children[0], pd.DataFrame):
            term = children[0].copy(deep=True)
        else:
            term = children[0]
        for i in range(2, len(children), 2):
            if children[i-1] == '*':
                term *= children[i]
            else:
                term /= children[i]
        if self.debug:
            logger.info(f'Term: {term}')
        return term

    def visit_expression(self, node, children):
        if self.debug:
            logger.info(f'Expression: {children}')
        if isinstance(children[0], pd.DataFrame):
            expr = children[0].copy(deep=True)
        else:
            expr = children[0]
        for i in range(2, len(children), 2):
            if i and children[i-1] == '-':
                expr -= children[i]
            else:
                expr += children[i]
        if self.debug:
            logger.info(f'Expression: {expr}')
        return expr

    # def visit_expression(self, node, children):
    #     logger.info(f'Expression found with {len(children)} child nodes')

    @property
    def tickers(self):
        return self.__tickers

    @property
    def sources(self):
        return self.__sources

    @property
    def source_tickers(self):
        return self.__source_tickers


class CustomIndex:
    def __init__(self, expr):
        self.__visitor = CIXVisitor()
        self.__parser = ParserPython(calc, reduce_tree=True)
        self.__expr = expr
        self.__parsed = False
        self.__result = None
        try:
            self.__parse_tree = self.__parser.parse(self.__expr)
        except arpeggio.NoMatch as e:
            raise ValueError(f'Invalid index expression: {e}')

    def __parse(self):
        if not self.__parsed:
            self.__result = visit_parse_tree(self.__parse_tree, self.__visitor)
            self.__parsed = True

    @property
    def tickers(self):
        self.__parse()
        return self.__visitor.tickers

    @property
    def sources(self):
        self.__parse()
        return self.__visitor.sources

    @property
    def source_tickers(self):
        self.__parse()
        return self.__visitor.source_tickers

    def evaluate(self, data=None):
        self.__visitor.data = data
        self.__parse()
        return self.__result

