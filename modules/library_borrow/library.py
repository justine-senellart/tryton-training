import datetime

from trytond.model import ModelSQL, ModelView, fields
from trytond.model.fields import SQL_OPERATORS
from trytond.pool import PoolMeta, Pool
from trytond.transaction import Transaction
from trytond.pyson import If, Eval, Date

from sql import Null
from sql.aggregate import Count, Min
from sql.operators import Concat

__all__ = [
    'User',
    'Borrowing',
    'Book',
    'Exemplary',
    ]


class User(ModelSQL, ModelView):
    'Library User'
    __name__ = 'library.user'

    borrowings = fields.One2Many('library.user.borrowing', 'user',
                                 'Borrowings')
    identifier = fields.Integer('identifier', required=True)
    name = fields.Char('Name')
    creation_date = fields.Date('Creation date', domain=[
            If(~Eval('creation_date'), [],
               [('creation_date', '<=', Date())])])
    number_borrowed = fields.Function(
        fields.Integer('Number books borrowed'),
        'getter_number_borrowed')
    number_late = fields.Function(
        fields.Integer('Number books late'),
        'getter_number_borrowed')
    expected_return_date = fields.Function(
        fields.Date('Expected return date'), 'getter_number_borrowed',
        searcher='search_expected_return_date')

    @classmethod
    def getter_number_borrowed(cls, users, name):
        Borrowed = Pool().get('library.user.borrowing')
        borrowed = Borrowed.__table__()
        cursor = Transaction().connection.cursor()
        default_value = None

        if name not in ('number_borrowed', 'number_late'):
            default_value = 0
        result = {x.id: default_value for x in users}
        column, where = None, None
        if name == 'number_borrowed':
            column = Count(borrowed.id)
            where = borrowed.return_date == Null
        elif name == 'number_late':
            column = Count(borrowed.id)
            where = (borrowed.return_date == Null) & (
                     borrowed.borrowing_date < datetime.date.today() +
                     datetime.timedelta(days=20))
        elif name == 'expected_return_date':
            column = Min(borrowed.borrowing_date)
            where = borrowed.return_date == Null
        else:
            raise Exception('Invalid function field name %s' % name)
        cursor.execute(*borrowed.select(borrowed.user, column,
                       where=where & borrowed.user.in_([x.id for x in users]),
                       group_by=[borrowed.user]))
        for user_id, value in cursor.fetchall():
            result[user_id] = value
            if name == 'expected_return_date' and value:
                result[user_id] += datetime.timedelta(days=20)
        return result

    @classmethod
    def search_expected_return_date(cls, name, clause):
        user = cls.__table__()
        borrowing = Pool().get('library.user.borrowing').__table__()
        _, operator, value = clause
        if isinstance(value, datetime.date):
            value = value + datetime.timedelta(days=-20)
        if isinstance(value, (list, tuple)):
            value = [(x + datetime.timedelta(days=-20) if x else x)
                     for x in value]
        Operator = SQL_OPERATORS[operator]
        query_table = user.join(borrowing, 'LEFT OUTER',
                                condition=borrowing.user == user.id)
        query = query_table.select(user.id,
                                   where=(borrowing.return_date == Null) |
                                   (borrowing.id == Null),
                                   group_by=user.id,
                                   having=Operator(Min(
                                                   borrowing.borrowing_date),
                                                   value))
        return[('id', 'in', query)]


class Borrowing(ModelSQL, ModelView):
    'Borrowing'
    __name__ = 'library.user.borrowing'

    user = fields.Many2One('library.user', 'User', required=True,
                           ondelete='CASCADE', select=True)
    exemplary = fields.Many2One('library.book.exemplary', 'Exemplary',
                                required=True, ondelete='CASCADE', select=True)
    borrowing_date = fields.Date('Borrowing date', required=True,
            domain=[('borrowing_date', '<=', Date())])
    return_date = fields.Date('Return date',
            domain=[If(~Eval('return_date'), [],
                    [('return_date', '<=', Date()),
                     ('return_date', '>=', Eval('borrowing_date'))])],
            depends=['borrowing_date'])
    expected_return_date = fields.Function(fields.Date('Expected return date'),
                                        'getter_expected_return_date',
                                        searcher='search_expected_return_date')

    def getter_expected_return_date(self, name):
        return self.borrowing_date + datetime.timedelta(days=20)

    @classmethod
    def search_expected_return_date(cls, name, clause):
        _, operator, value = clause
        if isinstance(value, datetime.date):
            value = value + datetime.timedelta(days=-20)
        if isinstance(value, (list, tuple)):
            value = [(x + datetime.timedelta(days=-20) if x else x)
                     for x in value]
        return [('borrowing_date', operator, value)]


class Book(metaclass=PoolMeta):
    __name__ = 'library.book'

    is_available = fields.Function(fields.Boolean('Is available'),
                                   'getter_is_available',
                                   searcher='search_is_available')

    @classmethod
    def getter_is_available(cls, books, name):
        pool = Pool()
        borrowing = pool.get('library.user.borrowing').__table__()
        exemplary = pool.get('library.book.exemplary').__table__()
        book = cls.__table__()
        result = {x.id: False for x in books}
        cursor = Transaction().connection.cursor()
        cursor.execute(*book.join(exemplary,
                condition=(exemplary.book == book.id)
                ).join(borrowing, 'LEFT OUTER',
                condition=(exemplary.id == borrowing.exemplary)
                ).select(book.id,
                where=(borrowing.return_date != Null) | (borrowing.id == Null)))
        for book_id, in cursor.fetchall():
            result[book_id] = True
        return result

    @classmethod
    def search_is_available(cls, name, clause):
        _, operator, value = clause
        if operator == '!=':
            value = not value
        pool = Pool()
        borrowing = pool.get('library.user.borrowing').__table__()
        exemplary = pool.get('library.book.exemplary').__table__()
        book = cls.__table__()
        query = book.join(exemplary,
                          condition=(exemplary.book == book.id)
                          ).join(borrowing, 'LEFT OUTER',
                          condition=(exemplary.id == borrowing.exemplary)
                          ).select(book.id,
                          where=(borrowing.return_date != Null) | (borrowing.id
                          == Null))
        return[('id', 'in' if value else 'not in', query)]


class Exemplary(metaclass=PoolMeta):
    __name__ = 'library.book.exemplary'

    borrowings = fields.One2Many('library.user.borrowing', 'exemplary',
                                 'Borrowings')
    is_available = fields.Function(fields.Boolean('Is available'),
                                   'getter_is_available',
                                   searcher='search_is_available')

    @classmethod
    def getter_is_available(cls, exemplaries, name):
        Borrowing = Pool().get('library.user.borrowing')
        borrowing = Borrowing.__table__()
        result = {x.id: True for x in exemplaries}

        cursor = Transaction().connection.cursor()
        cursor.execute(*borrowing.select(borrowing.exemplary,
                where=(borrowing.return_date == Null)
                & borrowing.exemplary.in_([x.id for x in exemplaries])))
        for exemplary_id in cursor.fetchall():
            result[exemplary_id] = False
        return result

    @classmethod
    def search_rec_name(cls, name, clause):
        return['OR',
               ('identifier',) + tuple(clause[1:]),
               ('book.title',) + tuple(clause[1:]),
               ]

    @classmethod
    def order_rec_name(cls, tables):
        exemplary, _ = tables[None]
        book = tables.get('book')

        if book is None:
            book = Pool().get('library.book').__table__()
            tables['book'] = {None: (book, book.id == exemplary.book)}
        return [Concat(book.title, exemplary.identifier)]

    @classmethod
    def search_is_available(cls, name, clause):
        _, operator, value = clause
        if operator == '!=':
            value = not value
        pool = Pool()
        borrowing = pool.get('library.user.borrowing').__table__()
        exemplary = cls.__table__()
        query = exemplary.join(borrowing, 'LEFT OUTER',
                               condition=(exemplary.id == borrowing.exemplary)
                               ).select(exemplary.id,
                               where=(borrowing.return_date != Null) |
                               (borrowing.id == Null))
        return [('id', 'in' if value else 'not in', query)]
