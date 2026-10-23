import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('accounts', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Kategori',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('kode', models.CharField(max_length=5, unique=True)),
                ('nama', models.CharField(blank=True, max_length=100)),
            ],
            options={
                'verbose_name_plural': 'Kategori klasifikasi',
                'ordering': ['kode'],
            },
        ),
        migrations.CreateModel(
            name='KodeTujuan',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('kode', models.CharField(max_length=10, unique=True)),
                ('nama_jabatan', models.CharField(max_length=150)),
            ],
            options={
                'verbose_name_plural': 'Kode tujuan',
                'ordering': ['kode'],
            },
        ),
        migrations.CreateModel(
            name='Pengesah',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('jabatan', models.CharField(default='Kepala Sub Bagian Tata Usaha', max_length=150)),
                ('nama', models.CharField(max_length=100)),
                ('nip', models.CharField(blank=True, max_length=30)),
                ('unit_kerja', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='accounts.unitkerja')),
            ],
            options={
                'verbose_name_plural': 'Pengesah',
            },
        ),
    ]
