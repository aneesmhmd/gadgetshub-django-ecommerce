# Generated by Django 4.1.7 on 2023-03-27 17:08

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0008_alter_order_ordered_date'),
    ]

    operations = [
        migrations.AlterField(
            model_name='orderitem',
            name='order_status',
            field=models.CharField(choices=[('Ordered', 'Ordered'), ('Shipped', 'Shipped'), ('Delivered', 'Delivered'), ('Cancelled', 'Cancelled'), ('Refunded', 'Refunded')], default='Ordered', max_length=20),
        ),
    ]
