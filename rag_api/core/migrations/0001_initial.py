"""Initial migration for RAG models."""
from django.db import migrations, models
import django.contrib.postgres.fields
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Repository',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('owner', models.CharField(max_length=255)),
                ('name', models.CharField(max_length=255)),
                ('url', models.URLField()),
                ('branch', models.CharField(default='main', max_length=255)),
                ('last_indexed', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'indexes': [
                    models.Index(fields=['owner', 'name'], name='owner_name_idx'),
                    models.Index(fields=['last_indexed'], name='last_indexed_idx'),
                ],
                'unique_together': {('owner', 'name')},
            },
        ),
        migrations.CreateModel(
            name='Document',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('file_path', models.TextField()),
                ('content', models.TextField()),
                ('file_type', models.CharField(max_length=50)),
                ('sha256_hash', models.CharField(max_length=64, unique=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('repository', models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='documents', to='core.repository')),
            ],
            options={
                'indexes': [
                    models.Index(fields=['repository', 'file_path'], name='repo_path_idx'),
                    models.Index(fields=['sha256_hash'], name='hash_idx'),
                    models.Index(fields=['file_type'], name='filetype_idx'),
                ],
            },
        ),
        migrations.CreateModel(
            name='Chunk',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('content', models.TextField()),
                ('chunk_index', models.IntegerField()),
                ('start_line', models.IntegerField(blank=True, null=True)),
                ('end_line', models.IntegerField(blank=True, null=True)),
                ('token_count', models.IntegerField(default=0)),
                ('bm25_tokens', django.contrib.postgres.fields.ArrayField(base_field=models.CharField(max_length=255), default=list, size=None)),
                ('bm25_term_frequencies', models.JSONField(default=dict)),
                ('embedding_id', models.CharField(blank=True, max_length=36, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('document', models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='chunks', to='core.document')),
            ],
            options={
                'indexes': [
                    models.Index(fields=['document', 'chunk_index'], name='doc_chunk_idx'),
                    models.Index(fields=['embedding_id'], name='embedding_idx'),
                ],
                'unique_together': {('document', 'chunk_index')},
            },
        ),
        migrations.CreateModel(
            name='BM25Index',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('idf_map', models.JSONField(default=dict)),
                ('num_docs', models.IntegerField(default=0)),
                ('avg_doc_len', models.FloatField(default=0.0)),
                ('last_updated', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name_plural': 'BM25 Indexes',
            },
        ),
        migrations.CreateModel(
            name='QueryLog',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('query_text', models.TextField()),
                ('top_k', models.IntegerField(default=5)),
                ('hybrid_weight_bm25', models.FloatField(default=0.3)),
                ('hybrid_weight_vector', models.FloatField(default=0.7)),
                ('execution_time_ms', models.IntegerField()),
                ('result_count', models.IntegerField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'indexes': [
                    models.Index(fields=['created_at'], name='query_date_idx'),
                ],
            },
        ),
        migrations.CreateModel(
            name='QueryResult',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('rank', models.IntegerField()),
                ('bm25_score', models.FloatField(default=0.0)),
                ('vector_score', models.FloatField(default=0.0)),
                ('hybrid_score', models.FloatField(default=0.0)),
                ('rerank_score', models.FloatField(default=0.0)),
                ('chunk', models.ForeignKey(on_delete=models.deletion.CASCADE, to='core.chunk')),
                ('query_log', models.ForeignKey(on_delete=models.deletion.CASCADE, to='core.querylog')),
            ],
            options={
                'indexes': [
                    models.Index(fields=['query_log', 'rank'], name='query_rank_idx'),
                ],
                'unique_together': {('query_log', 'chunk', 'rank')},
            },
        ),
        migrations.AddField(
            model_name='querylog',
            name='chunks_retrieved',
            field=models.ManyToManyField(through='core.QueryResult', to='core.chunk'),
        ),
    ]
