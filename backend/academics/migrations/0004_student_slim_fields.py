from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("academics", "0003_student_photo"),
    ]

    operations = [
        migrations.RemoveField(model_name="student", name="dni"),
        migrations.RemoveField(model_name="student", name="birth_date"),
        migrations.RemoveField(model_name="student", name="email"),
        migrations.RemoveField(model_name="student", name="phone"),
        migrations.RemoveField(model_name="student", name="photo"),
        migrations.AddField(
            model_name="student",
            name="age",
            field=models.PositiveSmallIntegerField(null=True, blank=True),
        ),
    ]

