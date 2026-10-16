from django.db import migrations, models


def set_initial_order(apps, schema_editor):
    Kategori = apps.get_model("master", "Kategori")
    for position, kategori in enumerate(Kategori.objects.order_by("kode")):
        Kategori.objects.filter(pk=kategori.pk).update(urutan=position)


class Migration(migrations.Migration):

    dependencies = [
        ("master", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="kategori",
            name="urutan",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.RunPython(set_initial_order, migrations.RunPython.noop),
        migrations.AlterModelOptions(
            name="kategori",
            options={
                "ordering": ["urutan", "kode"],
                "verbose_name_plural": "Kategori klasifikasi",
            },
        ),
    ]
