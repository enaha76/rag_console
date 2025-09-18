"""
Initial schema

Revision ID: 20250918_000001
Revises: 
Create Date: 2025-09-18 00:00:01
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20250918_000001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Users
    op.create_table(
        'users',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('email', sa.String(length=255), nullable=False, unique=True, index=True),
        sa.Column('username', sa.String(length=100), nullable=False),
        sa.Column('hashed_password', sa.String(length=255), nullable=False),
        sa.Column('llm_provider', sa.String(length=50), server_default='openai'),
        sa.Column('llm_model', sa.String(length=100), server_default='gpt-3.5-turbo'),
        sa.Column('embedding_model', sa.String(length=100), server_default='sentence-transformers/all-MiniLM-L6-v2'),
        sa.Column('role', sa.String(length=50), server_default='user'),
        sa.Column('permissions', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('1')),
        sa.Column('email_verified', sa.Boolean(), server_default=sa.text('0')),
        sa.Column('last_login', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )

    # Documents
    op.create_table(
        'documents',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('user_id', sa.String(length=36), sa.ForeignKey('users.id'), nullable=False, index=True),
        sa.Column('filename', sa.String(length=255), nullable=False),
        sa.Column('original_filename', sa.String(length=255), nullable=False),
        sa.Column('content_type', sa.String(length=100), nullable=False),
        sa.Column('file_size', sa.Integer(), nullable=False),
        sa.Column('file_path', sa.String(length=500), nullable=False),
        sa.Column('status', sa.String(length=50), server_default='uploaded', index=True),
        sa.Column('total_chunks', sa.Integer(), server_default='0'),
        sa.Column('processed_chunks', sa.Integer(), server_default='0'),
        sa.Column('title', sa.String(length=500), nullable=True),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('language', sa.String(length=10), server_default='en'),
        sa.Column('word_count', sa.Integer(), server_default='0'),
        sa.Column('collection_name', sa.String(length=100), nullable=True),
        sa.Column('embedding_model', sa.String(length=100), nullable=True),
        sa.Column('doc_metadata', sa.JSON(), nullable=True),
        sa.Column('tags', sa.JSON(), nullable=True),
        sa.Column('uploaded_at', sa.DateTime(), nullable=False),
        sa.Column('processed_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )

    # Document Chunks
    op.create_table(
        'document_chunks',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('document_id', sa.String(length=36), sa.ForeignKey('documents.id'), nullable=False, index=True),
        sa.Column('user_id', sa.String(length=36), sa.ForeignKey('users.id'), nullable=False, index=True),
        sa.Column('chunk_index', sa.Integer(), nullable=False),
        sa.Column('text_content', sa.Text(), nullable=False),
        sa.Column('chunk_size', sa.Integer(), nullable=False),
        sa.Column('start_char', sa.Integer(), nullable=True),
        sa.Column('end_char', sa.Integer(), nullable=True),
        sa.Column('page_number', sa.Integer(), nullable=True),
        sa.Column('vector_id', sa.String(length=100), nullable=True, index=True),
        sa.Column('embedding_model', sa.String(length=100), nullable=True),
        sa.Column('embedding_dimension', sa.Integer(), nullable=True),
        sa.Column('last_similarity_score', sa.Float(), nullable=True),
        sa.Column('doc_metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )

    # Queries
    op.create_table(
        'queries',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('user_id', sa.String(length=36), sa.ForeignKey('users.id'), nullable=False, index=True),
        sa.Column('query_text', sa.Text(), nullable=False),
        sa.Column('query_type', sa.String(length=50), server_default='search'),
        sa.Column('processing_time_ms', sa.Float(), nullable=True),
        sa.Column('status', sa.String(length=50), server_default='completed', index=True),
        sa.Column('retrieved_chunks_count', sa.Integer(), server_default='0'),
        sa.Column('retrieved_documents', sa.JSON(), nullable=True),
        sa.Column('similarity_threshold', sa.Float(), server_default='0.7'),
        sa.Column('llm_provider', sa.String(length=50), nullable=True),
        sa.Column('llm_model', sa.String(length=100), nullable=True),
        sa.Column('prompt_template', sa.Text(), nullable=True),
        sa.Column('input_tokens', sa.Integer(), server_default='0'),
        sa.Column('output_tokens', sa.Integer(), server_default='0'),
        sa.Column('total_tokens', sa.Integer(), server_default='0'),
        sa.Column('estimated_cost', sa.Float(), server_default='0.0'),
        sa.Column('user_rating', sa.Integer(), nullable=True),
        sa.Column('feedback', sa.Text(), nullable=True),
        sa.Column('session_id', sa.String(length=100), nullable=True, index=True),
        sa.Column('conversation_turn', sa.Integer(), server_default='1'),
        sa.Column('query_metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )

    # Query Responses
    op.create_table(
        'query_responses',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('query_id', sa.String(length=36), sa.ForeignKey('queries.id'), nullable=False, unique=True, index=True),
        sa.Column('response_text', sa.Text(), nullable=False),
        sa.Column('response_format', sa.String(length=50), server_default='text'),
        sa.Column('context_used', sa.Text(), nullable=True),
        sa.Column('context_chunks', sa.JSON(), nullable=True),
        sa.Column('confidence_score', sa.Float(), nullable=True),
        sa.Column('source_attribution', sa.JSON(), nullable=True),
        sa.Column('contains_citations', sa.Boolean(), server_default=sa.text('0')),
        sa.Column('fact_checked', sa.Boolean(), server_default=sa.text('0')),
        sa.Column('is_cached', sa.Boolean(), server_default=sa.text('0')),
        sa.Column('cache_hit', sa.Boolean(), server_default=sa.text('0')),
        sa.Column('generated_at', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table('query_responses')
    op.drop_table('queries')
    op.drop_table('document_chunks')
    op.drop_table('documents')
    op.drop_table('users')
