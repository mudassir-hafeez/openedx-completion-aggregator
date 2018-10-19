# -*- coding: utf-8 -*-
# Generated by Django 1.10.8 on 2018-10-18 00:13
from __future__ import unicode_literals

from django.db import migrations, models
import django.utils.timezone
import model_utils.fields
import opaque_keys.edx.django.models
import six


BATCH_SIZE = 1000


def copy_data(apps, schema_editor):
    """
    Add indexes to completion_aggregator_stalecompletion without locking.

    Copy data into the new stalecompletionnew table in batches, then rename
    both tables, then do a final copy of any new data that came in.
    """

    copy_sql_tmpl = """
        INSERT INTO %(target)s (`created`, `modified`, `username`, `course_key`, `block_key`, `force`, `resolved`)
            SELECT `created`, `modified`, `username`, `course_key`, `block_key`, `force`, `resolved`
                FROM %(source)s
                WHERE id > %%s
                ORDER BY id
                LIMIT %%s OFFSET %%s
    """
    StaleCompletion = apps.get_model("completion_aggregator", "StaleCompletion")
    cursor = schema_editor.connection.cursor()
    max_id = StaleCompletion.objects.order_by('-id')[0].id
    count = StaleCompletion.objects.count()
    copy_sql = copy_sql_tmpl % {
        'source': 'completion_aggregator_stalecompletion',
        'target': 'completion_aggregator_stalecompletionnew',
    }
    for offset in six.moves.range(0, count, BATCH_SIZE):
        cursor.execute(copy_sql, [0, BATCH_SIZE, offset])
        if offset % 100000 == 0:
            print("Transferred {} records at {}".format(offset, django.utils.timezone.now()))


    cursor.execute(
        """
        RENAME TABLE
            completion_aggregator_stalecompletion TO completion_aggregator_stalecompletionold,
            completion_aggregator_stalecompletionnew TO completion_aggregator_stalecompletion
        """
    )
    cursor.execute(
        """
        SELECT COUNT(*)
            FROM completion_aggregator_stalecompletionold
            WHERE id > %s
        """,
        [max_id]
    )
    end_count = cursor.fetchone()[0]

    copy_sql = copy_sql_tmpl % {
        'source': 'completion_aggregator_stalecompletionold',
        'target': 'completion_aggregator_stalecompletion',
    }
    for offset in six.moves.range(0, end_count, BATCH_SIZE):
        cursor.execute(copy_sql, [max_id, BATCH_SIZE, offset])


class Migration(migrations.Migration):

    dependencies = [
        ('completion_aggregator', '0003_stalecompletion'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.CreateModel(
                    name='StaleCompletionNew',
                    fields=[
                        ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                        ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                        ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                        ('username', models.CharField(max_length=255)),
                        ('course_key', opaque_keys.edx.django.models.CourseKeyField(max_length=255)),
                        ('block_key', opaque_keys.edx.django.models.UsageKeyField(blank=True, max_length=255, null=True)),
                        ('force', models.BooleanField(default=False)),
                        ('resolved', models.BooleanField(default=False)),
                    ],
                ),
                migrations.AlterIndexTogether(
                    name='stalecompletionnew',
                    index_together=set([('username', 'course_key', 'created', 'resolved')]),
                ),
                migrations.RunPython(copy_data)
            ],
            state_operations=[
                migrations.AlterIndexTogether(
                    name='stalecompletion',
                    index_together=set([('username', 'course_key', 'created', 'resolved')]),
                )
            ],
        )
    ]
