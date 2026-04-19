# Generated manually for dynamic category status support.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="categorymodel",
            name="status",
            field=models.CharField(
                choices=[("active", "ACTIVE"), ("inactive", "INACTIVE")],
                db_index=True,
                default="active",
                max_length=20,
            ),
        ),
        migrations.AddIndex(
            model_name="categorymodel",
            index=models.Index(fields=["status"], name="catalog_cat_status_5c8ad2_idx"),
        ),
        migrations.RunSQL(
            sql="""
                UPDATE catalog_category
                SET status = CASE
                    WHEN is_active = TRUE THEN 'active'
                    ELSE 'inactive'
                END
            """,
            reverse_sql="""
                UPDATE catalog_category
                SET is_active = CASE
                    WHEN status = 'active' THEN TRUE
                    ELSE FALSE
                END
            """,
        ),
    ]

