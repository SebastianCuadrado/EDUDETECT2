from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("academics", "0002_classroom_name"),
    ]

    operations = [
        migrations.AddField(
            model_name="student",
            name="photo",
            field=models.ImageField(upload_to="students/", null=True, blank=True),
        ),
    ]

