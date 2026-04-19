from django.db import migrations
from pgvector.django import VectorExtension, VectorField


class Migration(migrations.Migration):
    dependencies = [
        ("ai", "0001_initial"),
    ]

    operations = [
        VectorExtension(),
        migrations.AddField(
            model_name="knowledgechunkmodel",
            name="embedding",
            field=VectorField(blank=True, dimensions=1536, null=True),
        ),
    ]
