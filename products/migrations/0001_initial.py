# Generated migration for Product model

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Product',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(db_index=True, max_length=255)),
                ('category', models.CharField(db_index=True, max_length=100)),
                ('price', models.DecimalField(decimal_places=2, max_digits=10)),
                ('updated_at', models.DateTimeField()),
                ('external_id', models.CharField(db_index=True, max_length=64, unique=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('modified_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'ordering': ['-updated_at'],
            },
        ),
        migrations.AddIndex(
            model_name='product',
            index=models.Index(fields=['category', 'price'], name='products_pr_categor_idx'),
        ),
    ]
