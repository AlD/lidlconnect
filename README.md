# lidlconnect

## Usage

### Initialize
```py
In [1]: import lidlconnect

In [2]: lidl = lidlconnect.LIDLConnect(
   ...:     username="01520123456789", password="123456"
   ...: )
```

### Current balance

```py
In [1]: lidl.balance
Out[1]: 8.86
```

### Available tariffs

```py
In [1]: [ (t['name'], t['tariffoptionId']) for t in lidl.tariffs ]
Out[1]:
[('DayFlat', 'CCS_92016'),
 ('DayFlat 100', 'CCS_92038'),
 ('Internetoption 500 MB', 'CCS_92001'),
 ('Internetoption 1 GB', 'CCS_92002'),
 ('Minuten-Option 100', 'CCS_92008'),
 ('Community-Flatrate', 'CCS_92009'),
 ('Festnetz-Flatrate', 'CCS_92003')]
```

### Booked tariffs

```py
In [1]: lidl.booked_tariffs
Out[1]:
[{'automaticExtension': False,
  'tariffoptionId': 'CCS_92008',
  'name': 'Minuten-Option 100',
  'price': 199,
  'duration': {'amount': 14, 'unit': 'DAY'},
  'statusKey': 'CDL',
  'startOfRuntime': '2022-12-20T00:00:00+01:00',
  'endOfRuntime': '2023-01-03T00:00:00+01:00',
  'possibleChangingDate': '03.01.2023',
  'buttonText': 'Kündbar zum 03.01.2023',
  'cancelable': False,
  'formattedPrice': '1,99 €',
  'restrictedService': False,
  'tariffState': 'Gültig bis 03.01.2023'}]
```

### Book something

```py
logging.basicConfig(level=logging.INFO)

lidl.buy_tariff_option(name="Minuten-Option 100")
```

> INFO:root:Nothing to do, available balance is: 71/100
