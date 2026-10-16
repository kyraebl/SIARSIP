import json

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Kategori


class KategoriOrderingTests(TestCase):
    def test_categories_follow_manual_order(self):
        Kategori.objects.create(kode="BB", nama="Kedua", urutan=1)
        Kategori.objects.create(kode="AA", nama="Pertama", urutan=0)

        self.assertEqual(
            list(Kategori.objects.values_list("kode", flat=True)),
            ["AA", "BB"],
        )

    def test_admin_can_save_dragged_order(self):
        first = Kategori.objects.create(kode="AA", urutan=0)
        second = Kategori.objects.create(kode="BB", urutan=1)
        admin_user = get_user_model().objects.create_superuser(
            username="superadmin",
            email="admin@example.com",
            password="test-password",
        )
        self.client.force_login(admin_user)

        response = self.client.post(
            reverse("admin:master_kategori_reorder"),
            data=json.dumps({"ids": [second.pk, first.pk]}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            list(Kategori.objects.values_list("pk", flat=True)),
            [second.pk, first.pk],
        )

    def test_admin_changelist_includes_drag_controls(self):
        Kategori.objects.create(kode="AA")
        admin_user = get_user_model().objects.create_superuser(
            username="superadmin",
            email="admin@example.com",
            password="test-password",
        )
        self.client.force_login(admin_user)

        response = self.client.get(reverse("admin:master_kategori_changelist"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "master/kategori-sort.js")
        self.assertContains(response, "kategori-drag-handle")

    def test_admin_rejects_incomplete_order(self):
        category = Kategori.objects.create(kode="AA")
        admin_user = get_user_model().objects.create_superuser(
            username="superadmin",
            email="admin@example.com",
            password="test-password",
        )
        self.client.force_login(admin_user)

        response = self.client.post(
            reverse("admin:master_kategori_reorder"),
            data=json.dumps({"ids": []}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        category.refresh_from_db()
        self.assertEqual(category.urutan, 0)
