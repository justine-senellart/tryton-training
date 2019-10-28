from trytond.model import ModelSQL, ModelView

__all__ = [
        'Genre',
        'Editor',
        'Author',
        'Book',
        'Exemplaries',
        ]

class Genre(ModelSQL, ModelView):
    'Genre'
    __name__ = 'library.genre'

class Editor(ModelSQL, ModelView):
    'Editor'
    __name__ = 'library.editor'

class Author(ModelSQL, ModelView):
    'Author'
    __name__ = 'library.author'

class Book(ModelSQL, ModelView):
    'Book'
    __name__ = 'library.book'

class Exemplaries(ModelSQL, ModelView):
    'Exemplaries'
    __name__ = 'library.book.exemplaries'
