from money_box.wsgi import *
from app.models import Payments

description_1 = 'альмак'
description_2 = 'Альмак'

category = Payments.objects.filter(description__iregex=description_1)
print(category)