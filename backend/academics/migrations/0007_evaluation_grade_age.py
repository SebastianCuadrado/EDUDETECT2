from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("academics", "0006_evaluation_answers"),
    ]

    operations = [
        migrations.AddField(
            model_name="evaluation",
            name="student_grade",
            field=models.PositiveSmallIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="evaluation",
            name="student_age",
            field=models.IntegerField(blank=True, null=True),
        ),
    ]
