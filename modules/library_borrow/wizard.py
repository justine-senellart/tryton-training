import datetime

from trytond.pool import Pool
from trytond.model import ModelView, fields
from trytond.wizard import Wizard, StateView, StateTransition, StateAction
from trytond.wizard import Button
from trytond.transaction import Transaction
from trytond.pyson import Date, Eval, PYSONEncoder
from trytond.exceptions import UserError


__all__ = [
           'BorrowBook',
           'BorrowSelectedBook',
           'ReturnBook',
           'ReturnSelectedBook',
          ]


class BorrowBook(Wizard):
    'Borrow Book'
    __name__ = 'library.user.borrow_book'

    start_state = 'select_book'
    select_book = StateView('library.user.borrow_book.selected_book',
                            'library_borrow.borrow_selected_book_view_form', [
                                Button('Cancel', 'end', 'tryton-cancel'),
                                Button('Borrow', 'borrow_book', 'tryton-ok',
                                       default=True)])
    borrow_book = StateTransition()
    open_borrowings = StateAction('library_borrow.act_open_user_borrowing')

    def default_select_book(self, name):
        user = None
        exemplaries = []
        if Transaction().context.get('active_model') == 'library.user':
            user = Transaction().context.get('active_id')
        elif Transaction().context.get('active_model') == 'library.book':
            books = Pool().get('library.book').browse(
                Transaction().context.get('active_ids'))
            for book in books:
                if not book.is_available:
                    continue
                for exemplary in book.exemplaries:
                    if exemplary.is_available:
                        exemplaries.append(exemplary.id)
                        break
        return {
            'user': user,
            'exemplaries': exemplaries,
            'borrowing_date': datetime.date.today(),
            }

    def transition_borrow_book(self):
        Borrowing = Pool().get('library.user.borrowing')
        exemplaries = self.select_book.exemplaries
        user = self.select_book.user
        borrowings = []
        for exemplary in exemplaries:
            if not exemplary.is_available:
                raise UserError('unavailable', 'Exemplary is not available')
            borrowings.append(Borrowing(user=user,
                    date=self.select_book.borrowing_date,
                    exemplary=exemplary))
        Borrowing.save(borrowings)
        self.select_book.borrowings = borrowings
        return 'open_borrowings'

    def do_open_borrowings(self, action):
        action['pyson_domain'] = PYSONEncoder().encode([
                ('id', 'in', [x.id for x in self.select_book.borrowings])])
        return action, {}


class BorrowSelectedBook(ModelView):
    'Borrow Selected Book'
    __name__ = 'library.user.borrow_book.selected_book'

    user = fields.Many2One('library.user', 'User', required=True)
    exemplaries = fields.Many2Many('library.book.exemplary', None, None,
                                   'Exemplaries', required=True,
                                   domain=[('is_available', '=', True)])
    borrowing_date = fields.Date('Borrowing date', required=True,
                                 domain=[('date', '<=', Date())])
    borrowings = fields.Many2Many('library.user.borrowing', None, None,
                                  'Borrowings', readonly=True)


class ReturnBook(Wizard):
    'Return Book'
    __name__ = 'library.user.return_book'

    start_state = 'select_borrowing'
    select_borrowing = StateView('library.user.return_book.selected_book',
                          'library_borrow.return_selected_book_view_form', [
                                Button('Cancel', 'end', 'tryton-cancel'),
                                Button('Return Book', 'return_book',
                                       'tryton-ok', default=True)])
    return_book = StateTransition()

    def default_select_borrowing(self, name):
        Borrowing = Pool().get('library.user.borrowing')
        user = None
        borrowings = []
        if Transaction().context.get('active_model') == 'library.user':
            user = Transaction().context.get('active_id')
            borrowings = [x for x in Borrowing.search([
                        ('user', '=', user), ('return_date', '=', None)])]
        elif (Transaction().context.get('active_model') ==
                'library.user.borrowing'):
            borrowings = Borrowing.browse(
                Transaction().context.get('active_ids'))
            if len({x.user for x in borrowings}) != 1:
                raise UserError('multiple_users',
                                'You cannot return books from different '
                                'users at once')
            if any(x.is_available for x in borrowings):
                raise UserError('available',
                                'Cannot return an available exemplary')
            user = borrowings[0].user.id
        return {
            'user': user,
            'borrowings': [x.id for x in borrowings],
            'return_date': datetime.date.today(),
            }

    def transition_return_book(self):
        Borrowing = Pool().get('library.user.borrowing')
        Borrowing.write(list(self.select_borrowing.borrowings), {
                'return_date': self.select_borrowing.return_date})
        return 'end'


class ReturnSelectedBook(ModelView):
    'Return Selected Book'
    __name__ = 'library.user.return_book.selected_book'

    user = fields.Many2One('library.user', 'User', required=True)
    borrowings = fields.Many2Many('library.user.borrowing', None, None,
        'Borrowings', domain=[('user', '=', Eval('user')),
                              ('return_date', '=', None)])
    return_date = fields.Date('Date', required=True, domain=[('return_date',
                                                             '<=', Date())])
