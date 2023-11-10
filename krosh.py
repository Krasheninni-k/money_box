from datetime import datetime, timedelta

date = None

if not date:
    target_date = datetime.now().date() - timedelta(days=1)
    print('ok')
    print(target_date)
else:
    target_date = date
    date_format = '%d.%m.%Y'
    target_date = datetime.strptime(target_date, date_format).date()
    print(target_date)