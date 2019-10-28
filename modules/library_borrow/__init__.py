from trytond.pool import Pool

from . import library
from . import wizard


def register():
    Pool.register(
        library.User,
        library.Borrowing,
        library.Book,
        library.Exemplary,
        wizard.BorrowSelectedBook,
        wizard.ReturnSelectedBook,
        module='library_borrow', type_='model')

    Pool.register(
        wizard.BorrowBook,
        wizard.ReturnBook,
        module='library_borrow', type_='wizard')
