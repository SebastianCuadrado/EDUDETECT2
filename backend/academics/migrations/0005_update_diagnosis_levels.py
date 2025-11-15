from django.db import migrations, models


def map_old_to_new(apps, schema_editor):
    Evaluation = apps.get_model('academics', 'Evaluation')
    mapping = {
        'DISLEXIA': 'ALTO',
        'RIESGO': 'MEDIO',
        'NORMAL': 'BAJO',
    }
    for old, new in mapping.items():
        Evaluation.objects.filter(diagnosis=old).update(diagnosis=new)


class Migration(migrations.Migration):
    dependencies = [
        ('academics', '0004_student_slim_fields'),
    ]

    operations = [
        migrations.AlterField(
            model_name='evaluation',
            name='diagnosis',
            field=models.CharField(
                choices=[
                    ('BAJO', 'Menos del 60% (Nivel Bajo)'),
                    ('MEDIO', 'Entre 60% - 85% (Nivel Medio)'),
                    ('ALTO', 'Más del 85% (Nivel Alto)')
                ],
                max_length=20,
            ),
        ),
        migrations.RunPython(map_old_to_new, migrations.RunPython.noop),
    ]

