domain=[If (~Eval('B') | ~Eval('C'),
            [('A', '=', '0')],
            If (Eval('B') > Eval('C'),
                 [('A', '>', '0')],
                 []
       ))]


domain=[OR ('x', '>=', Eval('B')), ('x', '=', Eval('C'))]
