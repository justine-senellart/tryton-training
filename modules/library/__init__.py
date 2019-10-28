from trytond.pool import Pool
import library

def register():
    Pool.register(
            library.Genre,
            library.Editor,
            library.Author,
            library.Book,
            library.Exemplaries,
            module='library', type_='model')

