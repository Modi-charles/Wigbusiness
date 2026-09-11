from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("sales", "0005_salereturn_approval_note_salereturn_approved_at_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="salereturn",
            name="rejection_reason",
            field=models.TextField(blank=True),
        ),
    ]