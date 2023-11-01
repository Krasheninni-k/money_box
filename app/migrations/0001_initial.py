# Generated by Django 3.2.16 on 2023-10-25 22:17

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Category',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=256, verbose_name='Статья расходов')),
            ],
            options={
                'verbose_name': 'Статья расходов',
                'verbose_name_plural': 'Статьи расходов',
            },
        ),
        migrations.CreateModel(
            name='Payments',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateTimeField(blank=True, verbose_name='Дата платежа')),
                ('amount', models.DecimalField(blank=True, decimal_places=2, default=0, max_digits=8, null=True, verbose_name='Сумма')),
                ('description', models.CharField(max_length=256, verbose_name='Описание')),
                ('category', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='app.category', verbose_name='Статья расходов')),
            ],
            options={
                'verbose_name': 'Расход',
                'verbose_name_plural': 'Расходы',
                'ordering': ['-date'],
            },
        ),
    ]
