from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("academics", "0005_update_diagnosis_levels"),
    ]

    operations = [
        migrations.AddField(
            model_name="evaluation",
            name="answers",
            field=models.JSONField(blank=True, null=True),
        ),
    ]
