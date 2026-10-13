"""baseline

The six tables as the models define them, before any migration existed.

A database that the service already created (init_db() builds the same tables) has all of this. Do not run it
there. Mark that database as being at this revision instead: `alembic stamp 0001`.

Revision ID: 0001
Revises: 
Create Date: 2026-10-13
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0001'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('advertiser',
    sa.Column('advertiserid', sa.String(), nullable=False),
    sa.Column('advertisername', sa.String(), nullable=True),
    sa.Column('industry', sa.String(), nullable=True),
    sa.Column('brands', sa.String(), nullable=True),
    sa.Column('contactinfo', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('advertisertype', sa.String(), nullable=True),
    sa.Column('createdby', sa.String(), nullable=True),
    sa.Column('updatedby', sa.String(), nullable=True),
    sa.Column('createdat', sa.DateTime(), nullable=True),
    sa.Column('updatedat', sa.DateTime(), nullable=True),
    sa.Column('advertiserstate', sa.String(), nullable=True),
    sa.PrimaryKeyConstraint('advertiserid')
    )
    op.create_table('publisher',
    sa.Column('publisherid', sa.String(), nullable=False),
    sa.Column('publishername', sa.String(), nullable=True),
    sa.Column('contactinfo', sa.JSON(), nullable=True),
    sa.Column('publisherstate', sa.String(), nullable=True),
    sa.Column('publisherdomain', sa.String(), nullable=True),
    sa.Column('createdby', sa.String(), nullable=True),
    sa.Column('updatedby', sa.String(), nullable=True),
    sa.Column('createdat', sa.DateTime(), nullable=True),
    sa.Column('updatedat', sa.DateTime(), nullable=True),
    sa.Column('preference', sa.JSON(), nullable=True),
    sa.PrimaryKeyConstraint('publisherid')
    )
    op.create_table('adunit',
    sa.Column('adunitid', sa.String(), nullable=False),
    sa.Column('adunittype', sa.String(), nullable=True),
    sa.Column('adunitname', sa.String(), nullable=True),
    sa.Column('publisherid', sa.String(), nullable=False),
    sa.Column('adunitstate', sa.String(), nullable=True),
    sa.Column('createdby', sa.String(), nullable=True),
    sa.Column('updatedby', sa.String(), nullable=True),
    sa.Column('createdat', sa.DateTime(), nullable=True),
    sa.Column('updatedat', sa.DateTime(), nullable=True),
    sa.Column('preference', sa.JSON(), nullable=True),
    sa.ForeignKeyConstraint(['publisherid'], ['publisher.publisherid'], ),
    sa.PrimaryKeyConstraint('adunitid')
    )
    op.create_table('campaign',
    sa.Column('campaignid', sa.String(), nullable=False),
    sa.Column('campaignname', sa.String(), nullable=True),
    sa.Column('advertiserid', sa.String(), nullable=False),
    sa.Column('startdate', sa.DateTime(), nullable=True),
    sa.Column('enddate', sa.DateTime(), nullable=True),
    sa.Column('budget', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('frequencycaps', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('createdat', sa.DateTime(), nullable=True),
    sa.Column('updatedat', sa.DateTime(), nullable=True),
    sa.Column('createdby', sa.String(), nullable=True),
    sa.Column('updatedby', sa.String(), nullable=True),
    sa.Column('campaignstate', sa.String(), nullable=True),
    sa.ForeignKeyConstraint(['advertiserid'], ['advertiser.advertiserid'], ),
    sa.PrimaryKeyConstraint('campaignid')
    )
    op.create_table('creative',
    sa.Column('creativeid', sa.String(), nullable=False),
    sa.Column('creativetype', sa.String(), nullable=True),
    sa.Column('creativename', sa.String(), nullable=True),
    sa.Column('creativestate', sa.String(), nullable=True),
    sa.Column('advertiserid', sa.String(), nullable=False),
    sa.Column('createdby', sa.String(), nullable=True),
    sa.Column('updatedby', sa.String(), nullable=True),
    sa.Column('createdat', sa.DateTime(), nullable=True),
    sa.Column('updatedat', sa.DateTime(), nullable=True),
    sa.Column('assets', sa.JSON(), nullable=True),
    sa.ForeignKeyConstraint(['advertiserid'], ['advertiser.advertiserid'], ),
    sa.PrimaryKeyConstraint('creativeid')
    )
    op.create_table('ads',
    sa.Column('adid', sa.String(), nullable=False),
    sa.Column('adname', sa.String(), nullable=True),
    sa.Column('campaignid', sa.String(), nullable=False),
    sa.Column('advertiserid', sa.String(), nullable=False),
    sa.Column('creativeid', sa.String(), nullable=True),
    sa.Column('startdate', sa.DateTime(), nullable=True),
    sa.Column('enddate', sa.DateTime(), nullable=True),
    sa.Column('landingurl', sa.String(), nullable=True),
    sa.Column('budget', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('frequencycaps', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('bidinfo', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('adtype', sa.String(), nullable=True),
    sa.Column('adpriority', sa.Integer(), nullable=True),
    sa.Column('targetinginfo', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('createdat', sa.DateTime(), nullable=True),
    sa.Column('updatedat', sa.DateTime(), nullable=True),
    sa.Column('createdby', sa.String(), nullable=True),
    sa.Column('updatedby', sa.String(), nullable=True),
    sa.Column('adstate', sa.String(), nullable=True),
    sa.Column('ad_unit_targeted', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.ForeignKeyConstraint(['advertiserid'], ['advertiser.advertiserid'], ),
    sa.ForeignKeyConstraint(['campaignid'], ['campaign.campaignid'], ),
    sa.PrimaryKeyConstraint('adid')
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('ads')
    op.drop_table('creative')
    op.drop_table('campaign')
    op.drop_table('adunit')
    op.drop_table('publisher')
    op.drop_table('advertiser')
