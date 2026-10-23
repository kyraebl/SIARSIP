from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('master', '0002_kategori_urutan'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='kodetujuan',
            options={'ordering': ['kode'], 'verbose_name_plural': 'Pejabat penandatanganan'},
        ),
    ]
