from cix import CustomIndex
import pandas as pd


# basic expression
idx1 = CustomIndex('2 * (5 + 3)')

print(idx1.evaluate())


df = pd.DataFrame({'A': [1, 2, 3], 'B': [4, 5, 6]}, index=pd.bdate_range('2019-07-04', periods=3))

idx2 = CustomIndex('{A} + 2')
print(idx2.evaluate(data=df))


# simple expression
idx3 = CustomIndex('{A} - {B}')

print("Ticker dependencies:", idx3.tickers)

# valid index expression
idx4 = CustomIndex('2 + {A} * ({B} + 3)')

print("Ticker dependencies:", idx4.tickers)


# invalid
try:
    idx5 = CustomIndex('2 + A')
except ValueError as e:
    print(e)
    pass

