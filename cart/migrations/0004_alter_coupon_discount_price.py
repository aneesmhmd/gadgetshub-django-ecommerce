# Generated by Django 4.1.7 on 2023-03-18 10:09

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cart', '0003_cartitem_variant_alter_cart_user'),
    ]

    operations = [
        migrations.AlterField(
            model_name='coupon',
            name='discount_price',
            field=models.PositiveIntegerField(default=799),
        ),
    ]