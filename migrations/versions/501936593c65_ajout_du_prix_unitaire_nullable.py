"""Ajout du prix unitaire nullable

Revision ID: 501936593c65
Revises: 46e362d2b586
Create Date: 2025-05-22 13:12:32.822894

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '501936593c65'
down_revision = '46e362d2b586'
branch_labels = None
depends_on = None


def upgrade():
    # 1. Ajouter la colonne prix_unitaire en nullable
    with op.batch_alter_table('produit') as batch_op:
        batch_op.add_column(sa.Column('prix_unitaire', sa.Float(), nullable=True))

    # 2. Mettre à jour toutes les lignes existantes avec une valeur par défaut (ex: 0.0)
    op.execute('UPDATE produit SET prix_unitaire = 0.0 WHERE prix_unitaire IS NULL')

    # 3. Modifier la colonne pour la rendre NOT NULL
    with op.batch_alter_table('produit') as batch_op:
        batch_op.alter_column('prix_unitaire', nullable=False)

def downgrade():
    with op.batch_alter_table('produit') as batch_op:
        batch_op.drop_column('prix_unitaire')
