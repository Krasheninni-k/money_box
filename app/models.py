from django.db import models

class Category(models.Model):
    title = models.CharField('Статья расходов', max_length=256)

    class Meta:
        verbose_name = 'Статья расходов'
        verbose_name_plural = 'Статьи расходов'

    def __str__(self):
        return self.title


class Payments(models.Model):
    date = models.DateField('Дата платежа', blank=True)
    amount = models.DecimalField(
        'Сумма', max_digits=8, decimal_places=2,
        null=True, blank=True, default=0)
    description = models.CharField('Описание', max_length=256)
    category = models.ForeignKey(
        Category, on_delete=models.SET_NULL,
        verbose_name='Статья расходов', null=True)

    class Meta:
        verbose_name = 'Расход'
        verbose_name_plural = 'Расходы'
        ordering = ['-date']

    def __str__(self):
        date = self.date.strftime('%Y-%m-%d')
        return f'{date} - {self.amount} - {self.description}'
